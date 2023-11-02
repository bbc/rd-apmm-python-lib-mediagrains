#
# Makefile include file to set ECR docker variables
# Do not include directly, is used by ms_docker.mk
#
# Configurable variables:
#
#    AWS_SHARED_CREDENTIALS_FILE?=
#       The file location of AWS credentials file for ECR access. Defaults to using the forge certificate.
#

ifneq ($(findstring public.ecr.aws,$(DOCKER_REPO)),)
# ECR Public registry
	IS_ECR_REGISTRY:=true
	ECR_COMMAND:=ecr-public
	ECR_HOST:=$(word 1,$(subst /, ,$(DOCKER_REPO)))
# There is no ECS Public endpoint in eu-west-1, which is why us-east-1 is used instead
	ECR_LOGIN_REGION:=us-east-1
else  # ifneq ($(findstring public.ecr.aws,$(DOCKER_REPO)),)
ifneq ($(findstring dkr.ecr,$(DOCKER_REPO)),)
# ECR (Private) registry
	IS_ECR_REGISTRY:=true
	ECR_COMMAND:=ecr
	ECR_HOST:=$(word 1,$(subst /, ,$(DOCKER_REPO)))
	ECR_LOGIN_REGION:=$(word 4,$(subst ., ,$(DOCKER_REPO)))
else  # ifneq ($(findstring dkr.ecr,$(DOCKER_REPO)),)
	IS_ECR_REGISTRY:=false
endif  # ifneq ($(findstring dkr.ecr,$(DOCKER_REPO)),)
endif  # ifneq ($(findstring public.ecr.aws,$(DOCKER_REPO)),)



ifeq (${IS_ECR_REGISTRY},true)
	ECR_REPO_NAME:=cloudfit/${MODNAME}

ifeq (${GITHUB_ACTIONS},true)
	# On GitHub actions, the AWS credentials doesn't exist
	# But aws-cli is available and has access to creds via other means
	CREATE_ECR_REPO:=aws ${ECR_COMMAND} create-repository --repository-name ${ECR_REPO_NAME} --region ${ECR_LOGIN_REGION}
	ECR_LOGIN:=
	ECR_LOGOUT:=

# On GitHub Actions, ECR login and logout is handled by the workflow
define ecr_docker_push
	${CREATE_ECR_REPO} || true
	docker push $(1)
endef

else  # ifeq (${GITHUB_ACTIONS},true)

	CLOUDFIT_AWS_IMAGE:=ap-docker.artifactory.labs.bbc/cloudfit/aws:latest

ifneq ($(AWS_SHARED_CREDENTIALS_FILE),)
	AWS_DOCKER_ARGS:=-v ${AWS_SHARED_CREDENTIALS_FILE}:/root/.aws/config ${CLOUDFIT_AWS_IMAGE}
else  # ifneq ($(AWS_SHARED_CREDENTIALS_FILE),)
	AWS_DOCKER_ARGS:=-v ${FORGE_CERT}:/run/secrets/forgecert:ro ${CLOUDFIT_AWS_IMAGE}
endif # ifneq ($(AWS_SHARED_CREDENTIALS_FILE),)

	CREATE_ECR_REPO:=docker run --rm ${AWS_DOCKER_ARGS} ${ECR_COMMAND} create-repository --repository-name ${ECR_REPO_NAME} --region ${ECR_LOGIN_REGION}
	ECR_LOGIN:=docker run --rm -i ${AWS_DOCKER_ARGS} ${ECR_COMMAND} get-login-password --region ${ECR_LOGIN_REGION} | docker login --username AWS --password-stdin ${ECR_HOST}
	ECR_LOGOUT:=docker logout ${ECR_HOST}

# Log into the ECR registry before pushing, and then log out
# Create the AWS ECR repo because ECR doesn't support create on push - see https://github.com/aws/containers-roadmap/issues/853
define ecr_docker_push
	${CREATE_ECR_REPO} || true
	${ECR_LOGIN}
	docker push $(1); res=$$?; \
		${ECR_LOGOUT}; \
		exit $$res
endef

endif  # ifeq (${GITHUB_ACTIONS},true)
endif  # ifeq (${IS_ECR_REGISTRY},true)

