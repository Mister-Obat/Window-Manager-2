from wm_engine.logger import Logger
from wm_engine.engine import WindowManagerEngine
import time

# Mock Logger to force DEBUG_MODE if needed, but we used info logs.
# Mocking scanner is hard because of dependencies.
# Let's just create a dummy scanner function that mimics the logic and logging manually
# to verify the visual result.

Logger._last_log_time = time.time()

print("--- Simulating Save Layout ---")
Logger.info("Scan des fenêtres ouvertes...")
Logger.info("Début de l'analyse détaillée...")

# Simulate loop inside scanner
windows = ["Chrome", "Firefox", "Explorer", "Notepad"]

for w in windows:
    # Simulate work
    if w == "Chrome":
        time.sleep(1.2)
        # Scanner log logic
        t = 1.2
        if t > 0.1:
            Logger.info(f"Analyse URL ({t:.2f}s) : {w} - Google...")
    elif w == "Firefox":
        time.sleep(0.5)
        t = 0.5
        if t > 0.1:
             Logger.info(f"Analyse Incognito ({t:.2f}s) : {w} - Mozilla...")
    else:
        # Fast windows
        time.sleep(0.01)

Logger.info("Fin de l'analyse détaillée.")

for w in windows:
    Logger.info(f"Capturé : {w}")
