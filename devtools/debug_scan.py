import win32gui
import win32process
import psutil
import os
import sys

# Add current dir to path to import engine modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from wm_engine import automation

def scan():
    print("--- DEBUG SCAN STARTED ---")
    
    def enum_handler(hwnd, ctx):
        if not win32gui.IsWindowVisible(hwnd): return
        title = win32gui.GetWindowText(hwnd)
        if not title: return
        
        # Get Process Info
        cmdline = []
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            cmdline = proc.cmdline()
        except:
            pass

        exe = cmdline[0] if cmdline else "???"
        
        # Check specific apps
        is_chrome = "chrome" in exe.lower()
        is_firefox = "firefox" in exe.lower()
        is_explorer = "explorer" in exe.lower() and win32gui.GetClassName(hwnd) == "CabinetWClass"

        if is_chrome or is_firefox or is_explorer:
            print(f"\n[WINDOW] {title}")
            print(f"  > HWND: {hwnd}")
            print(f"  > EXE: {exe}")
            print(f"  > CMDLINE: {cmdline}")
            
            if is_explorer:
                # Test Path Extraction Methods
                path_com = "FAIL"
                try: path_com = automation.extract_path_from_explorer(hwnd) or "None (COM)"
                except Exception as e: path_com = f"ERROR: {e}"
                
                print(f"  > EXPLORER PATH (Final): {path_com}")
                
                # Raw Address Bar check
                try:
                    import uiautomation as auto
                    window = auto.ControlFromHandle(hwnd)
                    address_bar = window.Control(Name="Address", ControlTypeName="ToolBarControl", searchDepth=4).EditControl(Name="Address", searchDepth=3)
                    if not address_bar.Exists(0.1):
                         address_bar = window.Control(ControlType=auto.ControlType.EditControl, Name="Address", searchDepth=5)
                    
                    if address_bar.Exists(0.1):
                        val = address_bar.GetValuePattern().Value
                        print(f"  > RAW ADDRESS BAR: '{val}'")
                    else:
                        print("  > ADDRESS BAR NOT FOUND (UI Auto)")
                except Exception as e:
                    print(f"  > RAW ADDRESS BAR ERROR: {e}")

            if is_chrome or is_firefox:
                is_inc = automation.is_incognito(hwnd, title)
                print(f"  > INCOGNITO DETECTED (UI/Title): {is_inc}")
                
                # Check flags manually
                cmd_inc = False
                cmd_str = " ".join(cmdline).lower()
                if "--incognito" in cmd_str or "-private" in cmd_str or "-inprivate" in cmd_str:
                    cmd_inc = True
                print(f"  > INCOGNITO FLAG (Cmdline): {cmd_inc}")

    win32gui.EnumWindows(enum_handler, None)
    print("\n--- DEBUG SCAN FINISHED ---")

if __name__ == "__main__":
    scan()
