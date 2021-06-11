import subprocess

from apflog import apflog

from KeywordHandle import readem, readit, writeem


def cmdexec(cmd, cwd='./',fake=False,debug=False):
    args = ["apftask","do"]
    args = args + cmd.split()
    if fake:
        apflog("Would have executed: %s" % repr(cmd), echo=True)
        return True, 0

    apflog("Executing Command: %s" % repr(cmd), echo=True)

    p = subprocess.Popen(args, stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=cwd)

    while p.poll() is None:
        l = p.stdout.readline().rstrip('\n')
        apflog(l, echo=debug)

    out, err = p.communicate()
    if debug: apflog(out, echo=debug)
    if len(err): apflog(err, echo=debug)
    ret_code = p.returncode
    if ret_code == 0:
        return True, ret_code
    else:
        return False, ret_code

def operExec(instr,checkapf,fake=False):

    if fake:
        apflog("Would have executed %s" % (instr),echo=True)
        r=True
        code=None
    else:
        writeem(checkapf,'ROBOSTATE','offset_blind operating')
        r,code = cmdexec(instr)
        if r is False:
            apflog("Cannot execute %s" % (instr),level='error',echo=True)

    return r,code
