import json
import os

class LayoutStorage:
    def __init__(self, layout_file):
        self.layout_file = layout_file
        self.layouts = self.load_layouts()

    def load_layouts(self):
        if os.path.exists(self.layout_file):
            try:
                with open(self.layout_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading layouts: {e}")
                return {}
        return {}

    def save_layouts(self, layouts):
        self.layouts = layouts
        try:
            with open(self.layout_file, "w") as f:
                json.dump(self.layouts, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving layouts: {e}")
            return False

    def get_layout(self, name):
        # Hot reload to ensure latest disk state
        self.layouts = self.load_layouts()
        data = self.layouts.get(name)
        
        # Backward Compatibility: Convert List to V2 Dict
        if isinstance(data, list):
            return {"windows": data, "settings": {}}
        return data

    def set_layout(self, name, data):
        # Data logic: If we are saving just a list (old code), wrap it?
        # Or assumes caller now sends the full dict?
        # Let's be safe: If data is list, wrap it.
        if isinstance(data, list):
             # Try to preserve existing settings
             existing = self.get_layout(name)
             settings = existing.get("settings", {}) if existing else {}
             data = {"windows": data, "settings": settings}
             
        self.layouts[name] = data
        return self.save_layouts(self.layouts)

    def get_layout_settings(self, name):
         data = self.get_layout(name)
         if data: return data.get("settings", {})
         return {}

    def set_layout_settings(self, name, settings):
         data = self.get_layout(name)
         # If doesn't exist, create empty struct
         if not data:
              data = {"windows": [], "settings": settings}
         else:
              data["settings"] = settings
         
         self.layouts[name] = data
         return self.save_layouts(self.layouts)

    def rename_layout(self, old_name, new_name):
        # Refresh first
        self.layouts = self.load_layouts()
        if old_name in self.layouts:
            self.layouts[new_name] = self.layouts.pop(old_name)
            return self.save_layouts(self.layouts)
        return False
