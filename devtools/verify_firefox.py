from window_engine import WindowManagerEngine
import os
import win32gui

# Create a temporary layout file for the engine init
layout_file = os.path.join(os.getcwd(), "test_layout.json")
engine = WindowManagerEngine(layout_file)

print("\n--- Scanning Firefox Windows ---")
windows = engine.get_target_windows(detailed_scan=True)
firefox_found = False

for w in windows:
    if "Mozilla Firefox" in w['title']:
        firefox_found = True
        is_private = w.get('is_incognito', False)
        status = "[PRIVATE]" if is_private else "[NORMAL]"
        print(f"Firefox Window: '{w['title']}' => {status}")
        
        # Diagnostics if not detected but should be
        if not is_private:
             pass 

if not firefox_found:
    print("No Firefox windows found. Please open a Firefox Private window.")
