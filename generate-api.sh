#!/bin/bash

SPEC_FILE="../shared/openapi.yaml"
OUT_DIR="./"
PACKAGE_NAME="regexsolver.generated"

echo "Running openapi-generator-cli..."
openapi-generator-cli generate \
  -i "$SPEC_FILE" \
  -g python \
  -o "$OUT_DIR" \
  --additional-properties=packageName="$PACKAGE_NAME",library=asyncio


echo "pytest-asyncio >= 1.3.0" >> test-requirements.txt
