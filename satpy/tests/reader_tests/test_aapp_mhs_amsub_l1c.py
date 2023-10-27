#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2021 Pytroll

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Test module for the MHS AAPP level-1c reader."""


import datetime
import tempfile
import unittest

import numpy as np

from satpy.readers.aapp_mhs_amsub_l1c import _HEADERTYPE, _SCANTYPE, HEADER_LENGTH, MHS_AMSUB_AAPPL1CFile
from satpy.tests.utils import make_dataid

SCANLINE1 = [[26798, 27487, 23584, 24816, 26196],
             [26188, 27392, 23453, 24832, 26223],
             [23777, 26804, 23529, 24876, 26193],
             [23311, 26781, 23583, 24898, 26157],
             [23194, 26737, 23743, 24917, 26199],
             [23811, 26871, 23836, 25017, 26239],
             [25000, 27034, 23952, 25118, 26247],
             [25937, 26988, 24019, 25058, 26143],
             [25986, 26689, 24048, 25081, 25967],
             [24689, 26083, 24062, 24975, 25744],
             [23719, 25519, 24016, 24938, 25617],
             [23327, 25565, 23882, 24960, 25571],
             [23214, 25646, 23862, 24847, 25561],
             [23473, 25886, 23859, 24832, 25640],
             [23263, 25449, 23759, 24730, 25525],
             [23335, 25672, 23716, 24727, 25578],
             [23477, 25983, 23771, 24847, 25882],
             [23141, 25863, 23758, 24971, 26066],
             [23037, 25813, 23855, 25113, 26231],
             [22908, 25701, 23958, 25130, 26226],
             [22608, 25493, 23980, 25223, 26277],
             [22262, 25275, 24019, 25356, 26247],
             [21920, 25116, 24161, 25375, 26268],
             [21559, 24795, 24169, 25351, 26284],
             [21269, 24591, 24333, 25503, 26300],
             [21028, 24395, 24413, 25498, 26300],
             [20887, 24254, 24425, 25479, 26228],
             [20882, 24288, 24440, 25463, 26284],
             [20854, 24261, 24569, 25438, 26266],
             [20911, 24277, 24564, 25464, 26213],
             [21069, 24369, 24567, 25473, 26211],
             [20994, 24201, 24747, 25552, 26130],
             [21909, 24648, 24856, 25546, 26249],
             [21936, 24662, 24843, 25612, 26207],
             [21142, 24248, 24885, 25616, 26159],
             [21180, 24251, 24817, 25553, 26114],
             [21236, 24219, 24840, 25569, 26100],
             [21057, 24152, 24735, 25535, 26093],
             [20825, 24018, 24830, 25528, 26103],
             [20731, 23866, 24789, 25579, 26117],
             [20924, 23972, 24808, 25512, 26082],
             [21228, 24259, 24723, 25501, 26071],
             [21307, 24285, 24733, 25491, 26058],
             [21558, 24521, 24739, 25511, 26009],
             [21562, 24500, 24706, 25538, 26091],
             [21568, 24448, 24639, 25504, 26011],
             [21636, 24520, 24673, 25462, 26028],
             [21895, 24667, 24662, 25494, 26048],
             [22251, 24892, 24570, 25435, 25977],
             [22459, 25109, 24557, 25340, 26010],
             [22426, 25030, 24533, 25310, 25964],
             [22419, 24966, 24528, 25316, 25953],
             [22272, 24851, 24503, 25318, 25891],
             [22261, 24799, 24548, 25326, 25912],
             [22445, 25023, 24410, 25333, 25930],
             [22371, 24902, 24381, 25323, 25892],
             [21791, 24521, 24407, 25362, 25880],
             [20930, 23820, 24440, 25287, 25849],
             [21091, 24008, 24412, 25251, 25854],
             [21575, 24331, 24405, 25272, 25774],
             [21762, 24545, 24395, 25216, 25763],
             [21891, 24550, 24317, 25256, 25790],
             [21865, 24584, 24250, 25205, 25797],
             [21431, 24178, 24302, 25228, 25738],
             [21285, 23978, 24240, 25205, 25735],
             [21935, 24515, 24232, 25240, 25834],
             [22372, 24790, 24325, 25311, 25878],
             [22621, 24953, 24410, 25395, 25897],
             [23642, 25290, 24456, 25428, 25959],
             [23871, 25209, 24376, 25369, 25976],
             [22846, 24495, 24378, 25347, 25868],
             [22490, 24320, 24327, 25374, 25849],
             [23237, 24599, 24182, 25298, 25839],
             [23134, 24601, 24121, 25306, 25864],
             [22647, 24314, 24108, 25248, 25787],
             [22499, 24293, 24049, 25165, 25823],
             [22247, 23987, 23936, 25131, 25742],
             [22291, 23942, 23908, 25028, 25715],
             [22445, 24205, 23784, 24997, 25615],
             [22487, 24417, 23764, 24921, 25643],
             [22386, 24420, 23765, 24865, 25715],
             [22217, 24326, 23748, 24823, 25617],
             [21443, 23814, 23722, 24750, 25552],
             [20354, 22599, 23580, 24722, 25439],
             [20331, 22421, 23431, 24655, 25389],
             [19925, 21855, 23412, 24623, 25284],
             [20240, 22224, 23339, 24545, 25329],
             [20368, 22596, 23419, 24474, 25362],
             [20954, 23192, 23345, 24416, 25403],
             [22292, 24303, 23306, 24330, 25353]]

ANGLES_SCLINE1 = [[5926, 35786,  7682, 23367],
                  [5769, 35780,  7709, 23352],
                  [5614, 35774,  7733, 23339],
                  [5463, 35769,  7756, 23326],
                  [5314, 35763,  7777, 23313],
                  [5167, 35758,  7797, 23302],
                  [5022, 35753,  7816, 23290],
                  [4879, 35747,  7834, 23280],
                  [4738, 35742,  7851, 23269],
                  [4598, 35737,  7868, 23259],
                  [4459, 35732,  7883, 23249],
                  [4321, 35727,  7899, 23240],
                  [4185, 35721,  7913, 23231],
                  [4049, 35716,  7927, 23222],
                  [3914, 35711,  7940, 23213],
                  [3780, 35706,  7953, 23204],
                  [3647, 35701,  7966, 23195],
                  [3515, 35695,  7978, 23187],
                  [3383, 35690,  7990, 23179],
                  [3252, 35685,  8001, 23170],
                  [3121, 35680,  8013, 23162],
                  [2991, 35674,  8023, 23154],
                  [2861, 35669,  8034, 23146],
                  [2732, 35663,  8045, 23138],
                  [2603, 35658,  8055, 23130],
                  [2474, 35652,  8065, 23122],
                  [2346, 35647,  8075, 23114],
                  [2218, 35641,  8084, 23106],
                  [2090, 35635,  8094, 23098],
                  [1963, 35630,  8103, 23090],
                  [1836, 35624,  8112, 23082],
                  [1709, 35618,  8121, 23074],
                  [1582, 35612,  8130, 23066],
                  [1455, 35605,  8139, 23057],
                  [1329, 35599,  8148, 23049],
                  [1203, 35593,  8157, 23041],
                  [1077, 35586,  8165, 23032],
                  [951, 35580,  8174, 23023],
                  [825, 35573,  8182, 23014],
                  [699, 35566,  8191, 23005],
                  [573, 35560,  8199, 22996],
                  [448, 35553,  8208, 22987],
                  [322, 35548,  8216, 22977],
                  [196, 35545,  8224, 22968],
                  [71, 35561,  8233, 22958],
                  [54, 17463,  8241, 22947],
                  [179, 17489,  8249, 22937],
                  [305, 17486,  8258, 22926],
                  [431, 17479,  8266, 22915],
                  [556, 17471,  8275, 22903],
                  [682, 17461,  8283, 22891],
                  [808, 17451,  8291, 22879],
                  [934, 17440,  8300, 22866],
                  [1060, 17428,  8309, 22853],
                  [1186, 17416,  8317, 22839],
                  [1312, 17403,  8326, 22824],
                  [1438, 17390,  8335, 22809],
                  [1565, 17375,  8344, 22793],
                  [1692, 17360,  8353, 22776],
                  [1818, 17344,  8362, 22759],
                  [1946, 17327,  8371, 22740],
                  [2073, 17309,  8381, 22720],
                  [2201, 17289,  8390, 22699],
                  [2329, 17268,  8400, 22676],
                  [2457, 17245,  8410, 22652],
                  [2585, 17220,  8420, 22625],
                  [2714, 17194,  8431, 22597],
                  [2843, 17164,  8441, 22566],
                  [2973, 17132,  8452, 22533],
                  [3103, 17097,  8463, 22496],
                  [3234, 17058,  8475, 22455],
                  [3365, 17014,  8486, 22410],
                  [3497, 16965,  8498, 22359],
                  [3629, 16909,  8511, 22301],
                  [3762, 16844,  8524, 22236],
                  [3896, 16770,  8537, 22160],
                  [4031, 16683,  8551, 22071],
                  [4166, 16578,  8565, 21965],
                  [4303, 16452,  8580, 21837],
                  [4440, 16295,  8595, 21679],
                  [4579, 16096,  8611, 21478],
                  [4718, 15835,  8628, 21215],
                  [4860, 15477,  8646, 20856],
                  [5003, 14963,  8665, 20341],
                  [5147, 14178,  8684, 19553],
                  [5294, 12897,  8705, 18270],
                  [5442, 10778,  8727, 16150],
                  [5593,  7879,  8751, 13250],
                  [5747,  5305,  8776, 10674],
                  [5904,  3659,  8803,  9027]]

LATLON_SCLINE1 = [[715994,  787602],
                  [720651,  786999],
                  [724976,  786407],
                  [729013,  785827],
                  [732799,  785255],
                  [736362,  784692],
                  [739728,  784134],
                  [742919,  783583],
                  [745953,  783035],
                  [748844,  782492],
                  [751607,  781951],
                  [754254,  781412],
                  [756796,  780875],
                  [759240,  780338],
                  [761597,  779801],
                  [763872,  779264],
                  [766073,  778726],
                  [768206,  778186],
                  [770275,  777644],
                  [772287,  777100],
                  [774245,  776552],
                  [776153,  776000],
                  [778015,  775444],
                  [779836,  774882],
                  [781617,  774316],
                  [783361,  773743],
                  [785073,  773163],
                  [786753,  772576],
                  [788405,  771981],
                  [790031,  771377],
                  [791633,  770764],
                  [793212,  770140],
                  [794771,  769506],
                  [796312,  768860],
                  [797837,  768201],
                  [799346,  767528],
                  [800842,  766841],
                  [802326,  766138],
                  [803799,  765419],
                  [805264,  764681],
                  [806721,  763924],
                  [808171,  763147],
                  [809617,  762347],
                  [811060,  761523],
                  [812500,  760673],
                  [813939,  759796],
                  [815378,  758888],
                  [816819,  757949],
                  [818263,  756974],
                  [819712,  755962],
                  [821166,  754909],
                  [822627,  753812],
                  [824096,  752666],
                  [825575,  751468],
                  [827065,  750213],
                  [828567,  748894],
                  [830084,  747507],
                  [831617,  746043],
                  [833167,  744496],
                  [834736,  742855],
                  [836327,  741112],
                  [837940,  739253],
                  [839578,  737265],
                  [841243,  735132],
                  [842938,  732835],
                  [844665,  730352],
                  [846425,  727656],
                  [848223,  724716],
                  [850060,  721492],
                  [851941,  717939],
                  [853868,  713998],
                  [855845,  709597],
                  [857875,  704644],
                  [859963,  699024],
                  [862113,  692583],
                  [864329,  685119],
                  [866616,  676358],
                  [868979,  665918],
                  [871421,  653256],
                  [873947,  637570],
                  [876557,  617626],
                  [879250,  591448],
                  [882013,  555681],
                  [884815,  504285],
                  [887577,  425703],
                  [890102,  297538],
                  [891907,   85636],
                  [892134, -204309],
                  [890331, -461741],
                  [887022, -626300]]


class TestMHS_AMSUB_AAPPL1CReadData(unittest.TestCase):
    """Test the filehandler."""

    def setUp(self):
        """Set up the test case."""
        self._header = np.zeros(1, dtype=_HEADERTYPE)
        self._header["satid"][0] = 3
        self._header["instrument"][0] = 12
        self._header["tempradcnv"][0] = [[2968720, 0, 1000000, 5236956, 0],
                                         [1000000, 6114597, 0, 1000000, 6114597],
                                         [-3100, 1000270, 6348092, 0, 1000000]]
        self._data = np.zeros(3, dtype=_SCANTYPE)
        self._data["scnlinyr"][:] = 2020
        self._data["scnlindy"][:] = 261
        self._data["scnlintime"][0] = 36368496
        self._data["scnlintime"][1] = 36371163
        self._data["scnlintime"][2] = 36373830
        self._data["qualind"][0] = 0
        self._data["qualind"][1] = 0
        self._data["qualind"][2] = 0
        self._data["scnlinqual"][0] = 16384
        self._data["scnlinqual"][1] = 16384
        self._data["scnlinqual"][2] = 16384
        self._data["chanqual"][0] = [6, 6, 6, 6, 6]
        self._data["chanqual"][1] = [6, 6, 6, 6, 6]
        self._data["chanqual"][2] = [6, 6, 6, 6, 6]
        self._data["instrtemp"][:] = [29520, 29520, 29520]
        self._data["dataqual"][:] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                     0, 0]
        self._data["scalti"][0:3] = [8321, 8321, 8321]
        self._data["latlon"][0] = LATLON_SCLINE1
        self._data["angles"][0] = ANGLES_SCLINE1
        self._data["btemps"][0] = SCANLINE1
        self.filename_info = {"platform_shortname": "metop01",
                              "start_time": datetime.datetime(2020, 9, 17, 10, 6),
                              "orbit_number": 41509}

        self.filetype_info = {"file_reader": MHS_AMSUB_AAPPL1CFile,
                              "file_patterns":
                              ["mhsl1c_{platform_shortname}_{start_time:%Y%m%d_%H%M}_{orbit_number:05d}.l1c"],
                              "file_type": "mhs_aapp_l1c"}

    def test_platform_name(self):
        """Test getting the platform name."""
        with tempfile.TemporaryFile() as tmpfile:
            self._header.tofile(tmpfile)
            tmpfile.seek(HEADER_LENGTH, 0)
            self._data.tofile(tmpfile)

            fh_ = MHS_AMSUB_AAPPL1CFile(tmpfile, self.filename_info, self.filetype_info)

        assert fh_.platform_name == "Metop-C"

        self._header["satid"][0] = 1
        with tempfile.TemporaryFile() as tmpfile:
            self._header.tofile(tmpfile)
            tmpfile.seek(HEADER_LENGTH, 0)
            self._data.tofile(tmpfile)

            fh_ = MHS_AMSUB_AAPPL1CFile(tmpfile, self.filename_info, self.filetype_info)

        assert fh_.platform_name == "Metop-B"

    def test_sensor_name(self):
        """Test getting the sensor name."""
        with tempfile.TemporaryFile() as tmpfile:
            self._header.tofile(tmpfile)
            tmpfile.seek(HEADER_LENGTH, 0)
            self._data.tofile(tmpfile)

            fh_ = MHS_AMSUB_AAPPL1CFile(tmpfile, self.filename_info, self.filetype_info)

        assert fh_.sensor == "mhs"

        self._header["instrument"][0] = 11
        with tempfile.TemporaryFile() as tmpfile:
            self._header.tofile(tmpfile)
            tmpfile.seek(HEADER_LENGTH, 0)
            self._data.tofile(tmpfile)

            fh_ = MHS_AMSUB_AAPPL1CFile(tmpfile, self.filename_info, self.filetype_info)

        assert fh_.sensor == "amsub"

        self._header["instrument"][0] = 10

        with tempfile.TemporaryFile() as tmpfile:
            self._header.tofile(tmpfile)
            tmpfile.seek(HEADER_LENGTH, 0)
            self._data.tofile(tmpfile)

            with self.assertRaises(IOError):
                fh_ = MHS_AMSUB_AAPPL1CFile(tmpfile, self.filename_info, self.filetype_info)

    def test_read(self):
        """Test getting the platform name."""
        with tempfile.TemporaryFile() as tmpfile:
            self._header.tofile(tmpfile)
            tmpfile.seek(HEADER_LENGTH, 0)
            self._data.tofile(tmpfile)

            fh_ = MHS_AMSUB_AAPPL1CFile(tmpfile, self.filename_info, self.filetype_info)

            info = {}

            chmin = [199.25, 218.55, 233.06, 243.3, 252.84]
            chmax = [267.98, 274.87, 248.85, 256.16, 263.]
            for chn, name in enumerate(["1", "2", "3", "4", "5"]):
                key = make_dataid(name=name, calibration="brightness_temperature")
                res = fh_.get_dataset(key, info)

                assert res.min() == chmin[chn]
                assert res.max() == chmax[chn]

    def test_angles(self):
        """Test reading the angles."""
        with tempfile.TemporaryFile() as tmpfile:
            self._header.tofile(tmpfile)
            tmpfile.seek(HEADER_LENGTH, 0)
            self._data.tofile(tmpfile)

            fh_ = MHS_AMSUB_AAPPL1CFile(tmpfile, self.filename_info, self.filetype_info)
            info = {}
            key = make_dataid(name="solar_zenith_angle")
            res = fh_.get_dataset(key, info)

            assert np.all(res[2] == 0)
            assert np.all(res[1] == 0)
            expected = np.array([76.82, 77.09, 77.33, 77.56, 77.77, 77.97, 78.16, 78.34, 78.51,
                                 78.68, 78.83, 78.99, 79.13, 79.27, 79.4, 79.53, 79.66, 79.78,
                                 79.9, 80.01, 80.13, 80.23, 80.34, 80.45, 80.55, 80.65, 80.75,
                                 80.84, 80.94, 81.03, 81.12, 81.21, 81.3, 81.39, 81.48, 81.57,
                                 81.65, 81.74, 81.82, 81.91, 81.99, 82.08, 82.16, 82.24, 82.33,
                                 82.41, 82.49, 82.58, 82.66, 82.75, 82.83, 82.91, 83., 83.09,
                                 83.17, 83.26, 83.35, 83.44, 83.53, 83.62, 83.71, 83.81, 83.9,
                                 84., 84.1, 84.2, 84.31, 84.41, 84.52, 84.63, 84.75, 84.86,
                                 84.98, 85.11, 85.24, 85.37, 85.51, 85.65, 85.8, 85.95, 86.11,
                                 86.28, 86.46, 86.65, 86.84, 87.05, 87.27, 87.51, 87.76, 88.03])

            np.testing.assert_allclose(res[0], expected)

    def test_navigation(self):
        """Test reading the longitudes and latitudes."""
        with tempfile.TemporaryFile() as tmpfile:
            self._header.tofile(tmpfile)
            tmpfile.seek(HEADER_LENGTH, 0)
            self._data.tofile(tmpfile)

            fh_ = MHS_AMSUB_AAPPL1CFile(tmpfile, self.filename_info, self.filetype_info)
            info = {}
            key = make_dataid(name="longitude")
            res = fh_.get_dataset(key, info)

            assert np.all(res[2] == 0)
            assert np.all(res[1] == 0)
            expected = np.array([78.7602,  78.6999,  78.6407,  78.5827,  78.5255,  78.4692,
                                 78.4134,  78.3583,  78.3035,  78.2492,  78.1951,  78.1412,
                                 78.0875,  78.0338,  77.9801,  77.9264,  77.8726,  77.8186,
                                 77.7644,  77.71,  77.6552,  77.6,  77.5444,  77.4882,
                                 77.4316,  77.3743,  77.3163,  77.2576,  77.1981,  77.1377,
                                 77.0764,  77.014,  76.9506,  76.886,  76.8201,  76.7528,
                                 76.6841,  76.6138,  76.5419,  76.4681,  76.3924,  76.3147,
                                 76.2347,  76.1523,  76.0673,  75.9796,  75.8888,  75.7949,
                                 75.6974,  75.5962,  75.4909,  75.3812,  75.2666,  75.1468,
                                 75.0213,  74.8894,  74.7507,  74.6043,  74.4496,  74.2855,
                                 74.1112,  73.9253,  73.7265,  73.5132,  73.2835,  73.0352,
                                 72.7656,  72.4716,  72.1492,  71.7939,  71.3998,  70.9597,
                                 70.4644,  69.9024,  69.2583,  68.5119,  67.6358,  66.5918,
                                 65.3256,  63.757,  61.7626,  59.1448,  55.5681,  50.4285,
                                 42.5703,  29.7538,   8.5636, -20.4309, -46.1741, -62.63])

            np.testing.assert_allclose(res[0], expected)

            key = make_dataid(name="latitude")
            res = fh_.get_dataset(key, info)

            assert np.all(res[2] == 0)
            assert np.all(res[1] == 0)
            expected = np.array([71.5994, 72.0651, 72.4976, 72.9013, 73.2799, 73.6362, 73.9728,
                                 74.2919, 74.5953, 74.8844, 75.1607, 75.4254, 75.6796, 75.924,
                                 76.1597, 76.3872, 76.6073, 76.8206, 77.0275, 77.2287, 77.4245,
                                 77.6153, 77.8015, 77.9836, 78.1617, 78.3361, 78.5073, 78.6753,
                                 78.8405, 79.0031, 79.1633, 79.3212, 79.4771, 79.6312, 79.7837,
                                 79.9346, 80.0842, 80.2326, 80.3799, 80.5264, 80.6721, 80.8171,
                                 80.9617, 81.106, 81.25, 81.3939, 81.5378, 81.6819, 81.8263,
                                 81.9712, 82.1166, 82.2627, 82.4096, 82.5575, 82.7065, 82.8567,
                                 83.0084, 83.1617, 83.3167, 83.4736, 83.6327, 83.794, 83.9578,
                                 84.1243, 84.2938, 84.4665, 84.6425, 84.8223, 85.006, 85.1941,
                                 85.3868, 85.5845, 85.7875, 85.9963, 86.2113, 86.4329, 86.6616,
                                 86.8979, 87.1421, 87.3947, 87.6557, 87.925, 88.2013, 88.4815,
                                 88.7577, 89.0102, 89.1907, 89.2134, 89.0331, 88.7022])

            np.testing.assert_allclose(res[0], expected)
