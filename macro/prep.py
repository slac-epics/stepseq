#!/usr/bin/env python
import sys
import re

def process(lines, start):
    o = []
    i = 0;
    while i < len(lines):
        l = lines[i].strip()
        i = i + 1
        try:
            lp = l.index('(')
        except:
            lp = None
        try:
            rp = l.rindex(')')
        except: 
            rp = None
        try:
            ob = l.index('{') 
        except: 
            ob = None
        c = []
        if l[0] == '#':
            o.append([start+i, "COMMENT", l])
            continue
        if lp is not None and rp is not None:
            name = l[:lp].strip()
            args = []
            for x in l[lp+1:rp].split(','):
                x = x.strip()
                if x[0] == '"':
                    if x[-1] == '"':
                        args.append(x[1:-1])
                    else:
                        raise IOError("Line %d: Argument %s is missing a double quote" % (start+i, x))
                else:
                    args.append(x)
            c = [start+i, name, args]
        if l[:6] == "FINISH":
            c = [start+i, 'FINISH']
        if l[:4] == "ELSE":
            c = [start+i, 'ELSE']
        if ob is not None:
            st = i
            cnt = 1
            while i < len(lines):
                if '{' in lines[i]:
                    cnt = cnt + 1
                if '}' in lines[i]:
                    cnt = cnt - 1
                if cnt == 0:
                    break
                i = i + 1
            if i == len(lines):
                raise IOError("Line %d: Mismatched {}!" % (start+st))
            i = i + 1
            c.append(process(lines[st:i], start+st))
        if c != []:
            o.append(c)
    return o

def do_pad(s, n=12):
    return (s + "            ")[:n]

duplist = []

def recordND(type, name, initial, fp, fields=[], auto=None):
    global duplist
    if name in duplist:
        return
    record(type, name, initial, fp, fields, auto)
    duplist.append(name)

def record(type, name, initial, fp, fields=[], auto=None):
    fp.write('record(%s, %s) {\n' % (type, name))
    if initial is not None:
        fp.write('    field(VAL, "%s")\n' % initial)
    for t in fields:
        fp.write('    field(%s, "%s")\n' % t)
    if auto is not None:
        fp.write('    info(autosaveFields, "%s")\n' % auto)
    fp.write('}\n\n')

def is_int(s):
    try:
        x = int(s)
        return True
    except:
        return False

def is_float(s):
    try:
        x = float(s)
        return True
    except:
        return False

#
# Strings are harder.  Let's say if it contains a space,
# it's a string, and if it doesn't contain more than one
# colon, it's a string.  But we'll only warn here...
#
def is_str(s):
    try:
        x = s.index(' ')
        return True
    except:
        pass
    try:
        x = s.index(':', s.index(':'))
        return False
    except:
        return True

tdict = {"INT":   ("longout",   is_int,   False), 
         "FLOAT": ("ao",        is_float, False), 
         "STR":   ("stringout", is_str,   False)}

# The New regime: IF and WHILE can either have just a PVname as before,
# or a "PVname op constant" expression.  op can be ==, =, #, !=, >, <, >=,
# or <=.  There can be spaces.
#
# Given the string, return a two element list: the PVname, and the expression
# string ("" if there isn't one.)
def parse_expr(expr):
    first = 1000
    for c in ' =!<>#':
        try:
            f = expr.index(c)
            if f < first:
                first = f
        except:
            pass
    if first == 1000:
        return [expr, ""]
    else:
        return [expr[:first].strip(), expr[first:].strip()]

