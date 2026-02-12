import os
import sys
import subprocess
import requests
import json
import platform


class UpdateChecker:
    def __init__(self, logger=None):
        self.logger = logger
        self.repo_url = (
            "https://api.github.com/repos/notlousybook/DeepSeek-Desktop/releases/latest"
        )

    def check_for_update(self, script_dir):
        """Functional Linux update check against GitHub releases."""
        current_version = "0.0.0"
        version_path = os.path.join(script_dir, "version.txt")
        if os.path.exists(version_path):
            with open(version_path, "r") as f:
                current_version = f.read().strip()

        try:
            response = requests.get(self.repo_url, timeout=10)
            response.raise_for_status()
            release_info = response.json()
            latest_version = release_info.get("tag_name", "").lstrip("v")

            # Simple version comparison
            need_update = latest_version != current_version
            return need_update, current_version, latest_version, release_info
        except Exception as e:
            if self.logger:
                self.logger.error(f"Linux Update Check Failed: {e}")
            return False, current_version, None, {}


def launch_auto_updater():
    """Linux implementation of updater launch (placeholder for script/binary launch)."""
    print(
        "Linux: Auto-updater launch requested. In a real scenario, this would trigger a shell script."
    )
    subprocess.Popen(
        [
            "notify-send",
            "DeepSeek Update",
            "Update process started. Please check your terminal or logs.",
        ]
    )
