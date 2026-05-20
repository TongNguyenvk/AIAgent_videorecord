"""Worker exceptions for WebReel."""


class SessionExpiredError(Exception):
    """Raised when browser session is detected on login page.

    This indicates the Chrome profile cookies have expired and the user
    needs to re-login via Session Manager.
    """
    def __init__(self, message: str = "Session expired: detected login page", current_url: str = None):
        super().__init__(message)
        self.current_url = current_url