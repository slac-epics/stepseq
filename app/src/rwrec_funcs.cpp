#define USE_TYPED_RSET
#include<registryFunction.h>
#include<epicsExport.h>
#include<dbCommon.h>
#include<epicsVersion.h>
#include<aSubRecord.h>
#include<link.h>
#include<recGbl.h>
#include<dbAccess.h>
#include<stdio.h>
#include<stdlib.h>
#include<string.h>
#include<strings.h>
#include<menuFtype.h>

extern "C" {

static int doFmt(char *name, char *fmt, void **args, epicsEnum16 *atype, char *buf)
{
    char *s = fmt, *t = buf;
    while (*s) {
	if (*s != '%') {
	    *t++ = *s++;
	    continue;
	}
	switch (*++s) {
	case 'd':
	    if (*atype != menuFtypeLONG) {
		printf("ERROR %s: %%d format expects a LONG value!\n", name);
		*t = 0;
		return 1;
	    }
	    sprintf(t, "%d", **(epicsInt32 **)args);
	    t += strlen(t);
	    break;
	case 'u':
	    if (*atype != menuFtypeULONG) {
		printf("ERROR %s: %%u format expects a ULONG value!\n", name);
		*t = 0;
		return 1;
	    }
	    sprintf(t, "%u", **(epicsUInt32 **)args);
	    t += strlen(t);
	    break;
	case 's':
	    if (*atype != menuFtypeSTRING) {
		printf("ERROR %s: %%s format expects a STRING value!\n", name);
		*t = 0;
		return 1;
	    }
	    strcpy(t, *(char **)args);
	    t += strlen(t);
	    break;
	default:
	    printf("ERROR %s: unexpected format character '%c'.\n", name, *s);
	    *t = 0;
	    return 1;
	}
	args++;
	atype++;
	s++;
    }
    *t = 0;
    return 0;
}

long rwRecordInit(struct aSubRecord *psub)
{
    /*
     * What do we want here?
     *
     * A, the format, must be a string.
     * 
     * If a read:
     *     FTVA == FTU, and these are both a type we understand.
     *     FTVB is a string.
     */
    if (psub->fta != menuFtypeSTRING) {
	printf("ERROR: %s.FTA is not STRING for aSub rwRecord!\n", psub->name);
	psub->pact = TRUE;
    }
    if (!strcmp(psub->snam, "doReadRecord")) {
	if (psub->ftva != psub->ftu) {
	    printf("ERROR: %s.FTVA must match .FTU for aSub doReadRecord!\n", psub->name);
	    psub->pact = TRUE;
	}
	if (psub->ftva != menuFtypeSTRING && psub->ftva != menuFtypeDOUBLE &&
	    psub->ftva != menuFtypeLONG && psub->ftva != menuFtypeULONG) {
	    printf("ERROR: %s.FTVA must be LONG, ULONG, DOUBLE, or STRING!\n", psub->name);
	    psub->pact = TRUE;
	}
	if (psub->ftvb != menuFtypeSTRING) {
	    printf("ERROR: %s.FTVB must be STRING!\n", psub->name);
	    psub->pact = TRUE;
	}
    }
    return 0;
}

long doWriteRecord(struct aSubRecord *psub)
{
    char *fmt            = (char *)psub->a;
    void **args          = &psub->b;
    epicsEnum16 *atype   = &psub->ftb;
    void *val            = psub->u;
    int   ftype          = psub->ftu;
    char  buf[512];
    DBADDR addr;

    if (doFmt(psub->name, fmt, args, atype, buf)) {
	psub->pact = TRUE;
    } else {
	if (dbNameToAddr(buf, &addr)) {
	    printf("doWriteRecord: Cannot find PV %s?\n", buf);
	} else {
	    int dbrtype = (ftype == menuFtypeSTRING) 
		              ? DBR_STRING : 
		                ((ftype == menuFtypeDOUBLE) 
			            ? DBR_DOUBLE : DBR_LONG);
	    dbPutField(&addr, dbrtype, val, 1);
	}
    }
    psub->udf = false;
    recGblGetTimeStamp(psub);
    return 0;
}

long doReadRecord(struct aSubRecord *psub)
{
    char *fmt            = (char *)psub->a;
    void **args          = &psub->b;
    epicsEnum16 *atype   = &psub->ftb;
    char  buf[512];
    DBADDR addr;

    if (doFmt(psub->name, fmt, args, atype, buf)) {
	psub->pact = TRUE;
    } else if (strcmp(buf, (char *)psub->valb)) {
	/* A new PV to read, set up a subscription in INPU! */
	if (dbNameToAddr(buf, &addr)) {
	    printf("doReadRecord: Cannot find PV %s?\n", buf);
	} else {
	    char b2[512];
	    long options = 0, cnt = 1;
	    int dbrtype = (psub->ftva == menuFtypeSTRING) 
		            ? DBR_STRING : 
	                    ((psub->ftva == menuFtypeDOUBLE) 
			     ? DBR_DOUBLE : DBR_LONG);
	    /* First, get the current value into vala. */
	    dbGetField(&addr, dbrtype, psub->vala, &options, &cnt, NULL);
	    /* Second, put the current *name* into valb */
	    strcpy((char *)psub->valb, buf);
	    /* Finally, put the subscription link into inpu! */
	    strcat(buf, " CPP NMS");
	    sprintf(b2, "%s.INPU", psub->name);
	    if (!dbNameToAddr(b2, &addr))
		dbPutField(&addr, DBR_STRING, buf, 1);
	}
    } else {
	/* The PV name didn't change.  So just copy U to the output! */
	switch (psub->ftva) {
	case menuFtypeSTRING:
	    strcpy((char *)psub->vala, (char *)psub->u);
	    break;
	case menuFtypeDOUBLE:
	    *(epicsFloat64 *)psub->vala = *(epicsFloat64 *)psub->u;
	    break;
	case menuFtypeLONG:
	case menuFtypeULONG:
	    *(epicsInt32 *)psub->vala = *(epicsInt32 *)psub->u;
	    break;
	}
    }
    psub->udf = false;
    recGblGetTimeStamp(psub);
    return 0;
}

epicsRegisterFunction(rwRecordInit);
epicsRegisterFunction(doWriteRecord);
epicsRegisterFunction(doReadRecord);
};
