# CKAN RPC Quick Start Guide

Get up and running with the CKAN gRPC RPC service in 5 minutes.

## Installation

### 1. Install CKAN with RPC Support

```bash
# Clone CKAN repository
git clone https://github.com/ckan/ckan.git
cd ckan

# Install with RPC dependencies
pip install -e .
```

The gRPC dependencies are already in `requirements.txt`:
- grpcio
- grpcio-tools
- protobuf

### 2. Compile Protocol Buffers

```bash
# From the CKAN root directory
bash scripts/compile_grpc_protos.sh
```

This generates the necessary Python gRPC files:
- `ckan/rpc/proto/ckan_rpc_pb2.py`
- `ckan/rpc/proto/ckan_rpc_pb2_grpc.py`

## Starting the Server

### Start the gRPC Server

```bash
# Simple start on localhost:50051
python -m ckan.rpc.server

# With custom host and port
python -m ckan.rpc.server 0.0.0.0 50051

# Or programmatically
python -c "
from ckan.rpc.server import create_and_start_server
server = create_and_start_server(host='0.0.0.0', port=50051)
server.wait()
"
```

The server is now running and ready to accept gRPC requests!

## Creating a Python Client

### Simple Example

Create a file `test_rpc_client.py`:

```python
#!/usr/bin/env python
"""Simple CKAN RPC client example."""

import asyncio
import grpc
from ckan.rpc.proto import ckan_rpc_pb2, ckan_rpc_pb2_grpc
from google.protobuf import json_format


async def main():
    # Connect to the RPC server
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = ckan_rpc_pb2_grpc.CkanActionServiceStub(channel)

        # Example 1: List all available actions
        print("=" * 50)
        print("1. Listing available actions...")
        list_request = ckan_rpc_pb2.ActionListRequest()
        actions_resp = await stub.ListActions(list_request)
        print(f"Total actions available: {actions_resp.total}")
        print(f"First 5 actions:")
        for action in list(actions_resp.actions)[:5]:
            print(f"  - {action.name}")

        # Example 2: Get info about a specific action
        print("\n" + "=" * 50)
        print("2. Getting info about package_list action...")
        get_action_req = ckan_rpc_pb2.GetActionRequest()
        get_action_req.action_name = 'package_list'
        action_info = await stub.GetAction(get_action_req)
        print(f"Action: {action_info.name}")
        print(f"Side-effect free: {action_info.side_effect_free}")
        print(f"Description: {action_info.description[:100]}...")

        # Example 3: Execute an action (package_list)
        print("\n" + "=" * 50)
        print("3. Executing package_list action...")
        request = ckan_rpc_pb2.ActionRequest()
        request.action = 'package_list'
        request.context.api_version = 3

        response = await stub.ExecuteAction(request)
        print(f"Success: {response.success}")
        if response.success:
            result = json_format.MessageToDict(response.result)
            packages = result.get('result', [])
            print(f"Found {len(packages)} packages")
            if packages:
                print(f"First package: {packages[0]}")
        else:
            print(f"Error: {response.error.message}")

        # Example 4: Batch operations
        print("\n" + "=" * 50)
        print("4. Executing batch operations...")
        batch_req = ckan_rpc_pb2.BatchActionRequest()
        batch_req.stop_on_error = False

        # Add 3 package_list requests
        for i in range(3):
            req = batch_req.requests.add()
            req.action = 'package_list'
            req.context.api_version = 3

        batch_resp = await stub.ExecuteBatch(batch_req)
        print(f"Batch results:")
        print(f"  Total requests: {len(batch_resp.responses)}")
        print(f"  Successful: {len(batch_resp.responses) - batch_resp.failed_count}")
        print(f"  Failed: {batch_resp.failed_count}")
        print(f"  All succeeded: {batch_resp.all_succeeded}")


if __name__ == '__main__':
    asyncio.run(main())
```

Run it:

```bash
python test_rpc_client.py
```

### Output

```
==================================================
1. Listing available actions...
Total actions available: 150
First 5 actions:
  - activity_create
  - activity_detail
  - activity_list
  - activity_list_html
  - api_token_revoke

==================================================
2. Getting info about package_list action...
Action: package_list
Side-effect free: True
Description: Return a list of the names of the site's datasets (packages)...

==================================================
3. Executing package_list action...
Success: True
Found 5 packages
First package: my-first-dataset

==================================================
4. Executing batch operations...
Batch results:
  Total requests: 3
  Successful: 3
  Failed: 0
  All succeeded: True
```

## Creating a Resource (Advanced Example)

