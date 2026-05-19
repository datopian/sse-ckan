# CKAN gRPC RPC Deployment Guide

This guide covers deploying the CKAN gRPC RPC service in various environments.

## Prerequisites

- CKAN 2.9.0 or later
- Python 3.7+
- pip or pip3
- Optional: Docker, Kubernetes, or other container orchestration

## Local Deployment

### 1. Install Dependencies

```bash
cd /path/to/ckan
pip install -e .
```

This installs the base CKAN plus gRPC dependencies from `requirements.txt`:
- grpcio
- grpcio-tools
- protobuf

### 2. Compile Protocol Buffers

```bash
bash scripts/compile_grpc_protos.sh
```

**Output**:
```
Compiling gRPC Protocol Buffer files...
✓ Proto compilation successful!
Generated files:
-rw-r--r-- ckan/rpc/proto/ckan_rpc_pb2.py
-rw-r--r-- ckan/rpc/proto/ckan_rpc_pb2_grpc.py
```

### 3. Start the RPC Server

```bash
# Default: localhost:50051
python -m ckan.rpc.server

# Or specify host/port
python -m ckan.rpc.server 0.0.0.0 50051
```

**Output**:
```
INFO:ckan.rpc.server:Starting CKAN gRPC server on 0.0.0.0:50051
INFO:ckan.rpc.server:CKAN gRPC server started successfully
```

### 4. Test the Connection

```bash
python -c "
import grpc
channel = grpc.aio.insecure_channel('localhost:50051')
print('✓ Connection successful')
"
```

### 5. Test with Sample Client

Create `test_client.py`:

```python
#!/usr/bin/env python
import asyncio
import grpc
from ckan.rpc.proto import ckan_rpc_pb2, ckan_rpc_pb2_grpc

async def main():
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = ckan_rpc_pb2_grpc.CkanActionServiceStub(channel)
        req = ckan_rpc_pb2.ActionListRequest()
        resp = await stub.ListActions(req)
        print(f'✓ Found {resp.total} actions')

asyncio.run(main())
```

Run it:
```bash
python test_client.py
```

## Docker Deployment

### Using Docker Image

```bash
# Build custom image with RPC support
docker build -t ckan-with-rpc .

# Run container
docker run -p 5000:5000 -p 50051:50051 ckan-with-rpc
```

### Dockerfile Example

```dockerfile
FROM ckan/ckan:latest

# Install RPC dependencies
RUN pip install grpcio==1.68.0 grpcio-tools==1.68.0 protobuf==5.27.2

# Copy proto files
COPY ckan/rpc/proto /app/ckan/rpc/proto/

# Compile proto files
RUN python -m grpc_tools.protoc \
    -I/app/ckan/rpc/proto \
    --python_out=/app/ckan/rpc/proto \
    --grpc_python_out=/app/ckan/rpc/proto \
    /app/ckan/rpc/proto/ckan_rpc.proto

# Expose ports
EXPOSE 5000 50051

# Start both web and RPC services
CMD ["sh", "-c", "ckan run --host 0.0.0.0 & python -m ckan.rpc.server 0.0.0.0 50051"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  db:
    image: postgres:12
    environment:
      POSTGRES_PASSWORD: ckan
      POSTGRES_USER: ckan
    volumes:
      - pg_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  solr:
    image: ckan/ckan-solr:latest
    environment:
      SOLR_JAVA_MEM: "-Xms512m -Xmx512m"

  ckan:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      CKAN_SQLALCHEMY_URL: postgresql://ckan:ckan@db:5432/ckan
      CKAN_REDIS_URL: redis://redis:6379/1
      CKAN_SOLR_URL: http://solr:8983/solr/ckan
      CKAN_RPC_ENABLED: "true"
      CKAN_RPC_HOST: "0.0.0.0"
      CKAN_RPC_PORT: "50051"
    ports:
      - "5000:5000"
      - "50051:50051"
    depends_on:
      - db
      - redis
      - solr
    volumes:
      - ./ckan_storage:/var/lib/ckan

  rpc-client:
    build:
      context: ./client
    environment:
      CKAN_RPC_HOST: ckan
      CKAN_RPC_PORT: "50051"
    depends_on:
      - ckan

volumes:
  pg_data:
```

