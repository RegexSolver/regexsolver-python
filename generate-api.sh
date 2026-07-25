#!/bin/bash

SPEC_FILE="../m-lab/shared/openapi.yaml"
OUT_DIR="./"
PACKAGE_NAME="regexsolver._generated"

echo "Running openapi-generator-cli..."
openapi-generator-cli generate \
  -i "$SPEC_FILE" \
  -g python \
  -o "$OUT_DIR" \
  --additional-properties=packageName="$PACKAGE_NAME",library=asyncio

echo "API Generation Complete."
