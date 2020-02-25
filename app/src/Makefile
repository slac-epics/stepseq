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

DBDINC += stepSequenceRecord.dbd
INC += seq_funcs.h

LIBSRCS += stepSequenceRecord.c

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD RULES AFTER THIS LINE

