import threading
import time
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import logging

class ClipboardWatcher:
    """Watches the clipboard for valid HTTP URLs and cleans them."""
    
    def __init__(self, callback):
        self.callback = callback
        self.running = False
        self._thread = None
        self._last_clipboard = ""
        
        self.recent_url = None
        self.recent_time = 0
        
        try:
            import pyperclip
            self.pyperclip = pyperclip
            self._has_clipboard = True
        except ImportError:
            logging.warning("pyperclip not installed. Clipboard watching disabled.")
            self._has_clipboard = False

    def start(self):
        if not self._has_clipboard:
            return
        self.running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def _watch_loop(self):
        while self.running:
            try:
                current_clipboard = (self.pyperclip.paste() or "").strip()
                if current_clipboard != self._last_clipboard:
                    self._last_clipboard = current_clipboard
                    if current_clipboard.startswith("http://") or current_clipboard.startswith("https://"):
                        # Clean it
                        cleaned, is_cleaned = self.clean_url(current_clipboard)
                        
                        self.recent_url = cleaned
                        self.recent_time = time.time()
                        
                        # Trigger UI callback
                        self.callback(cleaned, is_cleaned)
            except Exception:
                pass # ignore clipboard access errors
                
            time.sleep(2)

    def get_recent_url(self, window_seconds=5) -> str | None:
        """Returns the recent URL if it was copied within `window_seconds`."""
        if self.recent_url and (time.time() - self.recent_time) <= window_seconds:
            url = self.recent_url
            self.recent_url = None # consume it
            return url
        return None

    @staticmethod
    def clean_url(raw_url: str) -> tuple[str, bool]:
        """
        Strips tracking parameters from a URL.
        Returns (cleaned_url, was_cleaned_boolean).
        Retains: v, list, index, t
        Strips: si, utm_*, feature, etc.
        """
        parsed = urlparse(raw_url)
        query_params = parse_qsl(parsed.query, keep_blank_values=True)
        
        allowed_keys = {'v', 'list', 'index', 't'}
        
        cleaned_params = []
        was_cleaned = False
        
        for k, v in query_params:
            if k in allowed_keys:
                cleaned_params.append((k, v))
            else:
                was_cleaned = True
                
        if not was_cleaned:
            return raw_url, False
            
        new_query = urlencode(cleaned_params)
        
        # Reconstruct URL
        parts = list(parsed)
        parts[4] = new_query
        
        cleaned_url = urlunparse(parts)
        return cleaned_url, True