def generate_seq(name, seq, fp):
    global tdict
    i = 0
    sn = 0
    f = []
    out = []
    out.append("record(stepSequence, %s) {\n" % name)
    for (idx,l) in enumerate(seq):
        if l[1] == 'ELSE':
            # This is totally done by the previous IF.  We should check
            # there *is* a previous IF though!
            if idx == 0 or seq[idx-1][1] != 'IF':
                raise IOError("Line %d: Syntax error: ELSE with no previous IF!" % l[0])
            continue  
        if l[1] == "COMMENT":
            out.append("    %s\n" % l[2])
            continue
        if l[1] == "field":
            x = '    field(%s"%s")\n' % (do_pad(l[2][0] + ","), l[2][1])
            out.append(x)
            if l[2][0] not in ["FLNK"]:
                f.append(x)
            continue
        if i != 0 and i % 9 == 0:
            sn = sn + 1
            out.append('    field(REQ9,       "%s_%d.REQ PP")\n'       % (name, sn))
            out.append('    field(ABRT9,      "%s_%d.ABRT PP")\n'      % (name, sn))
            out.append('    field(STATE9,     "%s_%d.STATE CPP")\n'    % (name, sn))
            out.append('    field(STEPNAME9,  "%s_%d.STEPNAME CPP")\n' % (name, sn))
            out.append('    field(PRE9,       "")\n')
            out.append('}\n')
            out.append('\n')
            out.append('record(stepSequence, %s_%d) {\n' % (name, sn))
            for x in f:
                out.append(f)
        if len(l[2]) == 1:
            d = None
            r = l[2][0]
        else:
            d = l[2][0]
            r = l[2][1]
            if l[1] not in ['FINISH', 'IF', 'WHILE']:
                out.append('    field(PRE%d,       "%s")\n' % (i % 9, d))
        if l[1] == 'EPICS':
            out.append('    field(REQ%d,       "%s")\n' % (i % 9, r))
            if len(l) == 4:
                for ll in l[3]:
                    if ll[1] not in ['field', 'COMMENT']:
                        raise IOError("Line %d: Syntax error: field expected!" % ll[0])
                    if ll[1] == "COMMENT":
                        out.append("    %s\n" % ll[2])
                    else:
                        out.append('    field(%s"%s")\n' % (do_pad("%s%d," % (ll[2][0], i % 9)),
                                                            ll[2][1]))
            i = i + 1
            continue
        if l[1] == 'SUBSEQ':
            if d is not None and d != "" and d.strip()[-1] == ':':
                out.append('    field(STEPNAME%d,  "%s.STEPNAME CPP")\n' % (i % 9, r))
            out.append('    field(REQ%d,       "%s.REQ PP")\n' % (i % 9, r))
            out.append('    field(ABRT%d,      "%s.ABRT PP")\n' % (i % 9, r))
            out.append('    field(STATE%d,     "%s.STATE CPP")\n' % (i % 9, r))
            i = i + 1
            continue
        if l[1] == 'PROMPT':
            recordND("bo", r, "0", fp, [("ZNAM", "Off"), ("ONAM", "On")])
            if len(l[2]) == 3:
                dv = l[2][2]
            else:
                dv = "0"
            recordND("bo", r + "WT", "0", fp,
                   [("ZNAM", "Off"), ("ONAM", "On")])
            recordND("bo", r + "SW", "1", fp,
                   [("ZNAM", "Off"), ("ONAM", "On"),
                    ("OUT", r + "WT PP"), ("FLNK", r + "AU")])
            recordND("bo", r + "AU", dv, fp,
                   [("ZNAM", "Off"), ("ONAM", "On"), ("PINI", "YES"),
                    ("OUT", r + " PP"), ("FLNK", r + "CA")], "VAL")
            recordND("calcout", r + "CA", None, fp,
                   [("INPA", r + " CPP"), ("CALC", "(A>0)?0:1"),
                    ("OOPT", "Transition To Zero"), ("DOPT", "Use CALC"),
                    ("OUT", r + "WT PP")])
            out.append('    field(REQ%d,       "%sSW.PROC PP")\n' % (i % 9, r))
            out.append('    field(STATE%d,     "%sCA CPP")\n' % (i % 9, r))
            i = i + 1
            continue
        if l[1] == 'ABORT':
            record("seq", "%s:SQ%d" % (name, i), None, fp, [
                   ("SELM", "All"),
                   ("DOL1", "2"), ("LNK1", "%s:_S%d PP" % (name, i)),
                   ("DLY2", 1), 
                   ("DOL2", "1"), ("LNK2", "%s:_S%d PP" % (name, i))])
            record("longout", "%s:_S%d" % (name, i), "1", fp)
            out.append('    field(PRE%d,       "%s")\n' % (i % 9, r))
            out.append('    field(REQ%d,       "%s:SQ%d.PROC PP")\n' % (i % 9, name, i))
            out.append('    field(STATE%d,     "%s:_S%d CPP")\n' % (i % 9, name, i))
            
            i = i + 1
            continue
        if l[1] == 'DELAY':
            record("longout", "%s:_S%d" % (name, i), "0", fp)
            record("seq", "%s:_D%d" % (name, i), None, fp, [
                   ("SELM", "All"),
                   ("DOL1", "1"), ("LNK1", "%s:_S%d PP" % (name, i)),
                   ("DLY2", r), ("DOL2", "0"), ("LNK2", "%s:_S%d PP" % (name, i))])
            out.append('    field(REQ%d,       "%s:_D%d.PROC PP")\n' % (i % 9, name, i))
            out.append('    field(STATE%d,     "%s:_S%d CPP")\n' % (i % 9, name, i))
            i = i + 1
            continue
        if l[1] == 'FINISH':
            record("calcout", "%s:_F" % (name), None, fp, [
                   ("INPA", "%s.STATE CPP NMS" % (name)),
                   ("CALC", "A==1"),
                   ("OOPT", "Transition To Zero"),
                   ("DOPT", "Use OCAL"),
                   ("OCAL", "1"),
                   ("OUT",  "%s:FS.REQ PP" % (name))
                   ])
            generate_seq("%s:FS" % (name), l[2], fp);
            continue
        if l[1] == 'IF' or l[1] == 'WHILE':
            if len(l[2]) > 1:
                testcond  = l[2][0]
                name_expr = parse_expr(l[2][1])
            else:
                testcond  = "Testing Condition"
                name_expr = parse_expr(l[2][0])
            record("longout", "%s:_S%d" % (name, i), "0", fp)
            record("stringout", "%s:SN%d" % (name, i), "DONE", fp)
            record("seq", "%s:ST%d" % (name, i), None, fp, [
                   ("SELM", "All"),
                   ("DOL1", "1"),
                   ("LNK1", "%s:_S%d PP" % (name, i)),
                   ("DOL2", "1"),
                   ("LNK2", "%s:_N%d.PROC" % (name, i)),
                   ("DOL3", "1"),
                   ("LNK3", "%s:_T%d.PROC" % (name, i))])
            record("stringout", "%s:_N%d" % (name, i), testcond, fp,
                   [("OUT", "%s:SN%d PP" % (name, i))])
            record("calcout", "%s:MS%d" % (name, i), None, fp, 
                   [("INPA", "%s:SQ%d.STATE CPP" % (name, i)),
                    ("CALC", "A==0||A==2" if l[1] == 'IF' else "A==2"),
                    ("OOPT", "When Non-zero"),
                    ("DOPT", "Use OCAL"),
                    ("OCAL", "A"),
                    ("OUT",  "%s:_S%d PP" % (name, i))])
            record("stringout", "%s:MN%d" % (name, i), None, fp,
                   [("OMSL", "closed_loop"),
                    ("DOL",  "%s:SQ%d.STEPNAME CPP" % (name, i)),
                    ("OUT",  "%s:SN%d PP" % (name, i))])
            record("calcout", "%s:_T%d" % (name, i), None, fp, 
                   [("INPA", "%s NPP" % name_expr[0]),
                    ("CALC", "(A%s)?1:2" % name_expr[1]),
                    ("OOPT", "Every Time"),
                    ("DOPT", "Use CALC"),
                    ("OUT",  "%s:SL%d.SELN PP" % (name, i))])
            if idx+1 < len(seq) and seq[idx+1][1] == "ELSE":
                l2 = "%s:_E%d.REQ PP" % (name, i)
                v2 = "1"
                record("calcout", "%s:ES%d" % (name, i), None, fp, 
                       [("INPA", "%s:_E%d.STATE CPP" % (name, i)),
                        ("CALC", "A==0||A==2" if l[1] == 'IF' else "A==2"),
                        ("OOPT", "When Non-zero"),
                        ("DOPT", "Use OCAL"),
                        ("OCAL", "A"),
                        ("OUT",  "%s:_S%d PP" % (name, i))])
                record("stringout", "%s:EN%d" % (name, i), None, fp,
                       [("OMSL", "closed_loop"),
                        ("DOL",  "%s:_E%d.STEPNAME CPP" % (name, i)),
                        ("OUT",  "%s:SN%d PP" % (name, i))])
                generate_seq("%s:_E%d" % (name, i), seq[idx+1][2], fp)
            else:
                l2 = "%s:_S%d PP" % (name, i)
                v2 = "0"
            record("seq", "%s:SL%d" % (name, i), None, fp, [
                   ("SELM", "Specified"),
                   ("DOL1", "1"),
                   ("LNK1",  "%s:SQ%d.REQ PP" % (name, i)),
                   ("DOL2", v2),
                   ("LNK2", l2)
                   ])
            if l[1] == "WHILE":
                l[3].append([l[0], "field", ["FLNK", "%s:ST%d" % (name, i)]])
            generate_seq("%s:SQ%d" % (name, i), l[3], fp);
                
            out.append('    field(REQ%d,       "%s:ST%d.PROC")\n' % (i % 9, name, i))
            out.append('    field(ABRT%d,      "%s:SQ%d.ABRT PP")\n' % (i % 9, name, i))
            out.append('    field(STATE%d,     "%s:_S%d CPP")\n' % (i % 9, name, i))
            out.append('    field(STEPNAME%d,  "%s:SN%d CPP")\n' % (i % 9, name, i))
            i = i + 1
            continue
        if l[1] == 'WAIT':
            if len(l[2]) == 3:
                t = l[2][2]
            else:
                t = "-1"
            record("longout", "%s:TM%d" % (name, i), t, fp)
            record("longout", "%s:CT%d" % (name, i), "0", fp)
            record("longout", "%s:AB%d" % (name, i), "2", fp,
                   [("OUT",  "%s:_S%d PP" % (name, i))])
            record("longout", "%s:_S%d" % (name, i), "0", fp)
            record("calcout", "%s:CC%d" % (name, i), None, fp,
                   [("INPA", "%s:TM%d NPP" % (name, i)),
                    ("INPB", "%s:CT%d NPP" % (name, i)),
                    ("INPC", "%s:_S%d NPP" % (name, i)),
                    ("SCAN", "1 second"),
                    ("CALC", "(C==1)&&((A==-1)||(B!=0))"),
                    ("DOPT", "Use OCAL"),
                    ("OOPT", "When Non-zero"),
                    ("OUT",  "%s:CT%d PP" % (name, i)),
                    ("OCAL", "(B<-10||B==0)?(B?-1:0):(B-1)")])
            name_expr = parse_expr(l[2][1])
            record("calcout", "%s:CS%d" % (name, i), None, fp,
                   [("INPA", "%s:_S%d CPP" % (name, i)),
                    ("INPB", "%s:CT%d CPP" % (name, i)),
                    ("INPC", "%s CPP" % name_expr[0]),
                    ("CALC", "(A!=1)?A:((C%s)?0:(B==0?2:1))" % name_expr[1]),
                    ("DOPT", "Use CALC"),
                    ("OOPT", "Every Time"),
                    ("OUT",  "%s:_S%d PP" % (name, i))])
            record("seq", "%s:ST%d" % (name, i), None, fp, [
                   ("SELM", "All"),
                   ("DOL1", "1"),
                   ("LNK1", "%s:_S%d PP" % (name, i)),
                   ("DOL2", "%s:TM%d NPP" % (name, i)),
                   ("LNK2", "%s:CT%d PP" % (name, i))])
            out.append('    field(REQ%d,       "%s:ST%d.PROC")\n' % (i % 9, name, i))
            out.append('    field(ABRT%d,      "%s:AB%d.PROC")\n' % (i % 9, name, i))
            out.append('    field(STATE%d,     "%s:_S%d CPP")\n' % (i % 9, name, i))
            i = i + 1
            continue
        if l[1] == 'ASSIGN_CALC':
            ll = []
            for x in l[3]:
                if x[1] == 'field':
                    ll.append((x[2][0], x[2][1]))
                else:
                    raise IoError("ASSIGN_CALC can only contain fields!")
            #ll.append(("FLNK", "%s:_V%d"))
            record("calc", "%s:CA%d" % (name, i), None, fp, ll)
            record("ao", "%s:_V%d" % (name, i), None, fp, [
                   ("OMSL", "closed_loop"),
                   ("DOL",  "%s:CA%d PP" % (name, i)),
                   ("OUT",  "%s PP" % l[2][1])])
            if len(l[2]) > 2:
                if l[2][2] == 'bo':
                    record(l[2][2], l[2][1], None, fp, 
                           [('ZNAM', 'False'), ('ONAM', 'True')])
                else:
                    record(l[2][2], l[2][1], None, fp)
            out.append('    field(REQ%d,       "%s:_V%d.PROC")\n' % (i % 9, name, i))
            i = i + 1
            continue
        if l[1][:4] == 'SET_':
            td = tdict[l[1][4:]]
            if not td[1](l[2][2]):
                print "WARNING: %s for %s: %s does not look like it has type %s!" % (l[1], l[2][1], l[2][2], l[1][4:])
                if td[2]:
                    sys.exit(1)
            record(td[0], "%s:_V%d" % (name, i), l[2][2], fp, [
                   ("OMSL", "supervisory"),
                   ("OUT",  "%s PP" % l[2][1])])
            out.append('    field(REQ%d,       "%s:_V%d.PROC")\n' % (i % 9, name, i))
            i = i + 1
            continue;
        if l[1][:7] == 'ASSIGN_':
            td = tdict[l[1][7:]]
            if td[1](l[2][2]):
                print "WARNING: %s for %s: %s does not look like a PV!" % (l[1], l[2][1], l[2][2])
                if td[2]:
                    sys.exit(1)
            record(td[0], "%s:_V%d" % (name, i), None, fp, [
                   ("OMSL", "closed_loop"),
                   ("DOL",  "%s NPP" % l[2][2]),
                   ("OUT",  "%s PP" % l[2][1])])
            out.append('    field(REQ%d,       "%s:_V%d.PROC")\n' % (i % 9, name, i))
            i = i + 1
            continue;
        if l[1] == 'EXTERN':
            out.append('    field(PRE%d,       "%s")\n' % (i % 9, r))
        # These are needed for both ASUB and EXTERN.
        out.append('    field(REQ%d,       "%s:RQ%d PP")\n' % (i % 9, name, i))
        out.append('    field(ABRT%d,      "%s:AB%d PP")\n' % (i % 9, name, i))
        out.append('    field(STATE%d,     "%s:_S%d CPP")\n' % (i % 9, name, i))
        out.append('    field(STEPNAME%d,  "%s:SN%d CPP")\n' % (i % 9, name, i))
        record("longout", "%s:RQ%d" % (name, i), "0", fp)
        record("longout", "%s:AB%d" % (name, i), "0", fp)
        record("longout", "%s:_S%d" % (name, i), "0", fp)
        record("stringout", "%s:SN%d" % (name, i), "DONE", fp)
        if l[1] == 'ASUB':
            record("longout", "%s:_A%d" % (name, i), "0", fp)
            fp.write('record(aSub, "%s:SP%d") {\n' % (name, i))
            fp.write('    field(SNAM,  "aSubControl")\n')
            fp.write('    field(SCAN,  "Passive")\n')
            fp.write('    field(EFLG,  "ON CHANGE")\n')
            fp.write('    field(INPA,  "%s:RQ%d CPP")\n' % (name, i))
            fp.write('    field(FTA,   "LONG")\n')
            fp.write('    field(NOA,   "1")\n')
            fp.write('    field(INPB,  "%s:AB%d CPP")\n' % (name, i))
            fp.write('    field(FTB,   "LONG")\n')
            fp.write('    field(NOB,   "1")\n')
            # A little weird, but this is so we process passive, but 
            # still get the current value!
            fp.write('    field(INPC,  "%s:_S%d NPP")\n' % (name, i))
            fp.write('    field(FTC,   "LONG")\n')
            fp.write('    field(NOC,   "1")\n')
            fp.write('    field(INPD,  "%s:_S%d CPP")\n' % (name, i))
            fp.write('    field(FTD,   "LONG")\n')
            fp.write('    field(NOD,   "1")\n')
            fp.write('    field(OUTA,  "%s:RQ%d PP")\n' % (name, i))
            fp.write('    field(FTVA,  "LONG")\n')
            fp.write('    field(NOVA,  "1")\n')
            fp.write('    field(OUTB,  "%s:AB%d PP")\n' % (name, i))
            fp.write('    field(FTVB,  "LONG")\n')
            fp.write('    field(NOVB,  "1")\n')
            fp.write('    field(OUTC,  "%s:_S%d PP")\n' % (name, i))
            fp.write('    field(FTVC,  "LONG")\n')
            fp.write('    field(NOVC,  "1")\n')
            fp.write('    field(OUTD,  "%s:_A%d PP")\n' % (name, i))
            fp.write('    field(FTVD,  "LONG")\n')
            fp.write('    field(NOVD,  "1")\n')
            fp.write('    field(OUTE,  "%s:_P%d.VALT NPP")\n' % (name, i))
            fp.write('    field(FTVE,  "STRING")\n')
            fp.write('    field(NOVE,  "1")\n')
            fp.write('    field(OUTF,  "%s:_P%d.VALU NPP")\n' % (name, i))
            fp.write('    field(FTVF,  "LONG")\n')
            fp.write('    field(NOVF,  "1")\n')
            fp.write('}\n\n')
            fp.write('record(aSub, "%s:_P%d") {\n' % (name, i))
            fp.write('    field(SNAM,  "%s")\n' % r)
            fp.write('    field(EFLG,  "ON CHANGE")\n')
            fp.write('    field(SDIS,  "%s:_A%d")\n' % (name, i))
            fp.write('    field(DISV,  "0")\n')
            have_scan = False
            if len(l) == 4:
                for ll in l[3]:
                    if ll[1] not in ['field', 'COMMENT']:
                        raise IOError("Line %d: Syntax error: field expected!" % ll[0])
                    if ll[1] == "COMMENT":
                        fp.write("    %s\n" % ll[2])
                    else:
                        fp.write('    field(%s"%s")\n' % (do_pad(ll[2][0] + ',', 6),
                                                          ll[2][1]))
                        if ll[2][0] == 'SCAN':
                            have_scan = True
            fp.write('    field(OUTT,  "%s:SN%d PP")\n' % (name, i))
            fp.write('    field(FTVT,  "STRING")\n')
            fp.write('    field(NOVT,  "1")\n')
            fp.write('    field(OUTU,  "%s:_S%d PP")\n' % (name, i))
            fp.write('    field(FTVU,  "LONG")\n')
            fp.write('    field(NOVU,  "1")\n')
            if not have_scan:
                fp.write('    field(SCAN,  ".1 second")\n')
            fp.write('}\n\n')
            i = i + 1
            continue
        if l[1] == 'EXTERN':
            record("longout", "%s:PD%d" % (name, i), "-1", fp)
            record("longout", "%s:PP%d" % (name, i), "-1", fp)
            record("aSub", "%s:ST%d" % (name, i), None, fp,
                   [("SNAM", "ProcessInit"),
                    ("EFLG", "ALWAYS"),
                    ("INPA", "%s:PD%d CPP" % (name, i)),
                    ("FTA",  "LONG"),
                    ("NOA",  "1"),
                    ("INPB", "%s:RQ%d CPP" % (name, i)),
                    ("FTB",  "LONG"),
                    ("NOB",  "1"),
                    ("OUTA", "%s:_S%d PP" % (name, i)),
                    ("FTVA", "LONG"),
                    ("NOVA", "1"),
                    ("OUTB", "%s:SN%d PP" % (name, i)),
                    ("FTVB", "STRING"),
                    ("NOVB", "1"),
                    ("OUTC", "%s:SP%d.PROC" % (name, i)),
                    ("FTVC", "LONG"),
                    ("NOVC", "1")])
            record("stringout", "%s:_N%d" % (name, i), 
                   "%s:SN%d" % (name, i), fp)
            record("aSub", "%s:PM%d" % (name, i), None, fp,
                   [("SNAM",  "ProcessMonitor"),
                    ("EFLG",  "ON CHANGE"),
                    ("SCAN",  ".1 second"),
                    ("SDIS",  "%s:PD%d NPP" % (name, i)),
                    ("DISV",  "-1"),
                    ("INPA",  "%s:PD%d NPP" % (name, i)),
                    ("FTA",   "LONG"),
                    ("NOA",   "1"),
                    ("INPB",  "%s:AB%d NPP" % (name, i)),
                    ("FTB",   "LONG"),
                    ("NOB",   "1"),
                    ("INPC",  "%s:SN%d NPP" % (name, i)),
                    ("FTC",   "STRING"),
                    ("NOC",   "1"),
                    ("INPD",  "%s:_S%d NPP" % (name, i)),
                    ("FTD",   "LONG"),
                    ("NOD",   "1"),
                    ("INPE",  "%s:PP%d NPP" % (name, i)),
                    ("FTE",   "LONG"),
                    ("NOE",   "1"),
                    ("OUTA",  "%s:PD%d PP" % (name, i)),
                    ("FTVA",  "LONG"),
                    ("NOVA",  "1"),
                    ("OUTB",  "%s:AB%d PP" % (name, i)),
                    ("FTVB",   "LONG"),
                    ("NOVB",   "1"),
                    ("OUTC",  "%s:SN%d PP" % (name, i)),
                    ("FTVC",   "STRING"),
                    ("NOVC",   "1"),
                    ("OUTD",  "%s:_S%d PP" % (name, i)),
                    ("FTVD",  "LONG"),
                    ("NOVD",  "1"),
                    ("OUTE",  "%s:PP%d PP" % (name, i)),
                    ("FTVE",  "LONG"),
                    ("NOVE",  "1")])
            if len(l) != 4:
                raise IOError("Line %d: EXTERN must have a PROG field!" % l[0])
            prog = ""
            for ll in l[3]:
                if ll[1] not in ['field', 'COMMENT']:
                    raise IOError("Line %d: Syntax error: field expected!" % ll[0])
                if ll[1] == 'field':
                    if ll[2][0] == 'PROG':
                        prog = ll[2][1]
                    else:
                        raise IOError("Line %d: Unknown field for EXTERN: %s" % (ll[0], ll[2][0]))
            if prog == "":
                raise IOError("Line %d: EXTERN must have a PROG field!" % l[0])
            ll = [x.strip() for x in prog.split()]
            for (n, lll) in enumerate(ll):
                record("stringout", "%s:PG%d_%d" % (name, i, n), lll, fp)
            record("longout", "%s:AG%d" % (name, i), len(ll), fp)
            fp.write('record(aSub, "%s:SP%d") {\n' % (name, i))
            fp.write('    field(SNAM,  "ProcessSpawn")\n')
            fp.write('    field(SCAN,  "Passive")\n')
            fp.write('    field(EFLG,  "ON CHANGE")\n')
            # We seem to have a race, so let's let the record set the state quickly,
            # *then* poke the actual spawn routine.
            fp.write('    field(INPA,  "%s:RQ%d NPP")\n' % (name, i))
            fp.write('    field(FTA,   "LONG")\n')
            fp.write('    field(NOA,   "1")\n')
            fp.write('    field(INPB,  "%s:_S%d NPP")\n' % (name, i))
            fp.write('    field(FTB,   "LONG")\n')
            fp.write('    field(NOB,   "1")\n')
            fp.write('    field(INPC,  "%s:PD%d NPP")\n' % (name, i))
            fp.write('    field(FTC,   "LONG")\n')
            fp.write('    field(NOC,   "1")\n')
            fp.write('    field(INPD,  "%s:PP%d NPP")\n' % (name, i))
            fp.write('    field(FTD,   "LONG")\n')
            fp.write('    field(NOD,   "1")\n')
            fp.write('    field(INPE,  "%s:AG%d NPP")\n' % (name, i))
            fp.write('    field(FTE,   "LONG")\n')
            fp.write('    field(NOE,   "1")\n')
            fp.write('    field(INPF,  "%s:_N%d NPP")\n' % (name, i))
            fp.write('    field(FTF,   "STRING")\n')
            fp.write('    field(NOF,   "1")\n')
            for (n, lll) in enumerate(ll):
                c = chr(ord('G') + n)
                fp.write('    field(INP%s,  "%s:PG%d_%d NPP")\n' % 
                         (c, name, i, n))
                fp.write('    field(FT%s,   "STRING")\n' %  c)
                fp.write('    field(NO%s,   "1")\n' % c)
            fp.write('    field(OUTA,  "%s:RQ%d PP")\n' % (name, i))
            fp.write('    field(FTVA,  "LONG")\n')
            fp.write('    field(NOVA,  "1")\n')
            fp.write('    field(OUTB,  "%s:_S%d PP")\n' % (name, i))
            fp.write('    field(FTVB,  "LONG")\n')
            fp.write('    field(NOVB,  "1")\n')
            fp.write('    field(OUTC,  "%s:PP%d PP")\n' % (name, i))
            fp.write('    field(FTVC,  "LONG")\n')
            fp.write('    field(NOVC,  "1")\n')
            fp.write('    field(OUTD,  "%s:PD%d PP")\n' % (name, i))
            fp.write('    field(FTVD,  "LONG")\n')
            fp.write('    field(NOVD,  "1")\n')
            fp.write('}\n\n')
            i = i + 1
            continue
    out.append('}\n\n')
    for l in out:
        fp.write(l)

