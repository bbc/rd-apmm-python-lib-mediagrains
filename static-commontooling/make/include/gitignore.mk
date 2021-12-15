#
# Makefile include file to include standard cloudfit gitignore behaviour
# Do not include directly, is used by layer.mk, etc ...

# Custom gitignore file support
ifeq "$(CUSTOM_GITIGNORE_FILE)" ""
prepcode: $(topdir)/.gitignore

$(topdir)/.gitignore: $(commontooling_dir)/misc/$(CLOUDFIT_MAKE_MODE).gitignore
	cp -f $< $@

ifneq ($(EXTRA_GITIGNORE_LINES), "")
	echo "\n\n# Extra gitignore lines from Makefile" >> $@
	set -f; for ignore_line in $(EXTRA_GITIGNORE_LINES); do \
		echo $$ignore_line >> $@ ; \
	done
endif
endif
