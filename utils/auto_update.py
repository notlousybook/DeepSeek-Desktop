"""
DeepSeek Desktop Auto-Updater
A robust auto-updater for DeepSeek Desktop with backup, rollback, and retry mechanisms.
"""

import os
import sys
import shutil
import tempfile
import zipfile
import hashlib
import requests
import subprocess
import time
import argparse
import platform
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List
from tqdm import tqdm
import logging
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich import box

# Fix Unicode encoding issues on Windows
if platform.system() == "Windows":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


def safe_print(text: str) -> None:
    """Print text with Unicode encoding safety."""
    try:
        print(text)
    except UnicodeEncodeError:
        safe_text = text.encode("ascii", errors="replace").decode("ascii")
        print(safe_text)
    except Exception as e:
        print(f"[Encoding Error: {str(e)}]")


class SafeConsole(Console):
    """Rich console with Unicode safety fallback."""

    def print(self, *args, **kwargs) -> None:
        try:
            super().print(*args, **kwargs)
        except UnicodeEncodeError:
            if args:
                safe_args = [
                    arg.encode("ascii", errors="replace").decode("ascii")
                    if isinstance(arg, str)
                    else arg
                    for arg in args
                ]
                try:
                    super().print(*safe_args, **kwargs)
                except Exception:
                    safe_print("[Unicode display error - see log file for details]")
            else:
                safe_print("[Unicode display error - see log file for details]")
        except Exception as e:
            safe_print(f"[Console error: {str(e)}]")


# Initialize global console
console = SafeConsole()


class Config:
    """Configuration constants for the updater."""

    APP_NAME = "DeepSeekChat.exe"
    REPO_URL = (
        "https://api.github.com/repos/notlousybook/DeepSeek-Desktop/releases/latest"
    )
    VERSION_FILE = "version.txt"
    TEMP_DIR = Path(tempfile.gettempdir()) / "DeepSeekUpdate"
    MAX_RETRIES = 5
    RETRY_DELAY = 5
    REQUEST_TIMEOUT = 60
    SUBPROCESS_TIMEOUT = 30
    BACKUP_PREFIX = "backup"


class UpdaterError(Exception):
    """Base exception for updater errors."""

    pass


class DownloadError(UpdaterError):
    """Raised when download fails."""

    pass


class InstallationError(UpdaterError):
    """Raised when installation fails."""

    pass


class BackupError(UpdaterError):
    """Raised when backup/restore fails."""

    pass


class VersionError(UpdaterError):
    """Raised when version parsing fails."""

    pass


def get_base_path() -> Path:
    """
    Get the base path for resource lookup.

    Returns:
        Path: Base directory (script dir or PyInstaller bundle dir)
    """
    if getattr(sys, "frozen", False):
        # Running from PyInstaller bundle
        return Path(sys._MEIPASS)
    # Running from source
    return Path(__file__).parent


