"""
Comprehensive test suite for auto_update.py
Run with: python -m pytest tests/test_auto_update.py -v
"""

import os
import sys
import tempfile
import zipfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.auto_update import (
    Config,
    UpdaterError,
    DownloadError,
    InstallationError,
    BackupError,
    VersionError,
    get_base_path,
    get_script_directory,
    get_current_version,
    save_version,
    parse_version,
    compare_versions,
    validate_zip_file,
    format_size,
    format_time,
    create_backup,
    restore_backup,
    extract_and_install_update,
    is_app_running,
    kill_app,
    start_app,
    cleanup_temp_files,
    UpdateManager,
)


class TestPathFunctions:
    """Test path-related helper functions."""

    def test_get_base_path_frozen(self):
        """Test get_base_path when running from PyInstaller bundle."""
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "_MEIPASS", "/fake/bundle/path", create=True):
                result = get_base_path()
                assert result == Path("/fake/bundle/path")

    def test_get_base_path_source(self):
        """Test get_base_path when running from source."""
        with patch.object(sys, "frozen", False, create=True):
            result = get_base_path()
            assert isinstance(result, Path)
            assert result.exists()

    def test_get_script_directory_frozen(self):
        """Test get_script_directory for frozen executable."""
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "executable", "/fake/app.exe", create=True):
                result = get_script_directory()
                assert result == Path("/fake")

    def test_get_script_directory_source(self):
        """Test get_script_directory for source."""
        with patch.object(sys, "frozen", False, create=True):
            result = get_script_directory()
            assert isinstance(result, Path)


class TestVersionFunctions:
    """Test version parsing and comparison functions."""

    def test_parse_version_simple(self):
        """Test parsing simple version strings."""
        parts, prerelease = parse_version("1.2.3")
        assert parts == [1, 2, 3]
        assert prerelease is None

    def test_parse_version_with_prerelease(self):
        """Test parsing version with prerelease tag."""
        parts, prerelease = parse_version("1.2.3-beta")
        assert parts == [1, 2, 3]
        assert prerelease == "beta"

    def test_parse_version_with_v_prefix(self):
        """Test parsing version with v prefix."""
        parts, prerelease = parse_version("v1.2.3")
        assert parts == [1, 2, 3]
        assert prerelease is None

    def test_parse_version_invalid_empty(self):
        """Test parsing empty version raises error."""
        with pytest.raises(VersionError):
            parse_version("")

    def test_parse_version_invalid_none(self):
        """Test parsing None version raises error."""
        with pytest.raises(VersionError):
            parse_version(None)

    def test_parse_version_invalid_format(self):
        """Test parsing invalid version format raises error."""
        with pytest.raises(VersionError):
            parse_version("not-a-version")

    def test_compare_versions_equal(self):
        """Test comparing equal versions."""
        assert compare_versions("1.2.3", "1.2.3") is True

    def test_compare_versions_current_newer(self):
        """Test when current is newer than latest."""
        assert compare_versions("2.0.0", "1.0.0") is True

    def test_compare_versions_current_older(self):
        """Test when current is older than latest."""
        assert compare_versions("1.0.0", "2.0.0") is False

    def test_compare_versions_different_lengths(self):
        """Test comparing versions with different part lengths."""
        assert compare_versions("1.0", "1.0.0") is True
        assert compare_versions("1.0.0", "1.0") is True

    def test_compare_versions_prerelease(self):
        """Test comparing versions with prerelease tags."""
        assert compare_versions("1.0.0", "1.0.0-beta") is True  # Release > prerelease
        assert compare_versions("1.0.0-beta", "1.0.0") is False  # Prerelease < release

    def test_compare_versions_invalid_fallback(self):
        """Test that invalid versions return False (assume update needed)."""
        assert compare_versions("invalid", "1.0.0") is False


