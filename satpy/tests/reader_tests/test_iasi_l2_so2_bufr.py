#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019 Satpy developers
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

"""Unittesting the SEVIRI L2 BUFR reader."""

import sys

import numpy as np
from datetime import datetime

#if sys.version_info < (2, 7):
#    import unittest2 as unittest
#else:
import unittest

#try:
from unittest import mock
#except ImportError:
#    import mock




# Test IASI level 2 SO2 product messages

msg={
'unpack': 1,
'inputDelayedDescriptorReplicationFactor':5,
'edition':4,
'masterTableNumber':0,
'bufrHeaderCentre':254,
'bufrHeaderSubCentre':0,
'updateSequenceNumber':0,
'dataCategory':3,
'internationalDataSubCategory':255,
'dataSubCategory':230,
'masterTablesVersionNumber':31,
'localTablesVersionNumber': 0,
'typicalYear': 2020,
'typicalMonth': 2,
'typicalDay': 4,
'typicalHour': 8,
'typicalMinute': 59,
'typicalSecond': 0,
'numberOfSubsets': 120,
'observedData': 1,
'compressedData': 1,
'unexpandedDescriptors': np.array([  
   1007,   1031,  25060,   2019,   2020,   4001,   4002,   4003 ,  4004,   4005,
   4006,   5040, 201133,   5041, 201000,   5001,   6001,   5043 ,  7024,   5021,
   7025,   5022,   7007,  40068,   7002,  15045,  12080, 102000 , 31001,   7007,
  15045],dtype=np.int),
'#1#satelliteIdentifier': 4,
'#1#centre': 254,
'#1#softwareIdentification': 605,
'#1#satelliteInstruments': 221,
'#1#satelliteClassification': 61,
'#1#year': 2020,
'#1#month': 2,
'#1#day': 4,
'#1#hour': 9,
'#1#minute': 1,
'#1#second': 11,
'#1#orbitNumber': 68984,
'#1#scanLineNumber': 447,
'#1#latitude': np.array([
 -33.4055, -33.6659, -33.738 , -33.4648, -33.263 , -33.5027, -33.5673, -33.3172,
 -33.1332, -33.3564, -33.4151, -33.1832, -33.0132, -33.2232, -33.2771, -33.0596,
 -32.903 , -33.1021, -33.1522, -32.9466, -32.7982, -32.9884, -33.0354, -32.8395,
 -32.7005, -32.8832, -32.9276, -32.7399, -32.6061, -32.7826, -32.8251, -32.644
, -32.5168, -32.6883, -32.7292, -32.5537, -32.4261, -32.5934, -32.6331, -32.4621,
 -32.3397, -32.5036, -32.5425, -32.3752, -32.2537, -32.4151, -32.4534, -32.289
, -32.1682, -32.3277, -32.3657, -32.2035, -32.0826, -32.2407, -32.2788, -32.1182,
 -31.9952, -32.1527, -32.1911, -32.0313, -31.9068, -32.0642, -32.1032, -31.9438,
 -31.8147, -31.9727, -32.0127, -31.8529, -31.7177, -31.8769, -31.9181, -31.7573,
 -31.6182, -31.7792, -31.8222, -31.6598, -31.5106, -31.674 , -31.7191, -31.5545,
 -31.3962, -31.5628, -31.6107, -31.4431, -31.2727, -31.4434, -31.4947, -31.3233,
 -31.1375, -31.3131, -31.3686, -31.1926, -30.9867, -31.1684, -31.2293, -31.0476,
 -30.8201, -31.009 , -31.0768, -30.8882, -30.6289, -30.8265, -30.9031, -30.7062,
 -30.4071, -30.6153, -30.7036, -30.4967, -30.146 , -30.3672, -30.4712, -30.2521,
 -29.8276, -30.0649, -30.1911, -29.9569, -29.4268, -29.6844, -29.8436, -29.5903]),
    
'#1#longitude': np.array([ 
  2.53790e+00,  2.49440e+00,  3.08690e+00,  3.12690e+00,  1.15600e+00,
  1.11230e+00,  1.59640e+00,  1.63750e+00, -3.70000e-03, -4.73000e-02,
  3.61900e-01,  4.03500e-01, -1.00010e+00, -1.04340e+00, -6.88300e-01,
 -6.46600e-01, -1.88040e+00, -1.92340e+00, -1.60890e+00, -1.56730e+00,
 -2.66750e+00, -2.71020e+00, -2.42680e+00, -2.38520e+00, -3.38640e+00,
 -3.42890e+00, -3.16970e+00, -3.12830e+00, -4.04920e+00, -4.09150e+00,
 -3.85140e+00, -3.81000e+00, -4.66850e+00, -4.71080e+00, -4.48590e+00,
 -4.44450e+00, -5.25210e+00, -5.29440e+00, -5.08140e+00, -5.03990e+00,
 -5.80970e+00, -5.85220e+00, -5.64840e+00, -5.60670e+00, -6.34640e+00,
 -6.38920e+00, -6.19250e+00, -6.15060e+00, -6.86700e+00, -6.91020e+00,
 -6.71870e+00, -6.67640e+00, -7.37770e+00, -7.42140e+00, -7.23330e+00,
 -7.19050e+00, -7.88100e+00, -7.92530e+00, -7.73920e+00, -7.69570e+00,
 -8.38370e+00, -8.42900e+00, -8.24320e+00, -8.19890e+00, -8.88730e+00,
 -8.93360e+00, -8.74660e+00, -8.70130e+00, -9.39480e+00, -9.44230e+00,
 -9.25260e+00, -9.20620e+00, -9.91570e+00, -9.96460e+00, -9.77050e+00,
 -9.72270e+00, -1.04496e+01, -1.05002e+01, -1.02999e+01, -1.02505e+01,
 -1.10049e+01, -1.10576e+01, -1.08489e+01, -1.07977e+01, -1.15859e+01,
 -1.16409e+01, -1.14216e+01, -1.13682e+01, -1.21993e+01, -1.22570e+01,
 -1.20240e+01, -1.19681e+01, -1.28575e+01, -1.29185e+01, -1.26682e+01,
 -1.26093e+01, -1.35688e+01, -1.36337e+01, -1.33615e+01, -1.32990e+01,
 -1.43504e+01, -1.44199e+01, -1.41196e+01, -1.40529e+01, -1.52201e+01,
 -1.52953e+01, -1.49585e+01, -1.48867e+01, -1.62074e+01, -1.62896e+01,
 -1.59045e+01, -1.58264e+01, -1.73549e+01, -1.74460e+01, -1.69944e+01,
 -1.69085e+01, -1.87277e+01, -1.88302e+01, -1.82832e+01, -1.81873e+01]),

    '#1#fieldOfViewNumber': np.array([
   1,   2,   3,   4,   5,   6,   7,   8,   9,  10,  11 , 12,  13,  14,  15,  16,  17,  18,
  19,  20,  21,  22,  23,  24,  25,  26,  27,  28,  29 , 30,  31,  32,  33,  34,  35,  36,
  37,  38,  39,  40,  41,  42,  43,  44,  45,  46,  47 , 48,  49,  50,  51,  52,  53,  54,
  55,  56,  57,  58,  59,  60,  61,  62,  63,  64,  65 , 66,  67,  68,  69,  70,  71,  72,
  73,  74,  75,  76,  77,  78,  79,  80,  81,  82,  83 , 84,  85,  86,  87,  88,  89,  90,
  91,  92,  93,  94,  95,  96,  97,  98,  99, 100, 101 ,102, 103, 104, 105, 106, 107, 108,
 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119 ,120]),
    
'#1#satelliteZenithAngle': np.array([
 56.64, 56.64 ,58.38, 58.37, 52.15, 52.15, 53.8 , 53.79, 47.84, 47.84, 49.42 ,49.42,
 43.67, 43.67 ,45.21, 45.2 , 39.59, 39.59, 41.1 , 41.09, 35.59, 35.59, 37.08 ,37.07,
 31.65, 31.65 ,33.11, 33.1 , 27.75, 27.75, 29.2 , 29.19, 23.89, 23.89, 25.33 ,25.32,
 20.07, 20.06 ,21.49, 21.48, 16.26, 16.26, 17.67, 17.67, 12.47, 12.47, 13.88 ,13.87,
  8.7 ,  8.7  ,10.1 , 10.1 ,  4.95,  4.95,  6.34,  6.33,  1.33,  1.34,  2.64 , 2.63,
  2.72,  2.73 , 1.43,  1.41,  6.44,  6.45,  5.05,  5.05, 10.19, 10.19,  8.79 , 8.79,
 13.97, 13.98 ,12.57, 12.57, 17.77, 17.77, 16.35, 16.36, 21.58, 21.59, 20.16 ,20.17,
 25.42, 25.43 ,23.99, 24.  , 29.29, 29.29, 27.84, 27.85, 33.21, 33.21, 31.75 ,31.75,
 37.16, 37.17 ,35.68, 35.69, 41.19, 41.2 , 39.69, 39.69, 45.3 , 45.31, 43.76 ,43.77,
 49.52, 49.53 ,47.94, 47.94, 53.89, 53.9 , 52.25, 52.25, 58.48, 58.48, 56.74 ,56.75]),

    
    '#1#bearingOrAzimuth': np.array([
 276.93, 278.61, 278.27 ,276.61, 277.64, 279.42, 279.14, 277.38, 278.22, 280.11,
 279.88, 278.01, 278.69 ,280.72, 280.51, 278.51, 279.09, 281.3 , 281.11, 278.94,
 279.41, 281.83, 281.64 ,279.28, 279.68, 282.36, 282.18, 279.58, 279.88, 282.9
, 282.71, 279.79, 280.02 ,283.49, 283.29, 279.96, 279.98, 284.07, 283.84, 279.96,
 279.84, 284.85, 284.57 ,279.89, 279.4 , 285.9 , 285.49, 279.57, 278.31, 287.59,
 286.87, 278.78, 275.22 ,291.5 , 289.61, 276.76, 252.48, 315.67, 299.21, 268.02,
 117.92,  88.23,  72.78 ,132.31, 109.86,  97.41,  95.43, 111.52, 108.02, 100.14,
  99.35, 108.59, 107.2  ,101.44, 100.97, 107.44, 106.92, 102.37, 102.04, 107.04,
 106.84, 103.07, 102.81 ,106.88, 106.87, 103.65, 103.42, 106.87, 107.  , 104.18,
 103.97, 106.97, 107.2  ,104.69, 104.49, 107.14, 107.44, 105.16, 104.97, 107.35,
 107.74, 105.67, 105.47 ,107.64, 108.11, 106.2 , 105.99, 107.98, 108.54, 106.76,
 106.53, 108.38, 109.06 ,107.39, 107.14, 108.87, 109.7 , 108.13, 107.83, 109.46]),

    '#1#solarZenithAngle': np.array([
 44.36, 44.44, 43.98, 43.89, 45.47, 45.54, 45.16, 45.08, 46.4 , 46.47, 46.14, 46.07,
 47.21, 47.27, 46.99, 46.92, 47.92, 47.98, 47.73, 47.67, 48.56, 48.62, 48.39, 48.33,
 49.15, 49.21, 49.  , 48.94, 49.7 , 49.75, 49.55, 49.5 , 50.21, 50.26, 50.07, 50.02,
 50.69, 50.74, 50.56, 50.51, 51.15, 51.2 , 51.03, 50.98, 51.59, 51.64, 51.48, 51.43,
 52.02, 52.07, 51.91, 51.87, 52.45, 52.5 , 52.34, 52.29, 52.87, 52.92, 52.76, 52.71,
 53.29, 53.34, 53.18, 53.14, 53.71, 53.76, 53.6 , 53.56, 54.14, 54.18, 54.03, 53.98,
 54.58, 54.62, 54.46, 54.41, 55.03, 55.08, 54.91, 54.86, 55.5 , 55.55, 55.37, 55.32,
 55.99, 56.04, 55.85, 55.81, 56.51, 56.56, 56.37, 56.32, 57.08, 57.13, 56.91, 56.86,
 57.69, 57.74, 57.51, 57.46, 58.36, 58.42, 58.16, 58.1 , 59.11, 59.17, 58.88, 58.82,
 59.98, 60.04, 59.7 , 59.64, 60.98, 61.05, 60.65, 60.59, 62.2 , 62.27, 61.78, 61.72]),

    
    '#1#solarAzimuth': np.array([
 78.89, 78.66, 78.16, 78.41, 80.  , 79.8 , 79.4 , 79.62, 80.92, 80.74, 80.4 , 80.6
, 81.69, 81.53, 81.24, 81.42, 82.36, 82.21, 81.96, 82.12, 82.96, 82.82, 82.6 , 82.74,
 83.49, 83.36, 83.16, 83.3 , 83.98, 83.86, 83.68, 83.8 , 84.43, 84.32, 84.15, 84.27,
 84.86, 84.75, 84.59, 84.7 , 85.26, 85.15, 85.  , 85.11, 85.64, 85.54, 85.4 , 85.5
, 86.01, 85.91, 85.77, 85.88, 86.37, 86.28, 86.14, 86.24, 86.73, 86.63, 86.5 , 86.59,
 87.07, 86.98, 86.85, 86.94, 87.42, 87.33, 87.2 , 87.29, 87.77, 87.68, 87.55, 87.64,
 88.13, 88.04, 87.9 , 87.99, 88.49, 88.41, 88.27, 88.36, 88.87, 88.78, 88.64, 88.73,
 89.26, 89.17, 89.02, 89.11, 89.67, 89.59, 89.43, 89.51, 90.11, 90.02, 89.85, 89.94,
 90.58, 90.49, 90.31, 90.4 , 91.09, 91.  , 90.81, 90.89, 91.66, 91.57, 91.35, 91.44,
 92.29, 92.2 , 91.95, 92.04, 93.02, 92.93, 92.64, 92.73, 93.87, 93.79, 93.45, 93.54]),
    
'#1#height': 83270,
'#1#generalRetrievalQualityFlagForSo2': 9,
'#2#height':-1e+100,
'#1#sulphurDioxide': -1e+100,
'#1#brightnessTemperatureRealPart' :np.array([
  0.11,  0.11, -0.07,  0.08,  0.13,  0.15,  0.1 ,  0.06, -0.02, -0.03,  0.08,  0.17,
 -0.05,  0.12,  0.08, -0.06,  0.15,  0.08, -0.04, -0.01,  0.06,  0.17, -0.01,  0.15,
  0.18,  0.05,  0.11, -0.03,  0.09,  0.02,  0.04,  0.1 ,  0.  ,  0.  ,  0.01,  0.18,
 -0.2 ,  0.1 ,  0.  ,  0.13, -0.15,  0.09,  0.09, -0.1 ,  0.04,  0.06, -0.01, -0.03,
 -0.07, -0.05, -0.07, -0.09, -0.03, -0.13, -0.01,  0.1 , -0.21, -0.23, -0.18, -0.08,
 -0.09, -0.19, -0.07, -0.08, -0.19, -0.24, -0.24, -0.05, -0.03, -0.08, -0.01, -0.07,
 -0.03, -0.38, -0.39, -0.22, -0.28, -0.15, -0.1 , -0.26, -0.18, -0.11, -0.31, -0.18,
 -0.19, -0.26, -0.22, -0.19,  0.02, -0.19, -0.01, -0.38, -0.06, -0.34, -0.31, -0.19,
  0.08, -0.05, -0.08,  0.41, -0.19, -0.22, -0.03,  0.11, -0.26, -0.33, -0.08,  0.03,
 -0.05,  0.02,  0.17, -0.1 ,  0.01,  0.01,  0.05,  0.01,  0.15, -0.06, -0.14,  0.38]),
'#3#height': 7000,
'#2#sulphurDioxide': np.array([
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100 ,-1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100 ,-1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100 ,-1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100 ,-1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100 ,-1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100 ,-1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100 ,-1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100 ,-1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100 ,-1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100 ,-1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100 ,-1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100 ,-1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100 ,-1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100 ,-1.0e+100, -1.0e+100,
 -1.0e+100,  2.3e+000, -1.0e+100, -1.0e+100, -1.0e+100 ,-1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100 ,-1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100 ,-1.0e+100, -1.0e+100,
 -1.0e+100]),
'#4#height': 10000,
'#3#sulphurDioxide': np.array([
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100,  8.0e-001, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100]),
'#5#height' :13000,
'#4#sulphurDioxide': np.array([
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100,  5.0e-001, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100]),
'#6#height': 16000,
'#5#sulphurDioxide': np.array([
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100,  4.0e-001, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100]),
'#7#height': 25000,
'#6#sulphurDioxide': np.array([
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100,  5.0e-001, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100,
 -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100, -1.0e+100])
    
}