```python
#!/usr/bin/env python
"""Create a dataset and resource via RPC."""

import asyncio
import grpc
from ckan.rpc.proto import ckan_rpc_pb2, ckan_rpc_pb2_grpc
from google.protobuf import json_format


async def main():
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = ckan_rpc_pb2_grpc.CkanActionServiceStub(channel)

        # Create a dataset
        print("Creating dataset...")
        create_pkg_req = ckan_rpc_pb2.ActionRequest()
        create_pkg_req.action = 'package_create'
        create_pkg_req.context.user = 'admin'  # Requires admin privileges
        create_pkg_req.context.api_version = 3

        pkg_data = {
            'name': 'my-test-dataset',
            'title': 'My Test Dataset',
            'notes': 'A dataset created via RPC',
            'author': 'RPC Client',
            'tags': [
                {'name': 'test'},
                {'name': 'demo'}
            ]
        }

        create_pkg_req.data.CopyFrom(
            json_format.ParseDict(pkg_data, create_pkg_req.data.__class__())
        )

        pkg_resp = await stub.ExecuteAction(create_pkg_req)
        if pkg_resp.success:
            result = json_format.MessageToDict(pkg_resp.result)
            pkg_id = result['id']
            print(f"✓ Created package: {pkg_id}")

            # Create a resource in the dataset
            print("Creating resource...")
            create_res_req = ckan_rpc_pb2.ActionRequest()
            create_res_req.action = 'resource_create'
            create_res_req.context.user = 'admin'
            create_res_req.context.api_version = 3

            res_data = {
                'package_id': pkg_id,
                'url': 'https://example.com/data.csv',
                'name': 'Sample Data',
                'format': 'CSV',
                'description': 'Sample CSV file'
            }

            create_res_req.data.CopyFrom(
                json_format.ParseDict(res_data, create_res_req.data.__class__())
            )

            res_resp = await stub.ExecuteAction(create_res_req)
            if res_resp.success:
                result = json_format.MessageToDict(res_resp.result)
                res_id = result['id']
                print(f"✓ Created resource: {res_id}")
            else:
                print(f"✗ Failed to create resource: {res_resp.error.message}")
        else:
            print(f"✗ Failed to create package: {pkg_resp.error.message}")
            if pkg_resp.error.field_errors:
                for field, errors in pkg_resp.error.field_errors.items():
                    print(f"  {field}: {errors}")


if __name__ == '__main__':
    asyncio.run(main())
```

## Running Tests

```bash
# Run all RPC tests
pytest ckan/tests/rpc/ -v

# Run specific test file
pytest ckan/tests/rpc/test_action_service.py -v

# Run with coverage
pytest --cov=ckan.rpc ckan/tests/rpc/
```

## Next Steps

1. **Read the Full Documentation**: Check out `README.md` for comprehensive documentation
2. **Configure for Production**: See `CONFIG.md` for production setup
3. **Explore Action Library**: Visit `/api/action/` in your CKAN instance for a full list of actions
4. **Try Different Clients**: See examples for Node.js, Go, and other languages in README.md

## Common Tasks

### List All Available Actions

```python
request = ckan_rpc_pb2.ActionListRequest()
response = await stub.ListActions(request)
for action in response.actions:
    print(action.name)
```

### Search Packages

```python
request = ckan_rpc_pb2.ActionRequest()
request.action = 'package_search'
request.context.api_version = 3
request.data.CopyFrom(json_format.ParseDict(
    {'q': 'climate'},
    request.data.__class__()
))
response = await stub.ExecuteAction(request)
```

### Stream Packages

```python
stream_req = ckan_rpc_pb2.PackageStreamRequest()
stream_stub = ckan_rpc_pb2_grpc.CkanStreamServiceStub(channel)

async for package in stream_stub.StreamPackages(stream_req):
    print(f"Package: {package.name}")
```

### Batch Operations

```python
batch = ckan_rpc_pb2.BatchActionRequest()

# Add multiple requests
for i in range(5):
    req = batch.requests.add()
    req.action = 'package_list'
    req.context.api_version = 3

response = await stub.ExecuteBatch(batch)
print(f"Batch: {len(response.responses)} responses, Failed: {response.failed_count}")
```

## Troubleshooting

### Connection Refused

```
Error: [Errno 111] Connection refused
```

Solution: Make sure the RPC server is running:
```bash
python -m ckan.rpc.server
```

### Proto Not Found

```
ModuleNotFoundError: No module named 'ckan_rpc_pb2'
```

Solution: Compile proto files:
```bash
bash scripts/compile_grpc_protos.sh
```

### Permission Denied Errors

Some actions require authentication. Always set `request.context.user`:

```python
request.context.user = 'admin'  # or valid username
```

## Performance Tips

1. **Reuse channels**: Don't create a new channel for each request
2. **Use batch operations**: Send multiple actions in one batch
3. **Stream large results**: Use streaming for large result sets
4. **Enable compression**: Add `compression=grpc.Compression.Gzip`

```python
async with grpc.aio.insecure_channel(
    'localhost:50051',
    compression=grpc.Compression.Gzip
) as channel:
    stub = ckan_rpc_pb2_grpc.CkanActionServiceStub(channel)
```

## Need Help?

- Check the full [README.md](README.md) for comprehensive documentation
- Look at [CONFIG.md](CONFIG.md) for configuration options
- Review test files in `ckan/tests/rpc/` for examples
- Visit [CKAN Documentation](https://docs.ckan.org/)

Happy RPC-ing! 🚀
