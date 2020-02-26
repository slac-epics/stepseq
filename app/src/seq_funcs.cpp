#include<registryFunction.h>
#include<epicsExport.h>
#include<dbCommon.h>
#include<epicsVersion.h>
#if EPICS_VERSION == 3 && EPICS_REVISION == 14
#include<aSubRecord2.h>
#else
#include<aSubRecord.h>
#endif
#include<iocsh.h> 
#include<link.h>
#include<recGbl.h>
#include<dbAccess.h>
#include<stdio.h>
#include<stdlib.h>
#include<unistd.h>
#include<string.h>
#include<strings.h>
#include"seq_funcs.h"
#include<sys/types.h>
#include<sys/wait.h>
#include<signal.h>
#include<sched.h>
#include<errno.h>

extern "C" {
long aSubControl(struct aSubRecord *psub)
{
    epicsInt32 oreq       = *(epicsInt32 *)psub->a;
    epicsInt32 oabrt      = *(epicsInt32 *)psub->b;
    epicsInt32 ostate     = *(epicsInt32 *)psub->c;
    epicsInt32 *req       = (epicsInt32 *)psub->vala;
    epicsInt32 *abrt      = (epicsInt32 *)psub->valb;
    epicsInt32 *state     = (epicsInt32 *)psub->valc;
    epicsInt32 *active    = (epicsInt32 *)psub->vald;
    epicsInt8  *snameout  = (epicsInt8 *)psub->vale;
    epicsInt32 *stateout  = (epicsInt32 *)psub->valf;
    epicsInt8  *lnameout  = (epicsInt8 *)psub->ovle;
    epicsInt32 *lstateout = (epicsInt32 *)psub->ovlf;

    *state = ostate;
    if (ostate != selSSRstate_Running) {
        if (oreq)
            *state = selSSRstate_Running;
    }
    if (ostate == selSSRstate_Running) {
        if (oabrt)
            *state = selSSRstate_Aborted;
    }
    *req = 0;
    *abrt = 0;
    *active = (*state == selSSRstate_Running) ? 1 : 0;
    if (*active && ostate != selSSRstate_Running) {
        /* Initialize the stepname and state outputs of the aSub if 
           starting!  We're taking advantage of "ON CHANGE" here and
           faking it! */
        lnameout[0]= 'A';
        lnameout[1]= 0;
        *snameout = 0;
        *lstateout = selSSRstate_Done;
        *stateout = selSSRstate_Running;
    }
    psub->udf = false;
    recGblGetTimeStamp(psub);
    return 0;
}

long ProcessMonitor(struct aSubRecord *psub)
{
    epicsInt32 opid    = *(epicsInt32 *)psub->a;
    epicsInt32 oabrt   = *(epicsInt32 *)psub->b;
    epicsInt8  *osn    = (epicsInt8 *)psub->c;
    epicsInt32 ostate  = *(epicsInt32 *)psub->d;
    epicsInt32 *pid    = (epicsInt32 *)psub->vala;
    epicsInt32 *abrt   = (epicsInt32 *)psub->valb;
    epicsInt8  *sn     = (epicsInt8 *)psub->valc;
    epicsInt32 *state  = (epicsInt32 *)psub->vald;

    // Clear the abort, but just copy the rest of the state by default!
    *state = ostate;
    strcpy(sn, osn);
    *abrt = 0;
    *pid = opid;

    if (opid != -1) {
        siginfo_t info;
        info.si_pid = 0;
        int status = waitid(P_PID, opid, &info, WNOHANG | WEXITED);
        if (status) {
            printf("ProcessMonitor(%d): waitid returned status %d\n", opid, status);
            *state = selSSRstate_Aborted;
            *pid = -1;
            sprintf(sn, "ABORT: waitid error for pid %d", opid);
        } else if (info.si_pid != 0) {
            // si_status can be a signal or a return code.  We don't care,
            // either way, it counts as an abort.  Only returning zero is good!
            if (info.si_status) {
                *state = selSSRstate_Aborted;
            } else {
                *state = selSSRstate_Done;
                strcpy(sn, "DONE");
            }
            *pid = -1;
        }
        if (oabrt) {
            printf("Abort requested, sending signal to %d\n", opid);
            int status = killpg(opid, SIGINT);
            if (status) {
                printf("kill gives status %d?\n", status);
                perror("ProcessMonitor");
            }
        }
    }
    psub->udf = false;
    recGblGetTimeStamp(psub);
    return 0;
}

long ProcessSpawn(struct aSubRecord *psub)
{
    epicsInt32 oreq    = *(epicsInt32 *)psub->a;
    epicsInt32 ostate  = *(epicsInt32 *)psub->b;
    epicsInt32 opid    = *(epicsInt32 *)psub->c;
    epicsInt32 argc    = *(epicsInt32 *)psub->d;
    epicsInt8 *stepnm  = (epicsInt8 *)psub->e;
    epicsInt8 **av     = (epicsInt8 **)&psub->f;
    epicsInt32 *req    = (epicsInt32 *)psub->vala;
    epicsInt32 *state  = (epicsInt32 *)psub->valb;
    epicsInt32 *pid    = (epicsInt32 *)psub->valc;
    char      *argv[17]; // E-U!

    // Clear the request, but just let everything else be unchanged.
    *req = 0;
    *state = ostate;
    *pid = opid;

    memcpy(argv, av, 17*sizeof(char *));
    argv[argc] = NULL;

    if (oreq && opid == -1) {
        if (!(*pid = fork())) {
            struct sched_param param;
            int status;
            sigset_t set;
            char *buf = (char *)malloc(strlen(stepnm) + 12);
            sprintf(buf, "STEPNAMEPV=%s", stepnm);
            putenv(buf);
            sigemptyset(&set);
            sigprocmask(SIG_SETMASK, &set, NULL);       /* Take all signals! */
            setsid();                                   /* Be our own process group! */
            param.sched_priority = 0;
            sched_setscheduler(0, SCHED_OTHER, &param); /* Not real-time! */
            status = execvp(argv[0], argv);
            printf("Exec of %s failed with status %d?\n", argv[0], status);
            perror("ProcessSpawn");
            exit(1);
        }
        printf("Spawned process %d\n", *pid);
        *state = selSSRstate_Running;
    }
    psub->udf = false;
    recGblGetTimeStamp(psub);
    return 0;
}

long ProcessInit(struct aSubRecord *psub)
{
    epicsInt32 pid    = *(epicsInt32 *)psub->a;
    epicsInt32 req    = *(epicsInt32 *)psub->b;
    epicsInt32 *state = (epicsInt32 *)psub->vala;
    epicsInt8  *name  = (epicsInt8 *)psub->valb;
    epicsInt32 *proc  = (epicsInt32 *)psub->valc;
    *state = selSSRstate_Running;
    strcpy(name, "Starting");
    *proc = 1;
    psub->udf = false;
    recGblGetTimeStamp(psub);
    return (pid < 0 && req > 0) ? 0 : 1; /* Only write if 0! */
}

static const iocshArg setPathArg0 = {"dir"  ,    iocshArgString};
static const iocshArg *const setPathArgs[1] = {
    &setPathArg0,
};
static const iocshFuncDef setPathDef = {"setPath", 1, setPathArgs};

static void setPathCall(const iocshArgBuf * args)
{
    char *buf = (char *)malloc(strlen(args[0].sval) + 5);
    sprintf(buf, "PATH=%s", args[0].sval);
    putenv(buf);
}

static const iocshArg prefixPathArg0 = {"dir"  ,    iocshArgString};
static const iocshArg *const prefixPathArgs[1] = {
    &prefixPathArg0,
};
static const iocshFuncDef prefixPathDef = {"prefixPath", 1, prefixPathArgs};

static void prefixPathCall(const iocshArgBuf * args)
{
    char *path = getenv("PATH");
    char *buf = (char *)malloc(strlen(args[0].sval) + 6 + strlen(path));
    sprintf(buf, "PATH=%s:%s", args[0].sval, path);
    putenv(buf);
}

static const iocshArg postfixPathArg0 = {"dir"  ,    iocshArgString};
static const iocshArg *const postfixPathArgs[1] = {
    &postfixPathArg0,
};
static const iocshFuncDef postfixPathDef = {"postfixPath", 1, postfixPathArgs};

static void postfixPathCall(const iocshArgBuf * args)
{
    char *path = getenv("PATH");
    char *buf = (char *)malloc(strlen(args[0].sval) + 6 + strlen(path));
    sprintf(buf, "PATH=%s:%s", path, args[0].sval);
    putenv(buf);
}

static void seqRegistrar()
{
    iocshRegister(&setPathDef,  	setPathCall);
    iocshRegister(&prefixPathDef,	prefixPathCall);
    iocshRegister(&postfixPathDef,	postfixPathCall);
}

epicsExportRegistrar(seqRegistrar);
epicsRegisterFunction(aSubControl);
epicsRegisterFunction(ProcessMonitor);
epicsRegisterFunction(ProcessSpawn);
epicsRegisterFunction(ProcessInit);
};

