from wm_engine.logger import Logger
import time

print("Starting verification...")
# Give it a moment to stabilize initial timer
time.sleep(0.1)

Logger.info("First Log (Should be ~0.10s)")
time.sleep(1.0)
Logger.info("Second Log (Should be ~1.00s)")

time.sleep(0.5)
with Logger.step("Step Log (Should be prev ~0.50s)"):
    time.sleep(2.0)
# End of step should be duration ~2.00s

time.sleep(0.2)
Logger.success("Final Success (Should be ~0.20s)")
