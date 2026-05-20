"""
SSH Tunnel Manager - Secure Redis connection from Windows to Linux VPS.

Features:
  - Auto-setup SSH tunnel for Redis connection
  - Auto-reconnect on disconnect
  - Health check monitoring
  - Graceful shutdown
  - Fallback to manual tunnel instructions

Usage:
    from worker.ssh_tunnel import SSHTunnelManager
    
    # Auto-setup tunnel
    tunnel = SSHTunnelManager(
        vps_host="your-vps-ip",
        vps_user="your-user",
        vps_ssh_key_path="~/.ssh/id_rsa",
        local_port=6379,
        remote_port=6379
    )
    
    tunnel.start()
    # Now connect to Redis at localhost:6379
    
    # Cleanup
    tunnel.stop()
"""

import logging
import os
import time
from pathlib import Path
from typing import Optional

try:
    from sshtunnel import SSHTunnelForwarder
    SSHTUNNEL_AVAILABLE = True
except ImportError:
    SSHTUNNEL_AVAILABLE = False

logger = logging.getLogger("ssh_tunnel")


class SSHTunnelManager:
    """Manage SSH tunnel for Redis connection with auto-reconnect."""

    def __init__(
        self,
        vps_host: str,
        vps_user: str,
        vps_ssh_key_path: Optional[str] = None,
        vps_password: Optional[str] = None,
        local_port: int = 6379,
        remote_port: int = 6379,
        remote_bind_address: str = "127.0.0.1",
        reconnect_interval: int = 30,
        max_reconnect_attempts: int = 0,  # 0 = infinite
    ):
        """
        Initialize SSH tunnel manager.

        Args:
            vps_host: VPS hostname or IP address
            vps_user: SSH username
            vps_ssh_key_path: Path to SSH private key (optional)
            vps_password: SSH password (optional, not recommended)
            local_port: Local port to bind (default: 6379)
            remote_port: Remote Redis port (default: 6379)
            remote_bind_address: Remote bind address (default: 127.0.0.1)
            reconnect_interval: Seconds between reconnect attempts (default: 30)
            max_reconnect_attempts: Max reconnect attempts, 0 = infinite (default: 0)
        """
        if not SSHTUNNEL_AVAILABLE:
            raise ImportError(
                "sshtunnel library not installed. "
                "Install with: pip install sshtunnel"
            )

        self.vps_host = vps_host
        self.vps_user = vps_user
        self.vps_ssh_key_path = self._resolve_ssh_key_path(vps_ssh_key_path)
        self.vps_password = vps_password
        self.local_port = local_port
        self.remote_port = remote_port
        self.remote_bind_address = remote_bind_address
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts

        self.tunnel: Optional[SSHTunnelForwarder] = None
        self.is_running = False
        self.reconnect_count = 0

        # Validate configuration
        self._validate_config()

    def _resolve_ssh_key_path(self, key_path: Optional[str]) -> Optional[str]:
        """Resolve SSH key path with ~ expansion."""
        if not key_path:
            return None

        path = Path(key_path).expanduser()
        if not path.exists():
            logger.warning(f"SSH key not found: {path}")
            return None

        return str(path)

    def _validate_config(self):
        """Validate SSH tunnel configuration."""
        if not self.vps_host:
            raise ValueError("vps_host is required")

        if not self.vps_user:
            raise ValueError("vps_user is required")

        if not self.vps_ssh_key_path and not self.vps_password:
            logger.warning(
                "Neither SSH key nor password provided. "
                "Will try default SSH key locations."
            )

    def start(self) -> bool:
        """
        Start SSH tunnel.

        Returns:
            True if tunnel started successfully, False otherwise
        """
        if self.is_running:
            logger.warning("Tunnel already running")
            return True

        logger.info(f"Starting SSH tunnel to {self.vps_user}@{self.vps_host}")
        logger.info(f"Local port: {self.local_port} -> Remote: {self.remote_bind_address}:{self.remote_port}")

        try:
            # Create tunnel
            ssh_kwargs = {}
            if self.vps_ssh_key_path:
                ssh_kwargs["ssh_pkey"] = self.vps_ssh_key_path
                logger.info(f"Using SSH key: {self.vps_ssh_key_path}")
            elif self.vps_password:
                ssh_kwargs["ssh_password"] = self.vps_password
                logger.info("Using SSH password authentication")

            self.tunnel = SSHTunnelForwarder(
                ssh_address_or_host=(self.vps_host, 22),
                ssh_username=self.vps_user,
                remote_bind_address=(self.remote_bind_address, self.remote_port),
                local_bind_address=("127.0.0.1", self.local_port),
                **ssh_kwargs,
            )

            # Start tunnel
            self.tunnel.start()
            self.is_running = True
            self.reconnect_count = 0

            logger.info(f"SSH tunnel established: localhost:{self.local_port} -> {self.vps_host}:{self.remote_port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start SSH tunnel: {e}", exc_info=True)
            self.is_running = False
            self._print_manual_instructions()
            return False

    def stop(self):
        """Stop SSH tunnel gracefully."""
        if not self.is_running:
            return

        logger.info("Stopping SSH tunnel...")

        try:
            if self.tunnel:
                self.tunnel.stop()
                self.tunnel = None
        except Exception as e:
            logger.error(f"Error stopping tunnel: {e}")

        self.is_running = False
        logger.info("SSH tunnel stopped")

    def check_health(self) -> bool:
        """
        Check if tunnel is healthy.

        Returns:
            True if tunnel is active, False otherwise
        """
        if not self.is_running or not self.tunnel:
            return False

        try:
            return self.tunnel.is_active
        except Exception:
            return False

    def reconnect(self) -> bool:
        """
        Reconnect SSH tunnel.

        Returns:
            True if reconnect successful, False otherwise
        """
        logger.info("Attempting to reconnect SSH tunnel...")

        self.stop()
        time.sleep(2)  # Brief pause before reconnect

        success = self.start()

        if success:
            self.reconnect_count += 1
            logger.info(f"Reconnect successful (attempt #{self.reconnect_count})")
        else:
            logger.error("Reconnect failed")

        return success

    def run_with_auto_reconnect(self, health_check_interval: int = 30):
        """
        Run tunnel with automatic reconnection.

        This is a blocking call that monitors tunnel health and reconnects if needed.
        Use in a separate thread if you need non-blocking behavior.

        Args:
            health_check_interval: Seconds between health checks (default: 30)
        """
        logger.info("Starting tunnel with auto-reconnect...")

        # Initial connection
        if not self.start():
            logger.error("Initial tunnel connection failed")
            return

        # Monitor loop
        while True:
            try:
                time.sleep(health_check_interval)

                # Check tunnel health
                if not self.check_health():
                    logger.warning("Tunnel health check failed, reconnecting...")

                    # Check reconnect limit
                    if self.max_reconnect_attempts > 0 and self.reconnect_count >= self.max_reconnect_attempts:
                        logger.error(f"Max reconnect attempts ({self.max_reconnect_attempts}) reached, giving up")
                        break

                    # Attempt reconnect
                    if not self.reconnect():
                        logger.error(f"Reconnect failed, will retry in {self.reconnect_interval}s")
                        time.sleep(self.reconnect_interval)
                else:
                    logger.debug("Tunnel health check OK")

            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                break
            except Exception as e:
                logger.error(f"Error in auto-reconnect loop: {e}", exc_info=True)
                time.sleep(self.reconnect_interval)

        # Cleanup
        self.stop()
        logger.info("Auto-reconnect stopped")

    def _print_manual_instructions(self):
        """Print manual SSH tunnel setup instructions."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("MANUAL SSH TUNNEL SETUP")
        logger.info("=" * 60)
        logger.info("")
        logger.info("If automatic tunnel setup failed, you can create a manual tunnel:")
        logger.info("")
        logger.info("On Windows (PowerShell or CMD):")
        logger.info(f"  ssh -N -L {self.local_port}:localhost:{self.remote_port} {self.vps_user}@{self.vps_host}")
        logger.info("")
        logger.info("On Linux/Mac:")
        logger.info(f"  ssh -N -L {self.local_port}:localhost:{self.remote_port} {self.vps_user}@{self.vps_host}")
        logger.info("")
        logger.info("Then update your .env file:")
        logger.info(f"  REDIS_URL=redis://localhost:{self.local_port}/0")
        logger.info("")
        logger.info("Keep the SSH tunnel running in a separate terminal.")
        logger.info("=" * 60)
        logger.info("")

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


def create_tunnel_from_env() -> Optional[SSHTunnelManager]:
    """
    Create SSH tunnel manager from environment variables.

    Required env vars:
        VPS_HOST: VPS hostname or IP
        VPS_USER: SSH username

    Optional env vars:
        VPS_SSH_KEY_PATH: Path to SSH private key (default: ~/.ssh/id_rsa)
        VPS_PASSWORD: SSH password (not recommended)
        LOCAL_REDIS_PORT: Local port to bind (default: 6379)
        REMOTE_REDIS_PORT: Remote Redis port (default: 6379)
        TUNNEL_RECONNECT_INTERVAL: Seconds between reconnects (default: 30)

    Returns:
        SSHTunnelManager instance or None if config missing
    """
    vps_host = os.getenv("VPS_HOST")
    vps_user = os.getenv("VPS_USER")

    if not vps_host or not vps_user:
        logger.info("VPS_HOST or VPS_USER not set, skipping SSH tunnel setup")
        return None

    vps_ssh_key_path = os.getenv("VPS_SSH_KEY_PATH", "~/.ssh/id_rsa")
    vps_password = os.getenv("VPS_PASSWORD")
    local_port = int(os.getenv("LOCAL_REDIS_PORT", "6379"))
    remote_port = int(os.getenv("REMOTE_REDIS_PORT", "6379"))
    reconnect_interval = int(os.getenv("TUNNEL_RECONNECT_INTERVAL", "30"))

    return SSHTunnelManager(
        vps_host=vps_host,
        vps_user=vps_user,
        vps_ssh_key_path=vps_ssh_key_path,
        vps_password=vps_password,
        local_port=local_port,
        remote_port=remote_port,
        reconnect_interval=reconnect_interval,
    )


if __name__ == "__main__":
    # Test SSH tunnel
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s - %(message)s",
    )

    tunnel = create_tunnel_from_env()
    if tunnel:
        try:
            tunnel.run_with_auto_reconnect()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
    else:
        logger.error("Failed to create tunnel from environment variables")
