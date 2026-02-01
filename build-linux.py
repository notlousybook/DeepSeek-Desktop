import os
import shutil
import subprocess
import sys

# Configuration
FILE_MAPPING = {
    "linux/auto_update.py": "utils/auto_update.py"
}

BACKUP_EXTENSION = ".bak_win"

def backup_and_swap():
    """Backs up Windows files and swaps them with Linux stubs."""
    print("🔄 Swapping Windows files with Linux stubs...")
    for linux_file, target_file in FILE_MAPPING.items():
        if not os.path.exists(linux_file):
            print(f"⚠️  Warning: Linux stub {linux_file} not found. Skipping.")
            continue
            
        if os.path.exists(target_file):
            # Backup the windows files
            backup_path = target_file + BACKUP_EXTENSION
            shutil.copy2(target_file, backup_path)
            print(f"  Backed up {target_file} -> {backup_path}")
            
            # Swap files
            shutil.copy2(linux_file, target_file)
            print(f"  Swapped {target_file} with {linux_file}")
        else:
            print(f"⚠️  Target file {target_file} not found. Creating from stub.")
            # Ensure dir exists
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            shutil.copy2(linux_file, target_file)

def restore_files():
    """Restores original Windows files from backups."""
    print("Restoring original Windows files...")
    for _, target_file in FILE_MAPPING.items():
        backup_path = target_file + BACKUP_EXTENSION
        if os.path.exists(backup_path):
            shutil.move(backup_path, target_file)
            print(f"  Restored {target_file}")
        elif os.path.exists(target_file) and target_file in ["utils/auto_update.py"]:
             pass

def build():
    """Runs PyInstaller for Linux."""
    print("🐧 Starting Linux Build...")
    
    # PyInstaller arguments
    # Exclude Windows-specific modules that might be detected
    # clr is pythonnet and its windows only
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "DeepSeekChat_Linux",
        "--clean",
        "--exclude-module", "clr",
        "--exclude-module", "pythonnet",
        "--exclude-module", "ctypes.wintypes",
        "--add-data", "injection:injection",
        "main.py"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ Build successful! Check dist/ folder.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
    finally:
        restore_files()

if __name__ == "__main__":
    # Ensure we are in the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    try:
        backup_and_swap()
        build()
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        restore_files()
