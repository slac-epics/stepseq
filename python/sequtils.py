from psp.Pv import Pv
import pyca
import sys, os

def caput(pvname,value,timeout=1.0):
    try:
        pv = Pv(pvname)
        pv.connect(timeout)
        pv.get(ctrl=False, timeout=timeout)
        pv.put(value, timeout)
        pv.disconnect()
    except pyca.pyexc, e:
        print 'pyca exception: %s' %(e)
    except pyca.caexc, e:
        print 'channel access exception: %s' %(e)

def caget(pvname,timeout=1.0):
  try:
    pv = Pv(pvname)
    pv.connect(timeout)
    pv.get(ctrl=False, timeout=timeout)
    v = pv.value
    pv.disconnect()
    return v
  except pyca.pyexc, e:
    print 'pyca exception: %s' %(e)
    return None
  except pyca.caexc, e:
    print 'channel access exception: %s' %(e)
    return None

def abort():
    sys.exit(1)

def done():
    sys.exit(0)

def set_stepname(v):
    caput(os.getenv("STEPNAMEPV"), v)
