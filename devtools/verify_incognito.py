from window_engine import WindowManagerEngine
import os

# Create a temporary layout file for the engine init
layout_file = os.path.join(os.getcwd(), "test_layout.json")

print("Initializing WindowManagerEngine...")
engine = WindowManagerEngine(layout_file)

print("\nScanning windows...")
windows = engine.get_target_windows(detailed_scan=True)

print("\n--- Detection Results ---")
found_incognito = False
for w in windows:
    is_incognito = w.get('is_incognito', False)
    status = " [INCOGNITO]" if is_incognito else ""
    if is_incognito: found_incognito = True
    
    print(f"HWND: {w['hwnd']} | Title: {w['title']}{status}")
    if is_incognito:
        print(f"   => URL: {w.get('url', 'N/A')}")
        print(f"   => EXE: {w.get('cmdline')[0] if w.get('cmdline') else 'N/A'}")

print(f"\nTotal Windows: {len(windows)}")
if found_incognito:
    print("SUCCESS: Incognito window detected!")
else:
    print("WARNING: No Incognito window detected (Verify one is actually open).")
