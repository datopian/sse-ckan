# CKAN RPC Configuration Guide

## Server Configuration

### Basic Configuration

Configure the RPC server in your CKAN configuration file (e.g., `development.ini` or `production.ini`):

```ini
# RPC Service Configuration
ckan.rpc.enabled = true
ckan.rpc.host = 0.0.0.0
ckan.rpc.port = 50051
ckan.rpc.max_workers = 10
ckan.rpc.max_message_length = 104857600
```

### Environment Variables

Alternatively, use environment variables:

```bash
export CKAN_RPC_ENABLED=true
export CKAN_RPC_HOST=0.0.0.0
export CKAN_RPC_PORT=50051
export CKAN_RPC_MAX_WORKERS=10
export CKAN_RPC_MAX_MESSAGE_LENGTH=104857600
```

## Configuration Options

### `ckan.rpc.enabled`
- **Type**: Boolean
- **Default**: `false`
- **Description**: Enable/disable the gRPC RPC service
- **Example**: `true`

### `ckan.rpc.host`
- **Type**: String
- **Default**: `127.0.0.1`
- **Description**: Server bind address
- **Examples**:
  - `127.0.0.1` - Localhost only
  - `0.0.0.0` - All interfaces
  - `10.0.0.5` - Specific IP

### `ckan.rpc.port`
- **Type**: Integer
- **Default**: `50051`
- **Description**: Server bind port
- **Range**: 1-65535
- **Example**: `50051`

### `ckan.rpc.max_workers`
- **Type**: Integer
- **Default**: `10`
- **Description**: Maximum number of worker threads
- **Recommendation**: Set to `(2 × CPU cores) + 1` for optimal performance
- **Example**: `32` (for 16-core system)

### `ckan.rpc.max_message_length`
- **Type**: Integer
- **Default**: `104857600` (100MB)
- **Description**: Maximum message size in bytes
- **Notes**:
  - Increase for large file uploads
  - Be mindful of memory usage
  - Must be same on client and server
- **Examples**:
  - `52428800` (50MB)
  - `209715200` (200MB)
  - `1073741824` (1GB)

### `ckan.rpc.tls.enabled`
- **Type**: Boolean
- **Default**: `false`
- **Description**: Enable TLS/SSL encryption (future)

### `ckan.rpc.tls.cert_path`
- **Type**: String
- **Default**: None
- **Description**: Path to TLS certificate file
- **Example**: `/etc/ckan/certs/server.crt`

### `ckan.rpc.tls.key_path`
- **Type**: String
- **Default**: None
- **Description**: Path to TLS private key file
- **Example**: `/etc/ckan/certs/server.key`

### `ckan.rpc.log_level`
- **Type**: String
- **Default**: `INFO`
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Description**: Logging level for RPC service
- **Example**: `DEBUG`

### `ckan.rpc.reflection.enabled`
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable gRPC reflection (allows clients to discover service definitions)

### `ckan.rpc.health_check.enabled`
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable health check service

### `ckan.rpc.metrics.enabled`
- **Type**: Boolean
- **Default**: `false`
- **Description**: Enable Prometheus metrics export (future)

### `ckan.rpc.metrics.port`
- **Type**: Integer
- **Default**: `8000`
- **Description**: Prometheus metrics server port

## Development Configuration

For development with hot-reload:

```ini
[app:main]
debug = true

[ckan:rpc]
enabled = true
host = 127.0.0.1
port = 50051
max_workers = 4
log_level = DEBUG
reflection.enabled = true
```

## Production Configuration

For production deployment:

```ini
[ckan:rpc]
enabled = true
host = 0.0.0.0
port = 50051
max_workers = 32
max_message_length = 104857600
log_level = WARNING
tls.enabled = true
tls.cert_path = /etc/ckan/certs/server.crt
tls.key_path = /etc/ckan/certs/server.key
metrics.enabled = true
metrics.port = 8000
```

## Docker Configuration

For Docker deployments:

```dockerfile
FROM ckan/ckan:latest

# Install RPC dependencies
RUN pip install grpcio==1.68.0 grpcio-tools==1.68.0 protobuf==5.27.2

# Compile proto files
COPY ckan/rpc/proto /app/ckan/rpc/proto/
RUN python -m grpc_tools.protoc \
    -I/app/ckan/rpc/proto \
    --python_out=/app/ckan/rpc/proto \
    --grpc_python_out=/app/ckan/rpc/proto \
    /app/ckan/rpc/proto/ckan_rpc.proto

# Configuration
ENV CKAN_RPC_ENABLED=true
ENV CKAN_RPC_HOST=0.0.0.0
ENV CKAN_RPC_PORT=50051
ENV CKAN_RPC_MAX_WORKERS=10

EXPOSE 50051
```

### Docker Compose

```yaml
version: '3.8'

services:
  ckan:
    image: ckan/ckan:latest
    environment:
      CKAN_RPC_ENABLED: "true"
      CKAN_RPC_HOST: "0.0.0.0"
      CKAN_RPC_PORT: "50051"
      CKAN_RPC_MAX_WORKERS: "10"
    ports:
      - "5000:5000"  # Web UI
      - "50051:50051"  # gRPC
    volumes:
      - ./ckan_config:/etc/ckan/default
      - ./ckan_storage:/var/lib/ckan

  rpc-client:
    image: my-rpc-client:latest
    depends_on:
      - ckan
    environment:
      CKAN_RPC_HOST: ckan
      CKAN_RPC_PORT: "50051"
```

