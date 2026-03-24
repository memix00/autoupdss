from pathlib import Path
import argparse
import re
import shutil
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from playwright.sync_api import sync_playwright

# ==============================
# PATH MINI PC (MODIFICATO)
# ==============================
BASE_DIR = Path(r"C:\Users\Domotix\Documents\IPTV")

PLAYLIST_FILE = BASE_DIR / "memo_mp.m3u8"
BACKUP_FILE = BASE_DIR / "memo_mp_backup.m3u8"
DEBUG_FILE = BASE_DIR / "debug_streams.txt"

BRAVE_EXE = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
BRAVE_PROFILE_PATH = r"C:\Users\Domotix\AppData\Local\BraveSoftware\Brave-Browser\User Data\Profile 1"

# ==============================
# GITHUB CONFIG (MODIFICATO)
# ==============================
GIT_MODE = "push"
GIT_REPO_DIR = BASE_DIR
GIT_BRANCH = "main"
GIT_REMOTE = "origin"
GIT_COMMIT_PREFIX = "auto-update playlist"
VERSION_FILE = BASE_DIR / "playlist_version.txt"

# ==============================
# CANALI (UGUALE)
# ==============================
LIVE_CHANNELS = {
    "La Sexta": {
        "page": "https://www.atresplayer.com/directos/lasexta",
        "tokens": ["atres-live", "lasexta_usp", ".m3u8", ".isml", "chunklist", "manifest"],
        "aliases": ["La Sexta", "laSexta"],
        "wait_ms": 3000,
    },
    "Antena 3": {
        "page": "https://www.atresplayer.com/directos/antena3",
        "tokens": ["atres-live", "antena3_usp", ".m3u8", ".isml", "chunklist", "manifest"],
        "aliases": ["Antena 3", "A3", "Antena3"],
        "wait_ms": 3000,
    },
    "Neox": {
        "page": "https://www.atresplayer.com/directos/neox",
        "tokens": ["atres-live", "neox_usp", ".m3u8", ".isml", "chunklist", "manifest"],
        "aliases": ["Neox"],
        "wait_ms": 3000,
    },
    "Mega": {
        "page": "https://www.atresplayer.com/directos/mega",
        "tokens": ["atres-live", "mega_usp", ".m3u8", ".isml", "chunklist", "manifest"],
        "aliases": ["Mega"],
        "wait_ms": 3000,
    },
    "DMAX": {
        "page": "https://dmax.marca.com/en-directo",
        "tokens": [".m3u8", ".mpd", "playlist", "manifest", "dmax", "disco"],
        "aliases": ["DMAX", "DMax"],
        "wait_ms": 8000,
        "frame_autoplay": True,
    },
    "Sardegna 1": {
        "page": "https://www.sardegna1.it/live/diretta-live/",
        "tokens": ["dmcdn.net", ".m3u8", "live-", "sardegna1"],
        "aliases": ["Sardegna 1", "Sardegna1"],
        "wait_ms": 12000,
        "frame_autoplay": True,
    },
}

VIDEOLINA = {
    "page": "https://www.videolina.it/live",
    "aliases": ["Videolina"],
    "wait_ms": 3000,
}