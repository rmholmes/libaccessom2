
import pytest
from pathlib import Path
from jinja2 import Template
import random
import subprocess as sp
import json
import netCDF4 as nc
import numpy as np
from utils import create_nc_file

FORCING_FILE = "/g/data/ua8/JRA55-do/RYF/v1-3/RYF.rsds.1990_1991.nc"
FORCING_FIELDNAME = "rsds"
COUPLING_FIELDNAME = "swfld_ai"

forcing_tmpl = Template("""
{
  "description": "JRA55-do V1.3 RYF 1990-91 forcing",
  "inputs": [
    {
      "filename": "{{forcing_filename}}",
      "fieldname": "{{forcing_fieldname}}",
      "cname": "{{coupling_fieldname}}",
      "pertubations": [
        {{pertubation0}}
        {{pertubation1}}
      ]
    }
  ]
}""")

perturb_tmpl = Template("""
{
    "type": "{{type}}",
    "dimension": "{{dimension}}",
    "value": "{{value}}",
    "calendar": "{{calendar}}"
}""")


def get_forcing_field_shape():
    with nc.Dataset(FORCING_FILE) as f:
        return f.variables[FORCING_FIELDNAME].shape


class TestForcingPerturbations:

    def run_test(self, ptype, pdimension, pvalue, pcalendar):

        perturb_str = perturb_tmpl.render(type=ptype,
                                          dimension=pdimension,
                                          value=str(pvalue),
                                          calendar=pcalendar)

        with open('forcing.json', 'w') as f:
            s = forcing_tmpl.render(forcing_filename=FORCING_FILE,
                                    forcing_fieldname=FORCING_FIELDNAME,
                                    coupling_fieldname=COUPLING_FIELDNAME,
                                    pertubation0=perturb_str)
            f.write(s)

        # Read out a random time point to test against
        with nc.Dataset(FORCING_FILE) as f:
            time_var = f.variables['time']
            times = nc.num2date(time_var[:], time_var.units)
            tidx = random.randint(0, len(times))

            date_str = times[tidx].strftime('%Y-%m-%dT%H:%M:%S')
            src_data = f.variables[FORCING_FIELDNAME][tidx, :]

        # Run fortran code with given datetime
        ret = sp.run(['./forcing_test.exe', date_str])
        assert ret.returncode == 0

        # Read fortran code output
        assert Path('test_output.nc').exists()
        with nc.Dataset('test_output.nc') as f:
            dest_data = f.variables[FORCING_FIELDNAME][:]

        # Get the configured pertubation value
        if Path(str(pvalue)).exists():
            with nc.Dataset(pvalue) as f:
                perturb_array = f.variables[FORCING_FIELDNAME][:]
        else:
            perturb_array = int(pvalue)

        # Do the pertubation in Python code and check that it is as expected
        if ptype == 'scaling':
            assert np.allclose(src_data*perturb_array, dest_data)
        else:
            assert np.allclose(src_data+perturb_array, dest_data)


    @pytest.mark.parametrize("perturb_type", ['scaling', 'offset'])
    def test_spatiotemporal(self, perturb_type):
        """
        Test spatial scaling and offset
        """

        pass


    @pytest.mark.parametrize("perturb_type", ['scaling', 'offset'])
    def test_temporal(self, perturb_type):
        """
        Test temporal scaling and offset
        """

        pass



    @pytest.mark.parametrize("perturb_type", ['scaling', 'offset'])
    def test_spatial(self, perturb_type):
        """
        Test spatial scaling and offset
        """

        # Create 2d pertubation file
        perturb_value = './test_input.nc'

        shape =  get_forcing_field_shape()
        nx = shape[2]
        ny = shape[1]
        data_array = np.random.rand(ny, nx)
        create_nc_file(perturb_value, FORCING_FIELDNAME, data_array)

        self.run_test(perturb_type, 'spatial', perturb_value, 'forcing')


    @pytest.mark.parametrize("perturb_type", ['scaling', 'offset'])
    def test_constant(self, perturb_type):
        """
        Test constant scaling and offset
        """

        perturb_value = random.randint(0, 100)
        self.run_test(perturb_type, 'constant', perturb_value, 'forcing')

