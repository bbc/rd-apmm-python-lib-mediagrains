#
# Makefile include file to copy some files from commontooling/misc across to $(topdir)
#
# Before including this file may want to set any of the following variables:
#
#   MISC_FILES?=
#       A list of files in $(topdir) to be created
#

MISC_FILES?=
CLEAN_FILES += $(MISC_FILES)

# Use a static pattern rule to match misc files and their prereqs
$(MISC_FILES): $(topdir)/%: $(commontooling_dir)/misc/%
	cp -f $^ $@

prepcode: $(MISC_FILES)
