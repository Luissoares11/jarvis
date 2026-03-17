from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

MEMORY_FILE = DATA_DIR / "memory.json"

HOST = "0.0.0.0"
PORT = 8000