## Kubernetes Configuration

For Kubernetes deployments:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ckan-rpc-config
data:
  rpc.ini: |
    [ckan:rpc]
    enabled = true
    host = 0.0.0.0
    port = 50051
    max_workers = 10
    max_message_length = 104857600
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ckan
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: ckan
        image: ckan/ckan:latest
        env:
        - name: CKAN_RPC_ENABLED
          value: "true"
        - name: CKAN_RPC_HOST
          value: "0.0.0.0"
        - name: CKAN_RPC_PORT
          value: "50051"
        - name: CKAN_RPC_MAX_WORKERS
          value: "10"
        ports:
        - name: web
          containerPort: 5000
        - name: grpc
          containerPort: 50051
        livenessProbe:
          tcpSocket:
            port: grpc
          initialDelaySeconds: 10
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: ckan-rpc
spec:
  selector:
    app: ckan
  ports:
  - port: 50051
    protocol: TCP
  type: LoadBalancer
```

## SSL/TLS Configuration

### Generate Self-Signed Certificate

```bash
# Generate private key
openssl genrsa -out /etc/ckan/certs/server.key 2048

# Generate certificate
openssl req -new -x509 -key /etc/ckan/certs/server.key \
  -out /etc/ckan/certs/server.crt \
  -days 365 \
  -subj "/CN=ckan.example.com"
```

### Configure in CKAN

```ini
[ckan:rpc]
enabled = true
tls.enabled = true
tls.cert_path = /etc/ckan/certs/server.crt
tls.key_path = /etc/ckan/certs/server.key
```

### Client Configuration

```python
import grpc
import ssl

# Load credentials
credentials = grpc.ssl_channel_credentials(
    root_certificates=open('/path/to/ca.crt', 'rb').read(),
    private_key=open('/path/to/client.key', 'rb').read(),
    certificate_chain=open('/path/to/client.crt', 'rb').read()
)

# Create secure channel
channel = grpc.aio.secure_channel(
    'ckan.example.com:50051',
    credentials
)
```

## Load Balancing

### HAProxy Configuration

```
global
    log stdout local0
    log stdout local1 notice

defaults
    log     global
    mode    tcp
    timeout connect 5000
    timeout client  50000
    timeout server  50000

frontend ckan_rpc
    bind *:50051
    default_backend ckan_rpc_backend

backend ckan_rpc_backend
    mode tcp
    balance roundrobin
    option tcp-check
    server ckan1 10.0.0.1:50051 check
    server ckan2 10.0.0.2:50051 check
    server ckan3 10.0.0.3:50051 check
```

### Nginx Configuration (HTTP/2)

```nginx
upstream ckan_rpc {
    server ckan1:50051;
    server ckan2:50051;
    server ckan3:50051;
}

server {
    listen 50051 http2 ssl;
    ssl_certificate /etc/nginx/certs/server.crt;
    ssl_certificate_key /etc/nginx/certs/server.key;

    location / {
        grpc_pass grpc://ckan_rpc;
        grpc_socket_keepalive on;
    }
}
```

## Performance Tuning

### System-Level Settings

```bash
# Increase open file descriptors
ulimit -n 65536

# Increase TCP backlog
sysctl -w net.core.somaxconn=4096

# Optimize TCP window size
sysctl -w net.ipv4.tcp_rmem="4096 87380 67108864"
sysctl -w net.ipv4.tcp_wmem="4096 65536 67108864"
```

### CKAN Configuration

For optimal performance:

```ini
[ckan:rpc]
enabled = true
max_workers = 32                    # 2 × CPU cores + 1
max_message_length = 209715200      # 200MB
```

## Monitoring

### Health Check Endpoint

Once TLS/health check is implemented:

```bash
grpcurl -plaintext localhost:50051 grpc.health.v1.Health/Check
```

### Prometheus Metrics

Example configuration (future):

```ini
[ckan:rpc]
metrics.enabled = true
metrics.port = 8000
```

Access metrics at: `http://localhost:8000/metrics`

## Troubleshooting

### Verify Configuration

```bash
# Check if RPC service is enabled
ckan config-tool /etc/ckan/default/production.ini | grep rpc

# Test RPC connection
python -c "
import grpc
try:
    channel = grpc.aio.insecure_channel('localhost:50051')
    print('RPC service is reachable')
except Exception as e:
    print(f'RPC service error: {e}')
"
```

### Debug Mode

Enable debug logging:

```ini
[ckan:rpc]
log_level = DEBUG
```

Then check logs:

```bash
tail -f /var/log/ckan/ckan.log | grep RPC
```

## References

- [CKAN Configuration Guide](https://docs.ckan.org/en/latest/maintaining/configuration.html)
- [gRPC Configuration Best Practices](https://grpc.io/docs/guides/performance-best-practices/)
