import os
import sys
import shutil
import tempfile
import zipfile
import requests
import json
import subprocess
import time
import re
import argparse
import platform
from datetime import datetime
from tqdm import tqdm
import logging
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn
from rich.table import Table
from rich.text import Text
from rich.prompt import Confirm
from rich.layout import Layout
from rich.live import Live
from rich.align import Align
from rich import box

# Fix Unicode encoding issues on Windows
if platform.system() == "Windows":
    # Set environment variable for UTF-8 encoding
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # Reconfigure stdout/stderr to use UTF-8 if available
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, Exception):
        pass

def safe_print(text: str):
    """Print text with Unicode encoding safety"""
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback: replace problematic characters
        safe_text = text.encode('ascii', errors='replace').decode('ascii')
        print(safe_text)
    except Exception as e:
        # Last resort: print error message
        print(f"[Encoding Error: {str(e)}]")

# --- Configuration ---
APP_NAME = "DeepSeekChat.exe" if platform.system() == "Windows" else "DeepSeekChat"
REPO_URL = "https://api.github.com/repos/LousyBook94/DeepSeek-Desktop/releases/latest"
VERSION_FILE = "version.txt"
TEMP_DIR = os.path.join(tempfile.gettempdir(), "DeepSeekUpdate")
MAX_RETRIES = 5
RETRY_DELAY = 5

