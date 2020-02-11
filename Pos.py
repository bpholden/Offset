from __future__ import print_function
import ktl
import numpy as np
import sys
import re
import time

class Pos:

    def __init__(self, ra=0., dec=0., pmra=0, pmdec=0):
        self.name = ''
        self.ra = ra
        self.dec = dec
        self.sra = ""
        self.sdec = ""
        self.pmra = pmra
        self.pmdec = pmdec
        self.xpos = 0
        self.ypos = 0
        self.success = False

    def __str__ (self):
        return "<Pos ra=%f dec=%f xpos=%f ypos=%f>" % (self.ra, self.dec,self.xpos,self.ypos)
    

    def parse_string(self,instr,ra=False):
        mtch = re.search("(\-?)(\d+).(\d+).(\d+\.?\d*)",instr)
        if mtch:
            val = float(mtch.group(2)) + float(mtch.group(3))/60 + float(mtch.group(4))/3600
            cinstr = re.sub("\:"," ",instr)
            if len(mtch.group(1)) > 0:
                val *= -1
            if ra:
                val *= 15.
                self.ra = val
                self.sra = cinstr
            else:
                self.dec = val
                self.sdec = cinstr
        return

    def parse_starlist_line(self,inline):
        fields = inline.split()

        self.name = fields[0]
        rastr = "%s:%s:%s" % (fields[1],fields[2],fields[3])
        decstr = "%s:%s:%s" % (fields[4],fields[5],fields[6])
        self.parse_string(rastr,ra=True)
        self.parse_string(decstr)
        strpmra = fields[8]
        strpmdec = fields[9]
        _,self.pmra = strpmra.split("=")
        _,self.pmdec = strpmdec.split("=")

        return 
