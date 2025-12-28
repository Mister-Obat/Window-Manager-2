import win32api
from difflib import SequenceMatcher

def calculate_similarity(s1, s2):
    """ Returns a similarity score between 0.0 and 1.0 """
    return SequenceMatcher(None, s1, s2).ratio()

def clean_title(title):
    if not title: return ""
    t = title.lower()
    # Strip common browser suffixes
    suffixes = [
        " - google chrome", 
        " — mozilla firefox", 
        " - mozilla firefox", 
        " - microsoft edge", 
        " — navigation privée de mozilla firefox"
    ]
    for s in suffixes:
        if t.endswith(s):
            return title[:-len(s)].strip()
    return title

def normalize_url(url):
    if not url: return None
    if url.startswith("localhost") and not url.startswith("http"):
        return "http://" + url
    if not url.startswith("http") and not url.startswith("file") and "://" not in url:
        return "https://" + url
    return url

def ensure_rect_on_screen(rect):
    """
    Ensures the given window rect is visible on at least one monitor.
    If not, moves it to the primary monitor.
    rect = [x, y, x2, y2]
    """
    try:
        x, y, r, b = rect
        w = r - x
        h = b - y
        
        # Center point of the window
        cx = x + (w // 2)
        cy = y + (h // 2)
        
        monitors = win32api.EnumDisplayMonitors()
        for monitor in monitors:
            # monitor[2] is the rect (left, top, right, bottom)
            mx, my, mr, mb = monitor[2]
            if mx <= cx <= mr and my <= cy <= mb:
                return rect # Center is inside a monitor, executed as is.

        # If we are here, the window is off-screen.
        # Reset to primary monitor (0,0) with some padding
        print(f"Window {rect} is off-screen. Resetting to primary monitor.")
        return [50, 50, 50 + w, 50 + h]
        
    except Exception as e:
        print(f"Error checking screen bounds: {e}")
        return rect
