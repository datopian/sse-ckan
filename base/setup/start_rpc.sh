#!/bin/bash
# Start CKAN gRPC RPC Service

set -e

# Get environment variables
APP_DIR="${APP_DIR:-/srv/app}"
SRC_DIR="${SRC_DIR:-/srv/app/src}"
RPC_HOST="${CKAN_RPC_HOST:-0.0.0.0}"
RPC_PORT="${CKAN_RPC_PORT:-50051}"

echo "[RPC] Starting CKAN gRPC RPC Service"
echo "[RPC] Host: $RPC_HOST"
echo "[RPC] Port: $RPC_PORT"

# Ensure proto files are compiled
echo "[RPC] Checking Protocol Buffer compilation..."
if [ ! -f "${SRC_DIR}/ckan/ckan/rpc/proto/ckan_rpc_pb2.py" ]; then
    echo "[RPC] Compiling proto files..."
    cd "${SRC_DIR}/ckan"
    python3 -m grpc_tools.protoc \
        -I./ckan/rpc/proto \
        --python_out=./ckan/rpc/proto \
        --grpc_python_out=./ckan/rpc/proto \
        ./ckan/rpc/proto/ckan_rpc.proto
    echo "[RPC] Proto files compiled successfully"
else
    echo "[RPC] Proto files already compiled"
fi

# Start the RPC server
echo "[RPC] Starting server..."
cd "${SRC_DIR}/ckan"

# Run server with CKAN configuration loaded
export CKAN_INI="${CKAN_INI:-/srv/app/ckan.ini}"

python3 -m ckan.rpc "$RPC_HOST" "$RPC_PORT"
