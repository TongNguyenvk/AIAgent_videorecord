"""
State Reset Module - Automatically reset application state after planning phase.

Strategies:
  - Office apps (Excel/Word/PowerPoint): Close file + reopen from backup
  - Browsers (Chrome/Edge/Firefox): Kill process + relaunch URL
  - Simple apps (Notepad/Calculator): Kill + restart
  
Features:
  - Automatic backup creation before planning
  - Verify reset success
  - Timeout handling
  - Retry logic

Usage:
    # Create backup before planning
    resetter = StateResetter()
    backup_path = resetter.create_backup("C:/data.xlsx")
    
    # ... Agent planning phase ...
    
    # Reset to initial state
    new_instance = resetter.reset(
        app_instance=instance,
        backup_file=backup_path
    )
"""

import os
import shutil
import time
import logging
import psutil
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .app_launcher import AppLauncher, AppInstance, AppLaunchError

logger = logging.getLogger(__name__)


class StateResetError(Exception):
    """Raised when state reset fails."""
    pass


@dataclass
class ResetResult:
    """Result of a state reset operation."""
    success: bool
    new_instance: Optional[AppInstance]
    message: str
    reset_strategy: str


class StateResetter:
    """Reset application state to initial conditions."""
    
    def __init__(self, backup_dir: Optional[str] = None):
        """
        Initialize StateResetter.
        
        Args:
            backup_dir: Directory for backup files (default: workspace/backups)
        """
        if backup_dir is None:
            backup_dir = "workspace/backups"
        
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.launcher = AppLauncher()
    
    def create_backup(self, file_path: str) -> str:
        """
        Create a backup copy of a file.
        
        Args:
            file_path: Path to file to backup
            
        Returns:
            Path to backup file
            
        Raises:
            StateResetError: If backup fails
        """
        try:
            source = Path(file_path)
            
            if not source.exists():
                raise StateResetError(f"Source file not found: {file_path}")
            
            # Generate backup filename with timestamp
            timestamp = int(time.time())
            backup_name = f"{source.stem}_backup_{timestamp}{source.suffix}"
            backup_path = self.backup_dir / backup_name
            
            # Copy file
            logger.info(f"Creating backup: {source.name} -> {backup_path.name}")
            shutil.copy2(source, backup_path)
            
            # Verify backup
            if not backup_path.exists():
                raise StateResetError("Backup file not created")
            
            if backup_path.stat().st_size != source.stat().st_size:
                raise StateResetError("Backup file size mismatch")
            
            logger.info(f"Backup created successfully: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            raise StateResetError(f"Failed to create backup: {e}")
    
    def reset(
        self,
        app_instance: AppInstance,
        backup_file: Optional[str] = None,
        timeout: int = 30,
        verify: bool = True,
    ) -> ResetResult:
        """
        Reset application to initial state.
        
        Args:
            app_instance: AppInstance to reset
            backup_file: Path to backup file (for Office apps)
            timeout: Maximum seconds to wait for reset
            verify: If True, verify reset success
            
        Returns:
            ResetResult with new instance and status
            
        Raises:
            StateResetError: If reset fails
        """
        app_type = app_instance.app_type
        
        logger.info(f"Resetting {app_type} (PID={app_instance.pid})...")
        
        # Select strategy based on app type
        if app_type in ["excel", "word", "powerpoint"]:
            return self._reset_office_app(app_instance, backup_file, timeout, verify)
        
        elif app_type in ["chrome", "edge", "firefox"]:
            return self._reset_browser(app_instance, timeout, verify)
        
        else:
            return self._reset_simple_app(app_instance, timeout, verify)
    
    def _reset_office_app(
        self,
        instance: AppInstance,
        backup_file: Optional[str],
        timeout: int,
        verify: bool,
    ) -> ResetResult:
        """
        Reset Office app: Close file + reopen from backup.
        
        Strategy:
          1. Close the file (keep app open if possible)
          2. Restore original file from backup
          3. Reopen file
          4. Verify window exists
        """
        try:
            if not backup_file or not instance.file_path:
                logger.info("Office blank reset strategy: Kill + restart")
                logger.info(f"Killing process PID={instance.pid}...")
                self._kill_process(instance.pid, force=True)
                time.sleep(1)

                logger.info(f"Restarting {instance.app_type} without file...")
                new_instance = self.launcher.launch(
                    app_type=instance.app_type,
                    wait_seconds=5,
                    force_new=True,
                )

                if verify:
                    if not self.launcher.verify_instance(new_instance):
                        raise StateResetError("Reset verification failed")

                logger.info(f"Office blank reset successful (new PID={new_instance.pid})")

                return ResetResult(
                    success=True,
                    new_instance=new_instance,
                    message="Reset successful: Office app restarted without file",
                    reset_strategy="office_kill_restart_blank",
                )

            # Validate backup file
            if not Path(backup_file).exists():
                raise StateResetError(f"Backup file not found: {backup_file}")
            
            # Get original file path
            original_file = instance.file_path
            if not original_file:
                raise StateResetError("Original file path not available")
            
            logger.info(f"Office reset strategy: Close + restore + reopen")
            
            # Step 1: Kill the process (simpler than trying to close gracefully)
            logger.info(f"Killing process PID={instance.pid}...")
            self._kill_process(instance.pid, force=True)
            time.sleep(1)
            
            # Step 2: Restore original file from backup
            logger.info(f"Restoring file from backup...")
            shutil.copy2(backup_file, original_file)
            
            # Verify restore
            if not Path(original_file).exists():
                raise StateResetError("Failed to restore original file")
            
            logger.info(f"File restored: {original_file}")
            
            # Step 3: Reopen file
            logger.info(f"Reopening {instance.app_type} with file...")
            new_instance = self.launcher.launch(
                app_type=instance.app_type,
                file_path=original_file,
                wait_seconds=5,
                force_new=True,
            )
            
            # Step 4: Verify
            if verify:
                if not self.launcher.verify_instance(new_instance):
                    raise StateResetError("Reset verification failed")
            
            logger.info(f"Office app reset successful (new PID={new_instance.pid})")
            
            return ResetResult(
                success=True,
                new_instance=new_instance,
                message=f"Reset successful: File restored and reopened",
                reset_strategy="office_close_restore_reopen",
            )
            
        except AppLaunchError as e:
            raise StateResetError(f"Failed to relaunch app: {e}")
        except Exception as e:
            raise StateResetError(f"Office reset failed: {e}")
    
    def _reset_browser(
        self,
        instance: AppInstance,
        timeout: int,
        verify: bool,
    ) -> ResetResult:
        """
        Reset browser: Kill process + relaunch URL.
        
        Strategy:
          1. Kill browser process
          2. Relaunch with original URL
          3. Verify window exists
        """
        try:
            logger.info(f"Browser reset strategy: Kill + relaunch")
            
            # Get original URL
            url = instance.url or "about:blank"
            
            # Step 1: Kill process
            logger.info(f"Killing browser PID={instance.pid}...")
            self._kill_process(instance.pid, force=True)
            time.sleep(2)  # Wait for browser to fully close
            
            # Step 2: Relaunch with URL
            logger.info(f"Relaunching {instance.app_type} with URL: {url}")
            new_instance = self.launcher.launch(
                app_type=instance.app_type,
                url=url,
                wait_seconds=4,
                force_new=True,
            )
            
            # Step 3: Verify
            if verify:
                if not self.launcher.verify_instance(new_instance):
                    raise StateResetError("Reset verification failed")
            
            logger.info(f"Browser reset successful (new PID={new_instance.pid})")
            
            return ResetResult(
                success=True,
                new_instance=new_instance,
                message=f"Reset successful: Browser relaunched with URL",
                reset_strategy="browser_kill_relaunch",
            )
            
        except AppLaunchError as e:
            raise StateResetError(f"Failed to relaunch browser: {e}")
        except Exception as e:
            raise StateResetError(f"Browser reset failed: {e}")
    
    def _reset_simple_app(
        self,
        instance: AppInstance,
        timeout: int,
        verify: bool,
    ) -> ResetResult:
        """
        Reset simple app: Kill + restart.
        
        Strategy:
          1. Kill process
          2. Restart app (blank state)
          3. Verify window exists
        """
        try:
            logger.info(f"Simple app reset strategy: Kill + restart")
            
            # Step 1: Kill process
            logger.info(f"Killing process PID={instance.pid}...")
            self._kill_process(instance.pid, force=True)
            time.sleep(1)
            
            # Step 2: Restart app
            logger.info(f"Restarting {instance.app_type}...")
            new_instance = self.launcher.launch(
                app_type=instance.app_type,
                wait_seconds=3,
                force_new=True,
            )
            
            # Step 3: Verify
            if verify:
                if not self.launcher.verify_instance(new_instance):
                    raise StateResetError("Reset verification failed")
            
            logger.info(f"Simple app reset successful (new PID={new_instance.pid})")
            
            return ResetResult(
                success=True,
                new_instance=new_instance,
                message=f"Reset successful: App restarted",
                reset_strategy="simple_kill_restart",
            )
            
        except AppLaunchError as e:
            raise StateResetError(f"Failed to restart app: {e}")
        except Exception as e:
            raise StateResetError(f"Simple app reset failed: {e}")
    
    def _kill_process(self, pid: int, force: bool = False, timeout: int = 5) -> bool:
        """
        Kill a process by PID.
        
        Args:
            pid: Process ID to kill
            force: If True, use SIGKILL (force kill)
            timeout: Seconds to wait for graceful termination
            
        Returns:
            True if process killed, False if not found
            
        Raises:
            StateResetError: If kill fails
        """
        try:
            process = psutil.Process(pid)
            
            if force:
                # Force kill immediately
                logger.info(f"Force killing PID={pid}...")
                process.kill()
            else:
                # Try graceful termination first
                logger.info(f"Terminating PID={pid} gracefully...")
                process.terminate()
                
                # Wait for process to exit
                try:
                    process.wait(timeout=timeout)
                except psutil.TimeoutExpired:
                    logger.warning(f"Graceful termination timeout, force killing...")
                    process.kill()
            
            # Verify process is dead
            time.sleep(0.5)
            if psutil.pid_exists(pid):
                raise StateResetError(f"Process {pid} still exists after kill")
            
            logger.info(f"Process {pid} killed successfully")
            return True
            
        except psutil.NoSuchProcess:
            logger.warning(f"Process {pid} not found (already dead?)")
            return False
        except Exception as e:
            raise StateResetError(f"Failed to kill process {pid}: {e}")
    
    def cleanup_backups(self, max_age_hours: int = 24) -> int:
        """
        Clean up old backup files.
        
        Args:
            max_age_hours: Delete backups older than this many hours
            
        Returns:
            Number of files deleted
        """
        deleted = 0
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        try:
            for backup_file in self.backup_dir.glob("*_backup_*"):
                file_age = current_time - backup_file.stat().st_mtime
                
                if file_age > max_age_seconds:
                    logger.info(f"Deleting old backup: {backup_file.name}")
                    backup_file.unlink()
                    deleted += 1
            
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old backup(s)")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
            return deleted


# Convenience functions
def reset_excel(instance: AppInstance, backup_file: str, **kwargs) -> ResetResult:
    """Reset Excel app with backup file."""
    resetter = StateResetter()
    return resetter.reset(instance, backup_file=backup_file, **kwargs)


def reset_browser(instance: AppInstance, **kwargs) -> ResetResult:
    """Reset browser app."""
    resetter = StateResetter()
    return resetter.reset(instance, **kwargs)


def reset_notepad(instance: AppInstance, **kwargs) -> ResetResult:
    """Reset Notepad app."""
    resetter = StateResetter()
    return resetter.reset(instance, **kwargs)


if __name__ == "__main__":
    # Test script
    logging.basicConfig(level=logging.INFO)
    
    print("Testing State Resetter...")
    
    resetter = StateResetter()
    launcher = AppLauncher()
    
    # Test with Notepad
    print("\n1. Testing Notepad reset...")
    try:
        # Launch Notepad
        print("   Launching Notepad...")
        instance = launcher.launch("notepad")
        print(f"   Launched: PID={instance.pid}")
        
        # Wait a bit
        print("   Waiting 3 seconds...")
        time.sleep(3)
        
        # Reset
        print("   Resetting...")
        result = resetter.reset(instance)
        
        if result.success:
            print(f"   Success! New PID={result.new_instance.pid}")
            print(f"   Strategy: {result.reset_strategy}")
            print(f"   Message: {result.message}")
        else:
            print(f"   Failed: {result.message}")
            
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\nTest complete!")
