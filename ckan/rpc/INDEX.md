# CKAN gRPC RPC Service - Documentation Index

Welcome to the CKAN gRPC RPC service! This index helps you navigate all documentation and code.

## Quick Navigation

### Getting Started (5 minutes)
👉 **Start here**: [QUICKSTART.md](QUICKSTART.md)
- Installation instructions
- Starting the server
- First Python client example
- Common tasks reference

### Understanding the System
1. **[README.md](README.md)** - Full technical documentation
   - Architecture overview
   - Feature descriptions
   - Protocol Buffer reference
   - Client examples (Python, Node.js, Go)
   - Error handling patterns
   - Performance considerations

2. **[GRPC_RPC_IMPLEMENTATION.md](../GRPC_RPC_IMPLEMENTATION.md)** - Implementation summary
   - What was implemented
   - File structure
   - Features overview
   - Test coverage
   - Performance benchmarks

### Setting Up for Production
1. **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment guide
   - Docker setup
   - Kubernetes deployment
   - Systemd services
   - Load balancing
   - Monitoring and logging
   - Scaling strategies

2. **[CONFIG.md](CONFIG.md)** - Configuration reference
   - All configuration options
   - Environment variables
   - SSL/TLS setup
   - Performance tuning
   - Docker/Kubernetes examples

## File Structure

```
ckan/rpc/                          # Main RPC module
├── README.md                      # Technical documentation
├── QUICKSTART.md                  # 5-minute quick start
├── CONFIG.md                      # Configuration guide
├── DEPLOYMENT.md                  # Deployment strategies
├── INDEX.md                       # This file
├── __init__.py                    # Module initialization
├── server.py                      # gRPC server
├── proto/                         # Protocol Buffers
│   ├── ckan_rpc.proto            # Proto definitions (~450 lines)
│   ├── ckan_rpc_pb2.py           # Generated message classes
│   ├── ckan_rpc_pb2_grpc.py      # Generated service stubs
│   └── __init__.py               # Proto module init
└── service/                       # gRPC service implementations
    ├── action_service.py         # Action execution (~550 lines)
    ├── stream_service.py         # Streaming (~300 lines)
    └── __init__.py               # Service module init

ckan/tests/rpc/                   # Test suite
├── test_action_service.py        # Action service tests (~400 lines)
├── test_stream_service.py        # Stream service tests (~300 lines)
├── test_server.py                # Server tests (~250 lines)
└── __init__.py                   # Tests module init

scripts/
└── compile_grpc_protos.sh        # Proto compilation script
```

## Key Features at a Glance

| Feature | Location | Description |
|---------|----------|-------------|
| **Single Action Execution** | `action_service.py` | Execute any CKAN action |
| **Batch Operations** | `action_service.py` | Multiple actions in one request |
| **Action Discovery** | `action_service.py` | List and search available actions |
| **Streaming** | `stream_service.py` | Real-time data streaming |
| **Error Handling** | `action_service.py` | gRPC-compliant error responses |
| **Type Safety** | `proto/ckan_rpc.proto` | Protocol Buffer validation |

## Common Tasks

### I want to...

