import uiautomation as auto
import win32com.client
import urllib.parse
import os
from .logger import Logger

def extract_url_from_window(hwnd):
    try:
        window = auto.ControlFromHandle(hwnd)
        potential_names = [
            "Address and search bar", "Barre d'adresse et de recherche",
            "Address", "Adresse",
            "Search with Google or enter address",
            "Rechercher avec Google ou saisir une adresse"
        ]
        for name in potential_names:
            edit = window.EditControl(Name=name, searchDepth=15) 
            if edit.Exists(maxSearchSeconds=0.05):
                val = edit.GetValuePattern().Value
                if val: return val

        try:
            edit = window.EditControl(RegexName=".*(http|https|www|localhost|://).*", searchDepth=15)
            if edit.Exists(maxSearchSeconds=0.05):
                val = edit.GetValuePattern().Value
                if val: return val
        except:
            pass

        count = 0
        for control, depth in auto.WalkControl(window, maxDepth=12):
            if control.ControlTypeName == "EditControl":
                try:
                    name = control.Name
                    if "http" in name or "www." in name or "localhost" in name:
                            if control.GetPattern(auto.PatternId.ValuePattern):
                                return control.GetValuePattern().Value
                    if control.GetPattern(auto.PatternId.ValuePattern):
                        val = control.GetValuePattern().Value
                        if val and ("." in val or "http" in val or "localhost" in val):
                            return val
                except:
                    pass
            if count > 200: break
            count += 1
    except Exception:
        pass
    return None

def get_all_explorer_paths():
    """ Returns a dictionary {hwnd: path} for all open Explorer windows. """
    paths = {}
    try:
        shell = win32com.client.Dispatch("Shell.Application")
        for window in shell.Windows():
            try:
                # 8 = Local File System?
                # or just check LocationURL
                url = window.LocationURL
                if url.lower().startswith("file:///"):
                    path_encoded = url[8:].replace("/", "\\")
                    path = urllib.parse.unquote(path_encoded)
                    if os.path.isdir(path):
                        paths[window.HWND] = path
            except:
                pass
    except Exception:
        pass
    return paths

def extract_path_from_explorer(hwnd):
    # Backward compatibility wrapper, but inefficient for loops.
    
    # Method 1: COM Interface (Shell.Application) - Best / Standard
    # DISABLED: IdentifiÃ© as cause of freeze on some systems/minimized windows.
    try:
        Logger.debug("EXTRACT: Trying COM Method...")
        shell = win32com.client.Dispatch("Shell.Application")
        for window in shell.Windows():
            try:
                if window.HWND == hwnd:
                    url = window.LocationURL
                    if url.lower().startswith("file:///"):
                        path_encoded = url[8:].replace("/", "\\")
                        path = urllib.parse.unquote(path_encoded)
                        if os.path.isdir(path):
                            return path
            except:
                pass
    except Exception:
        pass

    # Method 2: UI Automation (Fallback) - Read Address Bar
    Logger.debug("EXTRACT: Trying UIA Method...")
    try:
        window = auto.ControlFromHandle(hwnd)
        # Modern Explorer (Windows 10/11) address bar
        # Modern Explorer (Windows 10/11) address bar
        potential_names = ["Address", "Adresse", "Barre d'adresse"]
        address_bar = None
        
        for name in potential_names:
            bar = window.Control(Name=name, ControlTypeName="ToolBarControl", searchDepth=4) \
                        .EditControl(Name=name, searchDepth=3)
            if bar.Exists(0.05):
                address_bar = bar
                break
        
        if not address_bar:
             # Older styles or search deeper
             for name in potential_names:
                bar = window.Control(ControlType=auto.ControlType.EditControl, Name=name, searchDepth=5)
                if bar.Exists(0.05):
                    address_bar = bar
                    break

        if address_bar and address_bar.Exists(0.1):
             raw = address_bar.GetValuePattern().Value
             # Clean up "Address: C:\..." or "Adresse : C:\..."
             # We look for the first occurrence of a drive letter pattern or slash
             if raw:
                 # Simple heuristic: Split by ": " if present, take the last part, or regex
                 # But safer: Look for "X:\"
                 import re
                 match = re.search(r'[a-zA-Z]:\\[^<>:"/|?*]*', raw)
                 if match:
                     path = match.group(0)
                     if os.path.isdir(path): return path
                 elif os.path.isdir(raw):
                     return raw
    except Exception:
        pass

    return None

def is_incognito(hwnd=None, title=""):
    """
    Detects if a window is in Incognito/Private mode.
    If 'hwnd' is None, only strict title checks are performed.
    If 'hwnd' is provided, performs title check then deep UI check.
    """
    title_lower = title.lower()
    
    # Fast Title Checks
    if "navigation privée de mozilla firefox" in title_lower or "(private browsing)" in title_lower:
        return True
    if "(navigation privée)" in title_lower:
        return True
    if title_lower.endswith("- incognito") or title_lower.endswith("- private"):
        return True
    if " - microsoft edge inprivate" in title_lower:
        return True
    # Edge fallback "InPrivate" in title is risky without strict checks
    if "inprivate" in title_lower and "microsoft edge" in title_lower:
        return True

    # If simple check passed or HWND not provided, stop here.
    if hwnd is None:
        return False

    # FIREFOX SPECIFIC: Trust Title Only.
    # Firefox is reliable with titles ("— Navigation privée"). 
    # Deep UI scan often finds false positives (e.g. "Open Private Window" in menu).
    if "firefox" in title_lower:
        return False
        
    # Deep UI Check (Slower)
    try:
        window = auto.ControlFromHandle(hwnd)
        keywords = ["Incognito", "Privée", "InPrivate", "Private"]
        
        # Shallow search first (Top level buttons often have the text)
        for control, depth in auto.WalkControl(window, maxDepth=4):
            name = control.Name
            if not name: continue
            for k in keywords:
                if k.lower() in name.lower():
                    return True
    except:
        pass
        
    return False
