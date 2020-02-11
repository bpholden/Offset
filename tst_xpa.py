import XPA

xpa = XPA.XPA()

xpa.preserve()
fn = "/usr/local/lick/data/apfguide/slitbox/apfguidercam_slitW_box_Out.reg"
xpa.loadregion(fn)
xpa.center(268.6,257.825)
xpa.zoom(zoom=2)
