import json
import os
from pathlib import Path
import customtkinter as ctk
from core import config

SETTINGS_FILE = config.BASE_DIR / "aury_settings.json"

# Appearance
CTK_APPEARANCE = "dark"
CTK_COLOR_THEME = "blue"

# Font Map
def get_fonts():
    return {
        "heading": ctk.CTkFont(family="Inter", size=24, weight="bold"),
        "body": ctk.CTkFont(family="Inter", size=14),
        "mono": ctk.CTkFont(family="Consolas", size=13),
        "small": ctk.CTkFont(family="Inter", size=12),
        "badge": ctk.CTkFont(family="Inter", size=11, weight="bold")
    }

def get_status_color(status: str) -> str:
    mapping = {
        "completed": config.HEX_SUCCESS,
        "failed": config.HEX_ERROR,
        "stopped": config.HEX_WARNING,
        "downloading": config.HEX_PRIMARY,
        "queued": config.COLOR_DIM,
        "paused": "#ffa500"
    }
    return mapping.get(status, "#ffffff")

def load_settings() -> dict:
    default_settings = {
        "download_dir": str(config.DOWNLOAD_DIR),
        "max_workers": config.MAX_WORKERS,
        "appearance": "dark",
        "theme": "blue",
        "auto_open": False,
        "speed_limit": "0"
    }
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                default_settings.update(data)
        except:
            pass
    return default_settings

def save_settings(data: dict):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)
