MS_DOCKER_PUSH:=TRUE
DOCKER_REGISTRY:=docker.io/bbcrd/

TOOL_LIST:=gsf_probe extract_gsf_essence wrap_audio_in_gsf wrap_video_in_gsf
TOOL_TARGETS:=$(addprefix tool-,$(TOOL_LIST))
TOOL_PUSH_TARGETS:=$(addprefix ms_docker-push-,$(TOOL_LIST))
TOOL_PUSH_LATEST_TARGETS:=$(addprefix ms_docker-push-latest-,$(TOOL_LIST))

include ./static-commontooling/make/lib_static_commontooling.mk
include ./static-commontooling/make/standalone.mk
include ./static-commontooling/make/pythonic.mk
include ./static-commontooling/make/docker.mk

all: tools-help

tools-help:
	@echo "make tools                       - Build the docker containers for all tools"
	@echo "make tool-gsf_probe              - Build the docker container for the gsf_probe tool"
	@echo "make tool-extract_gsf_essence    - Build the docker container for the extract_gsf_essence tool"
	@echo "make tool-wrap_audio_in_gsf      - Build the docker container for the wrap_audio_in_gsf tool"
	@echo "make tool-wrap_video_in_gsf      - Build the docker container for the wrap_video_in_gsf tool"
	@echo "make run-cmd-<tool name>         - Output the docker command required to make use of a tool container"

tools: $(TOOL_TARGETS)

tool-%: ms_docker-build-% ;

run-cmd-%: ms_docker-build-%
	@echo docker run --rm -it -v $(shell pwd):/data ${MODNAME}_$*:${BUILD_TAG}

ifeq "${enable_push}" "TRUE"
push: $(TOOL_PUSH_TARGETS) $(TOOL_PUSH_LATEST_TARGETS)

push-%: ms_docker-push-% ms_docker-push-latest-% ;
endif

.PHONY: tools tool-% run-cmd-% push-%