def get_script_directory() -> Path:
    """
    Get the directory where the script/executable is located.

    Returns:
        Path: Script directory
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def setup_logging(script_dir: Path) -> logging.Logger:
    """
    Set up logging to file and console with UTF-8 encoding.

    Args:
        script_dir: Directory where log file should be stored

    Returns:
        logging.Logger: Configured logger instance
    """
    if platform.system() == "Windows":
        os.environ["PYTHONIOENCODING"] = "utf-8"
        os.environ["PYTHONLEGACYWINDOWSSTDIO"] = "0"
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, Exception):
            pass

    log_path = script_dir / "update.log"
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    # File handler with UTF-8 encoding
    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)

    # Console handler with Unicode safety
    class SafeStreamHandler(logging.StreamHandler):
        def emit(self, record) -> None:
            try:
                super().emit(record)
            except UnicodeEncodeError:
                safe_msg = (
                    self.format(record)
                    .encode("ascii", errors="replace")
                    .decode("ascii")
                )
                try:
                    self.stream.write(safe_msg + self.terminator)
                except Exception:
                    pass

    console_handler = SafeStreamHandler()
    console_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.DEBUG, handlers=[file_handler, console_handler], force=True
    )

    logger = logging.getLogger()
    logger.info("Logging initialized with UTF-8 encoding support")
    return logger


def get_current_version(script_dir: Path) -> str:
    """
    Read current version from version.txt file.

    Args:
        script_dir: Directory containing version.txt

    Returns:
        str: Version string or "0.0.0" if not found
    """
    version_path = script_dir / Config.VERSION_FILE
    try:
        if version_path.exists():
            return version_path.read_text(encoding="utf-8").strip()
    except Exception as e:
        console.print(f"[yellow]Warning: Could not read version file: {e}[/yellow]")
    return "0.0.0"


def save_version(script_dir: Path, version: str) -> bool:
    """
    Save version to version.txt file.

    Args:
        script_dir: Directory where version.txt should be saved
        version: Version string to save

    Returns:
        bool: True if successful, False otherwise
    """
    version_path = script_dir / Config.VERSION_FILE
    try:
        version_path.write_text(version, encoding="utf-8")
        return True
    except Exception as e:
        console.print(f"[red]Error saving version: {e}[/red]")
        return False


def parse_version(v: str) -> Tuple[List[int], Optional[str]]:
    """
    Parse version string into numeric parts and prerelease tag.

    Args:
        v: Version string (e.g., "1.2.3-beta")

    Returns:
        Tuple of (version_parts, prerelease) where version_parts is a list of integers

    Raises:
        VersionError: If version string is invalid
    """
    if not v or not isinstance(v, str):
        raise VersionError(f"Invalid version: {v}")

    v = v.strip().lstrip("v")

    if "-" in v:
        core, prerelease = v.split("-", 1)
    else:
        core, prerelease = v, None

    try:
        parts = [int(x) for x in core.split(".")]
        if not parts:
            raise VersionError(f"Empty version parts: {v}")
        return parts, prerelease
    except ValueError as e:
        raise VersionError(f"Invalid version format '{v}': {e}")


def compare_versions(current: str, latest: str) -> bool:
    """
    Compare two version strings.

    Args:
        current: Current version string
        latest: Latest version string

    Returns:
        bool: True if current >= latest, False if update needed

    Note:
        Returns False (assume update needed) if parsing fails
    """
    try:
        current_parts, current_prerelease = parse_version(current)
        latest_parts, latest_prerelease = parse_version(latest)

        # Normalize lengths
        max_len = max(len(current_parts), len(latest_parts))
        current_parts.extend([0] * (max_len - len(current_parts)))
        latest_parts.extend([0] * (max_len - len(latest_parts)))

        # Compare numeric parts
        for cur, lat in zip(current_parts, latest_parts):
            if cur > lat:
                return True
            elif cur < lat:
                return False

        # Compare prerelease tags
        if current_prerelease is None and latest_prerelease is None:
            return True
        elif current_prerelease is None:
            return True  # Release > prerelease
        elif latest_prerelease is None:
            return False  # Prerelease < release
        else:
            return current_prerelease >= latest_prerelease

    except VersionError as e:
        console.print(
            f"[yellow]Version parsing error: {e}. Assuming update needed.[/yellow]"
        )
        return False


def validate_zip_file(zip_path: Path) -> bool:
    """
    Validate that a zip file is not corrupted.

    Args:
        zip_path: Path to zip file

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Try to read the file list
            zf.namelist()
            # Verify first file (optional but thorough)
            if zf.namelist():
                zf.read(zf.namelist()[0])
        return True
    except zipfile.BadZipFile:
        console.print("[red]Invalid or corrupted zip file[/red]")
        return False
    except Exception as e:
        console.print(f"[red]Zip validation error: {e}[/red]")
        return False


