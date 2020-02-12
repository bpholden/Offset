#! /opt/kroot/bin/kpython
from __future__ import print_function
import os
import sys
import re
import time
import atexit
import signal
import subprocess
import argparse

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
import CmdExec
from KeywordHandle import readem, readit, writeem




###
origowner = ''
success = False
def shutdown():
    if success == True:
        status = 'Exited/Success'
    else:
        status = 'Exited/Failure'

    try:
        ktl.write('apfschedule','ownrhint',origowner,timeout=0)
    except:
        pass


    try:
        ktl.write('apfguide','maxradius',256,timeout=0)
    except:
        pass

    try:
        if ktl.read('checkapf','instr_perm',binary=True) and ktl.read('checkapf','instrele',binary=True) == 1:
            ktl.write('apfmot','adcmod','Track',timeout=0)
    except:
        pass

    try:
        if ktl.read('apfucam','Event',binary=True,timeout=0) <= 2:
            ktl.write('apfucam','stop',True,timeout=0)
    except:
        pass
    
    try:
        APFTask.set(parent, 'STATUS', status)
    except:
        print ('Exited/Failure')
        
    return

def signalShutdown(signal,frame):

    open_ok = ktl.read('checkapf','open_ok',timeout=0)
    move_perm = ktl.read('checkapf','move_perm',timeout=0)
    instr_perm = ktl.read('checkapf','instr_perm',timeout=0)
    apflog("OPEN_OK= %s  MOVE_PERM= %s INSTR_PERM= %s" \
               %(open_ok,move_perm,instr_perm), echo=True)

    shutdown()

def parseArgs():


    parser = argparse.ArgumentParser(description="Set default options")
    parser.add_argument('-t', '--test', action='store_true', help="Starts in test mode. No modification to telescope, instrument, or observer settings will be made.")

    return opt
    
def focusTel(observe):
    autofoc = ktl.read('apftask','SCRIPTOBS_AUTOFOC',timeout=2)
    if observe.star.foc > 0 or observe.autofoc == "robot_autofocus_enable":
        APFTask.phase(parent,"Check/Measure_focus")
        if observe.star.foc < 2:
            r, code = CmdExec.operExec('focus_telescope',observe.checkapf,fake=observe.fake)
        else:
            r, code = CmdExec.operExec('focus_telescope --force',observe.checkapf,fake=observe.fake)
        if r is False:
            return r
    r, code = CmdExec.operExec('centerwait',observe.checkapf,fake=observe.fake)
    return r


