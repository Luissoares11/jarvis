import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

MEMORY_FILE = os.getenv("MEMORY_FILE", "data/memory")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
FOOTBALL_KEY = os.getenv("FOOTBALL_DATA_API_KEY")

HOST = "0.0.0.0"
PORT = 8000