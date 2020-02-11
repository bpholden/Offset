from __future__ import print_function
import ktl
import numpy as np

# helper functions that monitor WCS service from SLA, no math here.

class WCS:

    def __init__(self):

        self.apfgwcs = ktl.Service('apfgwcs')
        self.cd1_1 = self.apfgwcs['CD1_1S']
        self.cd1_2 = self.apfgwcs['CD1_2S']
        self.cd2_1 = self.apfgwcs['CD2_1S']
        self.cd2_2 = self.apfgwcs['CD2_2S']
        self.crval1 = self.apfgwcs['CRVAL1S']
        self.crval2 = self.apfgwcs['CRVAL2S']
        self.crpix1 = self.apfgwcs['CRPIX1P']
        self.crpix2 = self.apfgwcs['CRPIX2P']
        
        self.cd1_1.monitor()
        self.cd1_2.monitor()
        self.cd2_1.monitor()
        self.cd2_2.monitor()
        self.crval1.monitor()
        self.crval2.monitor()
        self.crpix1.monitor()
        self.crpix2.monitor()


    def __str__ (self):
        return "<WCS %f %f %f %f %f %f %f %f>" % (self.cd1_1, self.cd1_2,self.cd2_1,self.cd2_2,self.crval1, self.crval2, self.crpix1, self.crpix2)


    def s2p(self,ra,dec):
        dp = dec - self.crval2
        dr = ra - self.crval1
        dr *= np.cos(dec*np.pi/180.)

        ds = np.matrix([[dp],[dr]])
        
        cd = np.matrix([ [ float(self.cd1_1), float(self.cd1_2)] , [ float(self.cd2_1), float(self.cd2_2)]])

        icd = cd.I
        dx = icd * ds
        x = dx + np.matrix([[self.crpix1],[self.crpix2] ])
        return float(x[0]), float(x[1])


    def p2s(self,x,y):
        dX = np.matrix([[x - self.crpix1], [y - self.crpix2]] )
       
        cd = np.matrix([ [ float(self.cd1_1), float(self.cd1_2)] , [ float(self.cd2_1), float(self.cd2_2)]])

        icd = cd.I
        dS = cd * dX
        dec = self.crval2 + float(dS[1])
        ra  = self.crval1 + float(dS[0])/np.cos(dec*np.pi/180.)
        return ra, dec

