# CKAN gRPC RPC Service

This module provides high-performance gRPC-based RPC access to CKAN actions. It's designed for efficient API-to-API communication with features like batch operations, streaming, and action introspection.

## Overview

The CKAN RPC service exposes all CKAN actions through gRPC, providing several advantages over traditional HTTP REST APIs:

- **Performance**: gRPC uses HTTP/2 and Protocol Buffers, offering lower latency and higher throughput
- **Streaming**: Native support for bidirectional streaming for real-time data
- **Batch Operations**: Execute multiple actions in a single round trip
- **Type Safety**: Protocol Buffers provide strict typing and validation
- **Multiplexing**: Handle multiple concurrent operations on a single connection

## Architecture

```
┌─────────────────────────────────────────┐
│   CKAN Application                      │
│   ├── REST API (HTTP)                   │
│   └── gRPC RPC Service (HTTP/2)         │
│       ├── CkanActionService             │
│       │   ├── ExecuteAction              │
│       │   ├── ExecuteBatch               │
│       │   ├── ListActions                │
│       │   ├── GetAction                  │
│       │   └── ExecuteStream              │
│       └── CkanStreamService              │
│           ├── StreamPackages             │
│           ├── StreamResources            │
│           └── StreamActivity             │
└─────────────────────────────────────────┘
```

## Features

### 1. Single Action Execution

Execute individual CKAN actions with full context support:

```python
# Client example (Python)
import grpc
from ckan.rpc.proto import ckan_rpc_pb2, ckan_rpc_pb2_grpc
from google.protobuf import json_format

channel = grpc.aio.secure_channel('localhost:50051', creds)
stub = ckan_rpc_pb2_grpc.CkanActionServiceStub(channel)

request = ckan_rpc_pb2.ActionRequest()
request.action = 'package_create'
request.context.user = 'admin'
request.context.api_version = 3
request.data.CopyFrom(
    json_format.ParseDict(
        {'name': 'my-dataset', 'title': 'My Dataset'},
        request.data.__class__()
    )
)

response = await stub.ExecuteAction(request)
if response.success:
    print(f"Created package: {response.result['id']}")
else:
    print(f"Error: {response.error.message}")
```

### 2. Batch Operations

Execute multiple actions efficiently:

```python
batch_request = ckan_rpc_pb2.BatchActionRequest()
batch_request.stop_on_error = False

# Add multiple requests
for i in range(10):
    action_req = batch_request.requests.add()
    action_req.action = 'package_search'
    action_req.context.user = 'admin'
    action_req.data.CopyFrom(
        json_format.ParseDict({'q': f'tag:{i}'}, action_req.data.__class__())
    )

response = await stub.ExecuteBatch(batch_request)
print(f"Success: {response.all_succeeded}")
print(f"Failed: {response.failed_count}")
```

### 3. Streaming

Stream multiple action requests and responses:

```python
async def stream_actions(stub):
    async def request_generator():
        for i in range(100):
            req = ckan_rpc_pb2.ActionRequest()
            req.action = 'package_list'
            req.context.user = 'admin'
            yield req

    async for response in stub.ExecuteStream(request_generator()):
        if response.success:
            process(response.result)
        else:
            log_error(response.error)
```

### 4. Action Discovery

Discover available actions and their metadata:

```python
# List all actions
list_request = ckan_rpc_pb2.ActionListRequest()
response = await stub.ListActions(list_request)
print(f"Total actions: {response.total}")

# Filter by category
list_request.category = 'package'
response = await stub.ListActions(list_request)

# Search for actions
list_request.search = 'create'
response = await stub.ListActions(list_request)

# Get detailed info about specific action
get_request = ckan_rpc_pb2.GetActionRequest()
get_request.action_name = 'package_create'
action_info = await stub.GetAction(get_request)
print(f"Name: {action_info.name}")
print(f"Side-effect free: {action_info.side_effect_free}")
```

### 5. Streaming Data

Stream real-time data changes:

```python
# Stream package changes
stream_request = ckan_rpc_pb2.PackageStreamRequest()
stream_request.organization_id = 'my-org'

stream_stub = ckan_rpc_pb2_grpc.CkanStreamServiceStub(channel)
async for package in stream_stub.StreamPackages(stream_request):
    print(f"Package: {package.name}")
    for resource in package.resources:
        print(f"  - Resource: {resource.name} ({resource.format})")

# Stream activity
activity_request = ckan_rpc_pb2.ActivityStreamRequest()
async for activity in stream_stub.StreamActivity(activity_request):
    print(f"Activity: {activity.activity_type}")
```

