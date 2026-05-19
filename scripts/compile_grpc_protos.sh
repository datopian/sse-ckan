#!/bin/bash
# Compile CKAN gRPC Protocol Buffer files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PROTO_DIR="$PROJECT_ROOT/ckan/rpc/proto"

echo "Compiling gRPC Protocol Buffer files..."
echo "Project root: $PROJECT_ROOT"
echo "Proto directory: $PROTO_DIR"

# Compile proto files
python3 -m grpc_tools.protoc \
    -I"$PROTO_DIR" \
    --python_out="$PROTO_DIR" \
    --grpc_python_out="$PROTO_DIR" \
    "$PROTO_DIR/ckan_rpc.proto"

echo "✓ Proto compilation successful!"
echo "Generated files:"
ls -la "$PROTO_DIR"/*.py

# Update __init__.py to import generated files
echo "Updating imports in proto/__init__.py..."
cat > "$PROTO_DIR/__init__.py" << 'EOF'
"""
Protocol Buffer definitions for CKAN RPC service.

This module contains auto-generated Protocol Buffer definitions.
Do not edit manually - regenerate using compile_grpc_protos.sh
"""

from . import ckan_rpc_pb2
from . import ckan_rpc_pb2_grpc

__all__ = [
    'ckan_rpc_pb2',
    'ckan_rpc_pb2_grpc',
]
EOF

echo "✓ All done! Proto files compiled successfully."
