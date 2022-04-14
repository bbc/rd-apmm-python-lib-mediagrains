USE_VERSION_FILE:=TRUE
MS_DOCKER_PUSH:=TRUE

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

tools: tool-gsf_probe tool-extract_gsf_essence tool-wrap_audio_in_gsf tool-wrap_video_in_gsf

tool-gsf_probe: ms_docker-build-gsf_probe

tool-extract_gsf_essence: ms_docker-build-extract_gsf_essence

tool-wrap_audio_in_gsf: ms_docker-build-wrap_audio_in_gsf

tool-wrap_video_in_gsf: ms_docker-build-wrap_video_in_gsf

run-cmd-%: ms_docker-build-%
	@echo docker run --rm -it -v $(shell pwd):/data ${MODNAME}_$*:${BUILD_TAG}

ifeq "${enable_push}" "TRUE"
push: ms_docker-push-gsf_probe ms_docker-push-extract_gsf_essence ms_docker-push-wrap_audio_in_gsf ms_docker-push-wrap_video_in_gsf 

upload-docker: ms_docker-push-gsf_probe ms_docker-push-extract_gsf_essence ms_docker-push-wrap_audio_in_gsf ms_docker-push-wrap_video_in_gsf

push-%: ms_docker-push-%
	@echo Push successful
endif

.PHONY: tools tool-gsf_probe tool-extract_gsf_essence tool-wrap_audio_in_gsf tool-wrap_video_in_gsf run-cmd-% push-%