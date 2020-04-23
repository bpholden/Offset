from __future__ import print_function

import os

import time
import sys
sys.path.append("../")

import ktl
import APFTask

import Star
import GuidePos
import WCS
import Observe
import CmdExec
from apflog import apflog

fn = '/home/holden/starlists/double.lst'
fp = open(fn)
lines = fp.readlines()
fp.close()

guidestar = Star.Star(starlist_line=lines[0])
targetstar = Star.Star(starlist_line=lines[1])

parent = 'scriptobs'
#parent = 'example'
APFTask.establish(parent,os.getpid())
sx = ktl.read('apftask','slitbox_cenx')
sy = ktl.read('apftask','slitbox_ceny')
ktl.write('apfguide','guidex',sx)
ktl.write('apfguide','guidey',sy)

observe = Observe.Observe(parent=parent,fake=False)
guidepos = GuidePos.GuidePos()
guidepos.start()


observe.star = guidestar

if observe.fake is False:
    r, code = CmdExec.operExec("prep-obs",observe.checkapf)
#APFTask.set(parent,'VMAG',observe.star.vmag)
ktl.write('apftask','scriptobs_vmag',observe.star.vmag)
observe.updateRoboState()
observe.configureSpecDefault()
rv = observe.configureDeckerI2()
observe.updateRoboState()

APFTask.phase(parent,"Windshielding")
if parent == 'scriptobs':
    APFTask.set(parent,'windshield','Disable')
            
observe.setupStar()
windstr = 'windshield.csh %.1f 0 0 0' % (targetstar.tottime)
r, code = CmdExec.operExec(windstr,observe.checkapf)

slewstr = 'slew --targname %s -r %s -d %s --pm-ra-arc %s --pm-dec-arc %s' % (observe.star.name,observe.star.sra, observe.star.sdec, observe.star.pmra, observe.star.pmdec)
CmdExec.operExec(slewstr,observe.checkapf)
observe.spectrom.adctrack()
if observe.fake is not True:
    r, code = CmdExec.operExec('autoexposure',observe.checkapf)
    r, code = CmdExec.operExec('centerup',observe.checkapf)
    r, code = CmdExec.operExec('focus_telescope',observe.checkapf)
    r, code = CmdExec.operExec('centerwait',observe.checkapf)
    observe.mode.write('guide')

guidestar.ra,guidestar.dec = guidepos.wcs.p2s(float(observe.guidex.read()),float(observe.guidey.read()))

observe.star = targetstar
slewstr = 'slew --targname %s -r %s -d %s --pm-ra-arc %s --pm-dec-arc %s' % (observe.star.name,observe.star.sra, observe.star.sdec, observe.star.pmra, observe.star.pmdec)
observe.mode.write('off')
if observe.fake is False:
    CmdExec.operExec(slewstr,observe.checkapf)
guidepos.star = guidestar
guidepos.offset = True
observe.mode.write('guide')


time.sleep(targetstar.tottime)
guidepos.offset = False
observe.mode.write('off')
time.sleep(10)
gx = ktl.read('apfguide','guidex')
gy = ktl.read('apfguide','guidey')
print(gx,gy)
