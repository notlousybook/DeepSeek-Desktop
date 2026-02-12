import os
import shutil
import subprocess
import sys
import argparse


def get_version():
    """Read version from version.txt (single source of truth)"""
    version_path = "version.txt"

    if not os.path.exists(version_path):
        print(f"Warning: {version_path} not found, using default version")
        return "0.0.0"

    try:
        with open(version_path, "r", encoding="utf-8") as f:
            version = f.read().strip()

        if version:
            print(f"Found version: {version}")
            return version
        else:
            print("Warning: version.txt is empty, using default")
            return "0.0.0"

    except Exception as e:
        print(f"Error reading version file: {e}")
        return "0.0.0"


def build_app(fresh=False):
    # Ensure required files exist
    if not os.path.exists("injection"):
        print("Error: injection directory not found!")
        return
    if not os.path.exists("deepseek.ico"):
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

    # Get absolute path to icon
    icon_path = os.path.abspath("deepseek.ico")

    # PyInstaller command with absolute icon path
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",  # Create Windows GUI app (no console)
        f"--icon={icon_path}",
        f"--distpath={dist_dir}",
        f"--workpath={temp_dir}",
        f"--specpath={temp_dir}",
        "-n",
        "DeepSeekChat",
        "main.py",
    ]

    # Run PyInstaller
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Print build output
    print(result.stdout)
    if result.stderr:
        print("Build errors:", result.stderr)

    # Clean up temporary build artifacts
    shutil.rmtree(temp_dir, ignore_errors=True)

    # Create version.txt file for auto-updater
    version = get_version()
    version_file_path = os.path.join(dist_dir, "version.txt")
    with open(version_file_path, "w") as f:
        f.write(version)
    print(f"Created version.txt with version: {version}")

    # Define resources to copy to built directory
    resources_to_copy = [
        ("injection", "injection"),  # (source, destination)
        ("deepseek.ico", "deepseek.ico"),
    ]

    # --- Auto-Updater Logic ---
    updater_script_dir = os.path.join(os.path.dirname(__file__), "utils")
    generated_exe_path = os.path.join(updater_script_dir, "auto-updater.exe")
    final_exe_path = os.path.join(dist_dir, "auto-updater.exe")

    # Check if auto-updater.exe already exists in utils folder or if --fresh flag is used
    if fresh or not os.path.exists(generated_exe_path):
        print(
            f"{'--fresh flag used. Regenerating' if fresh else 'auto-updater.exe not found in utils/.'} Generating auto-updater.exe now..."
        )
        build_updater_script = os.path.join(updater_script_dir, "build-updater.py")

        if not os.path.exists(build_updater_script):
            print(f"Error: build-updater.py not found in {updater_script_dir}!")
            return  # Or handle error appropriately

        # Run build-updater.py
        # The build-updater.py script will place the exe directly in the utils directory

        result = subprocess.run(
            [sys.executable, build_updater_script], capture_output=True, text=True
        )
        if result.returncode != 0:
            print("Failed to build auto-updater.exe!")
            print("Error:", result.stderr)
            return  # Or handle error

        print("auto-updater.exe generated successfully!")
        # The build-updater.py script now places the exe directly in the utils directory
        # We need to copy it to the final build directory
        if not os.path.exists(generated_exe_path):
            print(
                "Critical Error: auto-updater.exe could not be found in utils directory after build process."
            )
            return

    # Copy the generated auto-updater.exe from utils to the dist_dir
    if os.path.exists(generated_exe_path):
        if not os.path.exists(final_exe_path):
            shutil.copy(generated_exe_path, final_exe_path)
            print(f"Copied auto-updater.exe from utils to {dist_dir}")
        else:
            print(f"auto-updater.exe already exists at {final_exe_path}")
    else:
        print("Warning: auto-updater.exe was not found in utils directory.")

    # Copy resources
    for src, dest in resources_to_copy:
        src_path = os.path.abspath(src)
        dest_path = os.path.join(dist_dir, dest)

        if os.path.isdir(src_path):
            shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
        else:
            shutil.copy(src_path, dest_path)

    print("\nBuild complete! Executable and resources are in ./built/ directory")

    # Open the output directory in Explorer
    os.startfile(os.path.abspath(dist_dir))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build the DeepSeek Desktop application and its updater."
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Force regeneration of the auto-updater.exe.",
    )
    args = parser.parse_args()
    build_app(fresh=args.fresh)
