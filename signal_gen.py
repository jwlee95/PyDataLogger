#!/usr/bin/env python
"""
-----------------------------------------------------------------
Copyright (c) 2015 Jeong-Whan Lee. All rights reserved.

 This program or module is free software: you can redistribute it and/or
 modify it under the terms of the GNU General Public License as published
 by the Free Software Foundation, either version 2 of the License, or
 version 3 of the License, or (at your option) any later version. It is
 provided for educational purposes and is distributed in the hope that
 it will be useful, but WITHOUT ANY WARRANTY; without even the implied
 warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
 the GNU General Public License for more details.
-----------------------------------------------------------------
@author: Jeong-whan Lee - Ivan (jwlee95@gmail.com)
@Created: Apr 12 15:41:15 2015
-----------------------------------------------------------------
Revision:

-----------------------------------------------------------------
"""
__author__ = 'Jeong-whan Lee'

from math import cos, sin, pi
import numpy as np


class SignalGen():

    def __init__(self, freq):

        self.a1 = self.b0 = self.yn0 = self.yn1 = self.yn2 = 0.0
        self.T0 = 1.0/500.0

        self.F0 = freq
        self.a1 = 2.0 * cos(pi * 2 * self.F0 * self.T0)
        self.b0 = sin(2*pi * self.F0 * self.T0)
        self.yn2 = 0.0 # Initial value: y[0] = 0
        self.yn1 = self.b0  # Initial value: y[1] = b0

    def forward(self):
        self.yn0 = self.a1 * self.yn1 - self.yn2
        self.yn2 = self.yn1
        self.yn1 = self.yn0
        return self.yn0

    def reset(self):
        self.a1 = 2.0 * cos( 2 * pi * self.F0 * self.T0)
        self.b0 = sin(2*pi * self.F0 * self.T0)
        self.yn2 = 0.0 # Initial value: y[0] = 0
        self.yn1 = self.b0  # Initial value: y[1] = b0

    def getSignal(self, no):
        sig = np.zeros(no)
        for i in range(no):
            sig[i] = self.forward()
        return sig


if __name__ == '__main__':

    sg = SignalGen(20)
    for i in range(100):
        print "Data = %5.3f" % sg.forward()

    print sg.getSignal(100)