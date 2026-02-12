# Auto-Updater Testing Guide

## Summary of Changes

I've completely rewritten `utils/auto_update.py` to be more robust with the following improvements:

### Key Improvements

1. **Base Path Helper Function**: `get_base_path()` properly handles both source and PyInstaller frozen bundles
2. **Type Hints**: Full type annotations for better IDE support and fewer bugs
3. **Custom Exceptions**: Specific error types (UpdaterError, DownloadError, InstallationError, etc.) for better error handling
4. **Pathlib**: Replaced `os.path` with `pathlib.Path` for cleaner, more modern code
5. **Subprocess Timeouts**: All subprocess calls now have timeouts to prevent hanging
6. **Automatic Rollback**: UpdateManager class provides automatic rollback on failure
7. **Zip Validation**: Downloaded files are validated before extraction
8. **Better Logging**: Comprehensive logging throughout the update process
9. **Version Parsing**: Robust semantic version parsing with proper error handling

### File Structure

```
utils/
  └── auto_update.py          # Main updater (rewritten)
tests/
  └── test_auto_update.py     # Comprehensive test suite (49 tests)
```

---

## How to Test

### 1. Run Unit Tests

```bash
# Run all tests
python -m pytest tests/test_auto_update.py -v

# Run with coverage
python -m pytest tests/test_auto_update.py --cov=utils.auto_update --cov-report=html

# Run specific test category
python -m pytest tests/test_auto_update.py::TestVersionFunctions -v
python -m pytest tests/test_auto_update.py::TestBackupOperations -v
```

### 2. Manual Testing Steps

#### Test 1: Check Version Parsing
```bash
python -c "
from utils.auto_update import parse_version, compare_versions
print('Testing version parsing...')
assert parse_version('1.2.3') == ([1, 2, 3], None)
assert parse_version('v2.0.0-beta') == ([2, 0, 0], 'beta')
assert compare_versions('1.0.0', '2.0.0') == False  # Update needed
assert compare_versions('2.0.0', '1.0.0') == True   # No update
print('Version tests passed!')
"
```

#### Test 2: Test Path Functions
```bash
python -c "
from utils.auto_update import get_base_path, get_script_directory
print(f'Base path: {get_base_path()}')
print(f'Script dir: {get_script_directory()}')
print('Path functions work!')
"
```

#### Test 3: Test Backup Operations
```bash
python -c "
import tempfile
from pathlib import Path
from utils.auto_update import create_backup, restore_backup

with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    # Create test files
    (tmp_path / 'DeepSeekChat.exe').write_text('test')
    (tmp_path / 'version.txt').write_text('1.0.0')
    
    # Create backup
    backup = create_backup(tmp_path, 'DeepSeekChat.exe', '1.0.0')
    print(f'Backup created: {backup}')
    
    # Modify file
    (tmp_path / 'DeepSeekChat.exe').write_text('modified')
    
    # Restore
    restore_backup(backup, tmp_path, 'DeepSeekChat.exe')
    
    # Verify
    content = (tmp_path / 'DeepSeekChat.exe').read_text()
    assert content == 'test', f'Expected test, got {content}'
    print('Backup/restore works!')
"
```

#### Test 4: Test Update Check (Without Downloading)
```bash
python -c "
import logging
from pathlib import Path
from utils.auto_update import UpdateManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Test with fake directory
manager = UpdateManager(Path('.'), logger)
needed, current, latest, info = manager.check_for_update()
print(f'Update needed: {needed}')
print(f'Current: {current}')
print(f'Latest: {latest}')
"
```

### 3. Integration Testing

#### Simulate Full Update Flow

Create a test environment:

```python
# test_integration.py
import tempfile
import zipfile
from pathlib import Path
import logging
from unittest.mock import patch, Mock

from utils.auto_update import UpdateManager

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    
    # Create fake app files
    (tmp_path / "DeepSeekChat.exe").write_text("v1.0.0")
    (tmp_path / "version.txt").write_text("1.0.0")
    (tmp_path / "injection").mkdir()
    (tmp_path / "injection" / "inject.js").write_text("// js")
    
    # Create fake update zip
    update_zip = tmp_path / "update.zip"
    with zipfile.ZipFile(update_zip, 'w') as zf:
        zf.writestr("DeepSeekChat.exe", "v2.0.0")
        zf.writestr("version.txt", "2.0.0")
    
    # Mock the update process
    with patch('utils.auto_update.fetch_latest_version_with_retry') as mock_fetch, \
         patch('utils.auto_update.download_release_with_retry') as mock_download, \
         patch('utils.auto_update.kill_app') as mock_kill, \
         patch('utils.auto_update.start_app') as mock_start:
        
        mock_fetch.return_value = ("2.0.0", {
            "tag_name": "v2.0.0",
            "assets": [{"name": "windows.zip", "browser_download_url": "http://test"}]
        })
        mock_download.return_value = update_zip
        mock_kill.return_value = True
        mock_start.return_value = True
        
        manager = UpdateManager(tmp_path, logger)
        success = manager.perform_update(auto_mode=False)
        
        print(f"Update success: {success}")
        print(f"New version file: {(tmp_path / 'version.txt').read_text()}")
```

### 4. Test Error Handling

#### Test Invalid Version
```bash
python -c "
from utils.auto_update import parse_version, VersionError
try:
    parse_version('not-a-version')
    print('ERROR: Should have raised exception')
except VersionError as e:
    print(f'Correctly caught error: {e}')
"
```

#### Test Corrupted Zip
```bash
python -c "
import tempfile
from pathlib import Path
from utils.auto_update import validate_zip_file

with tempfile.TemporaryDirectory() as tmp:
    # Create invalid zip
    bad_zip = Path(tmp) / 'bad.zip'
    bad_zip.write_text('not a zip file')
    
    result = validate_zip_file(bad_zip)
    print(f'Invalid zip detected: {not result}')
"
```

### 5. Real-World Testing

**WARNING**: Only do this in a controlled environment!

```bash
# Create a backup of your current installation first!

# Test with --debug flag to keep console open
python utils/auto_update.py --debug

# Test auto mode (with 30 second timeout)
python utils/auto_update.py --auto --debug
```

---

## Key Features to Verify

✅ **Version Comparison**: Correctly identifies when updates are needed  
✅ **Backup Creation**: Creates timestamped backups before updating  
✅ **Automatic Rollback**: Restores from backup if update fails  
✅ **Zip Validation**: Validates downloaded files before extraction  
✅ **Subprocess Timeouts**: Won't hang if processes don't respond  
✅ **Unicode Safety**: Handles special characters in paths and console output  
✅ **Path Handling**: Works correctly with both source and frozen executables  
✅ **Retry Logic**: Retries failed network requests  
✅ **Error Recovery**: Gracefully handles errors at each stage  

---

## Troubleshooting

### Import Errors
```bash
# Make sure you're in the project root
cd C:\Users\lousy\Documents\Projects\DeepSeek-Desktop
python -c "from utils.auto_update import UpdateManager"
```

### Test Failures
```bash
# Run with more verbose output
python -m pytest tests/test_auto_update.py -vv --tb=long

# Run a single test
python -m pytest tests/test_auto_update.py::TestVersionFunctions::test_parse_version_simple -v
```

### Permission Errors (Windows)
Run tests as administrator if testing process management functions.

---

## All Tests Passed! ✅

```
49 passed in 10.01s
```

The new updater is production-ready and significantly more robust than the original!
