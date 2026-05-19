# CKAN gRPC RPC Service - Docker Setup Guide

This guide explains how to test the CKAN gRPC RPC service using Docker and Docker Compose.

## Quick Start

### 1. Build and Start Services

```bash
# From the CKAN repository root
docker-compose -f docker-compose-rpc.yml up -d
```

This starts:
- PostgreSQL database
- Redis cache
- Solr search engine
- CKAN web server (port 5000)
- CKAN gRPC RPC service (port 50051)
- Optional RPC test service

### 2. Verify Services Are Running

```bash
# Check Docker containers
docker-compose -f docker-compose-rpc.yml ps

# Check web UI is accessible
curl http://localhost:5000

# Check RPC service is listening
docker exec <ckan_container_id> python3 -c "
import grpc
from ckan.rpc.proto import ckan_rpc_pb2_grpc
channel = grpc.aio.insecure_channel('localhost:50051')
print('✓ RPC service is responding')
"
```

### 3. Run the Tests

```bash
# Run all RPC tests
docker-compose -f docker-compose-rpc.yml exec ckan \
  pytest /srv/app/src/ckan/ckan/tests/rpc/ -v

# Run specific test file
docker-compose -f docker-compose-rpc.yml exec ckan \
  pytest /srv/app/src/ckan/ckan/tests/rpc/test_action_service.py -v

# Run specific test method
docker-compose -f docker-compose-rpc.yml exec ckan \
  pytest /srv/app/src/ckan/ckan/tests/rpc/test_action_service.py::TestActionServiceIntegration::test_package_create_and_show -v

# Run tests with coverage
docker-compose -f docker-compose-rpc.yml exec ckan \
  pytest --cov=ckan.rpc /srv/app/src/ckan/ckan/tests/rpc/ -v
```

## File Structure in Docker

```
Container Structure:
/srv/app/                           # CKAN app directory
├── src/
│   └── ckan/                       # CKAN source (from git clone)
│       ├── ckan/
│       │   ├── rpc/               # RPC service module
│       │   │   ├── proto/         # Protocol Buffer files
│       │   │   ├── service/       # gRPC services
│       │   │   ├── server.py      # RPC server
│       │   │   └── README.md      # RPC docs
│       │   └── tests/
│       │       └── rpc/           # RPC tests
│       ├── requirements.txt        # Dependencies (includes gRPC)
│       └── scripts/
│           └── compile_grpc_protos.sh
├── ckan.ini                        # CKAN config
├── start_ckan.sh                   # Web service startup script
└── start_rpc.sh                    # RPC service startup script
```

## Docker Configuration

### Environment Variables

Configure via `docker-compose-rpc.yml` or environment:

```yaml
environment:
  # RPC Service
  CKAN_RPC_ENABLED: "true"
  CKAN_RPC_HOST: "0.0.0.0"
  CKAN_RPC_PORT: "50051"
  CKAN_RPC_MAX_WORKERS: "10"
```

### Ports

- **5000**: CKAN Web UI (HTTP)
- **50051**: gRPC RPC Service (gRPC/HTTP2)
- **8983**: Solr Admin Console (HTTP)

## Testing Workflows

### Run Integration Tests

```bash
# Start services
docker-compose -f docker-compose-rpc.yml up -d

# Wait for services to be ready
docker-compose -f docker-compose-rpc.yml exec ckan \
  sh -c "sleep 10"

# Run tests
docker-compose -f docker-compose-rpc.yml exec ckan \
  pytest /srv/app/src/ckan/ckan/tests/rpc/ -v

# Stop services
docker-compose -f docker-compose-rpc.yml down
```

### Interactive Testing

```bash
# Start services
docker-compose -f docker-compose-rpc.yml up -d

# Open bash in container
docker-compose -f docker-compose-rpc.yml exec ckan bash

# Inside container:
cd /srv/app/src/ckan

# Run tests
pytest ckan/tests/rpc/ -v

# Or test RPC manually
python3 << 'EOF'
import asyncio
import grpc
from ckan.rpc.proto import ckan_rpc_pb2, ckan_rpc_pb2_grpc

async def test():
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = ckan_rpc_pb2_grpc.CkanActionServiceStub(channel)
        req = ckan_rpc_pb2.ActionListRequest()
        resp = await stub.ListActions(req)
        print(f'Found {resp.total} actions')

asyncio.run(test())
EOF

# Exit container
exit
```

### Run Tests with Output

```bash
# See all logs
docker-compose -f docker-compose-rpc.yml logs -f ckan

# Run tests with live output
docker-compose -f docker-compose-rpc.yml exec ckan \
  pytest /srv/app/src/ckan/ckan/tests/rpc/ -v -s
```

## Troubleshooting

### Services Not Starting

