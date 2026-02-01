import webview
import os
import argparse
import sys
import platform
import datetime
import base64
import io
import threading
import http.server
import socketserver
import socket
import subprocess
import time
import logging
import queue
import customtkinter as ctk

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

# For native Windows screenshots
if platform.system() == "Windows":
    try:
        import clr
        clr.AddReference('System.Drawing')
        clr.AddReference('System.Windows.Forms')
        from System.Drawing import Bitmap, Graphics, Imaging, Point, Size
        from System.Drawing.Imaging import ImageFormat
    except ImportError:
        clr = None

APP_TITLE = "DeepSeek - Into the Unknown"

# Verbose logging control (toggled in main based on release_mode)
VERBOSE_LOGS = True

# Global log queue for storing all log messages
log_queue = queue.Queue()
log_records = []

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

def _log(msg: str):
    global VERBOSE_LOGS, log_queue, log_records
    
    # Add to log queue and records
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {msg}"
    log_queue.put(log_entry)
    log_records.append(log_entry)
    
    # Keep only last 1000 log entries
    if len(log_records) > 1000:
        log_records = log_records[-1000:]
    
    # Always print to console for visibility with safe printing
    safe_print(msg)

# Windows-specific imports for dark titlebar
if platform.system() == "Windows":
    try:
        import ctypes
        from ctypes import wintypes
        import winreg
    except ImportError:
        ctypes = None
        wintypes = None
        winreg = None

# Global variable to store titlebar preference
titlebar_preference = 'auto'

def is_dark_mode_enabled():
    """Check if Windows is using dark mode"""
    if platform.system() != "Windows" or not winreg:
        return False
    
    try:
        # Check the registry for dark mode setting
        registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(registry_key, "AppsUseLightTheme")
        winreg.CloseKey(registry_key)
        # Value is 0 for dark mode, 1 for light mode
        return value == 0
    except (FileNotFoundError, OSError):
        # Default to light mode if we can't read the registry
        return False

def find_window_handle(window_title):
    """Find window handle by title with retry logic"""
    if platform.system() != "Windows" or not ctypes:
        return None
    
    try:
        user32 = ctypes.windll.user32
        
        # Try exact title match first
        hwnd = user32.FindWindowW(None, window_title)
        if hwnd:
            return hwnd
        
        # Try to enumerate all windows and find by partial title match
        # Define callback with proper WinAPI types
        EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, ctypes.py_object)
        def enum_windows_callback(hwnd, lst):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buffer, length + 1)
                if window_title.lower() in buffer.value.lower():
                    lst.append(hwnd)
                    return wintypes.BOOL(False)  # Stop enumeration
            return wintypes.BOOL(True)  # Continue enumeration
        
        callback = EnumWindowsProc(enum_windows_callback)
        user32.EnumWindows.argtypes = [EnumWindowsProc, ctypes.py_object]
        user32.EnumWindows.restype = wintypes.BOOL
        
        # List to store found window handle
        found_windows = []
        user32.EnumWindows(callback, ctypes.py_object(found_windows))
        
        if found_windows:
            return found_windows[0]
        
        return None
    except Exception as e:
        print(f"Error finding window handle: {e}")
        return None

def should_use_dark_titlebar():
    """Determine if dark titlebar should be used based on preference and system settings"""
    global titlebar_preference
    
    if titlebar_preference == 'dark':
        return True
    elif titlebar_preference == 'light':
        return False
    else:  # auto
        return is_dark_mode_enabled()

