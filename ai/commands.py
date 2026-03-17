# ai/commands.py
from datetime import datetime
import webbrowser

def run_command(text):
    """Check for built-in commands."""
    if "time" in text:
        return datetime.now().strftime("The time is %H:%M")
    if "youtube" in text:
        webbrowser.open("https://youtube.com")
        return "Opening YouTube..."
    if "google" in text:
        webbrowser.open("https://google.com")
        return "Opening Google..."
    return None