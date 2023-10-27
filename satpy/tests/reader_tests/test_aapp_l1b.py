#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2020 Satpy developers
#
# This file is part of satpy.
#
# satpy is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# satpy is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# satpy.  If not, see <http://www.gnu.org/licenses/>.
"""Test module for the avhrr aapp l1b reader."""

import datetime
import os
import tempfile
import unittest
from contextlib import suppress
from unittest import mock

import numpy as np

from satpy.readers.aapp_l1b import _HEADERTYPE, _SCANTYPE, AVHRRAAPPL1BFile
from satpy.tests.utils import make_dataid


class TestAAPPL1BAllChannelsPresent(unittest.TestCase):
    """Test the filehandler."""

    def setUp(self):
        """Set up the test case."""
        self._header = np.zeros(1, dtype=_HEADERTYPE)
        self._header["satid"][0] = 13
        self._header["radtempcnv"][0] = [[267194, -171669, 1002811],
                                         [930310,  -59084, 1001600],
                                         [828600,  -37854, 1001147]]
        # first 3b is off, 3a is on
        self._header["inststat1"][0] = 0b1111011100000000
        # switch 3a off at position 1
        self._header["statchrecnb"][0] = 1
        # 3b is on, 3a is off
        self._header["inststat2"][0] = 0b1111101100000000

        self._data = np.zeros(3, dtype=_SCANTYPE)
        self._data["scnlinyr"][:] = 2020
        self._data["scnlindy"][:] = 8
        self._data["scnlintime"][0] = 30195225
        self._data["scnlintime"][1] = 30195389
        self._data["scnlintime"][2] = 30195556
        self._data["scnlinbit"][0] = -16383
        self._data["scnlinbit"][1] = -16383
        self._data["scnlinbit"][2] = -16384
        calvis = np.array([[[0, 0, 0, 0, 0],
                            [0, 0, 0, 0, 0],
                            [543489984, -21941870, 1592440064, -545027008, 499]],
                           [[0, 0, 0, 0, 0],
                            [0, 0, 0, 0, 0],
                            [540780032,  -22145690, 1584350080, -543935616, 500]],
                           [[0, 0, 0, 0, 0],
                            [0, 0, 0, 0, 0],
                            [257550000, -10449420, 1812019968, -785690304, 499]]])
        self._data["calvis"][:] = calvis
        self._data["calir"] = [[[[0, -2675, 2655265],
                                 [0, 0, 0]],
                                [[33605, -260786, 226818992],
                                 [0, 0, 0]],
                                [[13869, -249508, 234624768],
                                 [0, 0, 0]]],
                               [[[0, -2675, 2655265],
                                 [0, 0, 0]],
                                [[33609, -260810, 226837328],
                                 [0, 0, 0]],
                                [[13870, -249520, 234638704],
                                 [0, 0, 0]]],
                               [[[0, 0, 0],
                                 [0, 0, 0]],
                                [[33614, -260833, 226855664],
                                 [0, 0, 0]],
                                [[13871, -249531, 234652640],
                                 [0, 0, 0]]]]
        self._data["hrpt"] = np.ones_like(self._data["hrpt"]) * (np.arange(2048) // 2)[np.newaxis, :, np.newaxis]

        self.filename_info = {"platform_shortname": "metop03", "start_time": datetime.datetime(2020, 1, 8, 8, 19),
                              "orbit_number": 6071}
        self.filetype_info = {"file_reader": AVHRRAAPPL1BFile,
                              'file_patterns': ['hrpt_{platform_shortname}_{start_time:%Y%m%d_%H%M}_{orbit_number:05d}.l1b'],  # noqa
                              "file_type": "avhrr_aapp_l1b"}

    def test_read(self):
        """Test the reading."""
        with tempfile.TemporaryFile() as tmpfile:
            self._header.tofile(tmpfile)
            tmpfile.seek(22016, 0)
            self._data.tofile(tmpfile)

            fh = AVHRRAAPPL1BFile(tmpfile, self.filename_info, self.filetype_info)
            info = {}
            mins = []
            maxs = []
            for name in ["1", "2", "3a"]:
                key = make_dataid(name=name, calibration="reflectance")
                res = fh.get_dataset(key, info)
                assert res.min() == 0
                assert res.max() >= 100
                mins.append(res.min().values)
                maxs.append(res.max().values)
                if name == "3a":
                    assert np.all(np.isnan(res[:2, :]))

            for name in ["3b", "4", "5"]:
                key = make_dataid(name=name, calibration="reflectance")
                res = fh.get_dataset(key, info)
                mins.append(res.min().values)
                maxs.append(res.max().values)
                if name == "3b":
                    assert np.all(np.isnan(res[2:, :]))

            np.testing.assert_allclose(mins, [0., 0., 0., 204.10106939, 103.23477235, 106.42609758])
            np.testing.assert_allclose(maxs, [108.40391775, 107.68545158, 106.80061233,
                                              337.71416096, 355.15898219, 350.87182166])

    def test_angles(self):
        """Test reading the angles."""
        with tempfile.TemporaryFile() as tmpfile:
            self._header.tofile(tmpfile)
            tmpfile.seek(22016, 0)
            self._data.tofile(tmpfile)

            fh = AVHRRAAPPL1BFile(tmpfile, self.filename_info, self.filetype_info)
            info = {}
            key = make_dataid(name="solar_zenith_angle")
            res = fh.get_dataset(key, info)
            assert np.all(res == 0)

    def test_navigation(self):
        """Test reading the lon and lats."""
        with tempfile.TemporaryFile() as tmpfile:
            self._header.tofile(tmpfile)
            tmpfile.seek(22016, 0)
            self._data.tofile(tmpfile)

            fh = AVHRRAAPPL1BFile(tmpfile, self.filename_info, self.filetype_info)
            info = {}
            key = make_dataid(name="longitude")
            res = fh.get_dataset(key, info)
            assert np.all(res == 0)
            key = make_dataid(name="latitude")
            res = fh.get_dataset(key, info)
            assert np.all(res == 0)

    def test_interpolation(self):
        """Test reading the lon and lats."""
        with tempfile.TemporaryFile() as tmpfile:
            self._header.tofile(tmpfile)
            tmpfile.seek(22016, 0)
            self._data.tofile(tmpfile)
            fh = AVHRRAAPPL1BFile(tmpfile, self.filename_info, self.filetype_info)
            lons40km = np.array([
                [-115.9773, -122.3054, -127.7482, -132.464, -136.5788, -140.1951,
                 -143.3961, -146.2497, -148.8112, -151.1259, -153.2309, -155.1568,
                 -156.9291, -158.5689, -160.0941, -161.5196, -162.8584, -164.1212,
                 -165.3176, -166.4557, -167.5426, -168.5846, -169.5872, -170.5555,
                 -171.4937, -172.406, -173.296, -174.1671, -175.0224, -175.865,
                 -176.6976, -177.523, -178.3439, -179.1628, -179.9825, 179.1944,
                 178.3651, 177.5267, 176.6761, 175.8098, 174.9242, 174.0149,
                 173.0773, 172.1057, 171.0935, 170.0326, 168.9128, 167.7211,
                 166.4397, 165.0436, 163.4946],
                [-115.9639, -122.2967, -127.7441, -132.4639, -136.5824, -140.2018,
                 -143.4055, -146.2614, -148.8249, -151.1413, -153.2478, -155.175,
                 -156.9484, -158.5892, -160.1152, -161.5415, -162.8809, -164.1443,
                 -165.3412, -166.4797, -167.567, -168.6094, -169.6123, -170.5808,
                 -171.5192, -172.4317, -173.3219, -174.1931, -175.0486, -175.8913,
                 -176.724, -177.5494, -178.3703, -179.1893, 179.991, 179.168,
                 178.3388, 177.5005, 176.6499, 175.7838, 174.8983, 173.9892,
                 173.0518, 172.0805, 171.0685, 170.0079, 168.8885, 167.6972,
                 166.4164, 165.0209, 163.4726],
                [-115.9504, -122.288, -127.7399, -132.4639, -136.5859, -140.2084,
                 -143.4148, -146.2731, -148.8386, -151.1567, -153.2647, -155.1932,
                 -156.9677, -158.6095, -160.1363, -161.5634, -162.9034, -164.1674,
                 -165.3648, -166.5038, -167.5915, -168.6341, -169.6374, -170.6061,
                 -171.5448, -172.4575, -173.3478, -174.2192, -175.0748, -175.9176,
                 -176.7503, -177.5758, -178.3968, -179.2157, 179.9646, 179.1416,
                 178.3124, 177.4742, 176.6238, 175.7577, 174.8724, 173.9635,
                 173.0263, 172.0552, 171.0436, 169.9833, 168.8643, 167.6734,
                 166.3931, 164.9982, 163.4507]])
            lats40km = np.array([
                [78.6613, 78.9471, 79.0802, 79.1163, 79.0889, 79.019, 78.9202,
                 78.8016, 78.6695, 78.528, 78.38, 78.2276, 78.0721, 77.9145,
                 77.7553, 77.5949, 77.4335, 77.2712, 77.1079, 76.9435, 76.7779,
                 76.6108, 76.4419, 76.2708, 76.0973, 75.921, 75.7412, 75.5576,
                 75.3696, 75.1764, 74.9776, 74.7721, 74.5592, 74.3379, 74.1069,
                 73.865, 73.6106, 73.342, 73.057, 72.7531, 72.4273, 72.076,
                 71.6945, 71.2773, 70.8171, 70.3046, 69.7272, 69.0676, 68.3014,
                 67.3914, 66.2778],
                [78.6703, 78.9565, 79.0897, 79.1259, 79.0985, 79.0286, 78.9297,
                 78.8111, 78.6789, 78.5373, 78.3892, 78.2367, 78.0811, 77.9233,
                 77.764, 77.6035, 77.442, 77.2796, 77.1162, 76.9518, 76.7861,
                 76.6188, 76.4498, 76.2787, 76.1051, 75.9287, 75.7488, 75.5651,
                 75.377, 75.1838, 74.9848, 74.7793, 74.5663, 74.3448, 74.1138,
                 73.8718, 73.6173, 73.3486, 73.0635, 72.7595, 72.4336, 72.0821,
                 71.7005, 71.2832, 70.8229, 70.3102, 69.7326, 69.0729, 68.3065,
                 67.3963, 66.2825],
                [78.6794, 78.9658, 79.0993, 79.1355, 79.1082, 79.0381, 78.9392,
                 78.8205, 78.6882, 78.5465, 78.3984, 78.2458, 78.0901, 77.9322,
                 77.7728, 77.6122, 77.4506, 77.2881, 77.1246, 76.96, 76.7942,
                 76.6269, 76.4578, 76.2866, 76.1129, 75.9364, 75.7564, 75.5727,
                 75.3844, 75.1911, 74.9921, 74.7864, 74.5734, 74.3518, 74.1207,
                 73.8786, 73.624, 73.3552, 73.0699, 72.7658, 72.4398, 72.0882,
                 71.7065, 71.2891, 70.8286, 70.3158, 69.7381, 69.0782, 68.3116,
                 67.4012, 66.2872]])
            fh._get_coordinates_in_degrees = mock.MagicMock()
            fh._get_coordinates_in_degrees.return_value = (lons40km, lats40km)
            (lons, lats) = fh._get_all_interpolated_coordinates()
            lon_data = lons.compute()
            assert (np.max(lon_data) <= 180)
            # Not longitdes between -110, 110 in indata
            assert np.all(np.abs(lon_data) > 110)

    def test_interpolation_angles(self):
        """Test reading the lon and lats."""
        with tempfile.TemporaryFile() as tmpfile:
            self._header.tofile(tmpfile)
            tmpfile.seek(22016, 0)
            self._data.tofile(tmpfile)
            fh = AVHRRAAPPL1BFile(tmpfile, self.filename_info, self.filetype_info)

            sunz40km = np.array(
                [[122.42, 121.72, 121.14, 120.63, 120.19, 119.79, 119.43, 119.1, 118.79, 118.51,
                  118.24, 117.99, 117.76, 117.53, 117.31, 117.1, 116.9, 116.71, 116.52, 116.33,
                  116.15, 115.97, 115.79, 115.61, 115.44, 115.26, 115.08, 114.91, 114.73, 114.55,
                  114.36, 114.18, 113.98, 113.79, 113.58, 113.37, 113.15, 112.92, 112.68, 112.43,
                  112.15, 111.87, 111.55, 111.22, 110.85, 110.44, 109.99, 109.47, 108.88, 108.18,
                  107.33],
                 [122.41, 121.71, 121.13, 120.62, 120.18, 119.78, 119.42, 119.09, 118.78, 118.5,
                  118.24, 117.99, 117.75, 117.52, 117.31, 117.1, 116.9, 116.7, 116.51, 116.32,
                  116.14, 115.96, 115.78, 115.6, 115.43, 115.25, 115.08, 114.9, 114.72, 114.54,
                  114.36, 114.17, 113.98, 113.78, 113.57, 113.36, 113.14, 112.91, 112.67, 112.42,
                  112.15, 111.86, 111.55, 111.21, 110.84, 110.43, 109.98, 109.46, 108.87, 108.17,
                  107.32]])
            satz40km = np.array(
                [[6.623e+01, 6.281e+01, 5.960e+01, 5.655e+01, 5.360e+01, 5.075e+01, 4.797e+01,
                  4.524e+01, 4.256e+01, 3.992e+01, 3.731e+01, 3.472e+01, 3.216e+01, 2.962e+01,
                  2.710e+01, 2.460e+01, 2.210e+01, 1.962e+01, 1.714e+01, 1.467e+01, 1.221e+01,
                  9.760e+00, 7.310e+00, 4.860e+00, 2.410e+00, 3.000e-02, 2.470e+00, 4.920e+00,
                  7.370e+00, 9.820e+00, 1.227e+01, 1.474e+01, 1.720e+01, 1.968e+01, 2.216e+01,
                  2.466e+01, 2.717e+01, 2.969e+01, 3.223e+01, 3.479e+01, 3.737e+01, 3.998e+01,
                  4.263e+01, 4.531e+01, 4.804e+01, 5.082e+01, 5.368e+01, 5.662e+01, 5.969e+01,
                  6.290e+01, 6.633e+01],
                 [6.623e+01, 6.281e+01, 5.960e+01, 5.655e+01, 5.360e+01, 5.075e+01, 4.797e+01,
                  4.524e+01, 4.256e+01, 3.992e+01, 3.731e+01, 3.472e+01, 3.216e+01, 2.962e+01,
                  2.710e+01, 2.460e+01, 2.210e+01, 1.962e+01, 1.714e+01, 1.467e+01, 1.221e+01,
                  9.760e+00, 7.310e+00, 4.860e+00, 2.410e+00, 3.000e-02, 2.470e+00, 4.920e+00,
                  7.370e+00, 9.820e+00, 1.227e+01, 1.474e+01, 1.720e+01, 1.968e+01, 2.216e+01,
                  2.466e+01, 2.717e+01, 2.969e+01, 3.223e+01, 3.479e+01, 3.737e+01, 3.998e+01,
                  4.263e+01, 4.531e+01, 4.804e+01, 5.082e+01, 5.368e+01, 5.662e+01, 5.969e+01,
                  6.290e+01, 6.633e+01]])
            azidiff40km = np.array([
                [56.9, 56.24, 55.71, 55.27, 54.9, 54.57, 54.29, 54.03, 53.8, 53.59,
                 53.4, 53.22, 53.05, 52.89, 52.74, 52.6, 52.47, 52.34, 52.22, 52.1,
                 51.98, 51.87, 51.76, 51.65, 51.55, 128.55, 128.65, 128.76, 128.86, 128.96,
                 129.07, 129.17, 129.27, 129.38, 129.49, 129.6, 129.72, 129.83, 129.95, 130.08,
                 130.21, 130.35, 130.5, 130.65, 130.81, 130.99, 131.18, 131.39, 131.63, 131.89,
                 132.19],
                [56.9, 56.24, 55.72, 55.28, 54.9, 54.58, 54.29, 54.03, 53.8, 53.59,
                 53.4, 53.22, 53.05, 52.89, 52.75, 52.6, 52.47, 52.34, 52.22, 52.1,
                 51.98, 51.87, 51.76, 51.65, 51.55, 128.55, 128.65, 128.75, 128.86, 128.96,
                 129.06, 129.17, 129.27, 129.38, 129.49, 129.6, 129.71, 129.83, 129.95, 130.08,
                 130.21, 130.35, 130.49, 130.65, 130.81, 130.99, 131.18, 131.39, 131.62, 131.89,
                 132.19]])
            fh._get_tiepoint_angles_in_degrees = mock.MagicMock()
            fh._get_tiepoint_angles_in_degrees.return_value = (sunz40km, satz40km, azidiff40km)
            (sunz, satz, azidiff) = fh._get_all_interpolated_angles()
            assert (np.max(sunz) <= 123)
            assert (np.max(satz) <= 70)


class TestAAPPL1BChannel3AMissing(unittest.TestCase):
    """Test the filehandler when channel 3a is missing."""

    def setUp(self):
        """Set up the test case."""
        self._header = np.zeros(1, dtype=_HEADERTYPE)
        self._header["satid"][0] = 13
        self._header["radtempcnv"][0] = [[267194, -171669, 1002811],
                                         [930310, -59084, 1001600],
                                         [828600, -37854, 1001147]]
        # first 3a is off, 3b is on
        self._header["inststat1"][0] = 0b1111011100000000
        # valid for the whole pass
        self._header["statchrecnb"][0] = 0
        self._header["inststat2"][0] = 0b0

        self._data = np.zeros(3, dtype=_SCANTYPE)
        self._data["scnlinyr"][:] = 2020
        self._data["scnlindy"][:] = 8
        self._data["scnlintime"][0] = 30195225
        self._data["scnlintime"][1] = 30195389
        self._data["scnlintime"][2] = 30195556
        self._data["scnlinbit"][0] = -16383
        self._data["scnlinbit"][1] = -16383
        self._data["scnlinbit"][2] = -16383
        calvis = np.array([[[0, 0, 0, 0, 0],
                            [0, 0, 0, 0, 0],
                            [543489984, -21941870, 1592440064, -545027008, 499]],
                           [[0, 0, 0, 0, 0],
                            [0, 0, 0, 0, 0],
                            [540780032, -22145690, 1584350080, -543935616, 500]],
                           [[0, 0, 0, 0, 0],
                            [0, 0, 0, 0, 0],
                            [257550000, -10449420, 1812019968, -785690304, 499]]])
        self._data["calvis"][:] = calvis
        self._data["calir"] = [[[[0, -2675, 2655265],
                                 [0, 0, 0]],
                                [[33605, -260786, 226818992],
                                 [0, 0, 0]],
                                [[13869, -249508, 234624768],
                                 [0, 0, 0]]],
                               [[[0, -2675, 2655265],
                                 [0, 0, 0]],
                                [[33609, -260810, 226837328],
                                 [0, 0, 0]],
                                [[13870, -249520, 234638704],
                                 [0, 0, 0]]],
                               [[[0, 0, 0],
                                 [0, 0, 0]],
                                [[33614, -260833, 226855664],
                                 [0, 0, 0]],
                                [[13871, -249531, 234652640],
                                 [0, 0, 0]]]]
        self._data["hrpt"] = np.ones_like(self._data["hrpt"]) * (np.arange(2048) // 2)[np.newaxis, :, np.newaxis]

        self.filename_info = {"platform_shortname": "metop03", "start_time": datetime.datetime(2020, 1, 8, 8, 19),
                              "orbit_number": 6071}
        self.filetype_info = {"file_reader": AVHRRAAPPL1BFile,
                              "file_patterns": [
                                  "hrpt_{platform_shortname}_{start_time:%Y%m%d_%H%M}_{orbit_number:05d}.l1b"],
                              # noqa
                              "file_type": "avhrr_aapp_l1b"}

    def test_loading_missing_channels_returns_none(self):
        """Test that loading a missing channel raises a keyerror."""
        with tempfile.TemporaryFile() as tmpfile:
            self._header.tofile(tmpfile)
            tmpfile.seek(22016, 0)
            self._data.tofile(tmpfile)

            fh = AVHRRAAPPL1BFile(tmpfile, self.filename_info, self.filetype_info)
            info = {}
            key = make_dataid(name="3a", calibration="reflectance")
            assert fh.get_dataset(key, info) is None

    def test_available_datasets_miss_3a(self):
        """Test that channel 3a is missing from available datasets."""
        with tempfile.TemporaryFile() as tmpfile:
            self._header.tofile(tmpfile)
            tmpfile.seek(22016, 0)
            self._data.tofile(tmpfile)

            fh = AVHRRAAPPL1BFile(tmpfile, self.filename_info, self.filetype_info)
            configured_datasets = [[None, {"name": "1"}],
                                   [None, {"name": "2"}],
                                   [None, {"name": "3a"}],
                                   [None, {"name": "3b"}],
                                   [None, {"name": "4"}],
                                   [None, {"name": "5"}],
                                   ]
            available_datasets = fh.available_datasets(configured_datasets)
            for status, mda in available_datasets:
                if mda["name"] == "3a":
                    assert status is False
                else:
                    assert status is True


class TestNegativeCalibrationSlope(unittest.TestCase):
    """Case for testing correct behaviour when the data has negative slope2 coefficients."""

    def setUp(self):
        """Set up the test case."""
        from satpy.readers.aapp_l1b import _HEADERTYPE, _SCANTYPE
        calvis = np.array([[[617200000, -24330000, 1840000000, -632800000, 498],  # calvis
                            [0, 0, 0, 0, 0],
                            [540000000, -21300002, 1610000000, -553699968, 501]],
                           [[750299968, -29560000, -2043967360, -784400000, 503],
                            [0, 0, 0, 0, 0],
                            [529000000, -20840002, 1587299968, -553100032, 500]],
                           [[0, 0, 0, 0, 0],
                            [0, 0, 0, 0, 0],
                            [261799984, -9820000, 1849200000, -808800000, 501]]], dtype="<i4")
        calir = np.array([[[0, -2932, 2907419], [0, 0, 0]],
                          [[18214, -200932, 182150896], [0, 0, 0]],
                          [[6761, -200105, 192092496], [0, 0, 0]]], dtype="<i4")

        hrpt = np.full((2048, 5), 1023, dtype="<i2")

        data = np.array([(1, 2021, 86, 0, 51110551, -16383, b"", 0, 0, [0, 0, 0], 0, b"",

                          calvis, calir,
                          [9, 6, 6], 0, 51110551, 120, 0, 5, 8479,
                          [[6034, 6670, 3759], [5930, 6322, 3805], [5845, 5997, 3846], [5773, 5689, 3882],  # angle
                           [5711, 5392, 3914], [5656, 5105, 3943], [5607, 4825, 3970], [5562, 4551, 3995],
                           [5522, 4281, 4019], [5484, 4016, 4041], [5450, 3754, 4062], [5417, 3495, 4082],
                           [5387, 3238, 4101], [5358, 2983, 4120], [5330, 2730, 4138], [5304, 2479, 4155],
                           [5279, 2229, 4172], [5254, 1980, 4189], [5231, 1731, 4205], [5208, 1484, 4221],
                           [5185, 1238, 4237], [5163, 991, 4253], [5142, 746, 4269], [5120, 500, 4284],
                           [5099, 255, 4300], [5078, 10, 4317], [5057, 234, 13667], [5036, 479, 13650],
                           [5015, 725, 13634], [4994, 970, 13617], [4973, 1216, 13599], [4951, 1463, 13582],
                           [4929, 1710, 13563], [4906, 1958, 13544], [4883, 2207, 13524], [4859, 2457, 13503],
                           [4834, 2708, 13481], [4809, 2961, 13458], [4782, 3216, 13434], [4754, 3472, 13407],
                           [4724, 3731, 13379], [4693, 3993, 13349], [4659, 4258, 13315], [4623, 4527, 13279],
                           [4584, 4801, 13238], [4542, 5081, 13192], [4495, 5367, 13140], [4443, 5663, 13080],
                           [4384, 5970, 13008], [4315, 6294, 12922], [4235, 6639, 12813]],
                          [1280, 0, 2048],
                          [[502821, -759360], [502866, -738803], [502629, -721850], [502234, -707448],  # pos
                           [501745, -694943], [501200, -683899], [500621, -674011], [500023, -665056],
                           [499415, -656867], [498801, -649315], [498185, -642296], [497568, -635729],
                           [496952, -629548], [496337, -623696], [495723, -618128], [495109, -612804],
                           [494495, -607689], [493879, -602755], [493261, -597974], [492640, -593325],
                           [492013, -588786], [491380, -584338], [490740, -579963], [490090, -575646],
                           [489428, -571370], [488753, -567121], [488063, -562884], [487355, -558645],
                           [486626, -554390], [485873, -550103], [485095, -545769], [484285, -541374],
                           [483441, -536898], [482558, -532326], [481630, -527636], [480650, -522806],
                           [479612, -517812], [478507, -512627], [477324, -507217], [476050, -501547],
                           [474671, -495571], [473167, -489239], [471515, -482486], [469685, -475235],
                           [467638, -467389], [465324, -458824], [462674, -449377], [459590, -438827],
                           [455932, -426864], [451483, -413032], [445887, -396607]],
                          [0, 0],
                          [644, 367, 860, 413, 527, 149, 746, 2, 172, 688, 760, 663, 606, 606, 200, 202, 206, 221,
                           221, 221, 498, 1023, 858, 463, 423, 857, 463, 424, 857, 463, 424, 858, 463, 424, 858,
                           463, 424, 858, 463, 423, 858, 463, 423, 858, 463, 422, 857, 463, 423, 858, 463, 424, 39,
                           39, 990, 991, 990, 38, 39, 991, 991, 991, 41, 40, 991, 991, 990, 42, 40, 992, 991, 991,
                           42, 41, 991, 991, 991, 40, 40, 991, 991, 990, 42, 40, 992, 992, 991, 42, 40, 992, 991,
                           991, 40, 40, 992, 991, 990, 42, 41, 992, 991, 990, 514], 0,
                          hrpt,
                          [0, 0],
                          [[15160, 772, 3117, 12810, 14869], [13355, 5399, 15160, 772, 3117],
                           # tip minor frame header
                           [12810, 2070, 3865, 5420, 15160], [772, 3118, 12810, 7183, 3584],
                           [29, 15160, 772, 3118, 12810], [4116, 3868, 12032, 15160, 772],
                           [3118, 12810, 286, 3863, 12073]],
                          [[b"\x15\x002/\x04\n", b"\x15\x002/\x04\n", b"\x03\x00\x03?\x033", b"\x03\x00\x03?\x033",
                            # cpu telemetry
                            b"\x0c\x00\r%\x02\x0c"],
                           [b"\x0c\x00\r%\x02\x0c", b"\x03\x00\x00\x0f", b"\x03\x00\x00\x0f", b"?\x00\x01?2\x11",
                            b"?\x00\x01?2\x11"]],
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                           0, 0,
                           0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                           0, 0,
                           0, 0, 0, 0, 0]),
                         (2, 2021, 86, 0, 51110718, -16383, b"", 0, 0, [0, 0, 0], 0, b"",
                          calvis, calir,
                          [9, 6, 6], 0, 51110551, 120, 0, 5, 8479,
                          [[6033, 6670, 3758], [5930, 6322, 3805], [5845, 5997, 3845], [5773, 5689, 3881],
                           [5710, 5392, 3913], [5655, 5105, 3943], [5606, 4825, 3970], [5562, 4551, 3995],
                           [5521, 4281, 4018], [5484, 4016, 4040], [5449, 3754, 4061], [5417, 3495, 4082],
                           [5386, 3238, 4101], [5357, 2983, 4119], [5330, 2730, 4137], [5303, 2479, 4155],
                           [5278, 2229, 4171], [5254, 1980, 4188], [5230, 1731, 4204], [5207, 1484, 4221],
                           [5185, 1238, 4236], [5163, 991, 4252], [5141, 746, 4268], [5120, 500, 4284],
                           [5099, 255, 4300], [5078, 10, 4316], [5057, 234, 13667], [5036, 479, 13651],
                           [5015, 725, 13634], [4993, 970, 13617], [4972, 1216, 13600], [4950, 1463, 13582],
                           [4928, 1710, 13564], [4906, 1958, 13545], [4882, 2207, 13525], [4858, 2457, 13504],
                           [4834, 2708, 13482], [4808, 2961, 13459], [4781, 3216, 13434], [4753, 3472, 13408],
                           [4723, 3731, 13380], [4692, 3993, 13349], [4659, 4258, 13316], [4623, 4527, 13279],
                           [4584, 4801, 13238], [4541, 5081, 13193], [4494, 5367, 13140], [4442, 5663, 13080],
                           [4383, 5970, 13009], [4315, 6294, 12922], [4234, 6639, 12813]], [1536, 768, 1280],
                          [[502725, -759364], [502770, -738811], [502533, -721862], [502137, -707463],
                           [501647, -694960], [501102, -683918], [500524, -674032], [499926, -665080],
                           [499318, -656892], [498704, -649341], [498087, -642324], [497471, -635758],
                           [496855, -629578], [496240, -623728], [495626, -618161], [495012, -612837],
                           [494398, -607724], [493783, -602790], [493165, -598011], [492543, -593362],
                           [491917, -588824], [491284, -584377], [490644, -580003], [489994, -575687],
                           [489332, -571412], [488658, -567163], [487967, -562927], [487259, -558689],
                           [486531, -554434], [485778, -550148], [485000, -545815], [484190, -541420],
                           [483347, -536946], [482464, -532374], [481536, -527685], [480556, -522856],
                           [479519, -517863], [478414, -512679], [477231, -507270], [475957, -501600],
                           [474578, -495626], [473075, -489294], [471423, -482542], [469593, -475293],
                           [467547, -467448], [465234, -458884], [462584, -449438], [459501, -438889],
                           [455844, -426928], [451396, -413097], [445801, -396674]], [0, 0],
                          [644, 367, 860, 413, 527, 149, 874, 2, 172, 688, 760, 830, 606, 607, 200, 200, 205, 214,
                           215,
                           214, 498, 1023, 857, 463, 423, 857, 463, 423, 858, 462, 423, 858, 463, 424, 859, 463,
                           424,
                           858, 463, 423, 858, 463, 423, 858, 463, 423, 858, 463, 424, 858, 463, 423, 39, 39, 991,
                           991,
                           990, 39, 39, 991, 991, 990, 41, 40, 991, 991, 991, 41, 40, 992, 991, 991, 42, 41, 991,
                           991,
                           990, 40, 40, 991, 991, 990, 42, 40, 992, 991, 990, 42, 41, 991, 991, 990, 41, 40, 991,
                           991,
                           990, 42, 41, 992, 991, 990, 514], 0,
                          hrpt,
                          [0, 0],
                          [[15160, 772, 3117, 12810, 14869], [13355, 5399, 15160, 772, 3117],
                           [12810, 2070, 3865, 5420, 15160], [772, 3118, 12810, 7183, 3584],
                           [29, 15160, 772, 3118, 12810], [4116, 3868, 12032, 15160, 772],
                           [3118, 12810, 286, 3863, 12073]], [
                              [b"\x15\x002/\x04\n", b"\x15\x002/\x04\n", b"\x03\x00\x03?\x033",
                               b"\x03\x00\x03?\x033",
                               b"\x0c\x00\r%\x02\x0c"],
                              [b"\x0c\x00\r%\x02\x0c", b"\x03\x00\x00\x0f", b"\x03\x00\x00\x0f",
                               b"?\x00\x01?2\x11",
                               b"?\x00\x01?2\x11"]],
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                           0, 0,
                           0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                           0, 0,
                           0, 0, 0, 0, 0]),
                         (3, 2021, 86, 0, 51110885, -16383, b"", 0, 0, [0, 0, 0], 0, b"",
                          calvis, calir,
                          [9, 6, 6], 0, 51110551, 120, 0, 5, 8479,
                          [[6033, 6670, 3757], [5929, 6322, 3804], [5844, 5997, 3845], [5772, 5689, 3880],
                           [5710, 5392, 3913], [5655, 5105, 3942], [5606, 4825, 3969], [5561, 4551, 3994],
                           [5521, 4281, 4018], [5483, 4016, 4040], [5448, 3754, 4061], [5416, 3495, 4081],
                           [5385, 3238, 4100], [5356, 2983, 4119], [5329, 2730, 4137], [5303, 2479, 4154],
                           [5277, 2229, 4171], [5253, 1980, 4187], [5229, 1731, 4204], [5206, 1484, 4220],
                           [5184, 1238, 4236], [5162, 991, 4252], [5140, 746, 4267], [5119, 500, 4283],
                           [5098, 255, 4299], [5077, 10, 4316], [5056, 234, 13668], [5035, 479, 13652],
                           [5014, 725, 13635], [4993, 970, 13618], [4971, 1216, 13601], [4950, 1463, 13583],
                           [4927, 1710, 13564], [4905, 1958, 13545], [4882, 2207, 13525], [4858, 2457, 13504],
                           [4833, 2708, 13482], [4807, 2961, 13459], [4780, 3216, 13435], [4752, 3472, 13408],
                           [4723, 3731, 13380], [4691, 3993, 13350], [4658, 4258, 13316], [4622, 4527, 13280],
                           [4583, 4801, 13239], [4541, 5081, 13193], [4494, 5367, 13141], [4441, 5663, 13081],
                           [4382, 5970, 13009], [4314, 6294, 12923], [4233, 6639, 12814]], [1024, 768, 1280],
                          [[502629, -759367], [502673, -738819], [502436, -721873], [502040, -707477],
                           [501550, -694977], [501005, -683938], [500427, -674054], [499829, -665103],
                           [499221, -656917], [498607, -649367], [497990, -642351], [497374, -635787],
                           [496758, -629609], [496143, -623759], [495529, -618193], [494916, -612871],
                           [494302, -607758], [493686, -602826], [493068, -598047], [492447, -593400],
                           [491821, -588862], [491188, -584416], [490548, -580043], [489898, -575727],
                           [489237, -571453], [488562, -567206], [487872, -562970], [487164, -558733],
                           [486435, -554479], [485683, -550194], [484905, -545862], [484096, -541467],
                           [483252, -536994], [482369, -532422], [481441, -527734], [480463, -522906],
                           [479425, -517914], [478320, -512730], [477137, -507322], [475864, -501654],
                           [474486, -495680], [472982, -489349], [471331, -482598], [469502, -475350],
                           [467456, -467506], [465143, -458944], [462494, -449499], [459412, -438951],
                           [455755, -426991], [451309, -413162], [445715, -396741]], [0, 0],
                          [644, 367, 860, 413, 527, 149, 1002, 2, 172, 688, 760, 997, 606, 607, 199, 199, 205, 224,
                           225,
                           224, 498, 1023, 857, 463, 423, 857, 463, 423, 858, 463, 423, 858, 462, 423, 858, 463,
                           423,
                           858, 463, 423, 858, 463, 423, 858, 463, 424, 858, 463, 424, 858, 463, 423, 39, 39, 990,
                           991,
                           991, 40, 39, 991, 991, 990, 42, 41, 991, 991, 990, 41, 40, 991, 991, 991, 41, 40, 992,
                           991,
                           990, 41, 40, 992, 991, 991, 41, 40, 992, 991, 990, 41, 40, 991, 991, 991, 41, 40, 991,
                           991,
                           991, 42, 41, 992, 991, 990, 514], 0,
                          hrpt, [0, 0],
                          [[15160, 772, 3117, 12810, 14869], [13355, 5399, 15160, 772, 3117],
                           [12810, 2070, 3865, 5420, 15160], [772, 3118, 12810, 7183, 3584],
                           [29, 15160, 772, 3118, 12810], [4116, 3868, 12032, 15160, 772],
                           [3118, 12810, 286, 3863, 12073]], [
                              [b"\x15\x002/\x04\n", b"\x15\x002/\x04\n", b"\x03\x00\x03?\x033",
                               b"\x03\x00\x03?\x033",
                               b"\x0c\x00\r%\x02\x0c"],
                              [b"\x0c\x00\r%\x02\x0c", b"\x03\x00\x00\x0f", b"\x03\x00\x00\x0f",
                               b"?\x00\x01?2\x11",
                               b"?\x00\x01?2\x11"]],
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                           0, 0,
                           0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                           0, 0,
                           0, 0, 0, 0, 0])],
                        dtype=_SCANTYPE)
        self.data = data
        header = np.array([(b"SSE", b" ", 3, 2003, 164, 22016, 0, 1, b"", b"SSE.HRPT.NN.D21086.S1411.E1416.B8169898.WE",
                            b"B8169898", 7, 0, 3, 4, 26018, 2021, 86, 51110551, 26018, 2021, 86, 51383551, 18, 290, b"",
                            63232, b"", 0, 0, 1639, 1639, 0, 0, 1639, 0, 1640, 0, 0, 0, 0, 0, 0, 0, b"", b"", b"", b"",
                            0, 2021, 50, 0, 0, 0, 0,
                            [[27660, 5090, 166, 0, 0, 0], [27668, 5101, 148, 0, 0, 0], [27657, 5117, 131, 0, 0, 0],
                             [27662, 5103, 148, 0, 0, 0]], [0, 0], [[1303, 79, 2460], [247, 135, 55]],
                            [[265980, -170388, 1003049], [928146, -43725, 1001395], [833253, -25342, 1000944]],
                            [0, 0, 0], b"  GRS 80", 0, 1, b"", 120, 0, 5, 2021, 85, 20805634, 722582600, 150530,
                            9900180, 15435470, 14974490, 31088821, 217697780, -758900, 687823610, 604477400, -387831420,
                            -192264620, 997397, b"", [0, 0, 0, 0, 0], 0, [0, 0, 0, 0, 0], 0, [0, 0, 0, 0, 0], 0,
                            [0, 0, 0, 0, 0], 0, [0, 0, 0, 0, 0], 0, [0, 0, 0, 0, 0], 0, [0, 0, 0, 0, 0], 0,
                            [0, 0, 0, 0, 0], 0, [0, 0, 0, 0, 0], 0, [0, 0, 0, 0, 0], 0, [0, 0, 0, 0, 0], 0,
                            [0, 0, 0, 0, 0], 0, [0, 0, 0, 0, 0], 0, [0, 0, 0, 0, 0], 0, [0, 0, 0, 0, 0], 0,
                            [0, 0, 0, 0, 0], 0, [0, 0, 0, 0, 0], 0, [0, 0, 0, 0, 0], 0, [0, 0, 0, 0, 0], 0,
                            [0, 0, 0, 0, 0], 0, [0, 0, 0, 0, 0], 0, [0, 0, 0, 0, 0], 0)],
                          dtype=_HEADERTYPE)
        self.header = header

        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(mode="wb", delete=False) as fd:
            fd.write(header.tobytes())
            fd.write(np.zeros(22016-_HEADERTYPE.itemsize, dtype=np.uint8).tobytes())
            fd.write(data)
            self.filename = fd.name

    def test_bright_channel2_has_reflectance_greater_than_100(self):
        """Test that a bright channel 2 has reflectances greater that 100."""
        from satpy.readers.aapp_l1b import AVHRRAAPPL1BFile
        from satpy.tests.utils import make_dataid
        file_handler = AVHRRAAPPL1BFile(self.filename, dict(), None)
        data = file_handler.get_dataset(make_dataid(name="2", calibration="reflectance"), dict())
        np.testing.assert_array_less(100, data.values)

    def tearDown(self):
        """Tear down the test case."""
        with suppress(PermissionError):
            os.remove(self.filename)