format_map = {'d' : 'LONG', 'u': 'ULONG', 's': 'STRING'}

# Utility function for read/write_record.
def process_rw_record(lines, start, fp, func):
    snam = "do%sRecord" % func.capitalize()
    l = lines[0][len(func)+7:]
    cnt = 1
    while '{' not in l:
        l += lines[cnt]
        cnt += 1
    h = [x.strip() for x in l.split(',')]
    if h[0][0] != '(':
        raise IOError("Line %d: Can't find '('?!?" % start)
    h[0] = h[0][1:].strip()
    if h[-1][-1] != '{':
        raise IOError("Line %d: Can't find '{'?!?" % start)
    h[-1] = h[-1][:-1].strip()
    if h[-1][-1] != ')':
        raise IOError("Line %d: Can't find ')'?!?" % start)
    h[-1] = h[-1][:-1].strip()
    h = [x[1:-1] if x[0] == '"' else x for x in h]  # Dequote it!
    name = h[0]
    fmt = h[1]
    val  = h[-1]
    typ  = h[-2]
    args = h[2:-2]
    if typ not in ['LONG', 'ULONG', 'DOUBLE', 'STRING']:
        raise IOError("Line %d: invalid type '%s'" % (start, typ))
    fp.write('record(stringout, %s_F)\n{\n' % name)
    fp.write('    field(PINI, "YES")\n')
    fp.write('    field(VAL, "%s")\n' % fmt)
    fp.write('}\n\n')
    fp.write('record(aSub, %s)\n{\n' % name)
    fp.write('    field(INAM, "rwRecordInit")\n')
    fp.write('    field(SNAM, "%s")\n' % snam)
    fp.write('    field(EFLG,  "ON CHANGE")\n\n')
    fp.write('    field(FTA,  "STRING")\n')
    fp.write('    field(NOA,  "1")\n')
    fp.write('    field(INPA, "%s_F NMS NPP")\n\n' % name)
    argc = 0
    for i in range(len(fmt)):
        if fmt[i] == '%':
            if fmt[i+1] not in "dus":
                raise IOError("Line %d: invalid format '%%%s'" % (start, fmt[i+1]))
            c = chr(ord('B') + argc)
            fp.write('    field(FT%c,  "%s")\n' % (c, format_map[fmt[i+1]]))
            fp.write('    field(NO%c,  "1")\n' % c)
            fp.write('    field(INP%c, "%s")\n\n' % (c, args[argc]))
            argc = argc + 1
    if argc != len(args):
        raise IOError("Line %d: wrong number of arguments in format!" % start)
    fp.write('    field(FTU,  "%s")\n' % typ)
    fp.write('    field(NOU,  "1")\n')
    if func == 'read':
        fp.write('\n')
        fp.write('    field(FTVA,  "%s")\n' % typ)
        fp.write('    field(NOVA,  "1")\n')
        fp.write('    field(OUTA,  "%s NMS PP")\n\n' % val)
        fp.write('    field(FTVB,  "STRING")\n')
        fp.write('    field(NOVB,  "1")\n\n')
    else: # write
        fp.write('    field(INPU,  "%s")\n\n' % val)  # No NMS NPP, because this might be a constant!
    for l in lines[cnt:]: # This should include the final '}'!
        fp.write(l)

def expand(lines, fp):
    i = 0;
    while i < len(lines):
        if (lines[i][:9] != "sequence(" and
            lines[i][:12] != "read_record(" and
            lines[i][:13] != "write_record("):
            fp.write(lines[i])
            i = i + 1
            continue
        start = i
        while lines[i][0] != '}':
            i = i + 1
        i = i + 1
        if lines[start][:9] == "sequence(":
            d = process(lines[start:i], start)
            generate_seq(d[0][2][0], d[0][3], fp)
        if lines[start][:12] == "read_record(":
            process_rw_record(lines[start:i], start, fp, "read")
        if lines[start][:13] == "write_record(":
            process_rw_record(lines[start:i], start, fp, "write")

if __name__ == '__main__':
    try:
        if len(sys.argv) != 3:
            print "Usage: expand foo.dbs foo.db"
            sys.exit(1)
        lines = open(sys.argv[1]).readlines()
        fp = open(sys.argv[2], 'w')
        expand(lines, fp)
        fp.close()
        sys.exit(0)
    except IOError, e:
        print e
        sys.exit(1)

