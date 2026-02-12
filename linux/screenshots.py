import subprocess
import os
import datetime

def take_screenshot():
    """Functional Linux screenshot using 'scrot' (requires 'scrot' installed)."""
    try:
        # Ensure assets directory exists
        assets_dir = os.path.join(os.getcwd(), 'assets')
        if not os.path.exists(assets_dir):
            os.makedirs(assets_dir)
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(assets_dir, filename)
        
        # Well works but has some problems
        subprocess.run(["scrot", filepath], check=True)
        
        print(f"Linux screenshot saved to: {filepath}")
        return {"status": "success", "path": filepath}
    except FileNotFoundError:
        return {"status": "error", "message": "Screenshot failed: 'scrot' not found. Please install it (e.g., sudo apt install scrot)."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
