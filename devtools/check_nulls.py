import json

with open("layouts.json", "r", encoding='utf-8') as f:
    data = json.load(f)

for name, windows in data.items():
    print(f"--- {name} ---")
    for w in windows:
        if w.get("url") is None and "explorer" not in w.get("cmdline", [""])[0].lower():
            print(f"NULL URL: {w.get('exact_title')} | Cmd: {w.get('cmdline')}")
