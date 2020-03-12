"""AiiDA-ORCA output parser"""
import io
import os

from cclib import io
from cclib.parser.utils import PeriodicTable

import pymatgen as mp

from aiida.parsers import Parser
from aiida.common import OutputParsingError, NotExistent
from aiida.engine import ExitCode
from aiida.orm import Dict, StructureData


class OrcaBaseParser(Parser):
    """Basic AiiDA parser for the output of Orca"""

    def parse(self, **kwargs):
        """Receives in input a dictionary of retrieved nodes. Does all the logic here."""
        results = {}
        try:
            out_folder = self.retrieved
        except NotExistent:
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        fname = self.node.process_class._DEFAULT_OUTPUT_FILE  #pylint: disable=protected-access

        if fname not in out_folder._repository.list_object_names():  #pylint: disable=protected-access
            raise OutputParsingError("Orca output file not retrieved")

        outobj = io.ccread(os.path.join(out_folder._repository._get_base_folder().abspath, fname))  #pylint: disable=protected-access

        output_dict = outobj.getattributes()

        # Quick hack to remedy cclib issue.
        output_dict['metadata'].update({'comments': 'AiiDA-ORCA Plugin'})

        if 'Opt' in output_dict['metadata']['keywords']:
            optimized_xyz_str = io.xyzwriter.XYZ(outobj, firstgeom=False, lastgeom=True).generate_repr()
            optimized_structure = StructureData(pymatgen_molecule=mp.Molecule.from_str(optimized_xyz_str, 'xyz'))
            self.out("output_structure", optimized_structure)

        if 'atomcharges' in output_dict:
            results['atomchages_mulliken'] = output_dict['atomcharges']['mulliken'].tolist()
            results['atomchages_lowdin'] = output_dict['atomcharges']['lowdin'].tolist()
        results['MO_energies'] = output_dict['moenergies'][0].tolist()
        results['SCF_energies'] = output_dict['scfenergies'].tolist()

        pt = PeriodicTable()  #pylint: disable=invalid-name

        results['elements'] = [pt.element[Z] for Z in output_dict['atomnos'].tolist()]

        self.out("output_parameters", Dict(dict=results))

        return ExitCode(0)