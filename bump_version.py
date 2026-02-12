#!/usr/bin/env python3
"""
Version bumper script for DeepSeek Desktop
Usage: python bump_version.py [major|minor|patch|X.Y.Z]

Examples:
  python bump_version.py patch     # 0.1.70 -> 0.1.71
  python bump_version.py minor     # 0.1.70 -> 0.2.0
  python bump_version.py major     # 0.1.70 -> 1.0.0
  python bump_version.py 1.0.0     # Set specific version
"""

import sys
import re
from pathlib import Path

VERSION_FILE = Path("version.txt")


def read_version():
    """Read current version from version.txt"""
    if not VERSION_FILE.exists():
        print(f"[ERROR] {VERSION_FILE} not found")
        sys.exit(1)

    try:
        version = VERSION_FILE.read_text().strip()
        print(f"Current version: {version}")
        return version
    except Exception as e:
        print(f"[ERROR] Error reading version: {e}")
        sys.exit(1)


def parse_version(version):
    """Parse version string into components"""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version)
    if not match:
        print(f"[ERROR] Invalid version format: {version}")
        sys.exit(1)
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def bump_version(version, bump_type):
    """Bump version based on type"""
    major, minor, patch = parse_version(version)

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        print(f"[ERROR] Unknown bump type: {bump_type}")
        sys.exit(1)


def validate_version(version):
    """Validate version format"""
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        print(f"[ERROR] Invalid version format: {version}")
        print("   Expected format: X.Y.Z (e.g., 1.2.3)")
        return False
    return True


def write_version(version):
    """Write new version to version.txt"""
    try:
        VERSION_FILE.write_text(version + "\n")
        print(f"[OK] Version updated to: {version}")
        print(f"[OK] Written to: {VERSION_FILE}")
        return True
    except Exception as e:
        print(f"[ERROR] Error writing version: {e}")
        return False


def main():
    if len(sys.argv) != 2:
        print("Usage: python bump_version.py [major|minor|patch|X.Y.Z]")
        print("\nExamples:")
        print("  python bump_version.py patch     # Bump patch version")
        print("  python bump_version.py minor     # Bump minor version")
        print("  python bump_version.py major     # Bump major version")
        print("  python bump_version.py 1.0.0     # Set specific version")
        sys.exit(1)

    arg = sys.argv[1]
    current_version = read_version()

    # Determine new version
    if arg in ["major", "minor", "patch"]:
        new_version = bump_version(current_version, arg)
        print(f"[INFO] Bumping {arg} version...")
    else:
        # Assume it's a specific version
        if not validate_version(arg):
            sys.exit(1)
        new_version = arg
        print(f"[INFO] Setting version to: {new_version}")

    # Write new version
    if write_version(new_version):
        print("\n[INFO] Done! Don't forget to:")
        print("   1. Update RELEASE_NOTES.md with changes for this version")
        print(
            "   2. Commit the changes: git add version.txt RELEASE_NOTES.md && git commit -m 'Bump version to X.Y.Z'"
        )
        print("   3. Tag the release: git tag vX.Y.Z")
        print("   4. Push: git push && git push --tags")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
