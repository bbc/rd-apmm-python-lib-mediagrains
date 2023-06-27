MS_DOCKER_PUSH:=TRUE
DOCKER_REPO:=public.ecr.aws/o4o2s1w1/cloudfit

include ./static-commontooling/make/lib_static_commontooling.mk
include ./static-commontooling/make/standalone.mk
include ./static-commontooling/make/pythonic.mk


# Only push latest tag if this version is a release (so there's no next version yet)
ifeq "${VERSION}" "${NEXT_VERSION}"
MS_DOCKER_PUSH_LATEST:=TRUE
endif

include ./static-commontooling/make/docker.mk

all: tools-help

tools-help:
	@echo "make tools                       - Build the docker container for the tools"
	@echo "make run-cmd                     - Output the docker command required to make use of a tool container"

tools: ms_docker-build ;

run-cmd: tools
	@echo docker run --rm -it -v $(shell pwd):/data ${MODNAME}:${BUILD_TAG}


.PHONY: tools
