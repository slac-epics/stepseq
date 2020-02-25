#include<stdio.h>
#include<stdlib.h>
#include<string.h>

#include "dbScan.h"
#include "dbDefs.h"
#include "dbEvent.h"
#include "alarm.h"
#include "dbAccess.h"
#include "recSup.h"
#include "recGbl.h"
#define GEN_SIZE_OFFSET
#include "stepSequenceRecord.h"
#undef GEN_SIZE_OFFSET
#include "epicsExport.h"
#include "callback.h"

/* Create RSET - Record Support Entry Table*/
#define report NULL
#define initialize NULL
static long init_record();
static long process();
#define special NULL
#define get_value NULL
#define cvt_dbaddr NULL
#define get_array_info NULL
#define put_array_info NULL
#define get_units NULL
#define get_precision NULL
#define get_enum_str NULL
#define get_enum_strs NULL
#define put_enum_str NULL
#define get_graphic_double NULL
#define get_control_double NULL
#define get_alarm_double NULL

rset stepSequenceRSET={
	RSETNUMBER,
	report,
	initialize,
	init_record,
	process,
	special,
	get_value,
	cvt_dbaddr,
	get_array_info,
	put_array_info,
	get_units,
	get_precision,
	get_enum_str,
	get_enum_strs,
	put_enum_str,
	get_graphic_double,
	get_control_double,
	get_alarm_double
};
epicsExportAddress(rset,stepSequenceRSET);

#if 1
#define DPRINTF(a) if (prec->tpro & 2) printf a;
#else
#define DPRINTF(a) 
#endif

static void processCallback(CALLBACK *cb)
{
    struct stepSequenceRecord *prec;
    callbackGetUser(prec, cb);
    DPRINTF(("%s callback, doing scanOnce! (pact=%d)\n", prec->name, prec->pact));
    prec->dlying = 0;
    scanOnce((struct dbCommon *)prec);
}

static long init_record(struct stepSequenceRecord *prec, int pass)
{
    CALLBACK *cb;
    if (pass == 0)
        return 0;
    prec->val = 0;
    prec->wait = 0;
    prec->req = 0;
    prec->abrt = 0;
    prec->state = selSSRstate_Done;
    strcpy(prec->stepname, "DONE");
    cb = (CALLBACK *)calloc(1,sizeof(CALLBACK));
    callbackSetCallback(processCallback, cb);
    callbackSetUser(prec, cb);
    callbackSetPriority(prec->prio, cb);
    prec->dpvt = (void *)cb;
    return 0;
}

#define VAL_MASK        1
#define REQ_MASK        2
#define ABRT_MASK       4
#define STATE_MASK      8
#define WAIT_MASK      16
#define CLR_MASK       32
#define STEPNAME_MASK  64

