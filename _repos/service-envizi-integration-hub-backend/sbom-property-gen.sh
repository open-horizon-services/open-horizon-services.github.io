#!/bin/bash

# This script generates a list of policy strings in a service.policy.json file a provided SBoM 

sbom="${PWD}/syft-output"

if [[ ! -f "${sbom}" ]]; then
    echo "ERROR: you must run 'make check-syft' first to generate a list of SBoM policies."
    exit
fi

# read in syft-output which contains SBoM data for the service
while IFS= read -r line
do
    PACKAGE=$(echo "${line}" | awk '{print $1}')
    VERSION=$(echo "${line}" | awk '{print $2}')

    if [[ "$PACKAGE" != "NAME" ]]; then
        jq -n --arg package "$PACKAGE" --arg version "$VERSION" '{ "name": $package, "value": $version }'  # service.policy.json > new.service.policy.json
    fi

done < "$sbom" | jq -n '.properties |= [inputs]' > service.policy.json