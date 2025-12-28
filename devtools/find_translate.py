import json

with open("layouts.json", "r", encoding='utf-8') as f:
    data = json.load(f)

found = False
for name, wins in data.items():
    for w in wins:
        title = w.get("exact_title", "")
        url = w.get("url", "")
        if "translate" in title.lower() or "google" in title.lower():
            print(f"Found in '{name}': {title}")
            print(f"  Incognito: {w.get('is_incognito')}")
            print(f"  URL: {url}")
            found = True

if not found:
    print("Google Translate window NOT found in layouts.json")
