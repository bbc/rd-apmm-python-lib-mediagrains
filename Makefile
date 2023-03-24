MS_DOCKER_PUSH:=TRUE
MS_DOCKER_PUSH_LATEST:=TRUE
DOCKER_REPO:=public.ecr.aws/o4o2s1w1/cloudfit

include ./static-commontooling/make/lib_static_commontooling.mk
include ./static-commontooling/make/standalone.mk
include ./static-commontooling/make/pythonic.mk
include ./static-commontooling/make/docker.mk

all: tools-help

tools-help:
	@echo "make tools                       - Build the docker container for the tools"
	@echo "make run-cmd                     - Output the docker command required to make use of a tool container"

tools: ms_docker-build ;

run-cmd: tools
	@echo docker run --rm -it -v $(shell pwd):/data ${MODNAME}:${BUILD_TAG}


.PHONY: tools tool-% run-cmd-%
