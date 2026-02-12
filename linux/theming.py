import os
import subprocess

def is_dark_mode_enabled():
    """Check for dark mode on Linux (GNOME/KDE)."""
    try:
        # GNOME check cuz obviously it is
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
            capture_output=True, text=True
        )
        if "'prefer-dark'" in result.stdout:
            return True
            
        # Alternative GTK check
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
            capture_output=True, text=True
        )
        if "dark" in result.stdout.lower():
            return True
    except:
        pass
    return False

def apply_dark_titlebar(window):
    """Linux theming is typically handled by the Window Manager/GTK theme."""
    # pywebview on Linux respects the system theme automatically. (well still sometimes lol)
    # No explicit DWM calls needed like in Windows.
    return True

def should_use_dark_titlebar():
    return is_dark_mode_enabled()
