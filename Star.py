from __future__ import print_function
import sys
import re


def checkflag(value,regexp,default):
    try:
        match = re.search(regexp,value)
        if match:
            return match.group(1)
        else:
            return default
    except:
        return default
    
def int_or_default(value,default=0):
    try:
        attr = int(value)
    except:
        attr = default
    return attr

def float_or_default(value,default=0.0):
    try:
        rv = float(value)
    except:
        rv = default
    return rv

class Star:

    def __init__(self, starlist_line=''):
        self.line = starlist_line
        self.name = ''
        self.ra = 0.
        self.dec = 0.
        self.sra = ""
        self.sdec = ""
        self.pmra = 0.0
        self.pmdec = 0.0

        self.raoff = None
        self.decoff = None
        
        self.I2 = "N"
        self.vmag = -10
        self.do = False
        self.texp = 0
        self.tottime = 0
        self.decker="W"
        self.count=0
        self.foc=0
        self.owner='public'
        self.lamp='none'
        self.uth='00'
        self.utm='00'
        self.block=''
        
        self.blank=False
        self.guide=False
        self.offset=False


        self.parse()

    def __repr__(self):
        rv = "< Star %s " % (self.name)
        rv += "%s %f " % (self.sra, self.ra)
        rv += "%s %f " % (self.sdec, self.dec)
        if self.raoff is not None:
            rv+= "%.2f " % (self.raoff)
        if self.raoff is not None:
            rv+= "%.2f " % (self.decoff)
        rv += "%s %s %s %s %s "  % (  self.I2, self.owner, str(self.blank), str(self.guide), str(self.do))
        rv += "%.1f %d %.1f %d %s>" % (self.texp, self.count, self.tottime, self.foc, self.decker)
        return rv
        

    def parse(self, starlist_line=None):
        if starlist_line:
            self.line = starlist_line
        split_line = self.line.split("#")
        data = split_line[0]
        if len(data) <= 0:
            return
        fields = data.split()
        if len(fields) < 12:
            return
        self.name = fields[0]
        self.sra = "%s:%s:%s" % (fields[1],fields[2],fields[3])
        self.sdec = "%s:%s:%s" % (fields[4],fields[5],fields[6])

        try:
            self.ra = float(fields[1]) + float(fields[2])/60. + float(fields[3])/3600.
            self.ra *= 15.0
        except:
            self.ra = -100.0

        try:
            self.dec = float(fields[4])
            if self.dec < 0:
                self.dec -= float(fields[5])/60. + float(fields[6])/3600.
            else:
                self.dec += float(fields[5])/60. + float(fields[6])/3600.
        except:
            self.dec = -100.0
        
        # fields[7] is meaningless
        fields_dict = dict()
        for i in range(8,len(fields)):
            key,value = fields[i].split("=")
            fields_dict[key] = value

        if 'pmra' in fields_dict.keys():
            self.pmra = float_or_default(fields_dict['pmra'])
        if 'pmdec' in fields_dict.keys():
            self.pmdec = float_or_default(fields_dict['pmdec'])
        if 'texp' in fields_dict.keys():
            self.texp = float_or_default(fields_dict['texp'])
        if 'vmag' in fields_dict.keys():
            self.vmag = float_or_default(fields_dict['vmag'],20.)

            
        if 'count' in fields_dict.keys():
            self.count = int_or_default(fields_dict['count'])

        if 'foc' in fields_dict.keys():
            self.foc = int_or_default(fields_dict['foc'])
            
        if 'I2' in fields_dict.keys():
            self.I2 = checkflag(fields_dict['I2'],"\A(y|Y|n|N)","N")
        if 'decker' in fields_dict.keys():
            self.decker = checkflag(fields_dict['decker'],"\A(W|N|T|S|O|K|L|M|B)","B")
        if 'owner' in fields_dict.keys():
            self.owner = checkflag(fields_dict['owner'],"\A(\w+)","public")
        if 'utm' in fields_dict.keys():
            self.utm = checkflag(fields_dict['utm'],"\A(\d+)","00")
        if 'uth' in fields_dict.keys():
            self.uth = checkflag(fields_dict['uth'],"\A(\d+)","00")

        if 'do' in fields_dict.keys():
            doflag = checkflag(fields_dict['do'],"\A(\w+)","")
            if doflag == "":
                self.do = False
            else:
                self.do = True


        if 'guide' in fields_dict.keys():
            flag =  checkflag(fields_dict['guide'],"\A(y|Y|n|N)","N")
            if flag == 'Y' or flag == 'y':
                self.guide = True
            else:
                self.guide = False
                

        if 'raoff' in fields_dict.keys():
            self.raoff = float_or_default(fields_dict['raoff'],None)
        if 'decoff' in fields_dict.keys():
            self.decoff = float_or_default(fields_dict['decoff'],None)
            
        if self.guide and self.decoff is not None and self.raoff is not None:
            self.offset = True
            
        if 'blank' in fields_dict.keys():
            flag =  checkflag(fields_dict['blank'],"\A(y|Y|n|N)","N")
            if flag == 'Y' or flag == 'y':
                self.blank = True
            else:
                self.blank = False
                
        if self.blank and self.decoff is not None and self.raoff is not None:
            self.offset = True


            
        self.tottime = (self.texp) * self.count  + 100 
        if self.count > 1:
            self.tottime += 40*(self.count - 1)
        if self.blank is True:
            self.tottime = 3600.

        return



if __name__ == "__main__":
    
    line="HR223 00 48 50.2 +50 58 5.4 2000 pmra=30.84 pmdec=-10.02 vmag=4.901 texp=900 I2=Y lamp=none uth=2 utm=43 expcount=1e+09 decker=W do= count=2 foc=2 owner=public # end"
    star = Star(starlist_line=line)
    print(star)
    line="HR223 00 48 50.2 +50 58 5.4 2000 pmra=30.84 pmdec=-10.02 vmag=4.901 texp=900 I2=Y lamp=none uth=2 utm=43 expcount=1e+09 decker=W do= count=2 foc=2 owner=public decoff=-3.0 raoff=+0.1 guide=y # end"
    star = Star(starlist_line=line)
    print(star)
    line="HR223 00 48 50.2 +50 58 5.4 2000 pmra=30.84 pmdec=-10.02 vmag=4.901 texp=900 I2=Y lamp=none uth=2 utm=43 expcount=1e+09 decker=W do=a count=2 foc=2 owner=public decoff=3.0 raoff=-0.1 blank=y # end"
    star = Star(starlist_line=line)
    print(star)

    
    import FakeWCS

    wcs = FakeWCS.WCS()
    
    wcs.crval1 = star.ra 
    wcs.crval2 = star.dec 

    x,y = wcs.s2p(star.ra,star.dec)
    print(x,y)
    print(wcs.p2s(x,y))
              
    wcs.crval1 = star.ra + star.raoff/3600.
    wcs.crval2 = star.dec + star.decoff/3600.

    x,y = wcs.s2p(star.ra,star.dec)
    print (x,y)
    print(wcs.p2s(x,y))
