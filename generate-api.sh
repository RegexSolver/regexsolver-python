#!/bin/bash

# The API serves its own specification, which is the source the SDK is generated
# from. Pass a path or another URL as the first argument to generate against it.
SPEC="${1:-https://api.regexsolver.com/openapi.json}"
OUT_DIR="./"
PACKAGE_NAME="regexsolver._generated"

echo "Running openapi-generator-cli..."
openapi-generator-cli generate \
  -i "$SPEC" \
  -g python \
  -o "$OUT_DIR" \
  --additional-properties=packageName="$PACKAGE_NAME",library=asyncio

echo "API Generation Complete."
