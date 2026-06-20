#!/bin/bash
# Generate Python code from protobuf definitions

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "Generating protobuf code from .proto files..."

python -m grpc_tools.protoc \
    -I. \
    --python_out=. \
    --grpc_python_out=. \
    protos/observations.proto

echo "Proto code generated successfully!"
echo "Created: protos/observations_pb2.py and protos/observations_pb2_grpc.py"