def apply_dark_titlebar(window):
    """Apply dark titlebar to the window on Windows"""
    if platform.system() != "Windows" or not ctypes:
        return True  # Return True on non-Windows platforms (no-op success)
    
    try:
        # Get the window handle
        hwnd = None
        
        # Try to get the window handle from different possible attributes
        if hasattr(window, 'hwnd'):
            hwnd = window.hwnd
        elif hasattr(window, '_window') and hasattr(window._window, 'hwnd'):
            hwnd = window._window.hwnd
        elif hasattr(window, 'gui') and hasattr(window.gui, 'hwnd'):
            hwnd = window.gui.hwnd
        
        # If we couldn't get it from the window object, try to find it by title
        if not hwnd:
            hwnd = find_window_handle(APP_TITLE)
        
        if hwnd:
            # Constants for DwmSetWindowAttribute
            DWMWA_USE_IMMERSIVE_DARK_MODE_NEW = 20  # Win10 1903+
            DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19  # Win10 1809 and earlier
            
            # Load dwmapi.dll
            dwmapi = ctypes.windll.dwmapi
            # Define function signature: HRESULT DwmSetWindowAttribute(HWND, DWORD, LPCVOID, DWORD)
            try:
                dwmapi.DwmSetWindowAttribute.argtypes = [
                    ctypes.c_void_p,  # HWND
                    ctypes.c_int,     # DWORD attribute
                    ctypes.c_void_p,  # LPCVOID pvAttribute
                    ctypes.c_uint     # DWORD cbAttribute
                ]
                dwmapi.DwmSetWindowAttribute.restype = ctypes.c_int  # HRESULT
            except AttributeError:
                # Older systems may not expose the symbol; keep best-effort behavior
                pass
             
            # Determine if we should use dark mode
            use_dark = should_use_dark_titlebar()
            dark_mode = ctypes.c_int(1 if use_dark else 0)
            
            # Try new attribute value first
            result = dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd),
                ctypes.c_int(DWMWA_USE_IMMERSIVE_DARK_MODE_NEW),
                ctypes.byref(dark_mode),
                ctypes.sizeof(dark_mode)
            )
            
            # Fallback to old attribute value on failure
            if result != 0:
                result = dwmapi.DwmSetWindowAttribute(
                    ctypes.c_void_p(hwnd),
                    ctypes.c_int(DWMWA_USE_IMMERSIVE_DARK_MODE_OLD),
                    ctypes.byref(dark_mode),
                    ctypes.sizeof(dark_mode)
                )
            
            if result == 0:  # S_OK
                mode_str = 'dark' if use_dark else 'light'
                source_str = f"({titlebar_preference} mode)" if titlebar_preference != 'auto' else "(system theme)"
                _log(f"Titlebar set to {mode_str} {source_str}")
                return True
            else:
                _log(f"Failed to set titlebar theme: error code {result}")
                return False
        else:
            _log("Could not find window handle for titlebar theming")
            return False
            
    except Exception as e:
        print(f"Error applying titlebar theme: {e}")
        return False

def apply_dark_titlebar_delayed(window):
    """Apply dark titlebar with a delay to ensure window is fully created"""
    import threading
    import time
    
    def delayed_apply():
        # Wait a bit for the window to be fully created
        time.sleep(0.5)
        
        # Try multiple times with progressive backoff
        for attempt in range(5):
            if apply_dark_titlebar(window):
                return  # Success, stop trying
            time.sleep(0.5 * (attempt + 1))  # Progressive backoff
        
        _log("Failed to apply dark titlebar after multiple attempts")
    
    # Run in a separate thread to avoid blocking
    thread = threading.Thread(target=delayed_apply, daemon=True)
    thread.start()

def inject_js(window):
    try:
        # Determine the base path based on whether we're running from source or frozen
        if getattr(sys, 'frozen', False):
            # Running from PyInstaller bundle
            base_path = sys._MEIPASS
        else:
            # Running from source
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        # Construct the full path to inject.js
        inject_path = os.path.join(base_path, 'injection', 'inject.js')
        
        # Read injection script
        with open(inject_path, 'r', encoding='utf-8') as f:
            js_code = f.read()
        
        # Inject JavaScript
        window.evaluate_js(js_code)
        _log(f"JavaScript injected from: {inject_path}")
    except Exception as e:
        _log(f"Error injecting JavaScript: {e}")

def on_window_loaded(window):
    """Called when window is loaded"""
    # Apply dark titlebar with delay to ensure window is fully created
    apply_dark_titlebar_delayed(window)
    # Inject original JavaScript
    inject_js(window)
    
    # Inject screenshot hotkey only in development (unfrozen) mode
    is_frozen = getattr(sys, 'frozen', False)
    if not is_frozen:
        hotkey_js = """
        console.log("DeepSeek: Screenshot hotkey active (Ctrl+Shift+S)");
        window.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.shiftKey && e.key === 'S') {
                e.preventDefault();
                console.log("Screenshot hotkey triggered (Native)");
                if (window.pywebview && window.pywebview.api) {
                    window.pywebview.api.take_screenshot().then(function(response) {
                        console.log("Screenshot response:", response);
                    });
                }
            }
        });
        """
        window.evaluate_js(hotkey_js)
    
    # Inject logs hotkey (works in both dev and frozen mode)
    logs_hotkey_js = """
    console.log("DeepSeek: Logs hotkey active (Ctrl+Shift+L)");
    window.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.shiftKey && e.key === 'L') {
            e.preventDefault();
            console.log("Logs hotkey triggered");
            if (window.pywebview && window.pywebview.api) {
                window.pywebview.api.open_logs_window().then(function(response) {
                    console.log("Logs window response:", response);
                });
            }
        }
    });
    """
    window.evaluate_js(logs_hotkey_js)