def fetch_latest_version_with_retry(
    logger: logging.Logger,
) -> Tuple[Optional[str], Optional[Dict]]:
    """
    Fetch latest release info from GitHub with retry logic.

    Args:
        logger: Logger instance

    Returns:
        Tuple of (version_string, release_info_dict) or (None, None) on failure
    """
    with console.status("[bold green]Fetching latest version..."):
        for attempt in range(Config.MAX_RETRIES):
            try:
                logger.debug(
                    f"[Attempt {attempt + 1}/{Config.MAX_RETRIES}] Fetching release info..."
                )

                headers = {
                    "User-Agent": "DeepSeek-Desktop-Updater/1.0",
                    "Accept": "application/vnd.github.v3+json",
                    "Connection": "keep-alive",
                }

                response = requests.get(
                    Config.REPO_URL, timeout=Config.REQUEST_TIMEOUT, headers=headers
                )
                response.raise_for_status()
                release_info = response.json()

                latest_version = release_info.get("tag_name", "")
                if not latest_version:
                    logger.error("Version tag not found in release.")
                    raise ValueError("Version tag not found in release.")

                latest_version = latest_version.lstrip("v")
                console.print("[green][OK][/green] Successfully fetched version info")
                return latest_version, release_info

            except requests.exceptions.SSLError as e:
                logger.error(f"[{attempt + 1}/{Config.MAX_RETRIES}] SSL Error: {e}")
                if attempt < Config.MAX_RETRIES - 1:
                    console.print(
                        f"[yellow]SSL error. Retrying in {Config.RETRY_DELAY}s...[/yellow]"
                    )
                    time.sleep(Config.RETRY_DELAY)
                else:
                    console.print("[red]SSL connection failed after all attempts[/red]")
                    return None, None

            except requests.exceptions.ConnectionError as e:
                logger.error(
                    f"[{attempt + 1}/{Config.MAX_RETRIES}] Connection Error: {e}"
                )
                if attempt < Config.MAX_RETRIES - 1:
                    console.print(
                        f"[yellow]Connection error. Retrying in {Config.RETRY_DELAY}s...[/yellow]"
                    )
                    time.sleep(Config.RETRY_DELAY)
                else:
                    console.print("[red]Connection failed after all attempts[/red]")
                    return None, None

            except requests.exceptions.Timeout as e:
                logger.error(f"[{attempt + 1}/{Config.MAX_RETRIES}] Timeout Error: {e}")
                if attempt < Config.MAX_RETRIES - 1:
                    console.print(
                        f"[yellow]Timeout error. Retrying in {Config.RETRY_DELAY}s...[/yellow]"
                    )
                    time.sleep(Config.RETRY_DELAY)
                else:
                    console.print("[red]Request timeout after all attempts[/red]")
                    return None, None

            except Exception as e:
                logger.error(
                    f"[{attempt + 1}/{Config.MAX_RETRIES}] Failed to fetch release info: {e}"
                )
                if attempt < Config.MAX_RETRIES - 1:
                    console.print(
                        f"[yellow]Error occurred. Retrying in {Config.RETRY_DELAY}s...[/yellow]"
                    )
                    time.sleep(Config.RETRY_DELAY)
                else:
                    console.print(
                        "[red]All attempts to fetch release info failed[/red]"
                    )
                    return None, None

    return None, None  # Fallback (should never reach here)