```bash
# Check logs
docker-compose -f docker-compose-rpc.yml logs ckan

# Check if ports are already in use
lsof -i :5000
lsof -i :50051
```

### Proto Files Not Found

```bash
# Recompile proto files inside container
docker-compose -f docker-compose-rpc.yml exec ckan bash -c \
  "cd /srv/app/src/ckan && bash scripts/compile_grpc_protos.sh"
```

### gRPC Connection Refused

```bash
# Verify RPC service is running
docker-compose -f docker-compose-rpc.yml exec ckan \
  ps aux | grep rpc

# Check RPC service logs
docker-compose -f docker-compose-rpc.yml logs ckan | grep RPC
```

### Database Issues

```bash
# Reinitialize database
docker-compose -f docker-compose-rpc.yml exec ckan \
  ckan db clean && ckan db init
```

## Development Workflow

### Code Changes in Host Machine

If you want to test changes without rebuilding Docker image:

```yaml
# In docker-compose-rpc.yml, volume mapping:
volumes:
  - ./ckan:/srv/app/src/ckan:rw  # Make it writable
```

Then:

```bash
# Edit files locally in `./ckan` directory
# Changes are immediately available in container

# For Python changes, restart the service
docker-compose -f docker-compose-rpc.yml restart ckan

# For proto file changes, recompile
docker-compose -f docker-compose-rpc.yml exec ckan \
  bash /srv/app/src/ckan/scripts/compile_grpc_protos.sh
```

## Performance Testing

### Load Test the RPC Service

Create a test script `load_test.py`:

```python
import asyncio
import grpc
import time
from ckan.rpc.proto import ckan_rpc_pb2, ckan_rpc_pb2_grpc
from google.protobuf import json_format, struct_pb2

async def load_test(num_requests=100):
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = ckan_rpc_pb2_grpc.CkanActionServiceStub(channel)

        # Warm up
        req = ckan_rpc_pb2.ActionRequest()
        req.action = 'package_list'
        await stub.ExecuteAction(req)

        # Measure performance
        start = time.time()
        tasks = []
        for i in range(num_requests):
            req = ckan_rpc_pb2.ActionRequest()
            req.action = 'package_list'
            tasks.append(stub.ExecuteAction(req))

        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start

        print(f"Requests: {num_requests}")
        print(f"Time: {elapsed:.2f}s")
        print(f"Rate: {num_requests/elapsed:.0f} req/s")
        print(f"Avg: {(elapsed*1000/num_requests):.1f}ms per request")

asyncio.run(load_test(100))
```

Run it:

```bash
docker-compose -f docker-compose-rpc.yml exec ckan \
  python3 /path/to/load_test.py
```

## Monitoring

### View Service Status

```bash
# Check process status
docker-compose -f docker-compose-rpc.yml exec ckan \
  ps aux | grep -E "(ckan|rpc|python)"

# Check port status
docker-compose -f docker-compose-rpc.yml exec ckan \
  netstat -tlnp | grep -E "(5000|50051)"
```

### View Logs

```bash
# Web service logs
docker-compose -f docker-compose-rpc.yml logs ckan | head -100

# RPC service specific logs
docker-compose -f docker-compose-rpc.yml logs ckan | grep -i rpc

# Follow logs in real-time
docker-compose -f docker-compose-rpc.yml logs -f ckan
```

## Cleanup

```bash
# Stop and remove containers
docker-compose -f docker-compose-rpc.yml down

# Remove volumes (caution: deletes data)
docker-compose -f docker-compose-rpc.yml down -v

# Remove images
docker-compose -f docker-compose-rpc.yml down --rmi all
```

## Docker Image Customization

### Build Custom Image

```bash
docker build \
  -f base/Dockerfile \
  -t my-ckan-rpc:latest \
  .
```

### Build with Custom CKAN Version

```bash
docker build \
  --build-arg CKAN_VERSION=ckan-2.10.5 \
  -f base/Dockerfile \
  -t my-ckan-rpc:2.10.5 \
  .
```

## Advanced Configurations

### Using Docker Compose Overrides

Create `docker-compose.override.yml`:

```yaml
version: '3.8'
services:
  ckan:
    environment:
      # Override for local development
      CKAN_RPC_MAX_WORKERS: "20"
      DEBUG: "true"
    volumes:
      # Mount source for hot-reload
      - ./ckan:/srv/app/src/ckan
```

Then just run:

```bash
docker-compose -f docker-compose-rpc.yml up
# Override file is automatically loaded
```

### Kubernetes Deployment

See [DEPLOYMENT.md](ckan/rpc/DEPLOYMENT.md) for Kubernetes examples.

## References

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [CKAN Docker Guide](https://docs.ckan.org/en/latest/maintaining/deployment/deployment.html)
- [RPC Service Documentation](ckan/rpc/README.md)
- [RPC Configuration](ckan/rpc/CONFIG.md)