## Setup and Installation

### 1. Install Dependencies

The gRPC dependencies are already included in `requirements.txt`:

```bash
pip install -e .
```

Or manually:

```bash
pip install grpcio==1.68.0 grpcio-tools==1.68.0 protobuf==5.27.2
```

### 2. Compile Protocol Buffers

Compile the proto files:

```bash
bash scripts/compile_grpc_protos.sh
```

This generates:
- `ckan/rpc/proto/ckan_rpc_pb2.py` - Protocol Buffer message definitions
- `ckan/rpc/proto/ckan_rpc_pb2_grpc.py` - gRPC service definitions

### 3. Start the Server

Start the gRPC server:

```bash
python -m ckan.rpc.server
```

Or with custom host/port:

```bash
python -m ckan.rpc.server 0.0.0.0 50051
```

## Protocol Buffer Definitions

### Main Services

#### CkanActionService

Handles action execution with RPC-style interface:

- `ExecuteAction`: Execute a single action
- `ExecuteBatch`: Execute multiple actions
- `ListActions`: Discover available actions
- `GetAction`: Get action metadata
- `ExecuteStream`: Stream-based action execution

#### CkanStreamService

Handles streaming data:

- `StreamPackages`: Stream package/dataset changes
- `StreamResources`: Stream resource changes
- `StreamActivity`: Stream activity log

### Message Types

#### ActionRequest

```protobuf
message ActionRequest {
  string action = 1;                    // Action name
  ActionContext context = 2;            // Request context
  google.protobuf.Struct data = 3;      // Action parameters
}
```

#### ActionResponse

```protobuf
message ActionResponse {
  bool success = 1;                     // Operation success
  google.protobuf.Struct result = 2;    // Result data
  ActionError error = 3;                // Error details
  string help = 4;                      // Help URL
  repeated ChangedEntity changed_entities = 5;
}
```

#### ActionContext

```protobuf
message ActionContext {
  string user = 1;                      // Username
  int32 api_version = 2;                // API version
  map<string, string> extras = 3;       // Additional context
}
```

#### ActionError

```protobuf
message ActionError {
  string type = 1;                      // Error type
  string message = 2;                   // Error message
  map<string, string[]> field_errors = 3; // Field-specific errors
}
```

## Client Examples

### Python Client

```python
#!/usr/bin/env python
"""CKAN gRPC client example."""

import asyncio
import grpc
from ckan.rpc.proto import ckan_rpc_pb2, ckan_rpc_pb2_grpc
from google.protobuf import json_format


async def main():
    # Connect to server
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = ckan_rpc_pb2_grpc.CkanActionServiceStub(channel)

        # Example 1: Create a package
        request = ckan_rpc_pb2.ActionRequest()
        request.action = 'package_create'
        request.context.user = 'admin'
        request.data.CopyFrom(
            json_format.ParseDict(
                {
                    'name': 'test-dataset',
                    'title': 'Test Dataset',
                    'author': 'Test User'
                },
                request.data.__class__()
            )
        )

        response = await stub.ExecuteAction(request)
        print(f"Create response: {response.success}")

        # Example 2: List actions
        list_request = ckan_rpc_pb2.ActionListRequest()
        list_request.category = 'package'
        actions = await stub.ListActions(list_request)
        print(f"Found {actions.total} package-related actions")

        # Example 3: Batch operations
        batch_req = ckan_rpc_pb2.BatchActionRequest()
        for i in range(3):
            req = batch_req.requests.add()
            req.action = 'package_list'
            req.context.user = 'admin'

        batch_resp = await stub.ExecuteBatch(batch_req)
        print(f"Batch: {len(batch_resp.responses)} responses, "
              f"Failed: {batch_resp.failed_count}")


if __name__ == '__main__':
    asyncio.run(main())
```

### Node.js/JavaScript Client

