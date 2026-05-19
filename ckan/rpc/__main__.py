"""
CKAN gRPC RPC Service - Module Entry Point

This module allows the RPC service to be started via:
    python3 -m ckan.rpc.server <host> <port>
"""

import sys
import logging

from .server import create_and_start_server

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='[%(name)s] %(levelname)s: %(message)s'
    )

    host = sys.argv[1] if len(sys.argv) > 1 else '0.0.0.0'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 50051

    try:
        server = create_and_start_server(host=host, port=port)
        server.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        if server:
            server.stop(grace=5)
