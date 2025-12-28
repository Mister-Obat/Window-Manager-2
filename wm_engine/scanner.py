import win32gui
import win32con
import win32process
import psutil
import time
from ctypes import windll, byref, c_int, sizeof

from . import automation
from .logger import Logger

class WindowScanner:
    def __init__(self, settings_manager):
        self.settings = settings_manager
        self._cache = {} # Cache for expensive operations (URL, Incognito)

    def clear_cache(self):
        """ Clears the internal cache. Call this before a new global operation. """
        self._cache = {}

    def _is_window_allowed(self, title, class_name=None, exe=None, is_explorer=False, overrides=None):
        """ Centralized Logic for Filtering Windows """
        
        # Use overrides if provided, else fall back to global settings
        def get_setting(key, default=None):
            if overrides and key in overrides: return overrides[key]
            return self.settings.get(key, default)

        # 1. Title Based Exclusions
        exclude_list = get_setting("exclude_titles", [])
        for ex in exclude_list:
            if ex == "Window Manager":
                if title == "Window Manager": return False
            elif ex.lower() in title.lower():
                return False

        if (":\\" in title and title.lower().endswith(".exe")) or title.lower().endswith(".exe"):
            return False

        if title == "Taskbar" or title == "Mise en veille": return False

        # 2. Class Based Exclusions
        if class_name:
            if class_name in ["Windows.UI.Core.CoreWindow", "ApplicationFrameWindow", "Shell_TrayWnd"]: 
                if class_name == "Shell_TrayWnd": return False
        
        # 3. Settings Based Exclusions
        is_chrome = "Google Chrome" in title or (exe and "chrome.exe" in exe)
        is_firefox = "Mozilla Firefox" in title or (exe and "firefox.exe" in exe)
        
        if get_setting("ignore_folders") and is_explorer: return False
        if get_setting("ignore_chrome") and is_chrome: return False
        if get_setting("ignore_firefox") and is_firefox: return False
        
        if get_setting("ignore_others"):
            if not is_explorer and not is_chrome and not is_firefox:
                return False

        return True

    def get_target_windows(self, detailed_scan=False, allow_peeking=True, overrides=None):
        windows = []
        
        # Batch Pre-fetch Explorer Paths to avoid O(N*M) COM overhead
        explorer_paths_map = {}
        if detailed_scan:
             # Logger.info("SCAN: Pre-fetching Explorer paths...")
             # explorer_paths_map = automation.get_all_explorer_paths()
             # Logger.info("SCAN: Explorer paths fetched.")
             pass


        def enum_handler(hwnd, ctx):
            if not win32gui.IsWindow(hwnd): return
            if not win32gui.IsWindowVisible(hwnd): return
            
            was_peaked = False
            
            title = win32gui.GetWindowText(hwnd)
            if not title: return
            
            # Logger.info(f"SCAN: Checking window '{title}'")
            # We add logs later in the loop to include class info
            
            # Style Checks
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            owner = win32gui.GetWindow(hwnd, win32con.GW_OWNER)
            
            if ex_style & win32con.WS_EX_TOOLWINDOW: return
            if owner != 0 and not (ex_style & win32con.WS_EX_APPWINDOW): return
            
            # Cloaked Check
            try:
                DWMWA_CLOAKED = 14
                cloaked = c_int(0)
                windll.dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, byref(cloaked), sizeof(cloaked))
                if cloaked.value != 0: return
            except:
                pass

            class_name = win32gui.GetClassName(hwnd)
            # Broaden check: Class OR Title (files folders usually have this in title if not hidden extensions)
            is_explorer = (class_name == "CabinetWClass" or "Explorateur de fichiers" in title or "File Explorer" in title)

            if not self._is_window_allowed(title, class_name=class_name, is_explorer=is_explorer, overrides=overrides):
                return


            try:
                placement = win32gui.GetWindowPlacement(hwnd)
                show_cmd = placement[1]
                if win32gui.IsIconic(hwnd):
                    rect = list(placement[4])
                else:
                    rect = list(win32gui.GetWindowRect(hwnd))
            except:
                rect = [0,0,0,0]
                show_cmd = win32con.SW_SHOWNORMAL

            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            if w < 20 or h < 20: return 

            cmdline = []
            cwd = ""
            url = None
            folder_path = None
            
            exe_name = None
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = psutil.Process(pid)
                exe_name = proc.name()
                try:
                    cmdline = proc.cmdline()
                    cwd = proc.cwd()
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass
            except:
                pass
            
            # Retrieve from Cache if available
            cached_data = self._cache.get(hwnd)
            
            if detailed_scan:
                if is_explorer:
                    is_minimized = win32gui.IsIconic(hwnd)
                    try:
                        # DEBUG: Check real placement
                        wp = win32gui.GetWindowPlacement(hwnd)
                        # Logger.info(f"SCAN: Explorer identified. Class='{class_name}', Minimized={is_minimized}, WP={wp}")
                    except:
                        pass
                        # Logger.info(f"SCAN: Explorer identified. Class='{class_name}', Minimized={is_minimized}")
                    
                    # 1. CHECK CACHE FIRST (Avoid Peeking Loop)
                    cached_path = self._cache.get(hwnd, {}).get("folder_path")
                    if cached_path:
                        folder_path = cached_path
                        # Logger.debug(f"SCAN: Cache Hit for '{title}' -> {folder_path}")
                    
                    # 2. CHECK PRE-FETCH MAP
                    if not folder_path:
                        folder_path = explorer_paths_map.get(hwnd)

                    # 3. PEEK & EXTRACT (Only if missing)
                    if not folder_path:
                        # FORCE PEEK for Explorer: UI Automation fails on minimized windows, causing freeze.
                        if is_minimized:
                            try:
                                Logger.info(f"SCAN: Force un-minimizing '{title}'...")
                                win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
                                time.sleep(0.05)
                                was_peaked = True
                            except: pass

                        # Extract
                        folder_path = automation.extract_path_from_explorer(hwnd)
                        
                        if folder_path:
                             Logger.debug(f"SCAN: Explorer HWND={hwnd} Title='{title}' -> Path='{folder_path}'")
                        


                # Check precise_urls using overrides if present
                use_precise = overrides.get("precise_urls", True) if overrides and "precise_urls" in overrides else self.settings.get("precise_urls", True)
                if use_precise:
                    # Only Browser windows need URL analysis
                    if "Chrome" in title or "Firefox" in title or "Edge" in title:
                        if win32gui.IsIconic(hwnd):
                            # Optimized "Peek" for Minimized Browsers
                            # We MUST show it to get the URL, otherwise we are blind.
                            # Check cache first to avoid repeating this visual glitch.
                            # Respect 'allow_peeking' flag (False during Save).
                            if allow_peeking and not (cached_data and "url" in cached_data):
                                    try:
                                        # Logger.debug(f"Peeking at minimized browser: {title[:30]}...")
                                        win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
                                        time.sleep(0.05)
                                        was_peaked = True
                                    except: pass
                        
                        # 1. CHECK CACHE
                        if cached_data and "url" in cached_data:
                            url = cached_data["url"]
                        else:
                             # 2. COMPUTE
                             # CRITICAL FIX: Only attempt extraction if window is physically visible (not minimized),
                             # OR if we intentionally peaked at it.
                             # If we are in Save Mode (allow_peeking=False) and it is minimized, we MUST SKIP extraction
                             # to avoid implicit un-minimization by UIAutomation.
                             if not win32gui.IsIconic(hwnd) or was_peaked:
                                 t0 = time.time()
                                 url = automation.extract_url_from_window(hwnd)
                                 dt = time.time() - t0
                                 
                                 if dt > 0.1:
                                         Logger.info(f"Analyse URL ({dt:.2f}s) : {title[:50]}...")

            is_incognito = False
            if detailed_scan:
                 # Check Cache for Incognito
                 if cached_data and "is_incognito" in cached_data:
                     is_incognito = cached_data["is_incognito"]
                 else:
                     # 1. Check UI/Title First (Most Accurate for specific windows)
                     t0_inc = time.time()
                     is_incognito = automation.is_incognito(hwnd, title)
                     dt_inc = time.time() - t0_inc
                     if dt_inc > 0.1:
                          Logger.info(f"Analyse Incognito ({dt_inc:.2f}s) : {title[:50]}...")
                     
                     # 2. Check Command Line (Fallback)
                     # Only use this if UI check failed AND it's not a known browser that usually shares status
                     if not is_incognito and cmdline:
                          cmd_str = " ".join(cmdline).lower()
                          is_browser_process = any(b in cmd_str for b in ["chrome.exe", "firefox.exe", "msedge.exe"])
                          
                          # CRITIQUE: Browsers share processes. If one window is private, the process might have the flag.
                          # This corrupts the status of Normal windows sharing that process.
                          # FIX: Do NOT trust cmdline for Browsers. Trust the Title/UI only.
                          
                          if not is_browser_process: 
                              if "--incognito" in cmd_str: is_incognito = True
                              elif "-private" in cmd_str: is_incognito = True
                              elif "-inprivate" in cmd_str: is_incognito = True
                          else:
                              # BROWSER SPECIFIC FIX
                              # Visible Windows: Trust Main Logic (UI/Title). 
                              # Minimized Windows: UI Check fails (pixels not drawn). Must use CmdLine.
                              # Chrome/Edge: CmdLine is reliable (Processes usually separated).
                              # Firefox: CmdLine is UNRELIABLE (Shared Process). Trust Title even if minimized.
                              
                              if win32gui.IsIconic(hwnd):
                                   is_chrome_edge = "chrome.exe" in cmd_str or "msedge.exe" in cmd_str
                                   
                                   # PASSIVE CHECK (CmdLine)
                                   if is_chrome_edge:
                                        if "--incognito" in cmd_str or "-inprivate" in cmd_str:
                                             is_incognito = True
                                   
                                   # ACTIVE PEEK (Ultimate Truth)
                                   # If passive check failed to find flag, but we suspect it might be private (or just simply unknown)
                                   # and we are in detailed_scan mode, we MUST know.
                                   # Capturing "User said no excuse".
                                   if is_chrome_edge and not is_incognito:
                                        try:
                                            # Logger.debug(f"PEEK: Force un-minimize to check Incognito: {title}")
                                            # 1. Un-minimize without activating
                                            win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
                                            time.sleep(0.05) # Tiny delay for UI tree to update
                                            
                                            # 2. Check UI
                                            is_incognito = automation.is_incognito(hwnd, title)
                                            
                                            # 3. DO NOT Re-minimize (Optimization requested by User)
                                            # Leave it open. Restorer will deciding what to do.
                                            # win32gui.ShowWindow(hwnd, win32con.SW_SHOWMINNOACTIVE)
                                            
                                            # Mark as touched so we can cleanup later if unused
                                            was_peaked = True
                                            pass
                                        except:
                                            pass
                                    

            
            # --- RE-MINIMIZE if we peaked (Restore State) ---
            # Central location to ensure ANY peaked window is restored
            if was_peaked:
                 try:
                     # Logger.debug(f"Reminimizing peaked window: {title}")
                     win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                     # For Firefox Private, sometimes a second kick is needed?
                     if "firefox" in title.lower():
                          time.sleep(0.05)
                          if not win32gui.IsIconic(hwnd):
                               win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                 except: pass

            # Update Cache
            if detailed_scan:
                 if hwnd not in self._cache:
                      self._cache[hwnd] = {}
                 
                 # Only update if we actually computed something
                 if url is not None: self._cache[hwnd]["url"] = url
                 if folder_path is not None: self._cache[hwnd]["folder_path"] = folder_path
                 self._cache[hwnd]["is_incognito"] = is_incognito

            windows.append({
                "hwnd": hwnd, 
                "title": title,
                "target_key": "File Explorer" if is_explorer else title,
                "rect": rect,
                "show_cmd": show_cmd,
                "exe_name": exe_name,
                "cmdline": cmdline,
                "cwd": cwd,
                "url": url,
                "folder_path": folder_path,
                "is_incognito": is_incognito,
                "is_minimized": win32gui.IsIconic(hwnd), # Still report initial state? OR current?
                # If we peaked, it is PHYSICALLY visible now, but logically was minimized.
                # Matcher logic uses is_minimized to be lenient. 
                # But since we KNOW Incognito status now, we don't need leniency.
                # So report as Visible (is_minimized=False) to enforce strict matching?
                # YES.
                "is_minimized": win32gui.IsIconic(hwnd), 
                "was_peaked": was_peaked
            })
            return

        win32gui.EnumWindows(enum_handler, None)
        return windows

    def should_ignore_saved(self, saved, overrides=None):
        """ Checks if a SAVED item should be ignored based on CURRENT or OVERRIDEN settings. """
        title = saved.get("exact_title", "")
        folder = saved.get("folder_path")
        cmdline = saved.get("cmdline", [])
        exe = cmdline[0].lower() if cmdline else ""
        
        is_explorer = (folder is not None) or "explorer" in exe
        
        return not self._is_window_allowed(title, exe=exe, is_explorer=is_explorer, overrides=overrides)
