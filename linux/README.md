# Linux Stubs

This directory contains Python files that serve as stubs for Windows-specific functionality.
During the Linux build process (`build-linux.py`), these files are temporarily swapped with their Windows counterparts to ensure the application builds and runs on Linux without Windows-specific dependencies (like `pythonnet` or `ctypes` Windows API calls).

## Files

- `auto_update.py`: Replaces `utils/auto_update.py`. Disables the auto-updater which is Windows-specific.
- `screenshots.py`: Stub for screenshot functionality. Though added scrot still it is doesn't work everywhere.
- `theming.py`: Stub for Windows titlebar theming. This works but depends on GNOME and GTK

## Usage

Run `python build-linux.py` to build the Linux executable. The script will handle the swapping and restoring of files automatically. Or just download the AppImage under release section.