#### Start the RPC server
→ See **[QUICKSTART.md - Starting the Server](QUICKSTART.md#starting-the-server)**

#### Create a Python client
→ See **[QUICKSTART.md - Creating a Python Client](QUICKSTART.md#creating-a-python-client)**

#### Execute a CKAN action via RPC
→ See **[README.md - Single Action Execution](README.md#1-single-action-execution)**

#### Do batch operations
→ See **[README.md - Batch Operations](README.md#2-batch-operations)**

#### Stream data
→ See **[README.md - Streaming Data](README.md#5-streaming-data)**

#### Deploy to Docker
→ See **[DEPLOYMENT.md - Docker Deployment](DEPLOYMENT.md#docker-deployment)**

#### Deploy to Kubernetes
→ See **[DEPLOYMENT.md - Kubernetes Deployment](DEPLOYMENT.md#kubernetes-deployment)**

#### Configure for production
→ See **[CONFIG.md - Production Configuration](CONFIG.md#production-configuration)**

#### Set up TLS/SSL
→ See **[CONFIG.md - SSL/TLS Configuration](CONFIG.md#ssltls-configuration)**

#### Use load balancing
→ See **[CONFIG.md - Load Balancing](CONFIG.md#load-balancing)**

#### Write a client in Node.js
→ See **[README.md - Node.js Client](README.md#nodesjsjavascript-client)**

#### Write a client in Go
→ See **[README.md - Go Client](README.md#go-client)**

#### Run tests
→ See **[QUICKSTART.md - Running Tests](QUICKSTART.md#running-tests)**

#### Understand the architecture
→ See **[README.md - Architecture](README.md#architecture)**

#### Find all configuration options
→ See **[CONFIG.md - Configuration Options](CONFIG.md#configuration-options)**

#### Debug connection issues
→ See **[QUICKSTART.md - Troubleshooting](QUICKSTART.md#troubleshooting)**

#### Monitor RPC service
→ See **[DEPLOYMENT.md - Monitoring](DEPLOYMENT.md#monitoring-and-logging)**

#### Handle errors properly
→ See **[README.md - Error Handling](README.md#error-handling)**

## Code Examples

### Quick Example - List Actions

```python
import asyncio
import grpc
from ckan.rpc.proto import ckan_rpc_pb2, ckan_rpc_pb2_grpc

async def list_actions():
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = ckan_rpc_pb2_grpc.CkanActionServiceStub(channel)
        response = await stub.ListActions(ckan_rpc_pb2.ActionListRequest())
        print(f"Found {response.total} actions")

asyncio.run(list_actions())
```

### Quick Example - Execute Action

```python
async def execute_action():
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = ckan_rpc_pb2_grpc.CkanActionServiceStub(channel)

        request = ckan_rpc_pb2.ActionRequest()
        request.action = 'package_list'
        request.context.api_version = 3

        response = await stub.ExecuteAction(request)
        if response.success:
            print("✓ Action succeeded")
        else:
            print(f"✗ Error: {response.error.message}")
```

## Services Provided

### CkanActionService
- **ExecuteAction()** - Execute a single action
- **ExecuteBatch()** - Execute multiple actions
- **ListActions()** - Discover available actions
- **GetAction()** - Get action metadata
- **ExecuteStream()** - Stream-based execution

### CkanStreamService
- **StreamPackages()** - Stream dataset changes
- **StreamResources()** - Stream resource changes
- **StreamActivity()** - Stream activity log

## Protocol Buffers

The service uses Protocol Buffers for type-safe communication:
- **File**: `ckan/rpc/proto/ckan_rpc.proto`
- **Generated**: `ckan_rpc_pb2.py`, `ckan_rpc_pb2_grpc.py`
- **Messages**: 15+ message types for all operations

See [README.md - Protocol Buffer Definitions](README.md#protocol-buffer-definitions) for details.

## Testing

The implementation includes comprehensive tests:

```bash
# Run all RPC tests
pytest ckan/tests/rpc/

# Run specific test file
pytest ckan/tests/rpc/test_action_service.py -v

# Run with coverage
pytest --cov=ckan.rpc ckan/tests/rpc/
```

**Test files**:
- `test_action_service.py` - 400 lines, 20+ test methods
- `test_stream_service.py` - 300 lines, 15+ test methods
- `test_server.py` - 250 lines, 10+ test methods

## Performance

Estimated improvements over REST HTTP:

| Operation | REST | gRPC | Improvement |
|-----------|------|------|-------------|
| Single action | 50-100ms | 10-20ms | **5-10x faster** |
| 100 actions | 5-10s | 500-1000ms | **8-10x faster** |
| Batch (10 actions) | 500-1000ms | 50-100ms | **8-10x faster** |

See [README.md - Performance Considerations](README.md#performance-considerations) for optimization tips.

## System Requirements

- **Python**: 3.7+
- **CKAN**: 2.9.0 or later
- **Dependencies**: Installed automatically via `pip install -e .`
  - grpcio 1.68.0
  - grpcio-tools 1.68.0
  - protobuf 5.27.2

## Deployment Options

- ✓ Local/development
- ✓ Docker containers
- ✓ Docker Compose
- ✓ Kubernetes
- ✓ Systemd services
- ✓ Supervisor
- ✓ HAProxy load balancing
- ✓ Nginx load balancing

See [DEPLOYMENT.md](DEPLOYMENT.md) for details.

## Installation Checklist

- [ ] Clone CKAN repository
- [ ] Run `pip install -e .`
- [ ] Run `bash scripts/compile_grpc_protos.sh`
- [ ] Start server: `python -m ckan.rpc.server`
- [ ] Create client and test
- [ ] Review [CONFIG.md](CONFIG.md) for production setup
- [ ] Review [DEPLOYMENT.md](DEPLOYMENT.md) for deployment strategy
- [ ] Run tests: `pytest ckan/tests/rpc/`

## Implementation Statistics

| Metric | Count |
|--------|-------|
| Lines of production code | 1,500+ |
| Lines of test code | 1,000+ |
| Lines of documentation | 2,500+ |
| Test methods | 50+ |
| Protobuf message types | 15+ |
| RPC service methods | 8 |
| Configuration options | 12+ |

## Support and Resources

- **CKAN Documentation**: https://docs.ckan.org/
- **gRPC Documentation**: https://grpc.io/docs/
- **Protocol Buffers**: https://developers.google.com/protocol-buffers
- **This Repository**: GitHub issues and discussions

## Next Steps

1. **For beginners**: Start with [QUICKSTART.md](QUICKSTART.md)
2. **For developers**: Read [README.md](README.md) for technical details
3. **For operators**: Check [DEPLOYMENT.md](DEPLOYMENT.md) and [CONFIG.md](CONFIG.md)
4. **For contributors**: Review [GRPC_RPC_IMPLEMENTATION.md](../GRPC_RPC_IMPLEMENTATION.md)

## Questions?

Refer to the appropriate documentation file above for your use case. Each file is designed to be comprehensive for its topic.

---

**Last Updated**: 2024-12-03
**Status**: ✅ Production Ready
