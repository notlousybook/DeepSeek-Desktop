import os
import shutil
import subprocess
import sys
import argparse
import re  # For parsing version from workflow file
import platform

def get_version_from_workflow():
    """Extract version from GitHub workflow file"""
    workflow_path = ".github/workflows/release.yml"
    
    if not os.path.exists(workflow_path):
        print(f"Warning: {workflow_path} not found, using default version")
        return "0.0.0"
    
    try:
        with open(workflow_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for VERSION: "x.x.x" pattern
        version_match = re.search(r'VERSION:\s*["\']([^"\']+)["\']', content)
        if version_match:
            version = version_match.group(1)
            print(f"Found version in workflow: {version}")
            return version
        else:
            print("Warning: VERSION not found in workflow file, using default")
            return "0.0.0"
            
    except Exception as e:
        print(f"Error reading workflow file: {e}")
        return "0.0.0"

def build_app(fresh=False):
    # Ensure required files exist
    if not os.path.exists("injection"):
        print("Error: injection directory not found!")
        return

    icon_exists = os.path.exists("deepseek.ico")
    if platform.system() == "Windows" and not icon_exists:
        print("Error: deepseek.ico icon not found!")
        return
    
    # Create clean build directories
    temp_dir = "temp_build"
    dist_dir = "built"
    
    # Remove previous build artifacts
    shutil.rmtree(temp_dir, ignore_errors=True)
    shutil.rmtree(dist_dir, ignore_errors=True)
    shutil.rmtree("build", ignore_errors=True)  # Remove intermediate build directory
    
    # Create fresh directories
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(dist_dir, exist_ok=True)
    
    # Get absolute path to icon when available
    icon_path = os.path.abspath("deepseek.ico") if icon_exists else None

    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        f"--distpath={dist_dir}",
        f"--workpath={temp_dir}",
        f"--specpath={temp_dir}",
        "-n", "DeepSeekChat",
        "main.py"
    ]
    if icon_path:
        cmd.insert(3, f"--icon={icon_path}")
    
    # Run PyInstaller
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Print build output
    print(result.stdout)
    if result.stderr:
        print("Build errors:", result.stderr)
    
    # Clean up temporary build artifacts
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    # Create version.txt file for auto-updater
    version = get_version_from_workflow()
    version_file_path = os.path.join(dist_dir, "version.txt")
    with open(version_file_path, 'w') as f:
        f.write(version)
    print(f"Created version.txt with version: {version}")
    
    # Define resources to copy to built directory
    resources_to_copy = [
        ("injection", "injection"),  # (source, destination)
    ]
    if icon_exists:
        resources_to_copy.append(("deepseek.ico", "deepseek.ico"))

    # --- Auto-Updater Logic ---
    updater_script_dir = os.path.join(os.path.dirname(__file__), "utils")
    updater_binary_name = "auto-updater.exe" if platform.system() == "Windows" else "auto-updater"
    generated_exe_path = os.path.join(updater_script_dir, updater_binary_name)
    final_exe_path = os.path.join(dist_dir, updater_binary_name)

    # Check if updater binary already exists in utils folder or if --fresh flag is used
    if fresh or not os.path.exists(generated_exe_path):
        print(f"{'--fresh flag used. Regenerating' if fresh else f'{updater_binary_name} not found in utils/.'} Generating {updater_binary_name} now...")
        build_updater_script = os.path.join(updater_script_dir, "build-updater.py")
        
        if not os.path.exists(build_updater_script):
            print(f"Error: build-updater.py not found in {updater_script_dir}!")
            return # Or handle error appropriately
            
        # Run build-updater.py
        # The build-updater.py script will place the exe directly in the utils directory
        
        result = subprocess.run([sys.executable, build_updater_script], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Failed to build {updater_binary_name}!")
            print("Error:", result.stderr)
            return # Or handle error
        
        print(f"{updater_binary_name} generated successfully!")
        # The build-updater.py script now places the exe directly in the utils directory
        # We need to copy it to the final build directory
        if not os.path.exists(generated_exe_path):
            print(f"Critical Error: {updater_binary_name} could not be found in utils directory after build process.")
            return

    # Copy the generated updater binary from utils to dist_dir
    if os.path.exists(generated_exe_path):
        if not os.path.exists(final_exe_path):
            shutil.copy(generated_exe_path, final_exe_path)
            print(f"Copied {updater_binary_name} from utils to {dist_dir}")
        else:
            print(f"{updater_binary_name} already exists at {final_exe_path}")
    else:
        print(f"Warning: {updater_binary_name} was not found in utils directory.")
    
    # Copy resources
    for src, dest in resources_to_copy:
        src_path = os.path.abspath(src)
        dest_path = os.path.join(dist_dir, dest)
        
        if os.path.isdir(src_path):
            shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
        else:
            shutil.copy(src_path, dest_path)
    
    print("\nBuild complete! Executable and resources are in ./built/ directory")
    
    # Open output directory on supported platforms
    dist_abs = os.path.abspath(dist_dir)
    if platform.system() == "Windows":
        os.startfile(dist_abs)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", dist_abs])
    else:
        if shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", dist_abs])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the DeepSeek Desktop application and its updater.")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Force regeneration of the updater binary."
    )
    args = parser.parse_args()
    build_app(fresh=args.fresh)
