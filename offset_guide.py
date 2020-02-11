from __future__ import print_function
import os
import sys
import re
import time
import atexit
import subprocess

import ktl
import numpy as np

import Pos
import WCS 
from CmdExec import cmdexec

def shutdown():
    try:
        apfguide['guidex'].write(guidex,wait=False)
        apfguide['guidey'].write(guidey,wait=False)
    except:
        pass
    return

apfguide = ktl.Service('apfguide')
guidex = apfguide['GUIDEX']
guidey = apfguide['GUIDEY']
mode = apfguide['MODE']

def parse_starlist_line(inline):
    fields = inline.split()
    pos = Pos.Pos()
    pos.name = fields[0]
    rastr = "%s:%s:%s" % (fields[1],fields[2],fields[3])
    decstr = "%s:%s:%s" % (fields[4],fields[5],fields[6])
    pos.parse_string(rastr,ra=True)
    pos.parse_string(decstr)
    strpmra = fields[8]
    strpmdec = fields[9]
    _,pos.pmra = strpmra.split("=")
    _,pos.pmdec = strpmdec.split("=")

    return pos
    
    
def read_starlist(filename):

    # HR5867 15 46 11.254 15 25 18.6 2000 pmra=65.38 pmdec=-38.61 vmag=3.66 texp=1200 I2=Y lamp=none uth=4 utm=58 expcount=1e+09 decker=N do=Y count=2 foc=0 owner=public

    fp = open(filename)
    # assume first two lines
    try:
        gline = fp.readline()
        tline = fp.readline()
    except:
        print("Not enough lines in %s" % (filename))
        sys.exit()
    fp.close()
    gpos = parse_starlist_line(gline)
    tpos = parse_starlist_line(tline)

    return gpos, tpos
    
    
def parse_args(argv):
    if len(argv) < 4:
        print (argv[0] + ": starlist")
        sys.exit()

    filename = sys.argv[1]
    if os.path.exists(filename) is False:
        sys.exit()

    gpos, tpos = read_starlist(filename)
        
    if len(argv) == 3:
        fake = False
    else:
        fake = True

    return gpos, tpos, fake

if __name__ == "__main__":

    atexit.register(shutdown)

    gpos, tpos, fake = parse_args(sys.argv)
    
    wcs = WCS.WCS()

    mode.write('off')

    # first slew to gpos - centerup and autoexposure
    specstr = 'modify -s eostele targname="%s" targra="%s" targdec="%s" targmuar="%s"  targmuad="%s"  targplax="0.0" targtype="RA/DEC"' % (gpos.name, gpos.sra, gpos.sdec, gpos.pmra, gpos.pmdec)
    r,code = cmdexec(specstr)
    if r is False:
        print("Cannot execute modify!")
        sys.exit()

    # need to set AZZPT and ELZPT
    # modify -s eostele ntazoff=$AZZPT nteloff=$ELZPT ntoffset=true
        
    windstr = 'windshield.csh 3600 0 0 0'
    r,code = cmdexec(windstr)
    if r is False:
        print("Cannot execute windshield.csh")
        sys.exit()
    r,code = cmdexec('autoexposure')
    if r is False:
        print("Cannot execute autoexposure")
        sys.exit()
    r,code = cmdexec('centerup')
    if r is False:
        print("Cannot execute centerup")
        sys.exit()

    # second offset from gpos to tpos
    mode.write('off')
    specstr = 'modify -s eostele targname="%s"' % (tpos.name)
    r,code = cmdexec(specstr)
    if r is False:
        print("Cannot execute modify")
        sys.exit()
    slewstr = 'slew -r %s -d %s --pm-ra-arc %s --pm-dec-arc %s' % (tpos.sra, tpos.sdec, tpos.pmra, tpos.pmdec)
    r,code = cmdexec(slewstr)
    if r is False:
        print("Cannot execute slew")
        sys.exit()
    # third guide on gpos with tpos in slit center

    apfguide['MAXRADIUS'].write(30,binary=True)
    mode.write('Guide')
    
    print(guidex.read(),guidey.read())
    while True:
        x,y = gpos.s2p(wcs)
        print (pos)
        r,d = gpos.p2s(wcs)
        print (r,d)
        guidex.write(gpos.xpos,binary=True)
        guidey.write(gpos.ypos,binary=True)            
        time.sleep(1)