## Kubernetes Deployment

### ConfigMap for Configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ckan-rpc-config
  namespace: ckan
data:
  rpc-server.conf: |
    [ckan:rpc]
    enabled = true
    host = 0.0.0.0
    port = 50051
    max_workers = 10
    max_message_length = 104857600
```

### Service Definition

```yaml
apiVersion: v1
kind: Service
metadata:
  name: ckan-rpc
  namespace: ckan
spec:
  selector:
    app: ckan
  type: LoadBalancer
  ports:
  - name: grpc
    port: 50051
    protocol: TCP
    targetPort: 50051
  - name: web
    port: 80
    protocol: TCP
    targetPort: 5000
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ckan
  namespace: ckan
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ckan
  template:
    metadata:
      labels:
        app: ckan
    spec:
      containers:
      - name: ckan
        image: ckan-with-rpc:latest
        imagePullPolicy: Always
        env:
        - name: CKAN_SQLALCHEMY_URL
          valueFrom:
            secretKeyRef:
              name: ckan-secrets
              key: db-url
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
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          tcpSocket:
            port: grpc
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        volumeMounts:
        - name: config
          mountPath: /etc/ckan/default
      volumes:
      - name: config
        configMap:
          name: ckan-rpc-config
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - ckan
              topologyKey: kubernetes.io/hostname
```

## Systemd Service Deployment

### Create Service File

Create `/etc/systemd/system/ckan-rpc.service`:

```ini
[Unit]
Description=CKAN gRPC RPC Service
After=network.target ckan.service
Requires=ckan.service

[Service]
Type=simple
User=ckan
Group=ckan
WorkingDirectory=/var/lib/ckan
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
Environment="CKAN_CONFIG=/etc/ckan/default/production.ini"
ExecStart=/usr/local/bin/python -m ckan.rpc.server 0.0.0.0 50051
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Start the Service

```bash
# Enable auto-start
sudo systemctl enable ckan-rpc

# Start the service
sudo systemctl start ckan-rpc

# Check status
sudo systemctl status ckan-rpc

# View logs
sudo journalctl -u ckan-rpc -f
```

## Systemd Socket Activation

### Socket Definition

Create `/etc/systemd/system/ckan-rpc.socket`:

```ini
[Unit]
Description=CKAN gRPC RPC Socket
Before=ckan-rpc.service

[Socket]
ListenStream=50051
Accept=yes

[Install]
WantedBy=sockets.target
```

### Enable Socket Activation

```bash
sudo systemctl enable ckan-rpc.socket
sudo systemctl start ckan-rpc.socket
```

## Supervisor Configuration

For older systems using Supervisor:

Create `/etc/supervisor/conf.d/ckan-rpc.conf`:

```ini
[program:ckan-rpc]
command=/usr/local/bin/python -m ckan.rpc.server 0.0.0.0 50051
user=ckan
group=ckan
directory=/var/lib/ckan
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/ckan/rpc.log
environment=CKAN_CONFIG=/etc/ckan/default/production.ini
```

Start it:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start ckan-rpc
```

## Load Balancing Configuration

### HAProxy Configuration

```haproxy
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

### Nginx Configuration (with gRPC support)

```nginx
upstream ckan_rpc {
    server ckan1:50051;
    server ckan2:50051;
    server ckan3:50051;
}

server {
    listen 50051 ssl http2;
    ssl_certificate /etc/nginx/certs/server.crt;
    ssl_certificate_key /etc/nginx/certs/server.key;
    ssl_protocols TLSv1.3 TLSv1.2;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        grpc_pass grpc://ckan_rpc;
        grpc_socket_keepalive on;
    }
}
```

## Production Checklist

