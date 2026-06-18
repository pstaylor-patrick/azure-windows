#!/usr/bin/env bash
set -euo pipefail

AWVM_TFSTATE_RG="${AWVM_TFSTATE_RG:-awvm-tfstate-rg}"
AWVM_TFSTATE_LOCATION="${AWVM_TFSTATE_LOCATION:-eastus2}"
AWVM_TFSTATE_CONTAINER="${AWVM_TFSTATE_CONTAINER:-tfstate}"

if [[ -z "${AWVM_TFSTATE_ACCOUNT:-}" ]]; then
  echo "Error: AWVM_TFSTATE_ACCOUNT must be set (3-24 lowercase alphanumeric, globally unique)" >&2
  exit 1
fi

az group create --name "$AWVM_TFSTATE_RG" --location "$AWVM_TFSTATE_LOCATION" --output none
az storage account create \
  --name "$AWVM_TFSTATE_ACCOUNT" \
  --resource-group "$AWVM_TFSTATE_RG" \
  --location "$AWVM_TFSTATE_LOCATION" \
  --sku Standard_LRS \
  --min-tls-version TLS1_2 \
  --allow-blob-public-access false \
  --encryption-services blob \
  --output none
az storage account blob-service-properties update \
  --account-name "$AWVM_TFSTATE_ACCOUNT" \
  --resource-group "$AWVM_TFSTATE_RG" \
  --enable-versioning true \
  --output none
az storage container create \
  --name "$AWVM_TFSTATE_CONTAINER" \
  --account-name "$AWVM_TFSTATE_ACCOUNT" \
  --auth-mode login \
  --output none

echo "Bootstrap complete. To use remote state, run:"
echo ""
echo "  export AWVM_TFSTATE_ACCOUNT=$AWVM_TFSTATE_ACCOUNT"
echo "  export AWVM_TFSTATE_RG=$AWVM_TFSTATE_RG"
echo "  export AWVM_TFSTATE_CONTAINER=$AWVM_TFSTATE_CONTAINER"
