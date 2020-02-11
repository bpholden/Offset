import os
import re
import shutil
import threading

import ktl
import APFTask

import XPA

class Slitbox(threading.Thread):
    """The Slitbox class is a separate thread that monitors the apfmot keywords appropriate for 
    updating the slitbox region. 
    """
    def __init__(self,parent='slitbox'):
        threading.Thread.__init__(self)
        self.setDaemon(True)

        self.xpa = XPA.XPA()
        self.parent=parent
        
        self.apfmot = ktl.Service('apfmot')
        self.deckersta = self.apfmot['DECKERSTA']
        self.decker = self.apfmot['DECKERNAM']
        self.iodinesta = self.apfmot['IODINESTA']
        self.iodine = self.apfmot['IODINENAM']
        
        self.eosgcam = ktl.Service('eosgcam')
        self.amplifier = self.eosgcam['IROPORT']
        self.amp = self.amplifier.read(binary=True)


        self.apfguide = ktl.Service('apfguide')
        self.guidex = self.apfguide['GUIDEX']
        self.guidey = self.apfguide['GUIDEY']
        self.regionfile = self.apfguide['REGIONFILE']        


        self.apftask = ktl.Service('apftask')
        self.cenx = self.apftask['SLITBOX_CENX']
        self.ceny = self.apftask['SLITBOX_CENY']
        self.cenx.monitor()
        self.ceny.monitor()
        
        self.regiondir = "@LROOT/data/apfguide/slitbox"
        self.regionfile = ""
        self.fpath = ""

        self.outfile = "/tmp/apf_active_region.reg"

        self.set_postfix()


    def __str__(self):
        # makes a string for debugging showing the important contents of the object
        return "< %s %s %f %f >" % (self.parent,self.fpath,self.cenx,self.ceny)

    def __repr__(self):
        return self.__str__()
        
    def set_postfix(self):
        """Reads the amplifier keyword and changes the postfix/suffix of the region name to the appropiate value
        The postfix is an attribute, but set_regionnfilename must be called to make this attribute change the region file name.
        """
        # this changes the sufix/postfix when the amplifier changes 
        try:
            self.amp = self.amplifier.read(binary=True)
            if self.amp == 0:
                self.postfix = "_chgmult"
            else:
                self.postfix = ""

        except:
            self.postfix = ""
            self.log("Cannot read eosgcam.AMPLIFIER",level='error')
        
    def set_regionfilename(self):
        """Reads in the appropriate apfmot keywords and combines those with the regiondir and 
        postfix to generate the final region file name. 
        """

        self.set_postfix()
        
        try:
            deckername = self.decker.read()
        except:
            self.regionfile = ""
            self.log("Cannot read apfmot keywords",level='error')
            return
        deckerfields = deckername.split()
        short_name = deckerfields[0]
        if short_name == 'Home':
            self.regionfile = ""
            return
        try:
            self.regionfile = "apfguidercam_slit"
            self.regionfile += short_name + "_box_"
            self.regionfile += self.iodine.read()
            self.regionfile += self.postfix + ".reg"
            self.fpath = os.path.join(self.regiondir,self.regionfile)
        except:
            self.regionfile = ""
            self.log("Cannot read apfmot keywords",level='error')

            

    def get_guidecen(self):
        """ Reads in the region file and parses it. The last box entry are set to the 
        central x and y pixel values. These are keywords for the APFTASK SLITBOX.
        """
        if os.path.exists(self.fpath):
            with open(self.fpath) as fp:
                contents = fp.readlines()
            for c in contents:
                mtch = re.search("box\((\d+\.?\d*)\,(\d+\.?\d*)",c)
                if mtch:
                    try:
                        self.cenx.write(float(mtch.group(1)))
                        self.ceny.write(float(mtch.group(2)))
                    except:
                        self.cenx.write(mtch.group(1))
                        self.ceny.write(mtch.group(2))
                        self.log("Cannot convert %s and/or %s to a float" % (self.cenx,self.ceny),level='error')
                        
        else:
            self.log("Cannot read %s" % (self.fpath),level='error')

            
    def cp_regionfile(self):
        """Copies the region file to the tmp directory."""
        if os.path.exists(self.outfile):
            try:
                os.unlink(self.outfile)
            except Exception as e:
                self.log("Cannot delete %s: %s" % (self.outfile,e),level='error')


        if os.path.exists(self.fpath):
            try:
                shutil.copy(self.fpath,self.outfile)
            except Exception as e:
                self.log("Cannot copy %s to %s: $s" % (self.fpath,self.outfile,e),level='error')

    def log(self,instr,level='info'):
        """ Wrapper for the logger du jour"""
        #        print(level,instr)
        APF.log(instr,level=level,echo=True)
    
    def run(self):
        """
        This spawns the thread that this the slitbox instance. 
        Operationally, this is just a collection of waitFors and 
        a while loop. 
        """


        self.xpa.preserve()

        # these calls initialize the object but does not actually change anything

        self.set_regionfilename()
        self.get_guidecen()

        
        while True:
            expression = "$apfmot.DECKERSTA != 4 or $apfmot.IODINESTA != 4 or $eosgcam.IROPORT != %d" % (self.amp)
            rv = APFTask.waitFor(self.parent,True,expression=expression,timeout=120)
            
            if rv:
                expression = "$apfmot.DECKERSTA == 4 and $apfmot.IODINESTA == 4"
                rv = APFTask.waitFor(self.parent,True,expression=expression,timeout=120)
                if rv:
                    self.set_regionfilename()
                    self.get_guidecen()
                    self.cp_regionfile()
                    self.xpa.loadregion(self.outfile)
                    self.xpa.center(self.cenx,self.ceny)
                    self.xpa.zoom()
                else:
                    self.log("Timed out waiting for apfmot stages to be ready",level='error')

if __name__ == "__main__":
    parent = 'example'
    APFTask.establish(parent,os.getpid())
    slitbox = Slitbox(parent=parent)
    slitbox.regiondir = "/usr/local/lick/data/apfguide/slitbox/"
    slitbox.start()
    while True:
        APFTask.wait(parent,True,timeout=60)
