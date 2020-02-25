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

#=============================
# Build an ioc application
# Use PROD_IOC_RTEMS for RTEMS only
# Use PROD_IOC_Linux for Linux only
PROD_IOC_Linux = mods

# mods.dbd will be created and installed
DBD += mods.dbd
DBD += stepSequenceRecord.dbd

DBDINC += stepSequenceRecord

# mods.dbd will be made up from these files:
mods_DBD += base.dbd
mods_DBD += iocAdmin.dbd
mods_DBD += asSupport.dbd
mods_DBD += stepSequenceRecord.dbd
mods_DBD += seq_funcs.dbd

# <name>_registerRecordDeviceDriver.cpp will be created from <name>.dbd
mods_SRCS += mods_registerRecordDeviceDriver.cpp
mods_SRCS_DEFAULT += modsMain.cpp

# Add locally compiled object code
#mods_SRCS += dbSubExample.c
mods_SRCS += stepSequenceRecord.c seq_funcs.cpp test_funcs.cpp

mods_LIBS += devIocStats
mods_LIBS += autosave
mods_LIBS += $(EPICS_BASE_IOC_LIBS)

#===========================

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD RULES AFTER THIS LINE

