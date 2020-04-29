import time
import threading

import ktl
import APF

import WCS
import Star

class GuidePos(threading.Thread):
    def __init__(self,parent='slitbox'):
        threading.Thread.__init__(self)
        self.setDaemon(True)

        self.apfguide = ktl.Service('apfguide')
        self.guidex = self.apfguide['GUIDEX']
        self.guidey = self.apfguide['GUIDEY']
        self.guidex.monitor()
        self.guidey.monitor()

        self.apftask = ktl.Service('apftask')
        self.cenx = self.apftask['SLITBOX_CENX']
        self.ceny = self.apftask['SLITBOX_CENY']
        self.cenx.monitor()
        self.ceny.monitor()


        self.wcs = WCS.WCS()
        self.star = None
        self.update = False
        self.offset = False

    def __repr__(self):
        return "<GuidePos guidex=%.2f guidey=%.2f slitx=%.2f slity=%.2f offset=%s update=%s>" % (self.guidex,self.guidey,self.cenx,self.ceny,self.offset,self.update)

    def log(self,instr,level='info'):
        """ Wrapper for the logger du jour"""
        #        print(level,instr)
        APF.log(instr,level=level,echo=True)
    
    def run(self):
        """

        Operationally, this is just a while loop. 
        """
        if self.wcs is None:
            self.wcs = WCS.WCS()
        
        while True:
            
            if self.star is not None:
                try:
                    x,y = self.wcs.s2p(self.star.ra,self.star.dec)
                    self.guidex.write(x,binary=True)
                    self.guidey.write(y,binary=True)
                    self.update = True
                    time.sleep(.1)
                except:
                    pass
            else:
                if self.update:
                    self.guidex.write(self.cenx)
                    self.guidey.write(self.ceny)
                    self.update = False

if __name__ == "__main__":
    
    apfguide = ktl.Service('apfguide')
    cenx = apfguide['GUIDEX']
    ceny = apfguide['GUIDEY']
    cenx.monitor()
    ceny.monitor()

    time.sleep(1)
    print (cenx, ceny)
    time.sleep(1)

    gp = GuidePos()
    gp.wcs = WCS.WCS()
    gstar = Star.Star()
    gstar.ra = float(gp.wcs.crval1)
    gstar.dec = float(gp.wcs.crval2)
    gp.start()
    time.sleep(.1)

    gp.offset = False
    print gp
    time.sleep(.1)
    gp.offset = True
    gp.star = gstar
    while float(cenx) > 0 and float(ceny) > 0:
        print(gp)
        time.sleep(1)

    gp.star = None
    gp.offset = False
    time.sleep(1.6)
    print gp
