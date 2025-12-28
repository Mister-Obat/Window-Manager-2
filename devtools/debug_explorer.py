import uiautomation as auto
import win32gui
import time
import win32com.client
import threading

def inspect_explorer_ui(hwnd):
    print(f"\n--- INSPECTING HWND {hwnd} ---")
    try:
        window = auto.ControlFromHandle(hwnd)
        print(f"Window Name: {window.Name}")
        
        print("Looking for Address Bar...")
        # Dump typical hierarchy
        for control, depth in auto.WalkControl(window, maxDepth=8):
             if control.ControlTypeName in ["EditControl", "ToolBarControl", "TextControl"]:
                  print(f"{'  '*depth} {control.ControlTypeName} - Name='{control.Name}' - Value='{control.GetValuePattern().Value if control.GetPattern(auto.PatternId.ValuePattern) else 'N/A'}'")
             
             if "adress" in control.Name.lower() or "address" in control.Name.lower():
                  print(f"!!! FOUND POTENTIAL MATCH: {control.Name} ({control.ControlTypeName}) !!!")
    except Exception as e:
        print(f"Error UIA: {e}")

def convert_com_path(url):
    import urllib.parse
    if url.lower().startswith("file:///"):
        path_encoded = url[8:].replace("/", "\\")
        return urllib.parse.unquote(path_encoded)
    return url

def test_com_method():
    print("\n--- TESTING COM METHOD (Threaded) ---")
    def _run():
        try:
            shell = win32com.client.Dispatch("Shell.Application")
            print(f"Shell dispatched. Windows count: {shell.Windows().Count}")
            for w in shell.Windows():
                try:
                    name = w.LocationName
                    url = w.LocationURL
                    path = convert_com_path(url)
                    print(f"COM Window: '{name}' -> '{path}'")
                except Exception as e:
                    print(f"  Error reading window: {e}")
        except Exception as e:
            print(f"COM Error: {e}")

    t = threading.Thread(target=_run)
    t.start()
    t.join(timeout=3.0)
    if t.is_alive():
        print("!!! COM METHOD FROZE (Timeout 3s) !!!")
    else:
        print("COM Method finished successfully.")

if __name__ == "__main__":
    print("Finding Explorer windows...")
    
    def enum_handler(hwnd, ctx):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetClassName(hwnd) == "CabinetWClass":
            title = win32gui.GetWindowText(hwnd)
            print(f"Found Explorer: '{title}' ({hwnd})")
            if "Games" in title or "Jeux" in title or "PC" in title:
                 inspect_explorer_ui(hwnd)
    
    win32gui.EnumWindows(enum_handler, None)
    
    test_com_method()
    print("\nDone.")