from utils.auto_update import UpdateChecker
class API:
    def __init__(self):
        self._window = None

    def get_logs(self):
        """Get all log records"""
        global log_records
        return {
            "status": "success",
            "logs": log_records
        }

    def open_logs_window(self):
        """Open a CustomTkinter window showing all logs"""
        global log_records
        
        def copy_all_logs():
            try:
                import pyperclip
                pyperclip.copy('\n'.join(log_records))
                status_label.configure(text="Copied all logs to clipboard!", text_color="green")
            except ImportError:
                status_label.configure(text="Please install pyperclip: pip install pyperclip", text_color="orange")
            except Exception as e:
                status_label.configure(text=f"Copy failed: {e}", text_color="red")
        
        def clear_logs():
            global log_records
            log_records.clear()
            text_box.delete("1.0", "end")
            status_label.configure(text="Logs cleared", text_color="green")
        
        def refresh_logs():
            text_box.delete("1.0", "end")
            text_box.insert("1.0", '\n'.join(log_records))
            status_label.configure(text=f"Showing {len(log_records)} log entries", text_color="white")
        
        def save_logs():
            try:
                filename = f"deepseek-logs-{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(log_records))
                status_label.configure(text=f"Logs saved to {filename}", text_color="green")
            except Exception as e:
                status_label.configure(text=f"Save failed: {e}", text_color="red")

        # Create the log window
        log_window = ctk.CTk()
        log_window.title("DeepSeek - Logs")
        log_window.geometry("800x600")
        
        # Set dark theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Main frame
        main_frame = ctk.CTkFrame(log_window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_label = ctk.CTkLabel(main_frame, text="DeepSeek Application Logs", font=("Inter", 16, "bold"))
        title_label.pack(pady=5)
        
        # Status label
        status_label = ctk.CTkLabel(main_frame, text=f"Showing {len(log_records)} log entries", font=("Inter", 12))
        status_label.pack(pady=2)
        
        # Button frame
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", padx=10, pady=5)
        
        # Buttons
        refresh_btn = ctk.CTkButton(button_frame, text="Refresh", command=refresh_logs, width=100)
        refresh_btn.pack(side="left", padx=5)
        
        copy_btn = ctk.CTkButton(button_frame, text="Copy All", command=copy_all_logs, width=100)
        copy_btn.pack(side="left", padx=5)
        
        save_btn = ctk.CTkButton(button_frame, text="Save to File", command=save_logs, width=100)
        save_btn.pack(side="left", padx=5)
        
        clear_btn = ctk.CTkButton(button_frame, text="Clear", command=clear_logs, width=100, fg_color="red")
        clear_btn.pack(side="left", padx=5)
        
        # Text box with scrollbar
        text_frame = ctk.CTkFrame(main_frame)
        text_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        text_box = ctk.CTkTextbox(text_frame, wrap="word", font=("Consolas", 11))
        text_box.pack(side="left", fill="both", expand=True)
        
        # Scrollbar
        scrollbar = ctk.CTkScrollbar(text_frame, command=text_box.yview)
        scrollbar.pack(side="right", fill="y")
        text_box.configure(yscrollcommand=scrollbar.set)
        
        # Initial load
        refresh_logs()
        
        # Auto-refresh every 2 seconds
        def auto_refresh():
            try:
                refresh_logs()
                log_window.after(2000, auto_refresh)
            except:
                pass  # Window closed
        
        auto_refresh()
        
        # Run the window
        log_window.mainloop()
        
        return {"status": "success", "message": "Logs window opened"}

    def get_version(self):
        """Read version from version.txt"""
        try:
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            version_path = os.path.join(base_path, 'version.txt')
            if os.path.exists(version_path):
                with open(version_path, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            _log(f"Error reading version.txt: {e}")
        return "1.0.0"

    def check_for_update(self):
        """Check for updates using the UpdateChecker"""
        try:
            checker = UpdateChecker()
            need_update, current, latest, info = checker.check_for_update(os.getcwd())
            return {
                "status": "success",
                "need_update": need_update,
                "current_version": current,
                "latest_version": latest,
                "release_notes": info.get("body", "") if info else "",
                "is_frozen": getattr(sys, 'frozen', False)
            }
        except Exception as e:
            _log(f"Error checking for update: {e}")
            return {"status": "error", "message": str(e)}

    def start_update(self):
        """Initiate the update process by launching the standalone updater"""
        _log("Initiating update...")
        try:
            launch_auto_updater()
            # The app should close itself to allow the updater to work
            if self._window:
                # Give a small delay for the updater to start
                threading.Timer(2.0, lambda: self._window.destroy()).start()
            return {"status": "success"}
        except Exception as e:
            _log(f"Error starting update: {e}")
            return {"status": "error", "message": str(e)}

    def take_screenshot(self):
        """Take a native screenshot of the window on Windows"""
        if not self._window:
            _log("API Error: Window not initialized")
            return {"status": "error", "message": "Window not initialized"}
            
        if platform.system() != "Windows" or not ctypes:
            return {"status": "error", "message": "Native screenshot only supported on Windows"}

        try:
            # Find the window handle
            hwnd = None
            if hasattr(self._window, 'hwnd'):
                hwnd = self._window.hwnd
            elif hasattr(self._window, '_window') and hasattr(self._window._window, 'hwnd'):
                hwnd = self._window._window.hwnd
            
            if not hwnd:
                hwnd = find_window_handle(APP_TITLE)
                
            if not hwnd:
                return {"status": "error", "message": "Could not find window handle"}

            # Get client area dimensions (the actual content area)
            client_rect = wintypes.RECT()
            ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(client_rect))
            
            width = client_rect.right - client_rect.left
            height = client_rect.bottom - client_rect.top
            
            if width <= 0 or height <= 0:
                return {"status": "error", "message": "Invalid window dimensions"}

            # Get the screen position of the top-left corner of the client area
            point = wintypes.POINT(0, 0)
            ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(point))

            # Capture using System.Drawing
            bmp = Bitmap(width, height)
            g = Graphics.FromImage(bmp)
            g.CopyFromScreen(Point(point.x, point.y), Point(0, 0), Size(width, height))
            
            # Ensure assets directory exists
            assets_dir = os.path.join(os.getcwd(), 'assets')
            if not os.path.exists(assets_dir):
                os.makedirs(assets_dir)
            
            # Generate filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(assets_dir, filename)
            
            # Save the image
            bmp.Save(filepath, ImageFormat.Png)
            
            # Cleanup
            g.Dispose()
            bmp.Dispose()
            
            _log(f"Native screenshot saved to: {filepath}")
            return {"status": "success", "path": filepath}
        except Exception as e:
            _log(f"Error taking native screenshot: {e}")
            return {"status": "error", "message": str(e)}

