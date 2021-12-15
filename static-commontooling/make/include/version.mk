#
# Makefile include file to include standard versioning support for top level
# Included by other .mk files, do not use directly.
#

PBRVERSION_VERSION?=1.2.0
# Since the version is pinned above, there's no need to pull images every time, especially since this tool runs very
# frequently
PBRVERSION?=$(DOCKER) run --rm -v $(project_root_dir):/data:ro bbcrd/pbrversion:$(PBRVERSION_VERSION)

# If VERSION is't already set (because it was exported from a higher-level Makefile, extractit from a top level VERSION
# file if present, otherwise we use PBR to extract the version from git in the right formats
ifndef VERSION
export VERSION := $(shell [ -f VERSION ] && cat VERSION || $(PBRVERSION))
export DOCKERISED_VERSION := $(shell [ -f VERSION ] && cat VERSION || $(PBRVERSION) --docker)
export NEXT_VERSION := $(shell [ -f VERSION ] && cat VERSION || $(PBRVERSION) --brief)

endif

all: help-version

# Versioning support
version:
	@echo $(VERSION)

next-version:
	@echo $(NEXT_VERSION)

ifeq "${topdir}" "${project_root_dir}"
release:
	git tag -a $(NEXT_VERSION) -m "v.$(NEXT_VERSION)"
	@echo "Added tag $(NEXT_VERSION) at commit $(GITCOMMIT), to push it up use: git push origin --tags"
endif

help-version:
	@echo "$(PROJECT)-$(VERSION)"
	@echo "make version                     - Print the current version of the code in the repo, including pre-release indicators"
	@echo "make next-version                - Print the version the code should have if it is released as it currently is"
ifeq "${topdir}" "${project_root_dir}"
	@echo "make release                     - Add a tag to the repo marking the current commit as a release"
endif

.PHONY: version next-version help-version release
