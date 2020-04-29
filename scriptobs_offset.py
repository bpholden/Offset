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
from Offset import Observe
import CmdExec
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
    parser.add_argument('-f', '--file', default=None, help="Starts in test mode. No modification to telescope, instrument, or observer settings will be made.")
    opt = parser.parse_args()
    return opt
    
def focusTel(observe):
    autofoc = ktl.read('apftask','SCRIPTOBS_AUTOFOC',timeout=2)
    if observe.star.foc > 0 or autofoc == "robot_autofocus_enable":
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


    opt = parseArgs()
    if opt.test:
        parent='example'
    else:
        parent = 'scriptobs'

    if opt.file:
        if os.path.exists(opt.file):
            fp = open(opt.file)
        else:
            print("File %s does not exist" % (opt.file))
            sys.exit()
    else:
        fp = sys.stdin
        
    # basic signal handling
    # should exit on most 
        
    atexit.register(shutdown)
    signal.signal(signal.SIGINT,  signalShutdown)
    signal.signal(signal.SIGTERM, signalShutdown)

    # task setup
            
    try:
        apflog("Attempting to establish apftask as %s" % parent,echo=True)
        APFTask.establish(parent, os.getpid())
    except Exception as e:
        apflog("Cannot establish as %s: %s." % (parent,e), echo=True)
        sys.exit("Couldn't establish APFTask %s" % parent)
    
    APFTask.phase(parent,"Reading star list and arguments")

    # These are the two objects that important
    # Observe handles a lot of details of observing, and points
    # to the current star being observed, holds a lot of the
    # scriptobs parameters
    #
    # GuidePos is the guider position and can be set to a guide
    # star on the slit or off
    
    observe = Observe(parent=parent,fake=opt.test)
    origowner = observe.origowner
    observe.record='no'
    
    guidepos = GuidePos()
    
    APFTask.step(parent,0)
    if observe.fake is False:
        APFTask.set(parent,'line_result',0)
    ndone = 0
    gstar = None
    acquire_success = False
    guidepos.start()
    
    r, code = CmdExec.operExec("prep-obs",observe.checkapf,fake=observe.fake)
    with fp as txt:
        for line in txt:
            observe.star = Star(starlist_line=line.strip())
            
            ndone = ndone + 1
            if observe.fake is False:
                APFTask.set(parent,"lines_done",ndone)
                APFTask.step(parent,ndone)
                APFTask.set(parent,suffix='LINE',value=observe.star.line)	
            
            if observe.star.blank is False and gstar is None:
                # this is not a blank field - there is a star to be observed
                APFTask.phase(parent,"Acquiring star %s" % (observe.star.name))
                acquire_success= False

                observe.setupGuider() # sets guider values to default
                observe.setupOffsets() # zero out Az/El offsets
                if observe.fake is False:
                    observe.mode.write('off') # stop guiding for acquisition
                    APFTask.set(parent,'VMAG',observe.star.vmag) # for autoexposure

                APFTask.phase(parent,"Configuring instrument")
                observe.configureSpecDefault()
                rv = observe.configureDeckerI2(wait=False)
                observe.updateRoboState() # this is hitting the deadman switch

                APFTask.phase(parent,"Windshielding")
                if observe.fake is False:
                    APFTask.set(parent,'windshield','Disable')
            
                observe.setupStar() # just configures eostele for windshield for slew
                windstr = 'windshield.csh %.1f 0 0 0' % (observe.star.tottime)
                r, code = CmdExec.operExec(windstr,observe.checkapf,fake=observe.fake)
                if r is False:
                    APFTask.set(parent,'line_result','ERR/WINDSHIELD')
                    continue

                # earlier spectrometer moves were nowait moves, spectrometer
                # should be ready by now
                rv = observe.spectrom.check_states(keylist=['DECKERNAM','IODINENAM'])
                if rv is False:
                    observe.log("Instrument move failed",level='error',echo=True)
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
                    continue
            
                APFTask.phase(parent,"Centering")
                r, code = CmdExec.operExec('centerup',observe.checkapf,fake=observe.fake)
                if r is False:
                    APFTask.set(parent,'line_result','Failed')
                    continue

                if observe.gexptime.read(binary=True) <= 1.0:
                    r = focusTel(observe)
                    if r is False:
                        APFTask.set(parent,'line_result','Failed')
                        continue

                if observe.fake is False:
                    observe.mode.write('guide')

 
                acquire_success= True
                APFTask.set(parent,'message','Acquired')
                
                observe.updateRoboState()
                
                if observe.star.guide:
                    gstar = Star(starlist_line=observe.star.line)
                else:
                    gstar = None
                    
                if observe.star.count > 0:
                    observe.takeExposures()

                observe.updateRoboState()
                if observe.fake is False:
                    APFTask.set(parent,'line_result','Success')

            elif gstar is not None or observe.star.blank:
                # do not reset guider, already at correct exposure for current guide star
                # do not zero out offset values
                if observe.fake is False:
                    observe.mode.write('off')
                if acquire_success is False:
                    continue

                specstr = 'modify -s eostele targname="%s"' % (observe.star.name)
                CmdExec.operExec(specstr,observe.checkapf)
                    
                if observe.star.blank:
                    APFTask.phase(parent,"Moving to blank field")
                    # skip blanks after an unsuccessful acquisition
                else:
                    APFTask.phase(parent,"Moving to target star from guide star")
                    
                if observe.star.offset is True:
                    if observe.fake:
                        apflog('eostele.NTRAOFF =%.3f eostele.NTDECOFF = %.3f' % (observe.star.raoff,observe.star.decoff),echo=True)
                    else:
                        writeem(eostele,'ntraoff',observe.star.raoff)
                        writeem(eostele,'ntdecoff',observe.star.decoff)
                        expression = "$eostele.AZSSTATE == Tracking && $eostele.ELSSTATE == Tracking"
                        rv = APFTask.waitfor(parent,True,expression=expression,timeout=300)            
                        if rv is False:
                            APFTask.set(parent,'line_result','Failure')
                            continue
                else:
                    slewstr = 'slew --targname %s -r %s -d %s --pm-ra-arc %s --pm-dec-arc %s' % (observe.star.name,observe.star.sra, observe.star.sdec, observe.star.pmra, observe.star.pmdec)
                    CmdExec.operExec(slewstr,observe.checkapf,fake=observe.fake)
                # set the ADC to tracking
                observe.spectrom.adctrack()

                if observe.star.blank:
                    if gstar is not None:
                        gstar = None
                else:
                    guidepos.star = gstar
                    guiderad = 30
                    if observe.fake:
                        apflog("Would have started guiding with a %f pixel radius" %(guiderad),echo=True)
                    else:
                        apfguide['MAXRADIUS'].write(guiderad,binary=True)
                        observe.mode.write('guide')
                        
                observe.updateRoboState()

                if observe.star.count > 0:
                    if observe.fake:
                        apflog("Would have taken %d exposures" % (observe.star.count),echo=True)
                    else:
                        if observe.takeExposures():
                            APFTask.set(parent,'line_result','Success')
                        observe.mode.write('Off')
                    gstar = None
                    guidepos.star = None
            
                observe.updateRoboState()
                
            APFTask.set(parent,'line_result','Success')

            
success = True
sys.exit('Done')
