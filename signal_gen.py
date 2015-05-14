__author__ = 'Jeong whan'

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