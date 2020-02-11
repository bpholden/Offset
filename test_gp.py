import Star
import GuidePos
import WCS
import Observe

fn = 'double.lst'
fp = open(fn)
lines = fp.readlines()
fp.close()

guidestar = Star(starlist_line=lines[0])
targetstar = Star(starlist_line=lines[1])

parent = 'scriptobs'
observe = Observe.Observe(parent=parent)
guidepos = GuidePos.GuidePos()
guidepos.start()

observe.star = guidestar

r, code = CmdExec.operExec("prep-obs",observe.checkapf)
APFTask.set(parent,'VMAG',observe.star.vmag)
observe.updateRoboState()
observe.configureSpecDefault()
rv = observe.configureDeckerI2()
observe.updateRoboState()

APFTask.phase(parent,"Windshielding")
APFTask.set(parent,'windshield','Disable')
            
observe.setupStar()
windstr = 'windshield.csh %.1f 0 0 0' % (observe.star.tottime)
r, code = CmdExec.operExec(windstr,observe.checkapf)

slewstr = 'slew --targname %s -r %s -d %s --pm-ra-arc %s --pm-dec-arc %s' % (observe.star.name,observe.star.sra, observe.star.sdec, observe.star.pmra, observe.star.pmdec)
CmdExec.operExec(slewstr,observe.checkapf)
observe.spectrom.adctrack()
r, code = CmdExec.operExec('autoexposure',observe.checkapf)
r, code = CmdExec.operExec('centerup',observe.checkapf)
r, code = CmdExec.operExec('focus_telescope',observe.checkapf)
r, code = CmdExec.operExec('centerwait',observe.checkapf)
observe.mode.write('guide')

guidestar.ra,guidestar.dec = guidepos.wcs.p2s(float(observe.guidex),float(observe.guidey))

observe.star = targetstar
slewstr = 'slew --targname %s -r %s -d %s --pm-ra-arc %s --pm-dec-arc %s' % (observe.star.name,observe.star.sra, observe.star.sdec, observe.star.pmra, observe.star.pmdec)
observe.mode.write('off')
CmdExec.operExec(slewstr,observe.checkapf)
guidepos.star = guidestar
guidepos.offset = True
observe.mode.write('guide')


