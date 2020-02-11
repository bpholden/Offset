#! /opt/kroot/bin/kpython
from __future__ import print_function
import os
import sys
import re
import time
import atexit
import subprocess


try:
    import ktl
    import APFTask
    from apflog import apflog
    havektl = True
except:
    print('Cannot import ktl')
    havektl = False
    
import numpy as np

from Offset import Pos
from Offset import WCS
from Offset import Star
from Offset import GuidePos
import Exposure
import Spectrometer
from KeywordHandle import readem, readit, writeem




###

success = False
def shutdown():
    if success == True:
        status = 'Exited/Success'
    else:
        status = 'Exited/Failure'

    try:
        ktl.write('apfschedule','ownrhint',origowner)
    except:
        pass
        
    try:
        APFTask.set(parent, 'STATUS', status)
    except:
        print ('Exited/Failure')
        
    return

def parse_args(argv):

        
    if len(argv) == 1:
        fake = False
    else:
        fake = True

    return fake

def focusTel(observe):
    autofoc = ktl.read('apftask','SCRIPTOBS_AUTOFOC',timeout=2)
    if observe.star.foc > 0 or observe.autofoc == "robot_autofocus_enable":
        APFTask.phase(parent,"Check/Measure_focus")
        if observe.star.foc < 2:
            r, code = CmdExec.operExec('focus_telescope',observe.checkapf)
        else:
            r, code = CmdExec.operExec('focus_telescope --force',observe.checkapf)
        if r is False:
            return r
    r, code = CmdExec.operExec('centerwait',observe.checkapf)
    return r


if __name__ == "__main__":

    
    atexit.register(shutdown)
    parent = 'scriptobs'
    
    APFTask.phase(parent,"Reading star list and arguments")
    fake = parse_args(sys.argv)

    observe = Observe.Observe(parent=parent,fake=fake)
    guidepos = GuidePos.GuidePos()
    
    APFTask.step(parent,0)

    APFTask.set(parent,'line_result',0)
    ndone = 0
    gstar = None
    guidepos.start()
    
    r, code = CmdExec.operExec("prep-obs",observe.checkapf)
    with sys.stdin as txt:
        for line in txt:
            observe.star = Star.Star(starlist_line=line.strip())
            
            ndone = ndone + 1
            APFTask.set(parent,"lines_done",ndone)

            APFTask.step(parent,ndone)
        

            APFTask.set(parent,suffix='LINE',value=observe.star.line)	
            
            if observe.star.blank is False and gstar is None:
                # this is not a blank field
                APFTask.phase(parent,"Acquiring star %s" % (observe.star.name))

                observe.setupGuider()
                observe.setupOffsets()
                observe.mode.write('off')
                APFTask.set(parent,'VMAG',observe.star.vmag)

                APFTask.phase(parent,"Configuring instrument")
                observe.configureSpecDefault()
                rv = observe.configureDeckerI2()
                observe.updateRoboState()

                APFTask.phase(parent,"Windshielding")
                APFTask.set(parent,'windshield','Disable')
            
                observe.setupStar()
                windstr = 'windshield.csh %.1f 0 0 0' % (observe.star.tottime)
                r, code = CmdExec.operExec(windstr,observe.checkapf)
                if r is False:
                    if observe.star.blank:
                        acquire_success = False
                    continue

                rv = observe.spectrom.check_states(keylist=['DECKERNAM','IODINENAM'])
                if rv is False:
                    observe.log("Instrument move failed",level='error',echo=True)
                    if observe.star.blank:
                        acquire_success = False
                    continue
            
                if observe.star.do:
                    r, code = observe.acquirePointingRef()
                    if r is False:
                        # one can always hope
                        observe.log("Pointing star acquisition failed, continuing", level='error', echo=True)
                        
                    observe.setupGuider()
                # slew to star - centerup and autoexposure

                slewstr = 'slew --targname %s -r %s -d %s --pm-ra-arc %s --pm-dec-arc %s' % (observe.star.name,observe.star.sra, observe.star.sdec, observe.star.pmra, observe.star.pmdec)
                CmdExec.operExec(slewstr,observe.checkapf)

                # set the ADC to tracking
                observe.spectrom.adctrack()
                # waitfor ?
            
                APFTask.phase(parent,"Autoexposure")
                r, code = CmdExec.operExec('autoexposure',observe.checkapf)
                if r is False:
                    APFTask.set(parent,'line_result','Failed')
                    if observe.star.blank:
                        acquire_success = False
                    continue
            
                APFTask.phase(parent,"Centering")
                r, code = CmdExec.operExec('centerup',observe.checkapf)
                if r is False:
                    if observe.star.blank:
                        acquire_success = False
                    APFTask.set(parent,'line_result','Failed')
                    continue

                if observe.gexptime.read(binary=True) <= 1.0:
                    r = focusTel(observe)
                    if r is False:
                        APFTask.set(parent,'line_result','Failed')
                        if observe.star.blank:
                            acquire_success = False
                        continue
                    
                observe.mode.write('guide')

                if observe.star.blank:
                    acquire_success= True
                APFTask.set(parent,'message','Acquired')
                    
                if observe.star.guide:
                    gstar = Star.Star(starlist_line=observe.star.line)
                elif observe.star.blank is False and observe.star.guide is False:
                    gstar = None
                    if observe.star.count > 0:
                        observe.takeExposures()
                    
                APFTask.set(parent,'line_result','Success')

            elif gstar is not None and observe.star.blank is False:
                # do not reset guider, already at correct exposure for current guide star
                # do not zero out offset values
                mode.write('off')

                if observe.star.offset is True:
                    writeem(eostele,'ntraoff',observe.star.raoff)
                    writeem(eostele,'ntdecoff',observe.star.decoff)
                    # waitfor Tracking
                    # watifor Slewing
                else:
                    slewstr = 'slew --targname %s -r %s -d %s --pm-ra-arc %s --pm-dec-arc %s' % (observe.star.name,observe.star.sra, observe.star.sdec, observe.star.pmra, observe.star.pmdec)
                    CmdExec.operExec(slewstr,observe.checkapf)
                # set the ADC to tracking
                spectra.adctrack()

                guidepos.star = gstar

                apfguide['MAXRADIUS'].write(30,binary=True)
                mode.write('guide')
                
                if observe.star.count > 0:
                    if observe.takeExposures():
                        APFTask.set(parent,'line_result','Success')
                    mode.write('Off')
                    gstar = None
                    guidepos.star = None
                    
                
            elif observe.star.blank is True:
                if gstar is not None:
                    gstar = None
                if acquire_success is False:
                    continue
                # skip blanks after an unsuccessful acquisition
                
                observe.mode.write('off')
                specstr = 'modify -s eostele targname="%s"' % (observe.star.name)
                CmdExec.operExec(specstr,observe.checkapf)

                APFTask.phase(parent,"Slewing to blank field")
                slewstr = 'slew -r %s -d %s --pm-ra-arc %s --pm-dec-arc %s' % (observe.star.sra, observe.star.sdec, observe.star.pmra, observe.star.pmdec)
                r, code = CmdExec.operExec(slewstr,observe.checkapf)

                observe.takeExposures()
            
                observe.updateRoboState()
                APFTask.set(parent,'line_result','Success')

            
success = True
sys.exit('Done')