def download_release_with_retry(
    asset_url: str, asset_name: str, logger: logging.Logger
) -> Path:
    """
    Download release asset with retry logic and progress bar.

    Args:
        asset_url: URL to download
        asset_name: Name of asset for display
        logger: Logger instance

    Returns:
        Path: Path to downloaded file

    Raises:
        DownloadError: If all retries fail
    """
    Config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    temp_zip_path = Config.TEMP_DIR / "update.zip"

    for attempt in range(Config.MAX_RETRIES):
        try:
            console.print(f"[bold blue]Downloading {asset_name}...[/bold blue]")

            with requests.get(
                asset_url, stream=True, timeout=Config.REQUEST_TIMEOUT
            ) as r:
                r.raise_for_status()
                total_size = int(r.headers.get("content-length", 0))

                downloaded = 0
                start_time = time.time()

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
                    TextColumn(
                        "{task.fields[downloaded_str]} / {task.fields[total_size_str]}"
                    ),
                    TextColumn("{task.fields[speed]}"),
                    TextColumn("{task.fields[eta]}"),
                    console=console,
                    expand=True,
                ) as progress:
                    task = progress.add_task(
                        "[cyan]Downloading",
                        total=total_size,
                        downloaded_str="0 B",
                        total_size_str="0 B",
                        speed="0 B/s",
                        eta="Calculating...",
                    )

                    with open(temp_zip_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)

                                elapsed = time.time() - start_time
                                speed = downloaded / elapsed if elapsed > 0 else 0

                                if speed > 0 and total_size > 0:
                                    remaining = (total_size - downloaded) / speed
                                    eta_str = time.strftime(
                                        "%H:%M:%S", time.gmtime(remaining)
                                    )
                                else:
                                    eta_str = "Calculating..."

                                downloaded_str = format_size(downloaded)
                                total_size_str = format_size(total_size)
                                speed_str = format_size(speed) + "/s"

                                progress.update(
                                    task,
                                    advance=len(chunk),
                                    downloaded_str=downloaded_str,
                                    total_size_str=total_size_str,
                                    speed=speed_str,
                                    eta=eta_str,
                                )

            # Validate downloaded file
            if not temp_zip_path.exists() or temp_zip_path.stat().st_size == 0:
                raise IOError("Downloaded file is empty or not found.")

            if not validate_zip_file(temp_zip_path):
                raise DownloadError("Downloaded file is corrupted or invalid.")

            elapsed = time.time() - start_time
            console.print(
                f"[green][OK][/green] Download complete! Time: {format_time(elapsed)}"
            )
            return temp_zip_path

        except Exception as e:
            logger.error(f"[{attempt + 1}/{Config.MAX_RETRIES}] Download failed: {e}")
            console.print(f"[red][FAIL][/red] Download failed: {e}")

            if attempt < Config.MAX_RETRIES - 1:
                console.print(f"[yellow]Retrying in {Config.RETRY_DELAY}s...[/yellow]")
                time.sleep(Config.RETRY_DELAY)
            else:
                console.print("[red]All download attempts failed[/red]")
                raise DownloadError(
                    f"Failed to download after {Config.MAX_RETRIES} attempts: {e}"
                )


def format_size(size_bytes: float) -> str:
    """Format size in bytes to human readable format."""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def format_time(seconds: float) -> str:
    """Format time in seconds to HH:MM:SS format."""
    return time.strftime("%H:%M:%S", time.gmtime(seconds))


