"""
CKAN gRPC Server

This module provides the gRPC server initialization and management for the
CKAN RPC service.
"""

import logging
import signal
from typing import Optional
from concurrent import futures

import grpc

from .service import CkanActionServiceImpl, CkanStreamServiceImpl
from .proto import ckan_rpc_pb2_grpc

log = logging.getLogger(__name__)


class CkanGrpcServer:
    """
    CKAN gRPC Server

    Manages the lifecycle of the CKAN gRPC server and its services.
    """

    def __init__(
        self,
        host: str = '127.0.0.1',
        port: int = 50051,
        max_workers: int = 10,
        max_message_length: int = 100 * 1024 * 1024  # 100MB
    ):
        """
        Initialize the gRPC server.

        Args:
            host: Server bind address
            port: Server bind port
            max_workers: Maximum number of worker threads
            max_message_length: Maximum message length in bytes
        """
        self.host = host
        self.port = port
        self.max_workers = max_workers
        self.max_message_length = max_message_length
        self.server: Optional[grpc.Server] = None

    def start(self) -> None:
        """Start the gRPC server."""
        try:
            # Create server with resource options
            options = [
                ('grpc.max_send_message_length', self.max_message_length),
                ('grpc.max_receive_message_length', self.max_message_length),
                ('grpc.max_connection_idle_ms', 300000),
                ('grpc.max_connection_age_ms', 600000),
                ('grpc.keepalive_time_ms', 30000),
                ('grpc.keepalive_timeout_ms', 10000),
            ]

            self.server = grpc.server(
                futures.ThreadPoolExecutor(max_workers=self.max_workers),
                options=options
            )

            # Add services
            action_service = CkanActionServiceImpl()
            stream_service = CkanStreamServiceImpl()

            ckan_rpc_pb2_grpc.add_CkanActionServiceServicer_to_server(
                action_service, self.server
            )
            ckan_rpc_pb2_grpc.add_CkanStreamServiceServicer_to_server(
                stream_service, self.server
            )

            # Bind server
            server_address = f'{self.host}:{self.port}'
            self.server.add_insecure_port(server_address)

            log.info(f"Starting CKAN gRPC server on {server_address}")
            self.server.start()
            log.info("CKAN gRPC server started successfully")

            # Handle graceful shutdown
            signal.signal(signal.SIGTERM, self._handle_signal)
            signal.signal(signal.SIGINT, self._handle_signal)

        except Exception as e:
            log.error(f"Failed to start gRPC server: {e}", exc_info=True)
            raise

    def stop(self, grace: int = 5) -> None:
        """
        Stop the gRPC server gracefully.

        Args:
            grace: Grace period in seconds for pending RPCs to complete
        """
        if self.server:
            log.info(f"Stopping CKAN gRPC server with {grace}s grace period")
            self.server.stop(grace)
            log.info("CKAN gRPC server stopped")

    def wait(self) -> None:
        """Wait for the server to terminate."""
        if self.server:
            try:
                self.server.wait_for_termination()
            except KeyboardInterrupt:
                log.info("Server interrupted by user")
                self.stop()

    def _handle_signal(self, signum, frame) -> None:
        """Handle shutdown signals."""
        log.info(f"Received signal {signum}, shutting down gracefully")
        self.stop()


def create_and_start_server(
    host: str = '127.0.0.1',
    port: int = 50051,
    max_workers: int = 10
) -> CkanGrpcServer:
    """
    Create and start a CKAN gRPC server.

    Args:
        host: Server bind address
        port: Server bind port
        max_workers: Maximum number of worker threads

    Returns:
        The running CkanGrpcServer instance
    """
    server = CkanGrpcServer(host=host, port=port, max_workers=max_workers)
    server.start()
    return server


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)

    host = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 50051

    server = create_and_start_server(host=host, port=port)
    server.wait()
