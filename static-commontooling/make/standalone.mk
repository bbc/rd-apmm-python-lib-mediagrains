#
# Makefile include file to include standard cloudfit tooling for a standalone project
# Should usually be the first file included in Makefile

#
# Before inclusing you may want to set the following variables:
#
#    EXTRA_GITIGNORE_LINES?=
#       Add extra lines that should appear in the generated .gitignore file
#

CLOUDFIT_MAKE_MODE=standalone

EXTRA_GITIGNORE_LINES?=

# Set up basic directories, assuming a Makefile in a layer directory
ifndef topdir
NUM_OF_PARENT:=$(shell echo $$(( $(words $(MAKEFILE_LIST)) - 1)) )
topdir:=$(realpath $(dir $(word $(NUM_OF_PARENT),$(MAKEFILE_LIST))))
project_root_dir?=$(topdir)
commontooling_dir?=$(project_root_dir)/commontooling
endif

include $(commontooling_dir)/make/include/core.mk
-include $(project_root_dir)/commontooling/make/include/jenkinsfile.mk
-include $(project_root_dir)/commontooling/make/include/pull_request_template.mk
include $(commontooling_dir)/make/include/gitignore.mk

prepcode: $(topdir)/.gitignore

.PHONY: prepcode
