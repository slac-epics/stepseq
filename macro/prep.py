#!/usr/bin/env python
import sys
import re

def process(lines):
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
            o.append(["COMMENT", l])
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
                        raise IOError("Argument %s is missing a double quote" % x)
                else:
                    args.append(x)
            c = [name, args]
        if l[:6] == "FINISH":
            c = ['FINISH']
        if ob is not None:
            start = i
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
                raise IOError("Mismatched {}!")
            i = i + 1
            c.append(process(lines[start:i]))
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

tdict = {"INT": "longout", "FLOAT": "ao", "STR": "stringout"}

def generate_seq(name, seq, fp):
    global tdict
    i = 0
    sn = 0
    f = []
    out = []
    out.append("record(stepSequence, %s) {\n" % name)
    for l in seq:
        if l[0] == "COMMENT":
            out.append("    %s\n" % l[1])
            continue
        if l[0] == "field":
            x = '    field(%s"%s")\n' % (do_pad(l[1][0] + ","), l[1][1])
            out.append(x)
            if l[1][0] not in ["FLNK"]:
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
        if len(l[1]) == 1:
            d = None
            r = l[1][0]
        else:
            d = l[1][0]
            r = l[1][1]
            if l[0] != 'FINISH':
                out.append('    field(PRE%d,       "%s")\n' % (i % 9, d))
        if l[0] == 'EPICS':
            out.append('    field(REQ%d,       "%s")\n' % (i % 9, r))
            if len(l) == 3:
                for ll in l[2]:
                    if ll[0] not in ['field', 'COMMENT']:
                        raise IOError("Syntax error: field expected!")
                    if ll[0] == "COMMENT":
                        out.append("    %s\n" % ll[1])
                    else:
                        out.append('    field(%s"%s")\n' % (do_pad("%s%d," % (ll[1][0], i % 9)),
                                                            ll[1][1]))
            i = i + 1
            continue
        if l[0] == 'SUBSEQ':
            if d is not None and d.strip()[-1] == ':':
                out.append('    field(STEPNAME%d,  "%s.STEPNAME CPP")\n' % (i % 9, r))
            out.append('    field(REQ%d,       "%s.REQ PP")\n' % (i % 9, r))
            out.append('    field(ABRT%d,      "%s.ABRT PP")\n' % (i % 9, r))
            out.append('    field(STATE%d,     "%s.STATE CPP")\n' % (i % 9, r))
            i = i + 1
            continue
        if l[0] == 'PROMPT':
            recordND("bo", r, "0", fp, [("ZNAM", "Off"), ("ONAM", "On")])
            if len(l[1]) == 3:
                dv = l[1][2]
            else:
                dv = "0"
            recordND("bo", r + "_WAIT", "0", fp,
                   [("ZNAM", "Off"), ("ONAM", "On")])
            recordND("bo", r + "_STARTWAIT", "1", fp,
                   [("ZNAM", "Off"), ("ONAM", "On"),
                    ("OUT", r + "_WAIT PP"), ("FLNK", r + "_AUTO")])
            recordND("bo", r + "_AUTO", dv, fp,
                   [("ZNAM", "Off"), ("ONAM", "On"), ("PINI", "YES"),
                    ("OUT", r + " PP"), ("FLNK", r + "_CALC")], "VAL")
            recordND("calcout", r + "_CALC", None, fp,
                   [("INPA", r + " CPP"), ("CALC", "(A>0)?0:1"),
                    ("OOPT", "Transition To Zero"), ("DOPT", "Use CALC"),
                    ("OUT", r + "_WAIT PP")])
            out.append('    field(REQ%d,       "%s_STARTWAIT.PROC PP")\n' % (i % 9, r))
            out.append('    field(STATE%d,     "%s_CALC CPP")\n' % (i % 9, r))
            i = i + 1
            continue
        if l[0] == 'ABORT':
            record("longout", "%s:_STATE%d" % (name, i), "2", fp)
            out.append('    field(PRE%d,       "%s")\n' % (i % 9, r))
            out.append('    field(REQ%d,       "%s:_STATE%d.PROC PP")\n' % (i % 9, name, i))
            out.append('    field(STATE%d,     "%s:_STATE%d CPP")\n' % (i % 9, name, i))
            
            i = i + 1
            continue
        if l[0] == 'DELAY':
            record("longout", "%s:_STATE%d" % (name, i), "0", fp)
            record("seq", "%s:_DELAY%d" % (name, i), None, fp, [
                   ("SELM", "All"),
                   ("DOL1", "1"), ("LNK1", "%s:_STATE%d PP" % (name, i)),
                   ("DLY2", r), ("DOL2", "0"), ("LNK2", "%s:_STATE%d PP" % (name, i))])
            out.append('    field(REQ%d,       "%s:_DELAY%d.PROC PP")\n' % (i % 9, name, i))
            out.append('    field(STATE%d,     "%s:_STATE%d CPP")\n' % (i % 9, name, i))
            i = i + 1
            continue
        if l[0] == 'FINISH':
            record("calcout", "%s:_FIN" % (name), None, fp, [
                   ("INPA", "%s.STATE CPP NMS" % (name)),
                   ("CALC", "A==1"),
                   ("OOPT", "Transition To Zero"),
                   ("DOPT", "Use OCAL"),
                   ("OCAL", "1"),
                   ("OUT",  "%s:_FIN_SEQ.REQ PP" % (name))
                   ])
            generate_seq("%s:_FIN_SEQ" % (name), l[1], fp);
            continue
        if l[0] == 'IF' or l[0] == 'WHILE':
            record("longout", "%s:_STATE%d" % (name, i), "0", fp)
            record("calcout", "%s:_MONST%d" % (name, i), None, fp, [
                   ("INPA", "%s:_SEQ%d.STATE CPP" % (name, i)),
                   ("CALC", "A==0||A==2" if l[0] == 'IF' else "A==2"),
                   ("OOPT", "When Non-zero"),
                   ("DOPT", "Use OCAL"),
                   ("OCAL", "A"),
                   ("OUT",  "%s:_STATE%d PP" % (name, i))
                   ])
            record("stringout", "%s:_SNAME%d" % (name, i), "DONE", fp)
            record("seq", "%s:_START%d" % (name, i), None, fp, [
                   ("SELM", "All"),
                   ("DOL1", "1"),
                   ("LNK1", "%s:_STATE%d PP" % (name, i)),
                   ("DOL2", "1"),
                   ("LNK2", "%s:_SETNAME%d.PROC" % (name, i)),
                   ("DOL3", "1"),
                   ("LNK3", "%s:_TEST%d.PROC" % (name, i))])
            record("stringout", "%s:_SETNAME%d" % (name, i), "Testing Condition", fp,
                   [("OUT", "%s:_SNAME%d PP" % (name, i))])
            record("stringout", "%s:_MONNAME%d" % (name, i), None, fp,
                   [("OMSL", "closed_loop"),
                    ("DOL",  "%s:_SEQ%d.STEPNAME CPP" % (name, i)),
                    ("OUT",  "%s:_SNAME%d PP" % (name, i))])
            record("calcout", "%s:_TEST%d" % (name, i), None, fp, [
                   ("INPA", "%s NPP" % l[1][1]),
                   ("CALC", "A?1:2"),
                   ("OOPT", "Every Time"),
                   ("DOPT", "Use CALC"),
                   ("OUT",  "%s:_SELECT%d.SELN PP" % (name, i))
                   ])
            record("seq", "%s:_SELECT%d" % (name, i), None, fp, [
                   ("SELM", "Specified"),
                   ("DOL1", "1"),
                   ("LNK1",  "%s:_SEQ%d.REQ PP" % (name, i)),
                   ("DOL2", "0"),
                   ("LNK2", "%s:_STATE%d PP" % (name, i)),
                   ])
            if l[0] == "WHILE":
                l[2].append(("field", ["FLNK", "%s:_START%d" % (name, i)]))
            generate_seq("%s:_SEQ%d" % (name, i), l[2], fp);
                
            out.append('    field(REQ%d,       "%s:_START%d.PROC")\n' % (i % 9, name, i))
            out.append('    field(ABRT%d,      "%s:_SEQ%d.ABRT PP")\n' % (i % 9, name, i))
            out.append('    field(STATE%d,     "%s:_STATE%d CPP")\n' % (i % 9, name, i))
            out.append('    field(STEPNAME%d,  "%s:_SNAME%d CPP")\n' % (i % 9, name, i))
            i = i + 1
            continue
        if l[0] == 'WAIT':
            if len(l[1]) == 3:
                t = l[1][2]
            else:
                t = "-1"
            record("longout", "%s:_TIMEOUT%d" % (name, i), t, fp)
            record("longout", "%s:_COUNT%d" % (name, i), "0", fp)
            record("longout", "%s:_ABRT%d" % (name, i), "2", fp,
                   [("OUT",  "%s:_STATE%d PP" % (name, i))])
            record("longout", "%s:_STATE%d" % (name, i), "0", fp)
            record("calcout", "%s:_CALCC%d" % (name, i), None, fp,
                   [("INPA", "%s:_TIMEOUT%d NPP" % (name, i)),
                    ("INPB", "%s:_COUNT%d NPP" % (name, i)),
                    ("INPC", "%s:_STATE%d NPP" % (name, i)),
                    ("SCAN", "1 second"),
                    ("CALC", "(C==1)&&((A==-1)||(B!=0))"),
                    ("DOPT", "Use OCAL"),
                    ("OOPT", "When Non-zero"),
                    ("OUT",  "%s:_COUNT%d PP" % (name, i)),
                    ("OCAL", "(B<-10||B==0)?(B?-1:0):(B-1)")])
            record("calcout", "%s:_CALCS%d" % (name, i), None, fp,
                   [("INPA", "%s:_STATE%d CPP" % (name, i)),
                    ("INPB", "%s:_COUNT%d CPP" % (name, i)),
                    ("INPC", "%s CPP" % l[1][1]),
                    ("CALC", "(A!=1)?A:(C?0:(B==0?2:1))"),
                    ("DOPT", "Use CALC"),
                    ("OOPT", "Every Time"),
                    ("OUT",  "%s:_STATE%d PP" % (name, i))])
            record("seq", "%s:_START%d" % (name, i), None, fp, [
                   ("SELM", "All"),
                   ("DOL1", "1"),
                   ("LNK1", "%s:_STATE%d PP" % (name, i)),
                   ("DOL2", "%s:_TIMEOUT%d NPP" % (name, i)),
                   ("LNK2", "%s:_COUNT%d PP" % (name, i))])
            out.append('    field(REQ%d,       "%s:_START%d.PROC")\n' % (i % 9, name, i))
            out.append('    field(ABRT%d,      "%s:_ABRT%d.PROC")\n' % (i % 9, name, i))
            out.append('    field(STATE%d,     "%s:_STATE%d CPP")\n' % (i % 9, name, i))
            i = i + 1
            continue
        if l[0] == 'ASSIGN_CALC':
            ll = []
            for x in l[2]:
                if x[0] == 'field':
                    ll.append((x[1][0], x[1][1]))
                else:
                    raise IoError("ASSIGN_CALC can only contain fields!")
            #ll.append(("FLNK", "%s:_VAL%d"))
            record("calc", "%s:_CALC%d" % (name, i), None, fp, ll)
            record("ao", "%s:_VAL%d" % (name, i), None, fp, [
                   ("OMSL", "closed_loop"),
                   ("DOL",  "%s:_CALC%d PP" % (name, i)),
                   ("OUT",  "%s PP" % l[1][1])])
            out.append('    field(REQ%d,       "%s:_VAL%d.PROC")\n' % (i % 9, name, i))
            i = i + 1
            continue
        if l[0][:4] == 'SET_':
            record(tdict[l[0][4:]], "%s:_VAL%d" % (name, i), l[1][2], fp, [
                   ("OMSL", "supervisory"),
                   ("OUT",  "%s PP" % l[1][1])])
            out.append('    field(REQ%d,       "%s:_VAL%d.PROC")\n' % (i % 9, name, i))
            i = i + 1
            continue;
        if l[0][:7] == 'ASSIGN_':
            record(tdict[l[0][7:]], "%s:_VAL%d" % (name, i), None, fp, [
                   ("OMSL", "closed_loop"),
                   ("DOL",  "%s NPP" % l[1][2]),
                   ("OUT",  "%s PP" % l[1][1])])
            out.append('    field(REQ%d,       "%s:_VAL%d.PROC")\n' % (i % 9, name, i))
            i = i + 1
            continue;
        if l[0] == 'EXTERN':
            out.append('    field(PRE%d,       "%s")\n' % (i % 9, r))
        # These are needed for both ASUB and EXTERN.
        out.append('    field(REQ%d,       "%s:_REQ%d PP")\n' % (i % 9, name, i))
        out.append('    field(ABRT%d,      "%s:_ABRT%d PP")\n' % (i % 9, name, i))
        out.append('    field(STATE%d,     "%s:_STATE%d CPP")\n' % (i % 9, name, i))
        out.append('    field(STEPNAME%d,  "%s:_SNAME%d CPP")\n' % (i % 9, name, i))
        record("longout", "%s:_REQ%d" % (name, i), "0", fp)
        record("longout", "%s:_ABRT%d" % (name, i), "0", fp)
        record("longout", "%s:_STATE%d" % (name, i), "0", fp)
        record("stringout", "%s:_SNAME%d" % (name, i), "DONE", fp)
        if l[0] == 'ASUB':
            record("longout", "%s:_ACTIVE%d" % (name, i), "0", fp)
            fp.write('record(aSub, "%s:_STEP%d") {\n' % (name, i))
            fp.write('    field(SNAM,  "aSubControl")\n')
            fp.write('    field(SCAN,  "Passive")\n')
            fp.write('    field(EFLG,  "ON CHANGE")\n')
            fp.write('    field(INPA,  "%s:_REQ%d CPP")\n' % (name, i))
            fp.write('    field(FTA,   "LONG")\n')
            fp.write('    field(NOA,   "1")\n')
            fp.write('    field(INPB,  "%s:_ABRT%d CPP")\n' % (name, i))
            fp.write('    field(FTB,   "LONG")\n')
            fp.write('    field(NOB,   "1")\n')
            # A little weird, but this is so we process passive, but 
            # still get the current value!
            fp.write('    field(INPC,  "%s:_STATE%d NPP")\n' % (name, i))
            fp.write('    field(FTC,   "LONG")\n')
            fp.write('    field(NOC,   "1")\n')
            fp.write('    field(INPD,  "%s:_STATE%d CPP")\n' % (name, i))
            fp.write('    field(FTD,   "LONG")\n')
            fp.write('    field(NOD,   "1")\n')
            fp.write('    field(OUTA,  "%s:_REQ%d PP")\n' % (name, i))
            fp.write('    field(FTVA,  "LONG")\n')
            fp.write('    field(NOVA,  "1")\n')
            fp.write('    field(OUTB,  "%s:_ABRT%d PP")\n' % (name, i))
            fp.write('    field(FTVB,  "LONG")\n')
            fp.write('    field(NOVB,  "1")\n')
            fp.write('    field(OUTC,  "%s:_STATE%d PP")\n' % (name, i))
            fp.write('    field(FTVC,  "LONG")\n')
            fp.write('    field(NOVC,  "1")\n')
            fp.write('    field(OUTD,  "%s:_ACTIVE%d PP")\n' % (name, i))
            fp.write('    field(FTVD,  "LONG")\n')
            fp.write('    field(NOVD,  "1")\n')
            fp.write('    field(OUTE,  "%s:_PROC%d.VALT NPP")\n' % (name, i))
            fp.write('    field(FTVE,  "STRING")\n')
            fp.write('    field(NOVE,  "1")\n')
            fp.write('    field(OUTF,  "%s:_PROC%d.VALU NPP")\n' % (name, i))
            fp.write('    field(FTVF,  "LONG")\n')
            fp.write('    field(NOVF,  "1")\n')
            fp.write('}\n\n')
            fp.write('record(aSub, "%s:_PROC%d") {\n' % (name, i))
            fp.write('    field(SNAM,  "%s")\n' % r)
            fp.write('    field(EFLG,  "ON CHANGE")\n')
            fp.write('    field(SDIS,  "%s:_ACTIVE%d")\n' % (name, i))
            fp.write('    field(DISV,  "0")\n')
            have_scan = False
            if len(l) == 3:
                for ll in l[2]:
                    if ll[0] not in ['field', 'COMMENT']:
                        raise IOError("Syntax error: field expected!")
                    if ll[0] == "COMMENT":
                        fp.write("    %s\n" % ll[1])
                    else:
                        fp.write('    field(%s"%s")\n' % (do_pad(ll[1][0] + ',', 6),
                                                          ll[1][1]))
                        if ll[1][0] == 'SCAN':
                            have_scan = True
            fp.write('    field(OUTT,  "%s:_SNAME%d PP")\n' % (name, i))
            fp.write('    field(FTVT,  "STRING")\n')
            fp.write('    field(NOVT,  "1")\n')
            fp.write('    field(OUTU,  "%s:_STATE%d PP")\n' % (name, i))
            fp.write('    field(FTVU,  "LONG")\n')
            fp.write('    field(NOVU,  "1")\n')
            if not have_scan:
                fp.write('    field(SCAN,  ".1 second")\n')
            fp.write('}\n\n')
            i = i + 1
            continue
        if l[0] == 'EXTERN':
            record("longout", "%s:_PID%d" % (name, i), "-1", fp)
            record("longout", "%s:_PIPE%d" % (name, i), "-1", fp)
            record("aSub", "%s:_START%d" % (name, i), None, fp,
                   [("SNAM", "ProcessInit"),
                    ("EFLG", "ALWAYS"),
                    ("INPA", "%s:_PID%d CPP" % (name, i)),
                    ("FTA",  "LONG"),
                    ("NOA",  "1"),
                    ("INPB", "%s:_REQ%d CPP" % (name, i)),
                    ("FTB",  "LONG"),
                    ("NOB",  "1"),
                    ("OUTA", "%s:_STATE%d PP" % (name, i)),
                    ("FTVA", "LONG"),
                    ("NOVA", "1"),
                    ("OUTB", "%s:_SNAME%d PP" % (name, i)),
                    ("FTVB", "STRING"),
                    ("NOVB", "1"),
                    ("OUTC", "%s:_STEP%d.PROC" % (name, i)),
                    ("FTVC", "LONG"),
                    ("NOVC", "1")])
            record("stringout", "%s:_SNAMENAME%d" % (name, i), 
                   "%s:_SNAME%d" % (name, i), fp)
            record("aSub", "%s:_PIDMON%d" % (name, i), None, fp,
                   [("SNAM",  "ProcessMonitor"),
                    ("EFLG",  "ON CHANGE"),
                    ("SCAN",  ".1 second"),
                    ("SDIS",  "%s:_PID%d NPP" % (name, i)),
                    ("DISV",  "-1"),
                    ("INPA",  "%s:_PID%d NPP" % (name, i)),
                    ("FTA",   "LONG"),
                    ("NOA",   "1"),
                    ("INPB",  "%s:_ABRT%d NPP" % (name, i)),
                    ("FTB",   "LONG"),
                    ("NOB",   "1"),
                    ("INPC",  "%s:_SNAME%d NPP" % (name, i)),
                    ("FTC",   "STRING"),
                    ("NOC",   "1"),
                    ("INPD",  "%s:_STATE%d NPP" % (name, i)),
                    ("FTD",   "LONG"),
                    ("NOD",   "1"),
                    ("INPE",  "%s:_PIPE%d NPP" % (name, i)),
                    ("FTE",   "LONG"),
                    ("NOE",   "1"),
                    ("OUTA",  "%s:_PID%d PP" % (name, i)),
                    ("FTVA",  "LONG"),
                    ("NOVA",  "1"),
                    ("OUTB",  "%s:_ABRT%d PP" % (name, i)),
                    ("FTVB",   "LONG"),
                    ("NOVB",   "1"),
                    ("OUTC",  "%s:_SNAME%d PP" % (name, i)),
                    ("FTVC",   "STRING"),
                    ("NOVC",   "1"),
                    ("OUTD",  "%s:_STATE%d PP" % (name, i)),
                    ("FTVD",  "LONG"),
                    ("NOVD",  "1"),
                    ("OUTE",  "%s:_PIPE%d PP" % (name, i)),
                    ("FTVE",  "LONG"),
                    ("NOVE",  "1")])
            if len(l) != 3:
                raise IOError("EXTERN must have a PROG field!")
            prog = ""
            for ll in l[2]:
                if ll[0] not in ['field', 'COMMENT']:
                    raise IOError("Syntax error: field expected!")
                if ll[0] == 'field':
                    if ll[1][0] == 'PROG':
                        prog = ll[1][1]
                    else:
                        raise IOError("Unknown field for EXTERN: %s" % ll[1][0])
            if prog == "":
                raise IOError("EXTERN must have a PROG field!")
            ll = [x.strip() for x in prog.split()]
            for (n, lll) in enumerate(ll):
                record("stringout", "%s:_PROG%d_%d" % (name, i, n), lll, fp)
            record("longout", "%s:_ARGS%d" % (name, i), len(ll), fp)
            fp.write('record(aSub, "%s:_STEP%d") {\n' % (name, i))
            fp.write('    field(SNAM,  "ProcessSpawn")\n')
            fp.write('    field(SCAN,  "Passive")\n')
            fp.write('    field(EFLG,  "ON CHANGE")\n')
            # We seem to have a race, so let's let the record set the state quickly,
            # *then* poke the actual spawn routine.
            fp.write('    field(INPA,  "%s:_REQ%d NPP")\n' % (name, i))
            fp.write('    field(FTA,   "LONG")\n')
            fp.write('    field(NOA,   "1")\n')
            fp.write('    field(INPB,  "%s:_STATE%d NPP")\n' % (name, i))
            fp.write('    field(FTB,   "LONG")\n')
            fp.write('    field(NOB,   "1")\n')
            fp.write('    field(INPC,  "%s:_PID%d NPP")\n' % (name, i))
            fp.write('    field(FTC,   "LONG")\n')
            fp.write('    field(NOC,   "1")\n')
            fp.write('    field(INPD,  "%s:_PIPE%d NPP")\n' % (name, i))
            fp.write('    field(FTD,   "LONG")\n')
            fp.write('    field(NOD,   "1")\n')
            fp.write('    field(INPE,  "%s:_ARGS%d NPP")\n' % (name, i))
            fp.write('    field(FTE,   "LONG")\n')
            fp.write('    field(NOE,   "1")\n')
            fp.write('    field(INPF,  "%s:_SNAMENAME%d NPP")\n' % (name, i))
            fp.write('    field(FTF,   "STRING")\n')
            fp.write('    field(NOF,   "1")\n')
            for (n, lll) in enumerate(ll):
                c = chr(ord('G') + n)
                fp.write('    field(INP%s,  "%s:_PROG%d_%d NPP")\n' % 
                         (c, name, i, n))
                fp.write('    field(FT%s,   "STRING")\n' %  c)
                fp.write('    field(NO%s,   "1")\n' % c)
            fp.write('    field(OUTA,  "%s:_REQ%d PP")\n' % (name, i))
            fp.write('    field(FTVA,  "LONG")\n')
            fp.write('    field(NOVA,  "1")\n')
            fp.write('    field(OUTB,  "%s:_STATE%d PP")\n' % (name, i))
            fp.write('    field(FTVB,  "LONG")\n')
            fp.write('    field(NOVB,  "1")\n')
            fp.write('    field(OUTC,  "%s:_PIPE%d PP")\n' % (name, i))
            fp.write('    field(FTVC,  "LONG")\n')
            fp.write('    field(NOVC,  "1")\n')
            fp.write('    field(OUTD,  "%s:_PID%d PP")\n' % (name, i))
            fp.write('    field(FTVD,  "LONG")\n')
            fp.write('    field(NOVD,  "1")\n')
            fp.write('}\n\n')
            i = i + 1
            continue
    out.append('}\n\n')
    for l in out:
        fp.write(l)

def expand(lines, fp):
    i = 0;
    while i < len(lines):
        if lines[i][:9] != "sequence(":
            fp.write(lines[i])
            i = i + 1
            continue
        start = i
        while lines[i][0] != '}':
            i = i + 1
        #print "\nSequence from line %d to line %d" % (start, i)
        d = process(lines[start:i+1])
        generate_seq(d[0][1][0], d[0][2], fp)
        i = i + 1

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

