#! @KPYTHON@
from __future__ import print_function
import sys
import re
import time
import atexit
import functools

import APFTask
import ktl
import numpy as np

import Pos
import WCS 
import Slitbox

def message(parent,msg):
    APFTask.set(parent,suffix='MESSAGE',value=msg)	
    return

def shutdown():
    try:
        apfguide['guidex'].write(guidex,wait=False)
        apfguide['guidey'].write(guidey,wait=False)
    except:
        pass

    try:
        APFTask.set(parent, 'STATUS', 'Exited/Failure')
    except:
        print ('Exited/Failure')

    return


def control_watch(keyword,parent):
    if keyword['populated'] == False:
        return
    try:
        value = keyword['binary']
        if value == 2:
            try:
                APF.log("Aborted by APFTask")
                APFTask.set(parent,suffix='STATUS',value='Exited/Failure')
            except:
                print("Aborted by APFTask")
            os.kill(os.getpid(),signal.SIGINT)
        elif value == 1:
            try:
                APFTask.set(parent,suffix='STATUS',value='PAUSED')
                # this task does nothing but fiddle bits so no actual
                # pausing is required
            except:
                APF.log("Failure to set STATUS in APFTask",level=error)
                os.kill(os.getpid(),signal.SIGINT)

        else:
            try:
                APFTask.set(parent,suffix='STATUS',value='Running')
            except:
                subp.kill()
                APF.log("Failure to set STATUS in APFTask",level=error)

    except:
        return


####


if __name__ == "__main__":

    #    parent = 'slitbox'
    parent = 'example'
    try:
        APFTask.establish(parent,os.getpid())
    except Exception, e:
        estr = "Cannot establish connection with APFTask: %s" % (e)
        APF.log(estr,level="error")
        sys.exit(estr)
    
    atexit.register(shutdown)
    APFTask.phase(parent,"Initializing")
    
    cw = functools.partial(control_watch,parent=parent)
    control.monitor()
    control.callback(cw)
        
    wcs = WCS.WCS()
    pos = Pos.Pos()
    slitbox = Slitbox.Slitbox()

    apfguide = ktl.Service('apfguide')
    guidex = apfguide['GUIDEX']
    guidey = apfguide['GUIDEY']
    guidex.monitor()
    guidey.monitor()

    ktl.write('apfguide','eos_guider_orient',20.0)
    ktl.write('apfguide','normal_is_flipped',False)
    
    APFTask.phase(parent,"Looping")
    offset_guiding = False

    slitbox.run() # this spawns the thread that computes the
    # correct slitbox and sets the CENX and CENY keywords
    # those are the values that should be used when not offset guiding
    
    while True:
        ras = ''
        decs = ''
        if ras != '' and decs != '':
            offsetg_uiding = True
            pos.parse_string(ras,ra=True)
            pos.parse_string(decs)
            msg = "cur guidex = %.3f and cur guidey = %.3f" % (apfguide['GUIDEX'].read(),apfguide['GUIDEY'].read())
            message(msg)
            APFTask.phase(parent,"Offset guiding")
            
        else:
            offset_guiding = False
            APFTask.phase(parent,"Slit center guiding")
            
            
        if offset_guiding:
            pos.xpos, pos.ypos = wcs.s2p(pos.ra,pos.dec)
            print (pos)
            r,d = wcs.p2s(pos.xpos,pos.ypos)
            print (r,d)
            if not fake:
                apfguide['GUIDEX'].write(pos.xpos,binary=True)
                apfguide['GUIDEY'].write(pos.ypos,binary=True)

            APFTask.wait(parent,True,timeout=1)
                
        else:
            if guidex != slitbox.cenx or guidey != slitbox.ceny:
                apfguide['GUIDEX'].write(slitbox.cenx)
                apfguide['GUIDEy'].write(slitbox.ceny)
            APFTask.wait(parent,True,timeout=1)
        