class TestFileOperations:
    """Test file read/write operations."""

    def test_get_current_version_exists(self, tmp_path):
        """Test reading version from existing file."""
        version_file = tmp_path / "version.txt"
        version_file.write_text("1.2.3")
        result = get_current_version(tmp_path)
        assert result == "1.2.3"

    def test_get_current_version_not_exists(self, tmp_path):
        """Test reading version when file doesn't exist."""
        result = get_current_version(tmp_path)
        assert result == "0.0.0"

    def test_save_version_success(self, tmp_path):
        """Test saving version successfully."""
        result = save_version(tmp_path, "2.0.0")
        assert result is True
        assert (tmp_path / "version.txt").read_text() == "2.0.0"

    def test_save_version_failure(self, tmp_path):
        """Test saving version to non-existent directory."""
        bad_path = tmp_path / "nonexistent" / "dir"
        result = save_version(bad_path, "2.0.0")
        assert result is False


class TestBackupOperations:
    """Test backup creation and restoration."""

    def test_create_backup_success(self, tmp_path):
        """Test creating backup of files."""
        # Create test files
        (tmp_path / "DeepSeekChat.exe").write_text("fake exe")
        (tmp_path / "version.txt").write_text("1.0.0")
        (tmp_path / "deepseek.ico").write_text("fake ico")
        (tmp_path / "injection").mkdir()
        (tmp_path / "injection" / "test.js").write_text("fake js")

        backup_dir = create_backup(tmp_path, "DeepSeekChat.exe", "1.0.0")

        assert backup_dir.exists()
        assert backup_dir.name.startswith("backup_1.0.0_")
        assert (backup_dir / "DeepSeekChat.exe").exists()
        assert (backup_dir / "version.txt").exists()
        assert (backup_dir / "injection" / "test.js").exists()

    def test_create_backup_missing_files(self, tmp_path):
        """Test creating backup when some files don't exist."""
        (tmp_path / "version.txt").write_text("1.0.0")

        backup_dir = create_backup(tmp_path, "DeepSeekChat.exe", "1.0.0")

        assert backup_dir.exists()
        # Should not fail even if files are missing

    def test_restore_backup_success(self, tmp_path):
        """Test restoring from backup."""
        # Create original files
        (tmp_path / "DeepSeekChat.exe").write_text("original")
        (tmp_path / "version.txt").write_text("1.0.0")

        # Create backup
        backup_dir = create_backup(tmp_path, "DeepSeekChat.exe", "1.0.0")

        # Modify original
        (tmp_path / "DeepSeekChat.exe").write_text("modified")

        # Restore
        result = restore_backup(backup_dir, tmp_path, "DeepSeekChat.exe")

        assert result is True
        assert (tmp_path / "DeepSeekChat.exe").read_text() == "original"

    def test_restore_backup_missing_dir(self, tmp_path):
        """Test restoring from non-existent backup."""
        result = restore_backup(tmp_path / "fake_backup", tmp_path, "DeepSeekChat.exe")
        assert result is False


class TestZipOperations:
    """Test zip file operations."""

    def test_validate_zip_file_valid(self, tmp_path):
        """Test validating a valid zip file."""
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test.txt", "content")

        assert validate_zip_file(zip_path) is True

    def test_validate_zip_file_invalid(self, tmp_path):
        """Test validating an invalid zip file."""
        zip_path = tmp_path / "test.zip"
        zip_path.write_text("not a zip file")

        assert validate_zip_file(zip_path) is False

    def test_validate_zip_file_nonexistent(self, tmp_path):
        """Test validating non-existent zip file."""
        zip_path = tmp_path / "nonexistent.zip"

        assert validate_zip_file(zip_path) is False

    def test_extract_and_install_update_success(self, tmp_path):
        """Test extracting and installing update."""
        # Create zip file
        zip_path = tmp_path / "update.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("DeepSeekChat.exe", "new exe")
            zf.writestr("version.txt", "2.0.0")

        # Create target directory
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Mock logger
        logger = Mock()

        result = extract_and_install_update(
            zip_path, target_dir, "DeepSeekChat.exe", logger
        )

        assert result is True
        assert (target_dir / "DeepSeekChat.exe").read_text() == "new exe"
        assert (target_dir / "version.txt").read_text() == "2.0.0"

    def test_extract_and_install_update_bad_zip(self, tmp_path):
        """Test extracting invalid zip."""
        zip_path = tmp_path / "update.zip"
        zip_path.write_text("not a zip")

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        logger = Mock()

        result = extract_and_install_update(
            zip_path, target_dir, "DeepSeekChat.exe", logger
        )

        assert result is False


