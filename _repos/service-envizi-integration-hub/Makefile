# Integration Hub facilitates the integration of data from various external systems into the IBM Envizi ESG Suite.

DOCKER_HUB_ID ?= ibmosquito
MATCH ?= "OhIntegrationHub"
TIME_OUT ?= 30

INTEGRATION_HUB_API_URL ?=http://localhost:3001


# The Open Horizon Exchange's organization ID namespace where you will be publishing files
HZN_ORG_ID ?= examples

export SERVICE_NAME ?= oh-integration-hub
PATTERN_NAME ?= pattern-oh-integration-hub
DEPLOYMENT_POLICY_NAME ?= deployment-policy-oh-integration-hub
NODE_POLICY_NAME ?= node-policy-oh-integration-hub
export SERVICE_VERSION ?= 1.0.0
export SERVICE_CONTAINER := $(DOCKER_HUB_ID)/$(SERVICE_NAME):$(SERVICE_VERSION)
ARCH ?= amd64

# Detect Operating System running Make
OS := $(shell uname -s)

# Leave blank for open DockerHub containers
# CONTAINER_CREDS:=-r "registry.wherever.com:myid:mypw"
CONTAINER_CREDS ?=

default: build run

build:
	docker build --platform linux/arm64 -t $(SERVICE_CONTAINER) .

dev: stop build
	docker run -it -v `pwd`:/outside \
          --name ${SERVICE_NAME} \
          -p 3000:3000 \
		  --env NEXT_PUBLIC_API_URL="${INTEGRATION_HUB_API_URL}" 
          $(SERVICE_CONTAINER) /bin/bash

run: stop
	docker run -d \
          --name ${SERVICE_NAME} \
          --restart unless-stopped \
          -p 3000:3000 \
          $(SERVICE_CONTAINER)


check-syft:
	@echo "=================="
	@echo "Generating SBoM syft-output file..."
	@echo "=================="
	syft $(SERVICE_CONTAINER) > syft-output
	cat syft-output

check:
	@echo "=================="
	@echo "SERVICE DEFINITION"
	@echo "=================="
	@cat service.json | envsubst
	@echo ""

# add SBOM for the source code 
check-grype:
	grype $(SERVICE_CONTAINER) > grype-output
	cat grype-output

sbom-policy-gen:
	@echo "=================="
	@echo "Generating service.policy.json file..."
	@echo "=================="
	./sbom-property-gen.sh


test:
	@echo "=================="
	@echo "Testing $(SERVICE_NAME)..."
	@echo "=================="
	@curl -sS http://127.0.0.1:3000

push:
	docker push $(SERVICE_CONTAINER)

publish: publish-service publish-service-policy publish-deployment-policy

remove: remove-deployment-policy remove-service-policy remove-service
	
publish-service:
	@echo "=================="
	@echo "PUBLISHING SERVICE"
	@echo "=================="
	@hzn exchange service publish -O $(CONTAINER_CREDS) --json-file=service.json --pull-image
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
	@hzn exchange service addpolicy -f service.policy.json $(HZN_ORG_ID)/$(SERVICE_NAME)_$(SERVICE_VERSION)_$(ARCH)
	@echo ""

remove-service-policy:
	@echo "======================="
	@echo "REMOVING SERVICE POLICY"
	@echo "======================="
	@hzn exchange service removepolicy -f $(HZN_ORG_ID)/$(SERVICE_NAME)_$(SERVICE_VERSION)_$(ARCH)
	@echo ""

publish-pattern:
	@ARCH=$(ARCH) \
        SERVICE_NAME="$(SERVICE_NAME)" \
        SERVICE_VERSION="$(SERVICE_VERSION)"\
        PATTERN_NAME="$(PATTERN_NAME)" \
	hzn exchange pattern publish -f pattern.json

publish-deployment-policy:
	@echo "============================"
	@echo "PUBLISHING DEPLOYMENT POLICY"
	@echo "============================"
	@hzn exchange deployment addpolicy -f deployment.policy.json $(HZN_ORG_ID)/policy-$(SERVICE_NAME)_$(SERVICE_VERSION)
	@echo ""

remove-deployment-policy:
	@echo "=========================="
	@echo "REMOVING DEPLOYMENT POLICY"
	@echo "=========================="
	@hzn exchange deployment removepolicy -f $(HZN_ORG_ID)/policy-$(SERVICE_NAME)_$(SERVICE_VERSION)
	@echo ""


stop:
	@docker rm -f ${SERVICE_NAME} >/dev/null 2>&1 || :

clean:
	@docker rmi -f $(SERVICE_CONTAINER) >/dev/null 2>&1 || :

agent-run:
	@echo "================"
	@echo "REGISTERING NODE"
	@echo "================"
	@hzn register --policy=node.policy.json
	@watch hzn agreement list

agent-run-pattern:
	@hzn register --pattern "${HZN_ORG_ID}/$(PATTERN_NAME)"
	
agent-stop:
	@hzn unregister -f

deploy-check:
	@hzn deploycheck all -t device -B deployment.policy.json --service=service.json --service-pol=service.policy.json --node-pol=node.policy.json

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

.PHONY: default build dev run test check push publish remove publish-service remove-service publish-service-policy remove-service-policy publish-pattern publish-deployment-policy remove-deployment-policy stop clean agent-run agent-run-pattern agent-stop deploy-check log