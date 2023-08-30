#define USE_TYPED_RSET
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include "dbScan.h"
#include "dbDefs.h"
#include "alarm.h"
#include "dbAccess.h"
#include "dbEvent.h"
#include "dbFldTypes.h"
#include "devSup.h"
#include "recSup.h"
#include "recGbl.h"
#include "special.h"
#define GEN_SIZE_OFFSET
#include "arbiterRecord.h"
#undef GEN_SIZE_OFFSET

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

rset arbiterRSET={
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
epicsExportAddress(rset,arbiterRSET);

static long init_record(struct arbiterRecord *prec, int pass)
{
    if (pass == 0)
        return 0;
    prec->val = -1;
    prec->state = 0;
    strcpy(prec->owner, "None");
    if (prec->tpro > 1)
	prec->tpro = 0;
    return 0;
}

static long process(struct arbiterRecord *prec)
{
    epicsUInt32 *req = &prec->req0;
    DBLINK      *own = &prec->own0;
    int i;
    int change = 0;
    unsigned short monitor_mask;

    prec->pact = TRUE;
    if (prec->tpro) {
	printf("%s process start!\n", prec->name);
    }
    if (prec->clear) {
	if (prec->tpro) {
	    printf("%s clear!\n", prec->name);
	}
	prec->val = -1;
	prec->state = 0;
	prec->clear = 0;
	db_post_events(prec, &prec->clear, DBE_VALUE);
	for (i = 0; i < 30; i++) {
	    req[i] = 0;
	    db_post_events(prec, &req[i], DBE_VALUE);
	}
	change = 1;
    }
    if (prec->val != -1) {       /* Already granted! */
	if (!req[prec->val]) {   /* Release requested! */
	    if (prec->tpro) {
		printf("%s release %d!\n", prec->name, prec->val);
	    }
	    prec->val = -1;
	    prec->state = (prec->state + 1) % 30;
	    change = 1;
	}
    }
    if (prec->val == -1) {       /* Not granted, look for a request! */
	for (i = 0; i < 30; i++) {
	    if (req[(prec->state + i) % 30]) {
		prec->val = prec->state = (prec->state + i) % 30;
		if (prec->tpro) {
		    printf("%s grant %d!\n", prec->name, prec->val);
		}
		change = 1;
		break;
	    }
	}
    }
    if (prec->tpro) {
	printf("%s process done!\n", prec->name);
    }
    if (change) {
	if (prec->val == -1)
	    strcpy(prec->owner, "None");
	else {
	    if (own[prec->val].type != CONSTANT) {
		long status = dbGetLink(&own[prec->val], DBR_STRING, prec->owner, 0, 0);
		if (status != 0) {
		    recGblSetSevr(prec, LINK_ALARM, INVALID_ALARM);
		}
	    } else {
		sprintf(prec->owner, "REQ%d", prec->val);
	    }
	}
    }
    prec->udf = 0;
    recGblGetTimeStamp(prec);
    monitor_mask = recGblResetAlarms(prec);
    if (change) {
	db_post_events(prec, &prec->state, monitor_mask | DBE_VALUE);
	db_post_events(prec, &prec->owner, monitor_mask | DBE_VALUE);
	db_post_events(prec, &prec->val, monitor_mask | DBE_VALUE | DBE_LOG);
    }
    recGblFwdLink(prec);
    prec->pact = FALSE;
    return 0;
}