def create_backup(script_dir: Path, app_name: str, version: str) -> Path:
    """
    Create backup of current application files.

    Args:
        script_dir: Application directory
        app_name: Executable name
        version: Current version for backup naming

    Returns:
        Path: Backup directory path

    Raises:
        BackupError: If backup creation fails
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir_name = f"{Config.BACKUP_PREFIX}_{version}_{timestamp}"
    backup_dir = script_dir / backup_dir_name

    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise BackupError(f"Failed to create backup directory: {e}")

    files_to_backup = [app_name, Config.VERSION_FILE, "deepseek.ico"]
    dirs_to_backup = ["injection"]

    console.print(
        Panel(
            f"[bold blue]Creating backup in {backup_dir_name}...[/bold blue]",
            border_style="blue",
        )
    )

    backup_table = Table(show_header=True, header_style="bold magenta")
    backup_table.add_column("Item", style="cyan")
    backup_table.add_column("Status", style="green")

    for item_name in files_to_backup:
        item_path = script_dir / item_name
        try:
            if item_path.exists():
                if item_path.is_file():
                    shutil.copy2(item_path, backup_dir / item_name)
                else:
                    shutil.copytree(item_path, backup_dir / item_name)
                backup_table.add_row(item_name, "[OK] Backed up")
            else:
                backup_table.add_row(item_name, "[SKIP] Not found")
        except Exception as e:
            backup_table.add_row(item_name, f"[FAIL] {e}")

    for dir_name in dirs_to_backup:
        dir_path = script_dir / dir_name
        try:
            if dir_path.exists():
                shutil.copytree(dir_path, backup_dir / dir_name, dirs_exist_ok=True)
                backup_table.add_row(f"{dir_name}/", "[OK] Backed up")
            else:
                backup_table.add_row(f"{dir_name}/", "[SKIP] Not found")
        except Exception as e:
            backup_table.add_row(f"{dir_name}/", f"[FAIL] {e}")

    console.print(backup_table)
    return backup_dir


def restore_backup(backup_dir: Path, script_dir: Path, app_name: str) -> bool:
    """
    Restore files from backup.

    Args:
        backup_dir: Backup directory path
        script_dir: Target directory for restoration
        app_name: Application name for logging

    Returns:
        bool: True if successful, False otherwise
    """
    if not backup_dir.exists():
        console.print(f"[red]Backup directory not found: {backup_dir}[/red]")
        return False

    console.print(
        Panel(
            f"[bold blue]Restoring from backup: {backup_dir.name}...[/bold blue]",
            border_style="blue",
        )
    )

    restore_table = Table(show_header=True, header_style="bold magenta")
    restore_table.add_column("Item", style="cyan")
    restore_table.add_column("Status", style="green")

    success = True
    for item in backup_dir.iterdir():
        src_path = item
        dest_path = script_dir / item.name

        try:
            # Remove existing file/dir
            if dest_path.exists():
                if dest_path.is_dir():
                    shutil.rmtree(dest_path)
                else:
                    dest_path.unlink()

            # Copy from backup
            if src_path.is_dir():
                shutil.copytree(src_path, dest_path)
            else:
                shutil.copy2(src_path, dest_path)
            restore_table.add_row(item.name, "[OK] Restored")
        except Exception as e:
            restore_table.add_row(item.name, f"[FAIL] {e}")
            success = False

    console.print(restore_table)
    return success


def extract_and_install_update(
    zip_path: Path, script_dir: Path, app_name: str, logger: logging.Logger
) -> bool:
    """
    Extract and install update from zip file.

    Args:
        zip_path: Path to update zip file
        script_dir: Target installation directory
        app_name: Application name
        logger: Logger instance

    Returns:
        bool: True if successful, False otherwise
    """
    console.print("[bold yellow]Extracting update...[/bold yellow]")
    extract_to_dir = Config.TEMP_DIR / "extracted"

    # Clean and create extraction directory
    if extract_to_dir.exists():
        shutil.rmtree(extract_to_dir)
    extract_to_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_to_dir)
        console.print("[green][OK][/green] Extraction successful!")
    except zipfile.BadZipFile as e:
        logger.error(f"Failed to extract zip file: {e}")
        console.print("[red][FAIL][/red] Corrupted zip file")
        return False
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        console.print(f"[red][FAIL][/red] Extraction failed: {e}")
        return False

    console.print("[bold yellow]Installing new files...[/bold yellow]")

    update_table = Table(show_header=True, header_style="bold magenta")
    update_table.add_column("File/Folder", style="cyan")
    update_table.add_column("Status", style="green")

    success_count = 0
    total_count = 0

    for item in extract_to_dir.iterdir():
        total_count += 1
        src_path = item
        dest_path = script_dir / item.name

        try:
            # Remove existing
            if dest_path.exists():
                if dest_path.is_dir():
                    shutil.rmtree(dest_path)
                else:
                    dest_path.unlink()

            # Copy new
            if src_path.is_dir():
                shutil.copytree(src_path, dest_path)
            else:
                shutil.copy2(src_path, dest_path)

            logger.info(f"Updated: {item.name}")
            update_table.add_row(item.name, "[OK] Updated")
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to update {item.name}: {e}")
            update_table.add_row(item.name, f"[FAIL] {e}")

    console.print(update_table)

    if success_count == total_count:
        console.print(f"[green][OK][/green] Successfully updated {success_count} items")
        return True
    else:
        console.print(
            f"[red][FAIL][/red] Failed to update {total_count - success_count} out of {total_count} items"
        )
        return False


def is_app_running(app_name: str) -> bool:
    """
    Check if application is currently running.

    Args:
        app_name: Name of executable to check

    Returns:
        bool: True if running, False otherwise
    """
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {app_name}", "/FO", "CSV"],
            capture_output=True,
            text=True,
            timeout=Config.SUBPROCESS_TIMEOUT,
            shell=False,
        )
        return app_name in result.stdout
    except Exception:
        return False


def kill_app(app_name: str, logger: logging.Logger) -> bool:
    """
    Kill running application.

    Args:
        app_name: Name of executable to kill
        logger: Logger instance

    Returns:
        bool: True if successful or not running, False if failed
    """
    if not is_app_running(app_name):
        return True

    try:
        logger.info(f"{app_name} is running. Attempting to close...")
        subprocess.run(
            ["taskkill", "/F", "/IM", app_name],
            check=True,
            capture_output=True,
            timeout=Config.SUBPROCESS_TIMEOUT,
            shell=False,
        )
        time.sleep(3)
        logger.info(f"{app_name} closed.")
        return True
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout while trying to close {app_name}")
        return False
    except subprocess.CalledProcessError:
        logger.info(f"{app_name} is not running.")
        return True
    except Exception as e:
        logger.error(f"Error closing {app_name}: {e}")
        return False


def start_app(app_path: Path, logger: logging.Logger) -> bool:
    """
    Start the application.

    Args:
        app_path: Path to executable
        logger: Logger instance

    Returns:
        bool: True if successful, False otherwise
    """
    if not app_path.exists():
        logger.error(f"Application not found: {app_path}")
        return False

    try:
        logger.info(f"Starting {app_path.name}...")
        subprocess.Popen([str(app_path)], shell=False)
        return True
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        return False


def cleanup_temp_files(logger: logging.Logger) -> None:
    """Clean up temporary update files."""
    logger.info("Cleaning up temporary files...")
    try:
        if Config.TEMP_DIR.exists():
            shutil.rmtree(Config.TEMP_DIR)
            logger.info("Cleanup complete.")
    except Exception as e:
        logger.error(f"Cleanup error: {e}")


class UpdateManager:
    """Manages the entire update process with automatic rollback."""

    def __init__(self, script_dir: Path, logger: logging.Logger):
        self.script_dir = script_dir
        self.logger = logger
        self.backup_dir: Optional[Path] = None
        self.current_version = "0.0.0"
        self.latest_version: Optional[str] = None
        self.release_info: Optional[Dict] = None

    def check_for_update(self) -> Tuple[bool, str, Optional[str], Optional[Dict]]:
        """
        Check if update is available.

        Returns:
            Tuple of (update_needed, current_version, latest_version, release_info)
        """
        self.current_version = get_current_version(self.script_dir)
        self.latest_version, self.release_info = fetch_latest_version_with_retry(
            self.logger
        )

        if not self.latest_version:
            return False, self.current_version, None, None

        update_needed = not compare_versions(self.current_version, self.latest_version)
        return (
            update_needed,
            self.current_version,
            self.latest_version,
            self.release_info,
        )

    def perform_update(self, auto_mode: bool = False) -> bool:
        """
        Perform the full update process with automatic rollback on failure.

        Args:
            auto_mode: Whether running in automatic mode

        Returns:
            bool: True if successful, False otherwise
        """
        # Check for update
        update_needed, current, latest, release_info = self.check_for_update()

        if not update_needed:
            console.print(
                Panel(
                    f"[bold green]Already at latest version ({current})![/bold green]",
                    border_style="green",
                )
            )
            self.logger.info("No update needed.")
            return True

        if not latest or not release_info:
            console.print("[red]Failed to fetch update information[/red]")
            return False

        # Display version info
        version_table = Table(show_header=False, box=box.ROUNDED)
        version_table.add_column("Current", style="cyan")
        version_table.add_column("Latest", style="green")
        version_table.add_row(current, latest)
        console.print(Panel(version_table, title="Version Info", border_style="blue"))

        console.print(
            Panel(
                f"[bold yellow]Update available: {current} -> {latest}[/bold yellow]",
                border_style="yellow",
            )
        )

        # Find Windows asset
        asset = None
        if "assets" in release_info:
            for a in release_info["assets"]:
                if "windows.zip" in a.get("name", "").lower():
                    asset = a
                    break

        if not asset:
            console.print("[red]Error: Windows release asset not found[/red]")
            return False

        # Get user confirmation in auto mode
        if auto_mode and not self._confirm_update_auto(current, latest):
            return False

        # Close running app
        if not kill_app(Config.APP_NAME, self.logger):
            console.print("[red]Failed to close running application[/red]")
            return False

        # Create backup before update
        try:
            self.backup_dir = create_backup(self.script_dir, Config.APP_NAME, current)
        except BackupError as e:
            console.print(f"[red]Backup creation failed: {e}[/red]")
            return False

        # Download and install
        try:
            zip_path = download_release_with_retry(
                asset["browser_download_url"], asset["name"], self.logger
            )

            if extract_and_install_update(
                zip_path, self.script_dir, Config.APP_NAME, self.logger
            ):
                # Update version file
                if save_version(self.script_dir, latest):
                    self.logger.info(f"Updated to version: {latest}")
                    console.print(
                        Panel(
                            f"[bold green]Update successful: {current} -> {latest}[/bold green]",
                            border_style="green",
                        )
                    )

                    # Start app
                    app_path = self.script_dir / Config.APP_NAME
                    if start_app(app_path, self.logger):
                        console.print("[green]Application started successfully[/green]")
                        cleanup_temp_files(self.logger)
                        return True
                    else:
                        console.print(
                            "[yellow]Update installed but failed to start app[/yellow]"
                        )
                        cleanup_temp_files(self.logger)
                        return True  # Still consider update successful
                else:
                    raise InstallationError("Failed to save version file")
            else:
                raise InstallationError("Installation failed")

        except Exception as e:
            self.logger.error(f"Update failed: {e}")
            console.print(f"[red]Update failed: {e}[/red]")
            console.print("[yellow]Restoring from backup...[/yellow]")

            # Automatic rollback
            if self.backup_dir and self.backup_dir.exists():
                if restore_backup(self.backup_dir, self.script_dir, Config.APP_NAME):
                    console.print("[green]Rollback successful[/green]")
                else:
                    console.print(
                        "[red]Rollback failed! Manual intervention may be required.[/red]"
                    )

            cleanup_temp_files(self.logger)
            return False

    def _confirm_update_auto(self, current: str, latest: str) -> bool:
        """Get user confirmation in auto mode with timeout."""
        try:
            import msvcrt
        except ImportError:
            self.logger.warning("msvcrt not available, proceeding without confirmation")
            return True

        confirmation_table = Table(show_header=False, box=box.ROUNDED)
        confirmation_table.add_column("Info", style="cyan")
        confirmation_table.add_row("NEW VERSION AVAILABLE!")
        confirmation_table.add_row(f"Current: {current}")
        confirmation_table.add_row(f"Latest:  {latest}")
        confirmation_table.add_row("")
        confirmation_table.add_row("You have 30 seconds to respond...")
        confirmation_table.add_row("Press Y to proceed, N to cancel")

        console.print(
            Panel(
                confirmation_table, title="Update Confirmation", border_style="yellow"
            )
        )

        start_time = time.time()
        while time.time() - start_time < 30:
            try:
                if msvcrt.kbhit():
                    user_input = msvcrt.getch().decode("utf-8").lower()
                    if user_input == "y":
                        return True
                    elif user_input == "n":
                        console.print("[yellow]Update cancelled by user[/yellow]")
                        return False
                    else:
                        console.print(
                            "[red]Invalid input. Press Y or N.[/red]", end="\r"
                        )
            except:
                pass
            time.sleep(0.1)

        console.print("[green]No response received. Auto-proceeding...[/green]")
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="DeepSeek Desktop Auto-Updater")
    parser.add_argument("--auto", action="store_true", help="Run in auto mode")
    parser.add_argument(
        "--debug", action="store_true", help="Keep console open for debugging"
    )
    args = parser.parse_args()

    script_dir = get_script_directory()
    logger = setup_logging(script_dir)

    logger.info(f"Script directory: {script_dir}")
    logger.info(f"Auto mode: {args.auto}")
    logger.info(f"Debug mode: {args.debug}")

    Config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Temp directory: {Config.TEMP_DIR}")

    # Run update
    manager = UpdateManager(script_dir, logger)
    success = manager.perform_update(auto_mode=args.auto)

    if not success and args.auto:
        sys.exit(1)

    if args.debug:
        input("\nPress Enter to exit...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Update cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        import traceback

        traceback.print_exc()
        sys.exit(1)