def get_script_directory():
    """Returns directory where script is located."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))
        
# Initialize Rich console with Unicode safety
class SafeConsole(Console):
    def print(self, *args, **kwargs):
        try:
            super().print(*args, **kwargs)
        except UnicodeEncodeError:
            # Fallback: try to print with safe text
            if args:
                safe_args = []
                for arg in args:
                    if isinstance(arg, str):
                        safe_arg = arg.encode('ascii', errors='replace').decode('ascii')
                        safe_args.append(safe_arg)
                    else:
                        safe_args.append(arg)
                try:
                    super().print(*safe_args, **kwargs)
                except Exception:
                    # Last resort: print error
                    safe_print("[Unicode display error - see log file for details]")
            else:
                safe_print("[Unicode display error - see log file for details]")
        except Exception as e:
            safe_print(f"[Console error: {str(e)}]")

console = SafeConsole()

def setup_logging(script_dir):
    """Set up logging to file and console with UTF-8 encoding"""
    # Ensure UTF-8 environment is set before any logging operations
    if platform.system() == "Windows":
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '0'
        
        # Force reconfigure of stdout/stderr with UTF-8
        try:
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
                sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, Exception):
            pass
    
    log_path = os.path.join(script_dir, "update.log")
    
    # Create custom formatter that handles Unicode
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    
    # File handler with UTF-8 encoding
    file_handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Console handler with Unicode safety
    class SafeStreamHandler(logging.StreamHandler):
        def emit(self, record):
            try:
                super().emit(record)
            except UnicodeEncodeError:
                # Fallback: encode with replacement
                safe_msg = self.format(record).encode('ascii', errors='replace').decode('ascii')
                try:
                    self.stream.write(safe_msg + self.terminator)
                except Exception:
                    # Last resort: skip the message
                    pass
    
    console_handler = SafeStreamHandler()
    console_handler.setFormatter(formatter)
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[file_handler, console_handler],
        force=True
    )
    
    logger = logging.getLogger()
    logger.info(f"Logging initialized with UTF-8 encoding support")
    return logger

def get_current_version(script_dir):
    """Reads current version from the VERSION_FILE."""
    version_path = os.path.join(script_dir, VERSION_FILE)
    if os.path.exists(version_path):
        with open(version_path, 'r') as f:
            return f.read().strip()
    return "0.0.0"

def fetch_latest_version_with_retry(logger):
    """Fetches the latest release info from GitHub with retry logic."""
    with console.status(f"[bold green]Fetching latest version...") as status:
        for attempt in range(MAX_RETRIES):
            try:
                logger.debug(f"[Attempt {attempt+1}/{MAX_RETRIES}] Fetching release info from GitHub...")
                
                # Set headers to avoid SSL issues and improve compatibility
                headers = {
                    'User-Agent': 'DeepSeek-Desktop-Updater/1.0',
                    'Accept': 'application/vnd.github.v3+json',
                    'Connection': 'keep-alive'
                }
                
                response = requests.get(REPO_URL, timeout=60, headers=headers)
                response.raise_for_status()
                release_info = response.json()
                
                latest_version = release_info.get("tag_name", "")
                if not latest_version:
                    logger.error("Version tag not found in release.")
                    raise ValueError("Version tag not found in release.")
                    
                latest_version = latest_version.lstrip('v')
                console.print(f"[green][OK][/green] Successfully fetched version info")
                return latest_version, release_info
            except requests.exceptions.SSLError as e:
                error_msg = f"[{attempt + 1}/{MAX_RETRIES}] SSL Error: {e}"
                logger.error(error_msg)
                
                if attempt < MAX_RETRIES - 1:
                    console.print(f"[yellow][WARN][/yellow] SSL error. Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    console.print(f"[red][FAIL][/red] SSL connection failed after all attempts")
                    return None, None
            except requests.exceptions.ConnectionError as e:
                error_msg = f"[{attempt + 1}/{MAX_RETRIES}] Connection Error: {e}"
                logger.error(error_msg)
                
                if attempt < MAX_RETRIES - 1:
                    console.print(f"[yellow][WARN][/yellow] Connection error. Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    console.print(f"[red][FAIL][/red] Connection failed after all attempts")
                    return None, None
            except requests.exceptions.Timeout as e:
                error_msg = f"[{attempt + 1}/{MAX_RETRIES}] Timeout Error: {e}"
                logger.error(error_msg)
                
                if attempt < MAX_RETRIES - 1:
                    console.print(f"[yellow][WARN][/yellow] Timeout error. Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    console.print(f"[red][FAIL][/red] Request timeout after all attempts")
                    return None, None
            except Exception as e:
                error_msg = f"[{attempt + 1}/{MAX_RETRIES}] Failed to fetch release info: {e}"
                if 'response' in locals():
                    error_msg += f"\nResponse status: {response.status_code}"
                logger.error(error_msg)
                
                if attempt < MAX_RETRIES - 1:
                    console.print(f"[yellow][WARN][/yellow] Error occurred. Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    console.print(f"[red][FAIL][/red] All attempts to fetch release info failed")
                    return None, None

def compare_versions(current, latest):
    """Compares two version strings. Returns True if current >= latest."""
    def parse_version(v):
        if '-' in v:
            core, prerelease = v.split('-', 1)
            return [int(x) for x in core.split('.')], prerelease
        return [int(x) for x in v.split('.')], None
    
    try:
        current_parts, current_prerelease = parse_version(current)
        latest_parts, latest_prerelease = parse_version(latest)
        
        max_len = max(len(current_parts), len(latest_parts))
        current_parts.extend([0] * (max_len - len(current_parts)))
        latest_parts.extend([0] * (max_len - len(latest_parts)))
        
        for cur, lat in zip(current_parts, latest_parts):
            if cur > lat:
                return True
            elif cur < lat:
                return False
        
        if current_prerelease is None and latest_prerelease is None:
            return True
        elif current_prerelease is None:
            return True
        elif latest_prerelease is None:
            return False
        else:
            return current_prerelease >= latest_prerelease
            
    except ValueError as e:
        print(f"Warning: Version parsing error: {e}. Assuming update needed.")
        return False

def bring_console_to_front():
    """Brings the console window to the front (Windows only)."""
    try:
        # Simple PowerShell call to activate console
        subprocess.run(
            ['powershell', '-Command', 'Write-Host "Bringing console to front..."'],
            check=True,
            capture_output=True,
            text=True
        )
    except Exception as e:
        print(f"Could not bring console to front: {e}")

class UpdateChecker:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def get_local_version(self, script_dir):
        return get_current_version(script_dir)

    def fetch_latest_info(self):
        latest_version, release_info = fetch_latest_version_with_retry(self.logger)
        return latest_version, release_info

    def sanitize_text_field(self, text, field_name="text"):
        """Sanitize any text field to handle Unicode characters safely"""
        if not text:
            return ""
        
        if not isinstance(text, str):
            # Convert non-string types to string first
            text = str(text)
        
        try:
            # Test if the text can be encoded safely as ASCII
            text.encode('ascii')
            return text
        except UnicodeEncodeError:
            # Replace problematic characters with ASCII equivalents
            sanitized = text.encode('ascii', errors='replace').decode('ascii')
            self.logger.debug(f"{field_name} contained Unicode characters, sanitized for display")
            return sanitized

    def sanitize_release_notes(self, release_body):
        """Sanitize release notes to handle Unicode characters safely"""
        return self.sanitize_text_field(release_body, "release notes")

    def sanitize_release_info(self, release_info):
        """Sanitize all fields in release info to handle Unicode characters safely"""
        if not release_info:
            return release_info
        
        sanitized_info = {}
        for key, value in release_info.items():
            if isinstance(value, str):
                sanitized_info[key] = self.sanitize_text_field(value, f"release_info.{key}")
            elif isinstance(value, list):
                # Handle lists of assets or other items
                sanitized_list = []
                for item in value:
                    if isinstance(item, dict):
                        sanitized_item = {}
                        for item_key, item_value in item.items():
                            if isinstance(item_value, str):
                                sanitized_item[item_key] = self.sanitize_text_field(item_value, f"release_info.{key}.{item_key}")
                            else:
                                sanitized_item[item_key] = item_value
                        sanitized_list.append(sanitized_item)
                    else:
                        sanitized_list.append(item)
                sanitized_info[key] = sanitized_list
            else:
                sanitized_info[key] = value
        
        return sanitized_info

    def check_for_update(self, script_dir):
        current = self.get_local_version(script_dir)
        latest, info = self.fetch_latest_info()
        if not latest:
            return False, current, None, None
        
        # Sanitize all release info to prevent encoding issues
        if info:
            info = self.sanitize_release_info(info)
        
        need_update = not compare_versions(current, latest)
        return need_update, current, latest, info

def download_release_with_retry(asset_url, asset_name, logger):
    """Downloads the release zip with retry logic and progress."""
    temp_zip_path = os.path.join(TEMP_DIR, "update.zip")
    
    for attempt in range(MAX_RETRIES):
        try:
            console.print(f"[bold blue]Downloading {asset_name}...[/bold blue]")
            
            with requests.get(asset_url, stream=True, timeout=60) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                
                # Custom progress tracking for ETA and speed
                downloaded = 0
                start_time = time.time()
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
                    TextColumn("[progress.file_size]{task.fields[downloaded_str]} / {task.fields[total_size_str]}"),
                    TextColumn("[progress.rate]{task.fields[speed]}"),
                    TextColumn("[progress.eta]{task.fields[eta]}"),
                    console=console,
                    expand=True
                ) as progress:
                    task = progress.add_task("[cyan]Downloading",
                                            total=total_size,
                                            downloaded_str="0 B",
                                            total_size_str="0 B",
                                            speed="0 B/s",
                                            eta="Calculating...")
                    
                    with open(temp_zip_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                
                                # Calculate progress metrics
                                elapsed = time.time() - start_time
                                speed = downloaded / elapsed if elapsed > 0 else 0
                                
                                # Calculate ETA
                                if speed > 0:
                                    remaining = (total_size - downloaded) / speed
                                    eta_str = time.strftime("%H:%M:%S", time.gmtime(remaining))
                                else:
                                    eta_str = "Calculating..."
                                
                                # Format size strings
                                downloaded_str = format_size(downloaded)
                                total_size_str = format_size(total_size)
                                speed_str = format_size(speed) + "/s"
                                
                                progress.update(task,
                                              advance=len(chunk),
                                              downloaded_str=downloaded_str,
                                              total_size_str=total_size_str,
                                              speed=speed_str,
                                              eta=eta_str)
            
            if os.path.exists(temp_zip_path) and os.path.getsize(temp_zip_path) > 0:
                elapsed = time.time() - start_time
                console.print(f"[green][OK][/green] Download complete! Elapsed time: {format_time(elapsed)}")
                return temp_zip_path
            else:
                raise IOError("Downloaded file is empty or not found.")

        except Exception as e:
            logger.error(f"[{attempt + 1}/{MAX_RETRIES}] Download failed: {e}")
            console.print(f"[red][FAIL][/red] Download failed: {e}")
            
            if attempt < MAX_RETRIES - 1:
                console.print(f"[yellow][WARN][/yellow] Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                console.print(f"[red][FAIL][/red] All download attempts failed")
                raise
    return None

def format_size(size_bytes):
    """Format size in bytes to human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def format_time(seconds):
    """Format time in seconds to HH:MM:SS format."""
    return time.strftime("%H:%M:%S", time.gmtime(seconds))

