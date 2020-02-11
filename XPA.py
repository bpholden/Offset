import os
import subprocess

class XPA():
    """
    The XPA class is a set of helper routines that do standard sort of xpa functions. 
    Currently, it only does the stuff that is done in the autoslitbox.csh script.
    
    The basic routine just makes subprocess check_call with correct arguments.
    The class should be instantated with the name of the XPA connection / ds9 title as the 
    name attribute.
    """
    def __init__(self,name="guider"):
        self.ds9name = name

    def xpaset(self,instr):
        # xpaset -p guider preserve pan yes
        args = instr.split()
        cmdexec = ["/opt/xpa/xpaset","-p",self.ds9name] + args

        try:
            r = subprocess.check_call(cmdexec)
        except subprocess.CalledProcessError:
            return 1
        return 0

    def preserve(self):
        rv = self.xpaset("preserve pan yes")
        if rv == 0:
            return self.xpaset("preserve regions yes")
        return 1
    def loadregion(self,regionname):
        rv = self.xpaset("regions delete all")
        
        if os.path.exists(regionname) and rv == 0:
            return self.xpaset("regions load " + regionname)
        else:
            return 1
        
    def center(self,guidex,guidey):    

        instr = "pan to %.2f %.2f physical" % (guidex,guidey)
        return self.xpaset(instr)

    def zoom(self,zoom=4):
        instr = "zoom to %d" %(zoom)
        return self.xpaset(instr)

        