```javascript
const grpc = require('@grpc/grpc-js');
const loader = require('@grpc/proto-loader');
const path = require('path');

const PROTO_PATH = path.join(__dirname, 'ckan_rpc.proto');

const packageDefinition = loader.loadSync(PROTO_PATH, {
  keepCase: true,
  enums: String,
  defaults: true,
  oneofs: true
});

const ckanRpc = grpc.loadPackageDefinition(packageDefinition).ckan.rpc;
const client = new ckanRpc.CkanActionService(
  'localhost:50051',
  grpc.credentials.createInsecure()
);

// Execute action
client.executeAction({
  action: 'package_list',
  context: {
    user: 'admin',
    api_version: 3
  },
  data: {}
}, (err, response) => {
  if (err) throw err;
  console.log('Response:', response);
});
```

### Go Client

```go
package main

import (
    "context"
    "log"
    pb "github.com/ckan/ckan/pkg/rpc"
    "google.golang.org/grpc"
)

func main() {
    conn, err := grpc.Dial("localhost:50051", grpc.WithInsecure())
    if err != nil {
        log.Fatal(err)
    }
    defer conn.Close()

    client := pb.NewCkanActionServiceClient(conn)

    resp, err := client.ExecuteAction(context.Background(), &pb.ActionRequest{
        Action: "package_list",
        Context: &pb.ActionContext{
            User:       "admin",
            ApiVersion: 3,
        },
        Data: &structpb.Struct{},
    })

    if err != nil {
        log.Fatal(err)
    }

    log.Printf("Success: %v\n", resp.Success)
}
```

## Error Handling

The gRPC service uses standard gRPC status codes and custom error messages:

| gRPC Code | CKAN Error | HTTP Equiv |
|-----------|-----------|-----------|
| `OK` | Success | 200 |
| `INVALID_ARGUMENT` | ValidationError | 400 |
| `NOT_FOUND` | NotFound | 404 |
| `PERMISSION_DENIED` | NotAuthorized | 403 |
| `INTERNAL` | Other exceptions | 500 |

### Example Error Handling

```python
try:
    response = await stub.ExecuteAction(request)
    if not response.success:
        error = response.error
        print(f"Error ({error.type}): {error.message}")
        if error.field_errors:
            for field, errors in error.field_errors.items():
                print(f"  {field}: {errors}")
except grpc.RpcError as e:
    print(f"RPC Error: {e.code()}: {e.details()}")
```

## Performance Considerations

1. **Message Size**: Default max message size is 100MB. Adjust in server config if needed.
2. **Connection Pooling**: Reuse channel connections for multiple requests.
3. **Streaming**: Use streaming for large result sets to reduce memory usage.
4. **Batch Operations**: Combine related operations into batch requests.
5. **Compression**: gRPC automatically handles compression. Enable with:

```python
channel = grpc.aio.insecure_channel(
    'localhost:50051',
    compression=grpc.Compression.Gzip
)
```

## Testing

Run the test suite:

```bash
# All RPC tests
pytest ckan/tests/rpc/

# Specific test file
pytest ckan/tests/rpc/test_action_service.py

# With coverage
pytest --cov=ckan.rpc ckan/tests/rpc/

# Verbose output
pytest -v ckan/tests/rpc/
```

## Troubleshooting

### Proto Compilation Issues

```bash
# Ensure grpcio-tools is installed
pip install grpcio-tools==1.68.0

# Manually compile
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. ckan_rpc.proto
```

### Connection Issues

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Test connectivity
import grpc
try:
    channel = grpc.aio.insecure_channel('localhost:50051')
    await channel.close()
    print("Connection successful")
except Exception as e:
    print(f"Connection failed: {e}")
```

### Performance Issues

1. Increase `max_workers` on server
2. Increase message size limits if needed
3. Use streaming for large responses
4. Enable compression for slower connections

## Future Enhancements

- [ ] Mutual TLS support
- [ ] Authentication/authorization per action
- [ ] Request/response middleware hooks
- [ ] Action result caching
- [ ] Rate limiting
- [ ] OpenTelemetry integration
- [ ] Prometheus metrics export
- [ ] Circuit breaker pattern for cascading failures

## References

- [gRPC Documentation](https://grpc.io/docs/)
- [Protocol Buffers Guide](https://developers.google.com/protocol-buffers)
- [CKAN Action API Docs](https://docs.ckan.org/en/latest/api/)
