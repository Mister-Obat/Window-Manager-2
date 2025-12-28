import json
import os

class SettingsManager:
    def __init__(self, settings_file):
        self.settings_file = settings_file
        self.settings = self.load_settings()

    def load_settings(self):
        default_settings = {
            "precise_urls": True,
            "restore_minimized": True,
            "ignore_folders": False,
            "ignore_chrome": False,
            "ignore_firefox": False,
            "ignore_others": False,
            "exclude_titles": [
                "Program Manager", "Microsoft Text Input Application", "Settings", "Paramètres",
                "Window Manager", "Calculatrice", "Nvidia Share", "Windows Input Experience",
                "Expérience d’entrée Windows", "tk", "monitorwindows", "monitor windows",
                "TclNotifier", "Launchpad", "Battery Watcher", "WinEventWindow", "WUIconWindow",
                "BroadcastListenerWindow", "UxdService", "MS_WebcheckMonitor", "MiracastConnectionWindow",
                "FNForMonitorMic", "NvSvc", "LMIGuardianSvc_hidden", "Task Host Window",
                "Dépassement de capacité", "Détails", "Démarrage", "Google Drive", "Survey",
                "Présence en temps réel"
            ]
        }
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    data = json.load(f)
                    # Merge with default to ensure all keys exist
                    for key, val in default_settings.items():
                        if key not in data:
                            data[key] = val
                    return data
            except Exception as e:
                print(f"Error loading settings: {e}")
        return default_settings

    def save_settings(self, new_settings):
        self.settings = new_settings
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f, indent=4)
            # Logger check? circular import risk if Logger uses Engine...
            # Logger is standalone? Yes.
            from .logger import Logger
            Logger.info("Settings saved successfully.")
        except Exception as e:
            print(f"Error saving settings: {e}")
            from .logger import Logger
            Logger.error(f"Error saving settings: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def get_slot_settings(self, index):
        slots = self.settings.get("slots", {})
        return slots.get(str(index), {}) # Return empty dict if not set (fallback to globals)

    def set_slot_settings(self, index, slot_data):
        if "slots" not in self.settings:
            self.settings["slots"] = {}
        
        self.settings["slots"][str(index)] = slot_data
        self.save_settings(self.settings)
    def get_ui_slots(self, count=5):
        # Default initialization if missing
        if "ui_slots" not in self.settings:
             return []
        
        slots = self.settings["ui_slots"]
        # Ensure it has enough items? No, UI handles defaults.
        return slots

    def set_ui_slot(self, index, name):
        if "ui_slots" not in self.settings:
            self.settings["ui_slots"] = [""] * 5 # Init with empty strings
        
        current_slots = self.settings["ui_slots"]
        # Expand if needed
        while len(current_slots) <= index:
            current_slots.append("")
        
        current_slots[index] = name
        self.settings["ui_slots"] = current_slots
        self.save_settings(self.settings)
