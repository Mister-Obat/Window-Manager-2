# Removed pywinauto
import uiautomation as auto
import win32gui
import win32process
import psutil
import time

def get_chrome_windows():
    chrome_windows = []
    def enum_handler(hwnd, ctx):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if "Google Chrome" in title:
                chrome_windows.append(hwnd)
    win32gui.EnumWindows(enum_handler, None)
    return chrome_windows

def inspect_window(hwnd):
    print(f"\n--- Inspecting Chrome Window HWND: {hwnd} ---")
    title = win32gui.GetWindowText(hwnd)
    print(f"Title: {title}")
    
    # Process Info
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)
        print(f"PID: {pid}")
        try:
            print(f"Cmdline: {proc.cmdline()}")
        except:
             print("Cmdline: Access Denied")
    except Exception as e:
        print(f"Process Info Error: {e}")

    # UI Automation - Look for Incognito Badge
    try:
        window = auto.ControlFromHandle(hwnd)
        print("Searching for 'Incognito' or 'Privée' elements...")
        
        # Method 1: Search by Name specifically in the top area
        # Incognito icon/text is usually in the title bar or adjacent
        
        # Let's walk the first few levels or look for specific text
        found_incognito = False
        
        # Common names for Incognito indicator in different languages
        keywords = ["Incognito", "Privée", "InPrivate", "Private"]
        
        count = 0
        for control, depth in auto.WalkControl(window, maxDepth=10):
            # Optimisation to not go too deep
            if count > 500: break 
            count += 1
            
            name = control.Name
            
            # Check for matches
            for k in keywords:
                if k.lower() in name.lower():
                    # Check if it's the actual indicator (Button or Text)
                    # Often "Incognito" is the name of the button that opens the profile menu or adjacent
                    print(f"!!! FOUND POTENTIAL INDICATOR: Name='{name}', Type='{control.ControlTypeName}'")
                    found_incognito = True
            
        if found_incognito:
            print("=> CONCLUSION: Likely Incognito")
        else:
            print("=> CONCLUSION: Likely Normal (or indicator not found)")

    except Exception as e:
        print(f"UI Automation Error: {e}")

if __name__ == "__main__":
    print("Scanning for Chrome windows...")
    windows = get_chrome_windows()
    print(f"Found {len(windows)} Chrome windows.")
    
    for hwnd in windows:
        inspect_window(hwnd)
