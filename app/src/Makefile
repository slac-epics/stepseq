TOP=../..

include $(TOP)/configure/CONFIG
#----------------------------------------
#  ADD MACRO DEFINITIONS AFTER THIS LINE
#=============================

#=====================================================
# Path to "NON EPICS" External PACKAGES: USER INCLUDES
#======================================================


#======================================================
# PATH TO "NON EPICS" EXTERNAL PACKAGES: USER LIBRARIES
#======================================================


# ======================================================
# LINK "NON EPICS" EXTERNAL PACKAGE LIBRARIES STATICALLY
#=======================================================

LIBRARY_IOC_Linux = stepseq
DBD += stepseq.dbd

stepseq_DBD += seq_funcs.dbd
stepseq_DBD += rwrec_funcs.dbd
stepseq_DBD += stepSequenceRecord.dbd
stepseq_DBD += arbiterRecord.dbd

DBDINC += stepSequenceRecord
DBDINC += arbiterRecord
INC += seq_funcs.h

LIBSRCS += stepSequenceRecord.c arbiterRecord.c seq_funcs.cpp rwrec_funcs.cpp

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD RULES AFTER THIS LINE

