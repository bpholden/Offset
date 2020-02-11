from __future__ import print_function
import sys
import re
import time
import atexit

import ktl
import numpy as np

import Pos
import WCS 
import Slitbox



def shutdown():
    try:
        apfguide['guidex'].write(guidex,wait=False)
        apfguide['guidey'].write(guidey,wait=False)
    except:
        pass
    return

apfguide = ktl.Service('apfguide')
guidex = apfguide['GUIDEX'].read()
guidey = apfguide['GUIDEY'].read()

                        
ktl.write('apfguide','eos_guider_orient',20.0)
ktl.write('apfguide','normal_is_flipped',False)


if __name__ == "__main__":

    atexit.register(shutdown)
    
    if len(sys.argv) < 3:
        print ("needs ra and dec strings")
        sys.exit()
    ras = str(sys.argv[1])
    decs = str(sys.argv[2])

    if len(sys.argv) == 4:
        fake = False
    else:
        fake = True
        apfguide['MAXRADIUS'].write(30,binary=True)
    
    wcs = WCS.WCS()
    pos = Pos.Pos()
    print (wcs)
    print (pos)
    pos.parse_string(ras,ra=True)
    pos.parse_string(decs)
    print (pos)

    print(apfguide['GUIDEX'].read(),apfguide['GUIDEY'].read())
    while True:
        x,y = pos.s2p(wcs)
        print (pos)
        r,d = pos.p2s(wcs)
        print (r,d)
        if not fake:
            apfguide['GUIDEX'].write(pos.xpos,binary=True)
            apfguide['GUIDEY'].write(pos.ypos,binary=True)            
        time.sleep(5)