def launch_auto_updater():
    """Launch the auto-updater with enhanced search and error handling"""
    import subprocess
    
    def show_windows_error_dialog(title, message):
        """Display a native Windows error dialog using ctypes"""
        if platform.system() == "Windows" and ctypes:
            try:
                MB_ICONERROR = 0x00000010
                MB_OK = 0x00000000
                
                # Create message box
                result = ctypes.windll.user32.MessageBoxW(
                    0,  # Handle to owner window
                    message,  # Message text
                    title,  # Dialog title
                    MB_ICONERROR | MB_OK  # Style
                )
            except Exception as e:
                print(f"Failed to show Windows error dialog: {e}")
        else:
            print(f"Error: {title} - {message}")
    
    def find_updater():
        """Search for auto-updater executable or Python script in specified locations"""
        # Define search locations in order of priority
        search_locations = [
            os.getcwd(),  # Current working directory
            os.path.join(os.path.dirname(__file__), 'build'),  # build/ directory
            os.path.join(os.path.dirname(__file__), 'utils'),  # utils/ directory
            os.path.dirname(sys.executable)  # Directory of the frozen executable
        ]
        
        # Define possible updater names
        executable_names = ['auto-updater.exe']
        script_names = ['auto-updater.py', 'auto_update.py']
        
        # Check for executable first
        for location in search_locations:
            for name in executable_names:
                potential_path = os.path.join(location, name)
                if os.path.exists(potential_path):
                    return potential_path, 'executable'
        
        # If executable not found, check for Python script
        for location in search_locations:
            for name in script_names:
                potential_path = os.path.join(location, name)
                if os.path.exists(potential_path):
                    return potential_path, 'script'
        
        return None, None
    
    try:
        # Find the updater
        updater_path, updater_type = find_updater()
        
        if updater_path:
            try:
                # Prepare UTF-8 environment for subprocess
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                env['PYTHONLEGACYWINDOWSSTDIO'] = '0'  # Ensure UTF-8 stdio on Windows
                
                if updater_type == 'executable':
                    # Launch executable with UTF-8 environment
                    subprocess.Popen([updater_path], 
                                   creationflags=subprocess.CREATE_NEW_CONSOLE,
                                   env=env)
                    _log(f"Launched auto-updater executable: {updater_path}")
                else:  # script
                    # Launch Python script with appropriate flags and UTF-8 environment
                    subprocess.Popen([sys.executable, updater_path, '--auto', '--debug'], 
                                   creationflags=subprocess.CREATE_NEW_CONSOLE,
                                   env=env)
                    _log(f"Launched auto-updater script: {updater_path}")
            except Exception as launch_error:
                error_msg = f"Failed to launch auto-updater: {launch_error}"
                _log(error_msg)
                show_windows_error_dialog("Auto-Updater Launch Error", error_msg)
        else:
            error_msg = "Auto-updater not found in any of the expected locations."
            _log(error_msg)
            show_windows_error_dialog("Auto-Updater Not Found", error_msg)
            
    except Exception as e:
        error_msg = f"Unexpected error launching auto updater: {e}"
        _log(error_msg)
        show_windows_error_dialog("Auto-Updater Error", error_msg)

