#include<stepSequenceRecord.h>

#define STEPNAME(p, v)                                 \
    strcpy((epicsInt8 *)(p)->valt, v)

#define DONE(p)                                        \
do {                                                   \
    *(epicsUInt32 *)((p)->valu) = selSSRstate_Done;    \
    STEPNAME(p, "Done");                               \
} while(0)

#define ABORT(p, v)                                    \
do {                                                   \
    *(epicsUInt32 *)((p)->valu) = selSSRstate_Aborted; \
    STEPNAME(p, v);                                    \
} while(0)