class TestUtilityFunctions:
    """Test utility functions."""

    def test_format_size_bytes(self):
        """Test formatting bytes."""
        assert format_size(0) == "0 B"
        assert format_size(512) == "512.0 B"

    def test_format_size_kilobytes(self):
        """Test formatting kilobytes."""
        assert format_size(1024) == "1.0 KB"
        assert format_size(1536) == "1.5 KB"

    def test_format_size_megabytes(self):
        """Test formatting megabytes."""
        assert format_size(1024 * 1024) == "1.0 MB"

    def test_format_time_zero(self):
        """Test formatting zero seconds."""
        assert format_time(0) == "00:00:00"

    def test_format_time_seconds(self):
        """Test formatting seconds."""
        assert format_time(3661) == "01:01:01"  # 1 hour, 1 minute, 1 second


class TestProcessOperations:
    """Test process management operations."""

    @patch("utils.auto_update.subprocess.run")
    def test_is_app_running_true(self, mock_run):
        """Test detecting running application."""
        mock_run.return_value = Mock(stdout="DeepSeekChat.exe,1234,Console")

        result = is_app_running("DeepSeekChat.exe")

        assert result is True
        mock_run.assert_called_once()

    @patch("utils.auto_update.subprocess.run")
    def test_is_app_running_false(self, mock_run):
        """Test detecting non-running application."""
        mock_run.return_value = Mock(stdout="")

        result = is_app_running("DeepSeekChat.exe")

        assert result is False

    @patch("utils.auto_update.subprocess.run")
    def test_is_app_running_exception(self, mock_run):
        """Test handling exception in process check."""
        mock_run.side_effect = Exception("Process error")

        result = is_app_running("DeepSeekChat.exe")

        assert result is False

    @patch("utils.auto_update.is_app_running")
    @patch("utils.auto_update.subprocess.run")
    def test_kill_app_success(self, mock_run, mock_is_running):
        """Test killing running application."""
        mock_is_running.side_effect = [True, False]  # Running, then not running
        mock_run.return_value = Mock()

        logger = Mock()
        result = kill_app("DeepSeekChat.exe", logger)

        assert result is True

    @patch("utils.auto_update.is_app_running")
    def test_kill_app_not_running(self, mock_is_running):
        """Test killing when app not running."""
        mock_is_running.return_value = False

        logger = Mock()
        result = kill_app("DeepSeekChat.exe", logger)

        assert result is True

    @patch("utils.auto_update.subprocess.Popen")
    def test_start_app_success(self, mock_popen):
        """Test starting application."""
        app_path = Path("/fake/path/DeepSeekChat.exe")

        with patch.object(Path, "exists", return_value=True):
            logger = Mock()
            result = start_app(app_path, logger)

            assert result is True
            mock_popen.assert_called_once()

    def test_start_app_not_found(self):
        """Test starting non-existent application."""
        app_path = Path("/fake/path/DeepSeekChat.exe")

        logger = Mock()
        result = start_app(app_path, logger)

        assert result is False