class DeepSeekApp:
    def __init__(self, release_mode=False):
        self.release_mode = release_mode
        self.api = API()
        self.window = None
        self.server_port = None

    def start_server(self):
        class FileHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=".", **kwargs)

            def end_headers(self):
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET')
                self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
                return super().end_headers()

            def do_GET(self):
                if self.path == '/port':
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(str(self.server.server_address[1]).encode())
                else:
                    super().do_GET()

        def find_available_port(start_port=8080):
            for port in range(start_port, start_port + 100):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    # Try to bind to the port to check availability
                    try:
                        sock.bind(("", port))
                        return port
                    except OSError:
                        continue # Port is in use, try next one
            return None

        self.server_port = find_available_port()
        if not self.server_port:
            _log("Could not find an available port for local server")
            return

        def run_server():
            with socketserver.TCPServer(("", self.server_port), FileHandler) as httpd:
                _log(f"Local server running on port {self.server_port}")
                httpd.serve_forever()

        threading.Thread(target=run_server, daemon=True).start()

    def run(self):
        self.start_server()
        
        is_frozen = getattr(sys, 'frozen', False)
        
        self.window = webview.create_window(
            APP_TITLE,
            "https://chat.deepseek.com",
            width=1200,
            height=800,
            text_select=True,
            js_api=self.api
        )
        self.api._window = self.window
        self.window.events.loaded += on_window_loaded
        
        # The update check is now handled by the UI (inject.js) 
        # which calls API.check_for_updates() and API.start_update()
        # instead of launching a background console on every startup.
        pass

        webview.start(
            private_mode=False,
            storage_path="./data",
            debug=not self.release_mode
        )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--release', action='store_true', help='Disable debug tools')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--dark-titlebar', action='store_true')
    group.add_argument('--light-titlebar', action='store_true')
    args = parser.parse_args()
    
    global titlebar_preference
    titlebar_preference = 'dark' if args.dark_titlebar else ('light' if args.light_titlebar else 'auto')
    
    is_frozen = getattr(sys, 'frozen', False)
    release_mode = args.release or is_frozen
    
    global VERBOSE_LOGS
    VERBOSE_LOGS = not release_mode
    
    app = DeepSeekApp(release_mode=release_mode)
    app.run()

if __name__ == "__main__":
    main()