- [ ] Dependencies installed (`pip install -e .`)
- [ ] Proto files compiled (`bash scripts/compile_grpc_protos.sh`)
- [ ] Server configuration set up
- [ ] TLS certificates generated
- [ ] Database migrations run
- [ ] Permissions verified
- [ ] Service started and verified
- [ ] Health checks configured
- [ ] Monitoring and logging set up
- [ ] Backups configured
- [ ] Load balancer configured
- [ ] Firewall rules updated
- [ ] Client libraries installed
- [ ] Tests passed
- [ ] Documentation reviewed

## Post-Deployment Verification

### 1. Check Server Status

```bash
# Using grpcurl (if installed)
grpcurl -plaintext localhost:50051 list

# Using Python
python -c "
import asyncio
import grpc
async def check():
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        from ckan.rpc.proto import ckan_rpc_pb2_grpc
        stub = ckan_rpc_pb2_grpc.CkanActionServiceStub(channel)
        print('✓ RPC service is responding')
asyncio.run(check())
"
```

### 2. List Available Actions

```bash
python -c "
import asyncio
import grpc
from ckan.rpc.proto import ckan_rpc_pb2, ckan_rpc_pb2_grpc

async def main():
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = ckan_rpc_pb2_grpc.CkanActionServiceStub(channel)
        req = ckan_rpc_pb2.ActionListRequest()
        resp = await stub.ListActions(req)
        print(f'✓ {resp.total} actions available')

asyncio.run(main())
"
```

### 3. Monitor Resource Usage

```bash
# CPU and memory
ps aux | grep 'rpc.server'

# Port listening
netstat -tlnp | grep 50051

# Log monitoring
tail -f /var/log/ckan/rpc.log
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 50051
lsof -i :50051

# Kill process
kill -9 <PID>
```

### Proto Compilation Fails

```bash
# Ensure grpc-tools is installed
pip install grpcio-tools==1.68.0

# Try manual compilation
python -m grpc_tools.protoc \
    -I./ckan/rpc/proto \
    --python_out=./ckan/rpc/proto \
    --grpc_python_out=./ckan/rpc/proto \
    ./ckan/rpc/proto/ckan_rpc.proto
```

### Connection Refused

1. Verify server is running: `ps aux | grep rpc.server`
2. Check port is listening: `netstat -tlnp | grep 50051`
3. Check firewall: `ufw status` or `iptables -L`
4. Check server logs

### High CPU Usage

- Increase `max_workers` parameter
- Monitor action execution times
- Check for slow database queries
- Optimize CKAN actions

## Rollback Procedure

If issues occur:

```bash
# Stop the RPC service
sudo systemctl stop ckan-rpc

# Revert to previous code version
git checkout <previous-commit>

# Remove compiled proto files
rm ckan/rpc/proto/ckan_rpc_pb2*.py

# Restart
sudo systemctl start ckan-rpc
```

## Monitoring and Logging

### Enable Debug Logging

In CKAN config:

```ini
[logger_ckan.rpc]
level = DEBUG
handlers = console
qualname = ckan.rpc
```

### Monitor Server Health

```bash
# Watch server metrics
watch -n 1 'ps aux | grep rpc.server'

# Monitor network connections
watch -n 1 'netstat -an | grep 50051 | wc -l'
```

## Scaling

To handle more requests:

1. **Increase worker threads**: Set `max_workers` higher
2. **Add server instances**: Run multiple RPC servers
3. **Load balance**: Use HAProxy or Nginx
4. **Optimize CKAN**: Check slow actions
5. **Database optimization**: Ensure CKAN DB is tuned

## Backup and Recovery

Include RPC configuration in backups:

```bash
# Backup RPC files
tar -czf ckan-rpc-backup.tar.gz \
    ckan/rpc/ \
    ckan/tests/rpc/ \
    scripts/compile_grpc_protos.sh
```

## References

- [CKAN Documentation](https://docs.ckan.org/)
- [gRPC Deployment Guide](https://grpc.io/docs/guides/performance-best-practices/)
- [Docker Documentation](https://docs.docker.com/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