FILETYPE_INFO = {'file_type':  'seviri_l2_bufr_csr'}

FILENAME_INFO = {'start_time': '20191112000000',
                 'spacecraft': 'MSG4'}
FILENAME_INFO2 = {'start_time': '20191112000000',
                  'spacecraft': 'MSG4',
                  'server': 'TESTSERVER'}
#MPEF_PRODUCT_HEADER = {
#    'NominalTime': datetime(2019, 11, 6, 18, 0),
#    'SpacecraftName': '08',
#    'RectificationLongitude': 'E0415'
#}

DATASET_INFO = {
    'name': 'so2_height_6',
    'file_type': 'iasi_l2_so2_bufr',
    'units': "dobson",
    'resolution': 12000,
    'coordinates': ['longitude', 'latitude'],
    'key': '#6#sulphurDioxide',
    'fill_value': -1.e+100
}

DATASET_ATTRS = {
    'platform_name': 'METOP-2',

}


class TestIasiL2So2Bufr(unittest.TestCase):
    """Test NativeMSGBufrHandler."""

    @unittest.skipIf(sys.platform.startswith('win'), "'eccodes' not supported on Windows")
    def iasi_l2_so2_bufr_test(self, filename):
        """Test the SEVIRI BUFR handler."""
        from satpy.readers.iasi_l2_so2_bufr import IASIL2SO2BUFR
        import eccodes as ec
        buf1 = ec.codes_bufr_new_from_samples('BUFR4_local_satellite')
        print("adding to buf1")
        for key in msg.keys():
            print("key:", key)
            val = msg[key]

            if np.isscalar(val):
                ec.codes_set(buf1, key,val)

            else:
                ec.codes_set_array(buf1, key, val)
        
        

        
        #ec.codes_set(buf1, 'unpack', 1)
        #samp1 = np.random.uniform(low=250, high=350, size=(128,))
        # write the bufr test data twice as we want to read in and the concatenate the data in the reader
        # 55 id corresponds to METEOSAT 8
        #ec.codes_set(buf1, 'satelliteIdentifier', 55)
        #ec.codes_set_array(buf1, '#1#brightnessTemperature', samp1)
        #ec.codes_set_array(buf1, '#1#brightnessTemperature', samp1)

        m = mock.mock_open()
        # only our offline product contain MPEF product headers so we get the metadata from there
        if ('BUFRProd' in filename):
            with mock.patch('satpy.readers.iasi_l2_so2_bufr.np.fromfile') as fromfile:
                fromfile.return_value = MPEF_PRODUCT_HEADER
                with mock.patch('satpy.readers.iasi_l2_so2_bufr.recarray2dict') as recarray2dict:
                    recarray2dict.side_effect = (lambda x: x)
                    fh = IASIL2SO2BUFR(filename, FILENAME_INFO2, FILETYPE_INFO)
                    fh.mpef_header = MPEF_PRODUCT_HEADER

        else:
            # No Mpef Header  so we get the metadata from the BUFR messages
            with mock.patch('satpy.readers.iasi_l2_so2_bufr.open', m, create=True):
                with mock.patch('eccodes.codes_bufr_new_from_file',
                                side_effect=[buf1, None, buf1, None, buf1, None]) as ec1:
                    ec1.return_value = ec1.side_effect
                    with mock.patch('eccodes.codes_set') as ec2:
                        ec2.return_value = 1
                        with mock.patch('eccodes.codes_release') as ec5:
                            ec5.return_value = 1
                            fh = IASIL2SO2BUFR(filename, FILENAME_INFO, FILETYPE_INFO)

        with mock.patch('satpy.readers.iasi_l2_so2_bufr.open', m, create=True):
            with mock.patch('eccodes.codes_bufr_new_from_file',
                            side_effect=[buf1, None, buf1]) as ec1:  # changed from [buf1, buf1, None] to prevent duplication of rows in array
                ec1.return_value = ec1.side_effect
                with mock.patch('eccodes.codes_set') as ec2:
                    ec2.return_value = 1
                    with mock.patch('eccodes.codes_release') as ec5:
                        ec5.return_value = 1
                        z = fh.get_dataset(None, DATASET_INFO)
                        print(z.values)
 


                        self.assertEqual(z.attrs['platform_name'],
                                         DATASET_ATTRS['platform_name'])
                        #self.assertEqual(z.attrs['ssp_lon'],
                        #                 DATASET_ATTRS['ssp_lon'])
                        #self.assertEqual(z.attrs['seg_size'],
                        #                 DATASET_ATTRS['seg_size'])

    def test_seviri_l2_bufr(self):
        """Call the test function."""
        self.iasi_l2_so2_bufr_test('W_XX-EUMETSAT-Darmstadt,SOUNDING+SATELLITE,METOPA+IASI_C_EUMC_20200204091455_68977_eps_o_so2_l2.bin')



def suite():
    """Test suite for test_scene."""
    loader = unittest.TestLoader()
    mysuite = unittest.TestSuite()
    mysuite.addTest(loader.loadTestsFromTestCase(TestIasiL2So2Bufr))
    return mysuite


if __name__ == "__main__":
    # So you can run tests from this module individually.
    unittest.main()
