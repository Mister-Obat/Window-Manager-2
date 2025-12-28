import os
import psutil
from .utils import calculate_similarity, clean_title
from .logger import Logger

class WindowMatcher:
    GENERIC_EXECUTABLES = [
        "python.exe", "pythonw.exe", "java.exe", "javaw.exe", 
        "node.exe", "cmd.exe", "powershell.exe", "wscript.exe", "cscript.exe"
    ]

    def find_match(self, saved, current_windows, used_hwnds):
        saved_title = saved.get("exact_title", "")
        saved_url = saved.get("url")
        saved_folder = saved.get("folder_path")
        saved_cmdline = saved.get("cmdline")
        saved_exe = saved.get("cmdline")[0] if saved.get("cmdline") else ""
        saved_inc = saved.get("is_incognito", False)
        
        candidates = []

        clean_saved_title = clean_title(saved_title)

        for current in current_windows:
            if current['hwnd'] in used_hwnds:
                continue

            score = 0
            current_title = current['title']
            clean_current_title = clean_title(current_title)
            
            # --- 1. TITLE MATCH ---
            if clean_saved_title and clean_current_title and clean_saved_title.lower() == clean_current_title.lower():
                score += 50
            elif saved_title == current_title:
                 score += 50
            elif saved_title in current_title or current_title in saved_title:
                 score += 30
            
            if score < 30: 
                 sim = calculate_similarity(saved_title.lower(), current_title.lower())
                 if sim > 0.9: score += 50
                 elif sim > 0.6: score += 30

            # --- 2. EXECUTABLE MATCH ---
            current_cmdline = current.get("cmdline")
            current_exe = current_cmdline[0] if current_cmdline and len(current_cmdline) > 0 else current.get("exe_name")
            saved_exe_name = saved.get("exe_name") # If we saved it? We should have. But older saves might not have it.
            # Fallback for saved_exe
            if not saved_exe:
                 saved_exe = saved_exe_name

            if saved_exe and current_exe:
                saved_exe_base = os.path.basename(saved_exe).lower()
                current_exe_base = os.path.basename(current_exe).lower()
                
                if saved_exe_base == current_exe_base:
                    # BASE SCORE
                    # If Generic (Python, etc.), we trust it LESS initially.
                    # We require argument match to confirm.
                    if saved_exe_base in self.GENERIC_EXECUTABLES:
                        score += 10 # Weak match for generic
                    else:
                         score += 50
                    
                    # Enhanced Script/Argument Matching
                    s_args = saved_cmdline[1:] if saved_cmdline and len(saved_cmdline) > 1 else []
                    c_args = current_cmdline[1:] if current_cmdline and len(current_cmdline) > 1 else []
                    
                    if s_args and c_args:
                        def find_payload(args):
                            for a in args:
                                # Heuristic: Has extension, not a flag
                                if "." in a and not a.startswith("-") and len(a) > 2: 
                                    return os.path.basename(a).lower()
                            return None
                        
                        s_payload = find_payload(s_args)
                        c_payload = find_payload(c_args)
                        
                        if s_payload and c_payload:
                            if s_payload == c_payload:
                                 score += 60 # Boost significantly (10+60 = 70, or 50+60=110)
                            else:
                                 # Different scripts/files -> Different Apps
                                 # CRITICAL: If generic, this is a DEFINITIVE MISMATCH.
                                 if saved_exe_base in self.GENERIC_EXECUTABLES:
                                     score -= 100
                                 else:
                                     score -= 80 
                        elif s_args == c_args:
                             # Exact arg match fallback
                             score += 50
                    elif len(s_args) != len(c_args):
                         # Argument count mismatch on generic -> Likely mismatch
                         if saved_exe_base in self.GENERIC_EXECUTABLES:
                             score -= 20
            
            # --- 3. SPECIFIC CHECKS ---
            current_url = current.get("url")
            current_folder = current.get("folder_path")
            current_inc = current.get("is_incognito", False)
            is_minimized = current.get("is_minimized", False)
            
            # Incognito Check: Be lenient if minimized (detection is hard)
            if saved_inc != current_inc:
                 if is_minimized and not saved_inc: 
                     # Case: Saved=Normal, Current=Detected as Private? Or vice versa?
                     # Minimized windows often fail detection (return Normal), so we must be lenient.
                     score -= 5 # Was -20. Allow Title(+50) - 5 = 45 (> 40 Threshold)
                 elif is_minimized:
                      # If Minimized and Saved=Incognito, but Current=Normal (likely default if blind detection failing)
                      Logger.debug(f"[MATCH-REJECT] Minimized Incognito Mismatch: '{current_title}' (Penalty -100)")
                      score -= 100 # Now that detection is reliable (Active Peek), we can reject mismatches.
                 else:
                      # HARD REJECTION for visible windows with wrong Mode
                      Logger.debug(f"[MATCH-REJECT] '{current_title}' vs Saved Inc={saved_inc} / Curr Inc={current_inc} -> Penalty -120")
                      score -= 120 

            is_browser = any(b in saved_exe.lower() for b in ["chrome", "firefox", "msedge"]) if saved_exe else False
            
            if saved_folder and current_folder:
                if saved_folder.lower() == current_folder.lower():
                    score += 100
                else:
                    score -= 80
            elif saved_folder and not current_folder:
                # Critical: We expect a folder but scanner couldn't verify current path.
                # Do NOT trust generic Exe match (explorer.exe).
                # Require strict title match to avoid stealing unrelated Explorer windows.
                if clean_saved_title and clean_current_title and clean_saved_title.lower() == clean_current_title.lower():
                     # Title matches exactly (e.g. "Games" == "Games"). Acceptable risk.
                     pass 
                elif saved_title == current_title:
                     pass
                else:
                     # No path verification AND no title match. Reject.
                     # This prevents "Downloads" matching "Games" via Exe-only score (50).
                     Logger.debug(f"[MATCH-REJECT] Folder Mismatch (Blind): '{current_title}' != '{saved_title}'")
                     score -= 50 
            
            # --- Browser Strictness (NEW) ---
            # If it's a browser, we MUST have a Title Match or a URL Match.
            # Matching on Exe only ("firefox.exe" == "firefox.exe") is insufficient and dangerous.
            title_match_score = score # Capture score derived from title (0, 30, 50)
            
            if has_url_match := (saved_url and current_url and (saved_url.lower() in current_url.lower() or current_url.lower() in saved_url.lower())):
                 score += 100
            elif saved_url and current_url:
                 score -= 150 # URL mismatch
            elif is_browser and not saved_url and current_url:
                 # Saved is Blank, but Current has a URL.
                 # Check if current is effectively blank
                 normalized = current_url.lower()
                 blank_indicators = [
                     "about:newtab", "about:blank", 
                     "chrome://newtab", "chrome://new-tab-page", 
                     "edge://newtab", "edge://new-tab-page"
                 ]
                 is_effectively_blank = any(x in normalized for x in blank_indicators)
                 
                 if not is_effectively_blank:
                      # Mismatch: User wants a blank page, found a content page.
                      score -= 100
            elif is_browser and saved_url and not current_url:
                if not is_minimized:
                    score -= 5 
                    if score <= 45: # Requires title match if blind
                        score -= 100
                else:
                    # Minimized: Trust Exe/Title more.
                    # CRITICAL FIX: If minimized, we are blind to URL/Incognito in many cases.
                    # ONLY force match if the executable actually matches (or we can't tell).
                    exe_match = False
                    if saved_exe and current_exe:
                        if os.path.basename(saved_exe).lower() == os.path.basename(current_exe).lower():
                            exe_match = True
                    
                    if exe_match:
                        # CRITICAL FIX CHECK: Ensure we don't override a Hard Reject from earlier (e.g. Incognito Mismatch)
                        # The BUG was 'score < -50', but if penalty is exactly -100 or -120, we need to respect it.
                        # Let's be safer: if score is negative, don't redeem it easily.
                        if score <= -20: 
                             Logger.debug(f"[MATCH-FORCE-SKIP] '{current_title}' Ignored (Score too low: {score})")
                        else:
                             # Redemption logic: It's minimized + Exe matches -> Likely the right one?
                             # BUT WAIT. If it's a Browser, Exe match is weak (all Firefox tabs share Exe).
                             # If we have NO Title match (score ~50 from Exe only), should we redeem?
                             # No. If Title doesn't match, it's just "some firefox window".
                             # We should only redeem if Title Match was present (Score > 50).
                             
                             if is_browser and title_match_score < 30:
                                  # Exe Matches (50) but Title Mismatch (0). Total 50.
                                  # If we force this, we match "Hotmail" to "YouTube". BAD.
                                  Logger.debug(f"[MATCH-SKIP] Minimized Browser '{current_title}' has Executable match but Title mismatch.")
                                  score -= 20 # Ensure it fails
                             else:
                                  score = 90 # almost perfect match
                                  Logger.debug(f"[MATCH-FORCE] Minimized Window '{current_title}' assumed valid (Score -> 90)")
                    else:
                        score -= 50 # Executable mismatch on minimized window -> unlikely matches

            if score >= 40:
                candidates.append((score, current))
    
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
