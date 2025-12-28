import time
import sys

class Logger:
    DEBUG_MODE = False # Can be toggled
    _last_log_time = time.time()

    @staticmethod
    def _get_time_delta():
        now = time.time()
        delta = now - Logger._last_log_time
        Logger._last_log_time = now
        return delta

    @staticmethod
    def info(msg, private=False):
        """ Standard user-facing log """
        delta = Logger._get_time_delta()
        prefix = "[PRIVÉ] " if private else ""
        print(f"> {prefix}{msg} ({delta:.2f}s)")

    @staticmethod
    def title(msg):
        """ Section header """
        # Reset timer so the title doesn't capture the previous gap, or maybe it should?
        # A title usually starts a new phase. Let's capture the gap to be honest.
        delta = Logger._get_time_delta() 
        print(f"\n--- {msg} --- ({delta:.2f}s)") 

    @staticmethod
    def success(msg):
        delta = Logger._get_time_delta()
        print(f"  [OK] {msg} ({delta:.2f}s)")

    @staticmethod
    def warn(msg):
        delta = Logger._get_time_delta()
        print(f"  [!] {msg} ({delta:.2f}s)")

    @staticmethod
    def error(msg):
        delta = Logger._get_time_delta()
        print(f"  [ERREUR] {msg} ({delta:.2f}s)")

    @staticmethod
    def debug(msg):
        """ Only prints if DEBUG_MODE is True """
        if Logger.DEBUG_MODE:
            # We don't update the public timer for debug logs to avoid confusing the user
            # who sees the public logs. "Gap time" should be between public logs.
            # But if we don't update, the next public log will include the time taken by debug ops.
            # That is actually CORRECT. Debug ops take time.
            print(f"  [DEBUG] {msg}")

    class Scope:
        """ Context Manager for timed steps """
        def __init__(self, msg, private=False):
            self.msg = msg
            self.private = private
            self.start_time = 0

        def __enter__(self):
            # Capture latent time before this step started
            delta = Logger._get_time_delta()
            
            prefix = "[PRIVÉ] " if self.private else ""
            # We print the delta from the PREVIOUS action here, if it's significant.
            # But usually lines look like: "> Action..." then "[OK] (Duration)"
            # If we add (Pre-lag) it might crowd it.
            # However, the user asked "entre chaque log".
            # So: "> Action... (latence: 0.5s)" ?
            # Or just "> Action... " and rely on the previous log's timestamp?
            # No, the previous log is practically gone.
            
            # User request: "avoir le temps qu'a mis l'action précédente à s'effectuer".
            # So yes, we should show it.
            print(f"  > {prefix}{self.msg} (prev: {delta:.2f}s)...", end="", flush=True)
            self.start_time = time.time()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = time.time() - self.start_time
            # Update the global timer so the NEXT log counts from NOW.
            Logger._last_log_time = time.time()
            
            if exc_type:
                print(f" [ECHEC] ({duration:.2f}s)")
            else:
                print(f" [OK] ({duration:.2f}s)")

    @staticmethod
    def step(msg, private=False):
        return Logger.Scope(msg, private)