class TestUpdateManager:
    """Test UpdateManager class."""

    def test_update_manager_init(self, tmp_path):
        """Test UpdateManager initialization."""
        logger = Mock()
        manager = UpdateManager(tmp_path, logger)

        assert manager.script_dir == tmp_path
        assert manager.logger == logger
        assert manager.current_version == "0.0.0"

    @patch("utils.auto_update.get_current_version")
    @patch("utils.auto_update.fetch_latest_version_with_retry")
    def test_check_for_update_no_update(self, mock_fetch, mock_get_version, tmp_path):
        """Test checking for update when none available."""
        mock_get_version.return_value = "1.0.0"
        mock_fetch.return_value = ("1.0.0", {"tag_name": "v1.0.0"})

        logger = Mock()
        manager = UpdateManager(tmp_path, logger)

        needed, current, latest, info = manager.check_for_update()

        assert needed is False
        assert current == "1.0.0"
        assert latest == "1.0.0"

    @patch("utils.auto_update.get_current_version")
    @patch("utils.auto_update.fetch_latest_version_with_retry")
    def test_check_for_update_available(self, mock_fetch, mock_get_version, tmp_path):
        """Test checking for update when available."""
        mock_get_version.return_value = "1.0.0"
        mock_fetch.return_value = ("2.0.0", {"tag_name": "v2.0.0"})

        logger = Mock()
        manager = UpdateManager(tmp_path, logger)

        needed, current, latest, info = manager.check_for_update()

        assert needed is True
        assert current == "1.0.0"
        assert latest == "2.0.0"

    @patch("utils.auto_update.get_current_version")
    @patch("utils.auto_update.fetch_latest_version_with_retry")
    def test_check_for_update_fetch_failure(
        self, mock_fetch, mock_get_version, tmp_path
    ):
        """Test checking for update when fetch fails."""
        mock_get_version.return_value = "1.0.0"
        mock_fetch.return_value = (None, None)

        logger = Mock()
        manager = UpdateManager(tmp_path, logger)

        needed, current, latest, info = manager.check_for_update()

        assert needed is False
        assert current == "1.0.0"
        assert latest is None


class TestCleanup:
    """Test cleanup operations."""

    def test_cleanup_temp_files(self, tmp_path):
        """Test cleaning up temporary files."""
        Config.TEMP_DIR = tmp_path / "DeepSeekUpdate"
        Config.TEMP_DIR.mkdir()
        (Config.TEMP_DIR / "test.txt").write_text("test")

        logger = Mock()
        cleanup_temp_files(logger)

        assert not Config.TEMP_DIR.exists()

    def test_cleanup_temp_files_nonexistent(self, tmp_path):
        """Test cleanup when temp dir doesn't exist."""
        Config.TEMP_DIR = tmp_path / "nonexistent"

        logger = Mock()
        cleanup_temp_files(logger)  # Should not raise


class TestIntegration:
    """Integration tests for the full update flow."""

    @patch("utils.auto_update.fetch_latest_version_with_retry")
    @patch("utils.auto_update.download_release_with_retry")
    @patch("utils.auto_update.extract_and_install_update")
    @patch("utils.auto_update.save_version")
    @patch("utils.auto_update.start_app")
    @patch("utils.auto_update.kill_app")
    @patch("utils.auto_update.create_backup")
    def test_full_update_flow_success(
        self,
        mock_backup,
        mock_kill,
        mock_start,
        mock_save,
        mock_extract,
        mock_download,
        mock_fetch,
        tmp_path,
    ):
        """Test successful full update flow."""
        # Setup mocks
        mock_fetch.return_value = (
            "2.0.0",
            {
                "tag_name": "v2.0.0",
                "assets": [
                    {
                        "name": "DeepSeekChat-windows.zip",
                        "browser_download_url": "http://fake.url",
                    }
                ],
            },
        )
        mock_backup.return_value = tmp_path / "backup"
        mock_download.return_value = tmp_path / "update.zip"
        mock_extract.return_value = True
        mock_save.return_value = True
        mock_start.return_value = True
        mock_kill.return_value = True

        # Create version file
        (tmp_path / "version.txt").write_text("1.0.0")

        logger = Mock()
        manager = UpdateManager(tmp_path, logger)

        result = manager.perform_update(auto_mode=False)

        assert result is True
        mock_fetch.assert_called_once()
        mock_download.assert_called_once()
        mock_extract.assert_called_once()
        mock_save.assert_called_once()

    @patch("utils.auto_update.fetch_latest_version_with_retry")
    def test_full_update_flow_no_update(self, mock_fetch, tmp_path):
        """Test update flow when no update available."""
        mock_fetch.return_value = ("1.0.0", {"tag_name": "v1.0.0"})

        (tmp_path / "version.txt").write_text("1.0.0")

        logger = Mock()
        manager = UpdateManager(tmp_path, logger)

        result = manager.perform_update(auto_mode=False)

        assert result is True  # Returns True because no update needed
        mock_fetch.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