def create_backup(script_dir, app_name, version):
    """Creates a backup of the current application and related files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir_name = f"backup_{version}_{timestamp}"
    backup_dir = os.path.join(script_dir, backup_dir_name)
    
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [app_name, VERSION_FILE, "deepseek.ico"]
    dirs_to_backup = ["injection"]

    console.print(Panel(f"[bold blue]Creating backup in {backup_dir_name}...[/bold blue]", border_style="blue"))
    
    backup_table = Table(show_header=True, header_style="bold magenta")
    backup_table.add_column("Item", style="cyan")
    backup_table.add_column("Status", style="green")
    
    for item_name in files_to_backup:
        item_path = os.path.join(script_dir, item_name)
        if os.path.exists(item_path):
            shutil.copy2(item_path, os.path.join(backup_dir, item_name))
            backup_table.add_row(item_name, "[OK] Backed up")
        else:
            backup_table.add_row(item_name, "[FAIL] Not found")

    for dir_name in dirs_to_backup:
        dir_path = os.path.join(script_dir, dir_name)
        if os.path.exists(dir_path):
            dest_path = os.path.join(backup_dir, dir_name)
            shutil.copytree(dir_path, dest_path)
            backup_table.add_row(f"{dir_name}/", "[OK] Backed up")
        else:
            backup_table.add_row(f"{dir_name}/", "[FAIL] Not found")
    
    console.print(backup_table)
    return backup_dir

def extract_and_install_update(zip_path, script_dir, app_name, logger):
    """Extracts the update and installs new files."""
    console.print("[bold yellow]Extracting update...[/bold yellow]")
    extract_to_dir = os.path.join(TEMP_DIR, "extracted")
    
    if os.path.exists(extract_to_dir):
        shutil.rmtree(extract_to_dir)
    os.makedirs(extract_to_dir, exist_ok=True)
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to_dir)
        console.print("[green][OK][/green] Extraction successful!")
    except zipfile.BadZipFile:
        logger.error("Failed to extract the zip file (it might be corrupted).")
        console.print("[red][FAIL][/red] Failed to extract the zip file")
        return False

    console.print("[bold yellow]Installing new files...[/bold yellow]")
    
    # Create a table for the update progress
    update_table = Table(show_header=True, header_style="bold magenta")
    update_table.add_column("File/Folder", style="cyan")
    update_table.add_column("Status", style="green")
    
    # Copy all files from extracted directory
    success_count = 0
    total_count = 0
    
    for item in os.listdir(extract_to_dir):
        total_count += 1
        src_path = os.path.join(extract_to_dir, item)
        dest_path = os.path.join(script_dir, item)
        
        try:
            if os.path.isdir(src_path):
                if os.path.exists(dest_path):
                    shutil.rmtree(dest_path)
                shutil.copytree(src_path, dest_path)
            else:
                shutil.copy2(src_path, dest_path)
            logger.info(f"Updated: {item}")
            update_table.add_row(item, "[OK] Updated")
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to update {item}: {e}")
            update_table.add_row(item, f"[FAIL] Failed: {str(e)}")
    
    console.print(update_table)
    
    if success_count == total_count:
        console.print(f"[green][OK][/green] Successfully updated {success_count} items")
        return True
    else:
        console.print(f"[red][FAIL][/red] Failed to update {total_count - success_count} out of {total_count} items")
        return False

def restore_backup(backup_dir, script_dir, app_name):
    """Restores files from a backup."""
    console.print(Panel(f"[bold blue]Restoring from backup: {os.path.basename(backup_dir)}...[/bold blue]", border_style="blue"))
    
    restore_table = Table(show_header=True, header_style="bold magenta")
    restore_table.add_column("Item", style="cyan")
    restore_table.add_column("Status", style="green")
    
    for item in os.listdir(backup_dir):
        src_path = os.path.join(backup_dir, item)
        dest_path = os.path.join(script_dir, item)
        
        try:
            if os.path.exists(dest_path):
                if os.path.isdir(dest_path):
                    shutil.rmtree(dest_path)
                else:
                    os.remove(dest_path)
                    
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dest_path)
            else:
                shutil.copy2(src_path, dest_path)
            restore_table.add_row(item, "[OK] Restored")
        except Exception as e:
            restore_table.add_row(item, f"[FAIL] Failed: {str(e)}")
    
    console.print(restore_table)

def main():
    parser = argparse.ArgumentParser(description="DeepSeek Desktop Auto-Updater")
    parser.add_argument("--auto", action="store_true", help="Run in auto mode (non-interactive).")
    parser.add_argument("--debug", action="store_true", help="Keep console open after update for debugging.")
    args = parser.parse_args()

    auto_mode = args.auto
    debug_mode = args.debug
    script_dir = get_script_directory()
    
    logger = setup_logging(script_dir)
    logger.info(f"Script directory: {script_dir}")
    
    os.makedirs(TEMP_DIR, exist_ok=True)
    logger.info(f"Temp directory: {TEMP_DIR}")

    # Check if application is running (only if update is needed)
    # This check will be performed after we confirm an update is needed
    pass

    # Get current version
    current_version = get_current_version(script_dir)
    logger.info(f"Current version: {current_version}")

    # Fetch latest version
    latest_version, release_info = fetch_latest_version_with_retry(logger)
    if not latest_version:
        if auto_mode:
            sys.exit(0)
        else:
            console.print(Panel("[bold red]Could not fetch latest version. Exiting.[/bold red]", border_style="red"))
            return
            
    logger.info(f"Latest version: {latest_version}")

    # Compare versions
    update_needed = not compare_versions(current_version, latest_version)
    logger.info(f"Update needed: {update_needed}")
    
    # Create a table for version information
    version_table = Table(show_header=False, box=box.ROUNDED)
    version_table.add_column("Current Version", style="cyan")
    version_table.add_column("Latest Version", style="green")
    version_table.add_row(current_version, latest_version)
    console.print(Panel(version_table, title="Version Information", border_style="blue"))
    
    # Only proceed with update process if an update is actually needed
    if not update_needed:
        console.print(Panel(f"[bold green]You already have the latest version ({current_version})![/bold green]", border_style="green"))
        # Exit without restarting DeepSeekChat.exe to prevent spamming
        logger.info("No update needed. Exiting without restarting application.")
        return

    # Check if application is running and close it if needed (only when update is needed)
    try:
        if platform.system() == "Windows":
            subprocess.check_output(
                f'tasklist /FI "IMAGENAME eq {APP_NAME}" /FO CSV | find "{APP_NAME}"',
                shell=True,
                stderr=subprocess.DEVNULL
            )
            logger.info(f"{APP_NAME} is running. Attempting to close...")
            subprocess.run(
                f'taskkill /F /IM "{APP_NAME}"',
                shell=True,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            subprocess.check_output(["pgrep", "-f", APP_NAME], stderr=subprocess.DEVNULL)
            logger.info(f"{APP_NAME} is running. Attempting to close...")
            subprocess.run(["pkill", "-f", APP_NAME], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)
        logger.info(f"{APP_NAME} closed.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.info(f"{APP_NAME} is not running.")
    
    console.print(Panel(f"[bold yellow]Update available: {current_version} -> {latest_version}[/bold yellow]", border_style="yellow"))

    # Find platform-appropriate asset
    asset_to_download = None
    target_markers = ["windows.zip"] if platform.system() == "Windows" else ["linux.zip", "linux.tar.gz", "linux"]
    if release_info and "assets" in release_info:
        for asset in release_info["assets"]:
            asset_name = asset["name"].lower()
            if any(marker in asset_name for marker in target_markers):
                asset_to_download = asset
                break

    if not asset_to_download:
        wanted = "Windows" if platform.system() == "Windows" else "Linux"
        console.print(Panel(f"[bold red]Error: {wanted} release asset not found.[/bold red]", border_style="red"))
        if auto_mode:
            sys.exit(1)
        return

    # Download asset
    try:
        zip_path = download_release_with_retry(
            asset_to_download["browser_download_url"],
            asset_to_download["name"],
            logger
        )
        if not zip_path:
            console.print(Panel("[bold red]Failed to download the update.[/bold red]", border_style="red"))
            if auto_mode:
                sys.exit(1)
            return
    except Exception as e:
        logger.error(f"Download error: {e}")
        console.print(Panel(f"[bold red]Download error: {e}[/bold red]", border_style="red"))
        if auto_mode:
            sys.exit(1)
        return

    # Auto mode confirmation
    user_input = None
    if auto_mode:
        bring_console_to_front()
        
        # Create a panel for the auto mode confirmation
        confirmation_table = Table(show_header=False, box=box.ROUNDED)
        confirmation_table.add_column("Info", style="cyan")
        confirmation_table.add_row("NEW VERSION AVAILABLE!")
        confirmation_table.add_row(f"Current: {current_version}")
        confirmation_table.add_row(f"Latest:  {latest_version}")
        confirmation_table.add_row("")
        confirmation_table.add_row("You have 30 seconds to respond...")
        confirmation_table.add_row("If no response, update will proceed automatically.")
        
        console.print(Panel(confirmation_table, title="Update Confirmation", border_style="yellow"))

        start_time = time.time()
        while time.time() - start_time < 30:
            try:
                if msvcrt.kbhit():
                    user_input = msvcrt.getch().decode('utf-8').lower()
                    if user_input in ['y', 'n']:
                        break
                    else:
                        console.print("\n[bold red]Invalid input. Please press Y or N.[/bold red]", end="", flush=True)
            except:
                pass
            time.sleep(0.1)

        if user_input == 'n':
            console.print(Panel("[bold yellow]Update cancelled by user.[/bold yellow]", border_style="yellow"))
            sys.exit(0)
        elif user_input != 'y':
            console.print(Panel("[bold green]No response received. Auto-proceeding with update...[/bold green]", border_style="green"))

    # Create backup
    backup_dir = create_backup(script_dir, APP_NAME, current_version)
    
    # Install update
    try:
        if extract_and_install_update(zip_path, script_dir, APP_NAME, logger):
            with open(os.path.join(script_dir, VERSION_FILE), 'w') as f:
                f.write(latest_version)
            logger.info(f"Updated version to: {latest_version}")
            
            # Create a success panel
            success_table = Table(show_header=False, box=box.ROUNDED)
            success_table.add_column("Info", style="green")
            success_table.add_row("Update installed successfully!")
            success_table.add_row(f"Version: {current_version} -> {latest_version}")
            
            console.print(Panel(success_table, title="Update Complete", border_style="green"))
        else:
            console.print(Panel("[bold red]Update failed. Restoring backup...[/bold red]", border_style="red"))
            restore_backup(backup_dir, script_dir, APP_NAME)
            if auto_mode:
                sys.exit(1)
            return
    except Exception as e:
        logger.error(f"Critical error during update: {e}")
        console.print(Panel("[bold red]Restoring backup...[/bold red]", border_style="red"))
        restore_backup(backup_dir, script_dir, APP_NAME)
        if auto_mode:
            sys.exit(1)
        return

    # Start application
    app_path = os.path.join(script_dir, APP_NAME)
    if os.path.exists(app_path):
        logger.info(f"Starting {APP_NAME}...")
        subprocess.Popen([app_path])
        
        # Create a completion panel
        completion_table = Table(show_header=False, box=box.ROUNDED)
        completion_table.add_column("Info", style="cyan")
        completion_table.add_row("UPDATE COMPLETED SUCCESSFULLY!")
        completion_table.add_row(f"Version: {current_version} -> {latest_version}")
        
        console.print(Panel(completion_table, title="Update Complete", border_style="cyan"))
    else:
        logger.error("Application executable not found after update.")
        console.print(Panel("[bold red]Application executable not found after update.[/bold red]", border_style="red"))
        restore_backup(backup_dir, script_dir, APP_NAME)
        if auto_mode:
            sys.exit(1)

    # Cleanup
    logger.info("Cleaning up temporary files...")
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    logger.info("Cleanup complete. Exiting.")

if __name__ == "__main__":
    try:
        import msvcrt
        main()
    except ImportError:
        console.print(Panel("[bold yellow]msvcrt module not found. Auto mode interactive prompt may not work correctly.[/bold yellow]", border_style="yellow"))
        main()
    except KeyboardInterrupt:
        console.print(Panel("[bold yellow]Update cancelled by user.[/bold yellow]", border_style="yellow"))
        sys.exit(1)
    except Exception as e:
        console.print(Panel(f"[bold red]An unexpected error occurred: {e}[/bold red]", border_style="red"))
        sys.exit(1)
