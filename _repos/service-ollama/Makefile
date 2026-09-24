# Multi-arch docker container instance intended for Open Horizon Linux edge nodes
# This container is provided by a third party from official sources — no build step required.
#
# Required Environment Variables:
# - HZN_ORG_ID: Your Open Horizon organization ID (default: examples)
# - HZN_EXCHANGE_USER_AUTH: Your Exchange credentials in format user:password
# - ARCH: Target architecture - amd64 or arm64 (default: amd64)
#
# Optional Environment Variables:
# - DOCKER_IMAGE_BASE: Base Docker image name (default: ollama/ollama)
# - DOCKER_IMAGE_VERSION: Docker image version tag (default: latest)
# - SERVICE_VERSION: Service version for Open Horizon (default: 0.0.1)
# - DOCKER_VOLUME_NAME: Docker volume for persistent storage (default: ollama-storage)
#
# Service Publishing Targets:
# - validate-service: Validate service definition files
# - publish-service: Publish service to Open Horizon Exchange
# - sign-service: Sign and publish service definition
# - list-services: List published services in Exchange
# - remove-service: Remove service from Exchange
# - publish-service-policy: Publish service policy
# - publish-deployment-policy: Publish deployment policy
# - agent-run: Register node with policy
# - agent-stop: Unregister node
#
export DOCKER_IMAGE_BASE ?= ollama/ollama
export DOCKER_IMAGE_NAME ?= ollama
export DOCKER_IMAGE_VERSION ?= latest
export DOCKER_VOLUME_NAME ?= ollama-storage
# DockerHub ID of the third party providing the image (usually yours if building and pushing)
export DOCKER_HUB_ID ?= ollama
# The Open Horizon organization ID namespace where you will be publishing the service definition file
export HZN_ORG_ID ?= examples
# Open Horizon settings for publishing metadata about the service
export DEPLOYMENT_POLICY_NAME ?= deployment-policy-ollama
export NODE_POLICY_NAME ?= node-policy-ollama
export SERVICE_NAME ?= service-ollama
export SERVICE_VERSION ?= 0.0.1
# Default ARCH to the architecture of this machine
# Convert uname -m output to Open Horizon architecture names
DETECTED_ARCH := $(shell uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')
export ARCH ?= $(DETECTED_ARCH)
# Detect Operating System running Make
OS := $(shell uname -s)
default: init run browse
check:
	@echo "====================="
	@echo "ENVIRONMENT VARIABLES"
	@echo "====================="
	@echo "DOCKER_IMAGE_BASE    default: ollama/ollama              actual: ${DOCKER_IMAGE_BASE}"
	@echo "DOCKER_IMAGE_NAME    default: ollama                     actual: ${DOCKER_IMAGE_NAME}"
	@echo "DOCKER_IMAGE_VERSION default: latest                     actual: ${DOCKER_IMAGE_VERSION}"
	@echo "DOCKER_VOLUME_NAME   default: ollama-storage             actual: ${DOCKER_VOLUME_NAME}"
	@echo "DOCKER_HUB_ID        default: ollama                     actual: ${DOCKER_HUB_ID}"
	@echo "HZN_ORG_ID           default: examples                   actual: ${HZN_ORG_ID}"
	@echo "DEPLOYMENT_POLICY_NAME default: deployment-policy-ollama actual: ${DEPLOYMENT_POLICY_NAME}"
	@echo "NODE_POLICY_NAME     default: node-policy-ollama         actual: ${NODE_POLICY_NAME}"
	@echo "SERVICE_NAME         default: service-ollama             actual: ${SERVICE_NAME}"
	@echo "SERVICE_VERSION      default: 0.0.1                      actual: ${SERVICE_VERSION}"
	@echo "ARCH                 default: amd64                      actual: ${ARCH}"
	@echo ""
	@echo "=================="
	@echo "SERVICE DEFINITION"
	@echo "=================="
	@cat horizon/service.definition.json | envsubst
	@echo ""
stop:
	@docker rm -f $(DOCKER_IMAGE_NAME) >/dev/null 2>&1 || :
init:
	@docker volume create $(DOCKER_VOLUME_NAME)
run: stop
	@docker run -d \
		--name $(DOCKER_IMAGE_NAME) \
		--restart=unless-stopped \
		-v $(DOCKER_VOLUME_NAME):/root/.ollama \
		-p 11434:11434 \
		$(DOCKER_IMAGE_BASE):$(DOCKER_IMAGE_VERSION)
dev: run attach
attach:
	@docker exec -it \
		`docker ps -aqf "name=$(DOCKER_IMAGE_NAME)"` \
		/bin/bash
test:
	@curl -sS http://127.0.0.1:11434
browse:
ifeq ($(OS),Darwin)
	@open http://127.0.0.1:11434
else
	@xdg-open http://127.0.0.1:11434
endif
clean: stop
	@docker rmi -f $(DOCKER_IMAGE_BASE):$(DOCKER_IMAGE_VERSION) >/dev/null 2>&1 || :
	@docker volume rm $(DOCKER_VOLUME_NAME)
distclean: agent-stop remove-deployment-policy remove-service-policy remove-service clean
build:
	@echo "There is no Docker image build process since this container is provided by a third-party from official sources."
push:
	@echo "There is no Docker image push process since this container is provided by a third-party from official sources."
publish: publish-service publish-service-policy publish-deployment-policy agent-run browse
# Pull, not push, Docker image since provided by third party
publish-service: publish-service-amd64 publish-service-arm64

publish-service-amd64:
	@echo "=============================="
	@echo "PUBLISHING SERVICE FOR AMD64"
	@echo "=============================="
	@ARCH=amd64 hzn exchange service publish -O -P --json-file=horizon/service.definition.json
	@echo ""

publish-service-arm64:
	@echo "=============================="
	@echo "PUBLISHING SERVICE FOR ARM64"
	@echo "=============================="
	@hzn exchange service publish -O -P --json-file=horizon/service.definition.arm64.json
	@echo ""
remove-service:
	@echo "=================="
	@echo "REMOVING SERVICE"
	@echo "=================="
	@hzn exchange service remove -f $(HZN_ORG_ID)/$(SERVICE_NAME)_$(SERVICE_VERSION)_$(ARCH)
	@echo ""
publish-service-policy:
	@echo "========================="
	@echo "PUBLISHING SERVICE POLICY"
	@echo "========================="
	@hzn exchange service addpolicy -f horizon/service.policy.json $(HZN_ORG_ID)/$(SERVICE_NAME)_$(SERVICE_VERSION)_$(ARCH)
	@echo ""
remove-service-policy:
	@echo "======================="
	@echo "REMOVING SERVICE POLICY"
	@echo "======================="
	@hzn exchange service removepolicy -f $(HZN_ORG_ID)/$(SERVICE_NAME)_$(SERVICE_VERSION)_$(ARCH)
	@echo ""
publish-deployment-policy:
	@echo "============================"
	@echo "PUBLISHING DEPLOYMENT POLICY"
	@echo "============================"
	@hzn exchange deployment addpolicy -f horizon/deployment.policy.json $(HZN_ORG_ID)/policy-$(SERVICE_NAME)_$(SERVICE_VERSION)
	@echo ""
remove-deployment-policy:
	@echo "=========================="
	@echo "REMOVING DEPLOYMENT POLICY"
	@echo "=========================="
	@hzn exchange deployment removepolicy -f $(HZN_ORG_ID)/policy-$(SERVICE_NAME)_$(SERVICE_VERSION)
	@echo ""
agent-run:
	@echo "================"
	@echo "REGISTERING NODE"
	@echo "================"
	@hzn register --policy=horizon/node.policy.json
	@watch hzn agreement list
agent-stop:
	@echo "==================="
	@echo "UN-REGISTERING NODE"
	@echo "==================="
	@hzn unregister -f
	@echo ""
# Validate service definition files
validate-service:
	@echo "======================="
	@echo "VALIDATING SERVICE"
	@echo "======================="
	@hzn dev service verify -f horizon/service.definition.json
	@echo ""

# Sign service definition
sign-service:
	@echo "=================="
	@echo "SIGNING SERVICE"
	@echo "=================="
	@hzn exchange service publish -O -f horizon/service.definition.json
	@echo ""

# List published services
list-services:
	@echo "====================="
	@echo "LISTING SERVICES"
	@echo "====================="
	@hzn exchange service list $(HZN_ORG_ID)/
	@echo ""

deploy-check:
	@hzn deploycheck all -t device -B horizon/deployment.policy.json --service=horizon/service.definition.json --service-pol=horizon/service.policy.json --node-pol=horizon/node.policy.json
log:
	@echo "========="
	@echo "EVENT LOG"
	@echo "========="
	@hzn eventlog list
	@echo ""
	@echo "==========="
	@echo "SERVICE LOG"
	@echo "==========="
	@hzn service log -f $(SERVICE_NAME)
.PHONY: default stop init run dev test clean build push attach browse publish publish-service publish-service-policy publish-deployment-policy publish-pattern agent-run distclean deploy-check check log remove-deployment-policy remove-service-policy remove-service