if __name__ == "__main__":


    opts = parseArgs()
    if opts.test:
        parent='example'
    else:
        parent = 'scriptobs'

    atexit.register(shutdown)
    signal.signal(signal.SIGINT,  signalShutdown)
    signal.signal(signal.SIGTERM, signalShutdown)
    
        
    try:
        apflog("Attempting to establish apftask as %s" % parent)
        APFTask.establish(parent, os.getpid())
    except Exception as e:
        apflog("Cannot establish as %s: %s." % (parent,e), echo=True)
        sys.exit("Couldn't establish APFTask %s" % parent)
    
    APFTask.phase(parent,"Reading star list and arguments")

    observe = Observe.Observe(parent=parent,fake=opt.test)
    origowner = observe.origowner
    guidepos = GuidePos.GuidePos()
    
    APFTask.step(parent,0)

    APFTask.set(parent,'line_result',0)
    ndone = 0
    gstar = None
    guidepos.start()
    
    r, code = CmdExec.operExec("prep-obs",observe.checkapf,fake=observe.fake)
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
                r, code = CmdExec.operExec(windstr,observe.checkapf,fake=observe.fake)
                if r is False:
                    if observe.star.blank:
                        acquire_success = False
                    APFTask.set(parent,'line_result','ERR/WINDSHIELD')
                    continue

                rv = observe.spectrom.check_states(keylist=['DECKERNAM','IODINENAM'])
                if rv is False:
                    observe.log("Instrument move failed",level='error',echo=True)
                    if observe.star.blank:
                        acquire_success = False
                    APFTask.set(parent,'line_result','ERR/SPECTROMETER')
                    continue
            
                if observe.star.do:
                    r, code = observe.acquirePointingRef()
                    if r is False:
                        # one can always hope
                        observe.log("Pointing star acquisition failed, continuing", level='error', echo=True)
                        
                    observe.setupGuider()
                # slew to star - centerup and autoexposure

                slewstr = 'slew --targname %s -r %s -d %s --pm-ra-arc %s --pm-dec-arc %s' % (observe.star.name,observe.star.sra, observe.star.sdec, observe.star.pmra, observe.star.pmdec)
                if observe.fake:
                    observe.log("Would have executed %s" % (slewstr),echo=True)
                else:
                    CmdExec.operExec(slewstr,observe.checkapf,fake=observe.fake)

                # set the ADC to tracking
                observe.spectrom.adctrack()
                # waitfor ?
            
                APFTask.phase(parent,"Autoexposure")
                if observe.fake:
                    observe.log("Would have executed %s" % ('autoexposure'),echo=True)
                    r=True
                else:
                    r, code = CmdExec.operExec('autoexposure',observe.checkapf,fake=observe.fake)
                
                if r is False:
                    APFTask.set(parent,'line_result','Failed')
                    if observe.star.blank:
                        acquire_success = False
                    continue
            
                APFTask.phase(parent,"Centering")
                r, code = CmdExec.operExec('centerup',observe.checkapf,fake=observe.fake)
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

                if observe.fake:
                    continue
                else:
                    observe.mode.write('guide')

                if observe.star.blank:
                    acquire_success= True
                APFTask.set(parent,'message','Acquired')
                    
                if observe.star.guide:
                    gstar = Star.Star(starlist_line=observe.star.line)
                elif observe.star.blank is False and observe.star.guide is False:
                    gstar = None
                    if observe.star.count > 0 and observe.fake is False:
                        observe.takeExposures()
                    
                APFTask.set(parent,'line_result','Success')

            elif gstar is not None and observe.star.blank is False:
                # do not reset guider, already at correct exposure for current guide star
                # do not zero out offset values
                if observe.fake is False:
                    mode.write('off')

                if observe.star.offset is True:
                    if observe.fake:
                        apflog('eostele.NTRAOFF =%.3f eostele.NTDECOFF = %.3f' % (observe.star.raoff,observe.star.decoff))
                    else:
                        writeem(eostele,'ntraoff',observe.star.raoff)
                        writeem(eostele,'ntdecoff',observe.star.decoff)
                    # waitfor Tracking
                    # watifor Slewing
                else:
                    slewstr = 'slew --targname %s -r %s -d %s --pm-ra-arc %s --pm-dec-arc %s' % (observe.star.name,observe.star.sra, observe.star.sdec, observe.star.pmra, observe.star.pmdec)
                    CmdExec.operExec(slewstr,observe.checkapf,fake=observe.fake)
                # set the ADC to tracking
                spectra.adctrack()

                guidepos.star = gstar
                guiderad = 30
                if observe.fake:
                    apflog("Would have started guiding with a %f pixel radius" %(guiderad))
                else:
                    apfguide['MAXRADIUS'].write(guiderad,binary=True)
                    mode.write('guide')
                
                if observe.star.count > 0:
                    if observe.fake:
                        apflog("Would have taken %d exposures" % (observe.star.count))
                    else:
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

                if observe.star.offset is True:
                    writeem(eostele,'ntraoff',observe.star.raoff)
                    writeem(eostele,'ntdecoff',observe.star.decoff)
                    # waitfor Tracking
                    # watifor Slewing
                else:
                    slewstr = 'slew --targname %s -r %s -d %s --pm-ra-arc %s --pm-dec-arc %s' % (observe.star.name,observe.star.sra, observe.star.sdec, observe.star.pmra, observe.star.pmdec)
                    CmdExec.operExec(slewstr,observe.checkapf)
                # set the ADC to tracking

                observe.takeExposures()
            
                observe.updateRoboState()
            APFTask.set(parent,'line_result','Success')

            
success = True
sys.exit('Done')