#define SET(fld, v, mask)       \
    do {                        \
        DPRINTF(("%s.%s set to %d\n", prec->name, #fld, (v)));\
        prec->fld = (v);        \
        monitor_mask |= (mask); \
    } while (0)

#define SET_VAL(v)     SET(val, (v), VAL_MASK)
#define SET_REQ(v)     SET(req, v, REQ_MASK)
#define SET_ABRT(v)    SET(abrt, v, ABRT_MASK)
#define SET_STATE(v)   SET(state, v, STATE_MASK)
#define SET_WAIT(v)    SET(wait, v, WAIT_MASK)
#define SET_CLR(v)     SET(clr, v, CLR_MASK)
#define SET_OREQ(v)                \
    do {                           \
        int ov = (v);              \
        DBLINK *l = (&prec->req0) + prec->val;\
        DPRINTF(("%s.REQ%d request (%s)\n", prec->name, prec->val, l->value.pv_link.pvname));\
        status = dbPutLink(l, DBR_LONG, &ov, 1);\
    } while (0)
#define SET_OABRT(v)               \
    do {                           \
        int ov = (v);              \
        DBLINK *l = (&prec->abrt0) + prec->val;\
        if (l->type != CONSTANT) { \
            DPRINTF(("%s.ABRT%d request (%s)\n", prec->name, prec->val, l->value.pv_link.pvname));\
            status = dbPutLink(l, DBR_LONG, &ov, 1);\
        }                          \
    } while (0)

static long process(struct stepSequenceRecord *prec)
{
    unsigned short mask;
    int monitor_mask = 0, curstate = 0, status, finish = 0, st;
    char sn[128], *s;

    DPRINTF(("%s process.\n", prec->name));
    if (prec->dlying)
        return 0;
    prec->pact = TRUE;
    /* Note, if no CLR link, status is 0, so we need to initialize curstate above! */
    status = dbGetLink(&prec->clr, DBR_LONG, &curstate, 0, 0);
    if (!status && curstate) {
        if (prec->state == selSSRstate_Aborted) {
            SET_STATE(selSSRstate_Done);
            SET_VAL(0);
        }
    }
    switch (prec->state) {
    case selSSRstate_Done:
    case selSSRstate_Aborted:
        if (prec->abrt)                /* Can't abort if we aren't running! */
            SET(abrt, 0, ABRT_MASK);   
        if (!prec->req)                /* No request == Nothing to do! */
            break;
        DPRINTF(("%s: start request!\n", prec->name));
        SET_REQ(0);
        SET_STATE(selSSRstate_Running);
        SET_VAL(0);
        SET_WAIT(0);
        /* Fall through! */
    case selSSRstate_Running:
        if (prec->req)             /* We're already running, so just clear the request! */
            SET_REQ(0);
        if (prec->wait) {          /* We have written to the output, waiting for done! */
            status = dbGetLink((&prec->state0) + prec->val, DBR_LONG, &curstate, 0, 0);
            if (status || curstate == selSSRstate_Aborted || prec->abrt) {
                DPRINTF(("Aborting: status = %d, curstate = %d, prec->abrt = %d\n", 
                         status, curstate, prec->abrt));
                /*
                 * Either we've failed to read the link, the child has
                 * aborted, or a parent has aborted.  So, abort!
                 */
                SET_STATE(selSSRstate_Aborted);
                recGblSetSevr(prec, LINK_ALARM, MAJOR_ALARM);
                if (prec->abrt && curstate != selSSRstate_Aborted) {
                    SET_OABRT(1);  /* We're actually ignoring errors here! */
                    SET_ABRT(0);
                }
                break;
            }
            DPRINTF(("Running: %s.STATE%d is %d\n", prec->name, prec->val, curstate));
            if (curstate != selSSRstate_Done) /* Not finished yet! */
                break;
            DPRINTF(("%s.STATE%d is done!\n", prec->name, prec->val));
            SET_VAL(prec->val+1);  /* Next step! */
            SET_WAIT(0);
        }
        if (prec->val == 10 || (&prec->req0)[prec->val].type == CONSTANT) { /* No next link, we're done!! */
            DPRINTF(("%s: DONE!!\n", prec->name));
            SET_STATE(selSSRstate_Done);
            SET_VAL(0);
            finish = 1;
            break;
        }
        SET_OREQ(1);
        prec->dlying = 1;
        callbackRequestDelayed(prec->dpvt, prec->dly); /* Wait a bit for the STATE to change! */
        if (status) {
            SET_STATE(selSSRstate_Aborted);
            recGblSetSevr(prec, LINK_ALARM, MAJOR_ALARM);
            break;
        }
        if ((&prec->state0)[prec->val].type == CONSTANT) {
            SET_VAL(prec->val + 1); /* Enter the next write state */
        } else {
            SET_WAIT(1);            /* Enter the wait state */
        }
        break;
    }

    /* Now, set the step name! */
    if (prec->state != selSSRstate_Done) {
        /*
         * OK, this is now more complicated than originally thought.
         * We really want this to be "PREn: STEPn".  But if someone is
         * aborted, we want to prepend "ABORT:"  But then "STEPn" might
         * already reflect this!
         */
        int abort = (prec->state == selSSRstate_Aborted);
        char *pre = (&prec->pre0)[prec->val];
        char buf[128], *t = buf;
        if (prec->dlying)
            strcpy(buf, "Next step");
        else {
            if ((&prec->stepname0)[prec->val].type == CONSTANT)
                buf[0] = 0;
            else {
                st = dbGetLink((&prec->stepname0) + (prec->val), 
                               DBR_STRING, t, 0, 0);
                if (st || !strcmp(buf, "DONE"))
                    t[0] = 0;
                else if (!strncmp(buf, "ABORT: ", 7)) { /* Strip "ABORT: "! */
                    t += 7;
                    abort = 1;
                }
            }
        }
        s = sn;
        if (abort) {
            strcpy(s, "ABORT: ");
            s += 7;
        }
        if (!*pre && !t[0]) {
            /* If we don't have any sort of a message, make one! */
            if (prec->val == 10 || (&prec->req0)[prec->val].type == CONSTANT)
                strcpy(buf, "DONE");
            else
                sprintf(buf, "Step %d", prec->val);
        }
        if (*pre) {
            strcpy(s, pre);
            s += strlen(pre);
            if (buf[0]) {
                strcpy(s, ": ");
                s += 2;
            }
        }
        if (t[0]) {
            strcpy(s, t);
            s += strlen(t);
        }
        if (strncmp(prec->stepname, sn, sizeof(prec->stepname))) {
            strncpy(prec->stepname, sn, sizeof(prec->stepname));
            monitor_mask |= STEPNAME_MASK;
        }
    } else {
        if (strcmp(prec->stepname, "DONE")) {
            strcpy(prec->stepname, "DONE");
            monitor_mask |= STEPNAME_MASK;
        }
    }

    prec->udf = FALSE;
    recGblGetTimeStamp(prec);

    /* Process the monitors! */
    mask = recGblResetAlarms(prec) | DBE_VALUE | DBE_LOG;
    if (monitor_mask & STEPNAME_MASK)
        db_post_events(prec, &prec->stepname, mask);
    if (monitor_mask & VAL_MASK)
        db_post_events(prec, &prec->val, mask);
    if (monitor_mask & REQ_MASK)
        db_post_events(prec, &prec->req, mask);
    if (monitor_mask & ABRT_MASK)
        db_post_events(prec, &prec->abrt, mask);
    if (monitor_mask & STATE_MASK)
        db_post_events(prec, &prec->state, mask);
    if (monitor_mask & WAIT_MASK)
        db_post_events(prec, &prec->wait, mask);

    /* If we have finished, process the forward link! */
    if (finish)
        recGblFwdLink(prec);

    prec->pact = FALSE;
    return 0;
}

