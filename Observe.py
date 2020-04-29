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
    havektl = True
except:
    print('Cannot import ktl')
    havektl = False
import APFTask
    
import numpy as np

sys.path.append("/home/holden/src")
import apflog

import WCS
import Star
import GuidePos
import Exposure
import Spectrometer
from KeywordHandle import readem, readit, writeem
import CmdExec 


class Observe:
    def __init__(self,parent='scriptobs',fake=False):

        self.parent = parent
        self.fake = fake
        
        self.apfschedule = ktl.Service('apfschedule')
        self.ownrhint = self.apfschedule['OWNRHINT']
        self.origowner = self.ownrhint.read()

        self.checkapf = ktl.Service('checkapf')
        self.dmtime = self.checkapf['DMTIME']
        self.dmtime.monitor()
        self.dmtime.callback(self.dmtimeMon)
        
        self.eostele = ktl.Service('eostele')

        self.apfguide = ktl.Service('apfguide')
        self.guidex = self.apfguide['GUIDEX']
        self.guidey = self.apfguide['GUIDEY']
        self.sourcex = self.apfguide['GUIDEX']
        self.sourcey = self.apfguide['GUIDEY']

        self.mode = self.apfguide['MODE']
        self.maxradius = self.apfguide['MAXRADIUS']
        self.maxradius.write(210,binary=True)
        
        self.eosgcam = ktl.Service('eosgcam')
        self.gexptime = self.eosgcam['gexptime']
        self.sumframe = self.eosgcam['sumframe']
        self.gain = self.eosgcam['gcgain']
        
        self.zps = APFTask.get("scriptobs",["AZZPT","ELZPT"])

        self.record = 'yes'
        
        self.wcs = WCS.WCS()
        self.star = None
        self.spectrom = Spectrometer.Spectrometer(parent=parent,fake=fake)


    def __repr__(self):
        return "<Observe %s %s >" % (self.parent,self.fake)

    def log(self, msg, level='Notice', echo=True):
        """Wraps the APF.log function. Messages are logged as current parent.
        """

        apflog.apflog(str(msg), level=level, echo=echo)

    def message(self, msg):
        """Wrapper that writes to current task message keyword.
        """

        try:
            APFTask.set(self.parent,'MESSAGE',msg)
        except:
            self.log("Cannot communicate with APFTask", level='error',echo=True)
        
    def updateRoboState(self):
        if self.fake:
            return
        try:
            self.checkapf['ROBOSTATE'].write('%s operating' % (self.parent),wait=True,timeout=20)
        except:
            self.log("Cannot update robostate!!!",level='error')
            
    # Callback for Deadman timer
    def dmtimeMon(self,dmtime):
        if dmtime['populated'] == False:
            return
        try:
            if float(dmtime) < 300.:
                self.updateRoboState()
        except Exception, e:
            self.log("Exception in dmtimemon: %s" % (e), level='error')



    def setupStar(self):
        """
        setupStar(self)
        
        Writes the self.star values to the EOS Telescope
        Service.
        
        """

        if self.star is None:
            return False
        
        rv = writeem(self.eostele,'targname',self.star.name)
        if rv:
            rv = writeem(self.eostele,'targra',self.star.sra)
        else :
            return
        writeem(self.eostele,'targdec',self.star.sdec)
        writeem(self.eostele,'targmuar',self.star.pmra)
        writeem(self.eostele,'targmuad',self.star.pmdec)
        writeem(self.eostele,'targtype',"RA/DEC")

        return True

    def setupGuider(self):
        """
        setupGuider(self)
        Writes guider values to standard defaults, 
        1 second epxosure, 1 frame, and medium gain.
        """
        
        self.gexptime.write(1,binary=True)
        self.sumframe.write(1,binary=True)
        self.gain.write(2,binary=True)                

    def setupOffsets(self):
        """
        setupOffsets(self)
        Zeros out the Azimuth and Elevation offsets for the telescope
        and restores them to default values (from keywords)
        """
        writeem(self.eostele,'ntazoff',self.zps["AZZPT"])
        writeem(self.eostele,'nteloff',self.zps["ELZPT"])

    def setupRDOffsets(self,raoff,decoff):
        """
        setupRDOffsets(self, raoff, decoff)
        Writes raoff and decoff to the RA Offset and Declination Offset 
        values for the EOS telescope service.
        """
        
        writeem(self.eostele,'ntraoff',raoff)
        writeem(self.eostele,'ntdecoff',decoff)


    def findNearbyStar(self):
        """
        pstar = findNearbyStar(self)

        Returns a Star object (pstar)

        This searches the bright star catalog for a pointing reference 
        near the position of the star that is part of the current 
        Observe object.

        Returns None if self.star is not defined or cannot find
        a star.

        """
        if self.star is None:
            return None
        
        (targra_h,targra_m,targra_s) = self.star.sra.split(":")
        (targdec_d,targdec_m,targdec_s) = self.star.sdec.split(":")
        instr = "/usr/local/lick/bin/robot/closest %s %s %s %s %s %s 5 1 8 " % (targra_h,targra_m,targra_s,targdec_d,targdec_m,targdec_s)
        self.log(instr,echo=True)
        inargs = instr.split()
        starcat = "/usr/local/lick/data/apf/StarCatalog.dat"
        fp_starcat = open(starcat)
        # note skipping apftask do, this should be quick
        p = subprocess.Popen(inargs, stdin=fp_starcat, stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd="./")

        out, err = p.communicate()
        ret_code = p.returncode
        if ret_code != 0:
            return None

        starvals = out.split()
        pstar = Star.Star()
        pstar.name = starvals[0]
        pstar.ra = float(starvals[1])*3.819718
        pstar.dec = float(starvals[2])*57.295779
        pstar.pmra = float(starvals[4])
        pstar.pmdec = float(starvals[5])
        
        return pstar
    


    
    def acquirePointingRef(self):

        pstar = self.findNearbyStar()

        if pstar is None:
            return False, -1

        instr = '/usr/local/lick/bin/robot/slewlock reference %s %f %f %f %f 210' % (pstar.name,pstar.ra,pstar.dec,pstar.pmra,pstar.pmdec)
        if self.fake:
            self.log("Would have run %s" % (instr), echo=True)
            r = True
            code= 0
        else:
            r, code = CmdExec.operExec(instr,self.checkapf)
            
        return r, code


    
    def takeExposures(self):

        if self.fake:
            return
        self.updateRoboState()
        spectraexp = Exposure.Exposure(self.star.texp,self.star.name,count=self.star.count,parent=self.parent,fake=self.fake,record=self.record)
        if self.star.blank and self.star.texp > 600:
            self.log("An exposure time of %d is greater than the recommended 600 secs for a blank field" % (self.star.texp))
            self.message("An exposure time of %d is greater than the recommended 600 secs for a blank field" % (self.star.texp))
            
        self.ownrhint.write(self.star.owner)
        if self.star.blank:
            ktl.write('apfguide','xpose_enable','false')
            self.log("Disabling exposure meter for blank field")
            self.message("Disabling exposure meter for blank field")
        else:
            ktl.write('apfguide','xpose_enable','true')
        

        # check ucam status
        combo_ps = spectraexp.comb.read(binary=True)
        if combo_ps > 0 and self.fake is not True:
            if combo_ps == 1:
                self.updateRoboState()
                rv = self.ucamStart(spectraexp.comb)
            else:
                self.updateRoboState()
                rv = self.ucamReboot(spectraexp.comb)
                if rv is False:
                    return rv
                self.updateRoboState()
                rv = self.ucamPowercycle(spectraexp.comb)
                if rv is False:
                    return rv
                rv = self.ucamStart(spectraexp.comb)
            if rv is False:
                return rv
            
        APFTask.phase(self.parent,"%d Spectra of %s" % (self.star.count,self.star.name))
        rv = spectraexp.expose()
        return rv


    def configureSpecDefault(self,wait=False):
        
        if self.fake:
            return
        self.spectrom.read()
        self.spectrom.enable()
        self.spectrom.state['HALOGEN2'] = 'Off'
        self.spectrom.state['THORIUM1'] = 'Off'
        self.spectrom.state['THORIUM2'] = 'Off'
        self.spectrom.state['HATCHPOS'] = 'Open'
        self.spectrom.state['CALMIRRORNAM'] = 'Out'
        self.spectrom.set_to_state(wait=wait)


    def configureDeckerI2(self,wait=False):
        self.updateRoboState()
        APFTask.set(self.parent,suffix='MESSAGE',value='Moving I2 cell')	
        if self.fake:
            return
            
        if self.star.I2 == "Y" or self.star.I2 == "y":
            rv = self.spectrom.iodine(wait=wait)
        else:
            rv = self.spectrom.iodine(position="Out",wait=wait)
        if rv is False:
            return False
        
        self.updateRoboState()

        
        if self.star.decker not in ["Pinhole","K","L","M","S","W","T","B","N","O"]:
            message("Decker %s not a recognized value" % (self.star.decker))
            return False
    
        rv = self.spectrom.decker(name=self.star.decker,wait=False)
        if rv is False:
            apflog("Moved failed",level='error',echo=True)
            return False
    
        return rv



    def ucamStart(self,comb):
        if fake:
            # would have restarted software
            self.log("Would have started UCAM software ")
            return True
        else:
            self.log("Starting UCAM ",echo=True)
            ktl.write("apftask","UCAMLAUNCHER_UCAM_COMMAND","run")
            nv = comb.waitFor(" == Ok",timeout=20)
        return nv


    def ucamReboot(self,comb):

        if self.fake:
            # would have restarted software

            self.log("Would have rebooted UCAM host",echo=True)
            return True
        
        try:
            ktl.write("apftask","UCAMLAUNCHER_UCAM_COMMAND","stop")
            self.log("Stopping UCAM",echo=True)
            v= comb.waitFor(" == MissingProcesses",timeout=10)
            self.log("Rebooting UCAM host",echo=True)
            ktl.write("apftask","UCAMLAUNCHER_UCAM_COMMAND","reboot")
            expression = "$apftask.ucamlauncher_status != Running"
