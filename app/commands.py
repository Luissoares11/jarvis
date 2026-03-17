from datetime import datetime
import webbrowser


def run_command(text: str):
    """Built-in commands."""
    if "time" in text:
        return datetime.now().strftime("The time is %H:%M")

    if "youtube" in text:
        webbrowser.open("https://youtube.com")
        return "Opening YouTube..."

    if "google" in text:
        webbrowser.open("https://google.com")
        return "Opening Google..."

    return None