#            rv = APFTask.waitfor(self.parent,True,expression=expression,timeout=300)
            time.sleep(300)
            expression = "$apftask.ucamlauncher_status == Running"
            if APFTask.waitfor(self.parent,True,expression=expression,timeout=300):            
                ktl.write("apftask","UCAMLAUNCHER_UCAM_COMMAND","start")
                return True
            else:
                self.log("UCAM host reboot failure, UCAM not running" , level="alert", echo=True)

        except:	      
            self.log("UCAM status bad, cannot restart")
            return False

    
    def ucamRestart(self,comb):

        if fake:
            # would have restarted software
                self.log("Would have restarted UCAM software ")
                return True
    
        try:
            self.message("Stopping UCAM")
            ktl.write("apftask","UCAMLAUNCHER_UCAM_COMMAND","stop")
            self.log("Stopping UCAM ",echo=True)
            v= comb.waitFor(" == MissingProcesses",timeout=10)
            if v:
                APF.log("Restarting UCAM ",echo=True)
                message(parent,"Restarting UCAM")
                ktl.write("apftask","UCAMLAUNCHER_UCAM_COMMAND","run")
                nv = comb.waitFor(" == Ok",timeout=20)
            else:
                self.log(parent,"Failure to stop UCAM?!? apfucam.COMBO_PS = %s" % (comb.read()),level='error')
                
                nv = False
        except:	      
            self.log(parent,"Exception UCAM status bad, cannot restart",level='error')
            nv = False

        if nv:
            return nv
        else:
            return self.ucamReboot(comb)
        
        return False

    def ucamPowercycle(self):


        if self.fake:
            self.message("would have executed @LROOT/bin/robot/robot_power_cycle_ucam")
            return True
        else:
            val = CmdExec.operExec("@LROOT/bin/robot/robot_power_cycle_ucam",self.checkapf)
            if val > 0:
                self.log("power cycle of UCAM failed")
                return False
            return True
        
        return True



    def shouldFocus(self):
        if self.gexptime <= 1:
            return True
        else:
            return False
    
if __name__ == "__main__":

    obs = Observe()
    print(obs)
