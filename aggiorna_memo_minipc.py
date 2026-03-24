import os
from pathlib import Path
import subprocess
from datetime import datetime

# ==============================
# CONFIG BASE
# ==============================

BASE_DIR = Path(r"C:\Users\Domotix\Documents\IPTV\autoupdss")

PLAYLIST_FILE = BASE_DIR / "memo_minipc.m3u8"
BACKUP_FILE = BASE_DIR / "backup" / "memo_backup.m3u8"
LOG_FILE = BASE_DIR / "logs" / "update_log.txt"

GIT_REPO_DIR = BASE_DIR

# ==============================
# SETUP CARTELLE
# ==============================

(BASE_DIR / "backup").mkdir(exist_ok=True)
(BASE_DIR / "logs").mkdir(exist_ok=True)

# ==============================
# LOG
# ==============================

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ==============================
# BACKUP PLAYLIST
# ==============================

def backup_playlist():
    if PLAYLIST_FILE.exists():
        with open(PLAYLIST_FILE, "r", encoding="utf-8") as src:
            content = src.read()
        with open(BACKUP_FILE, "w", encoding="utf-8") as dst:
            dst.write(content)
        log("Backup creato")

# ==============================
# AGGIORNAMENTO PLAYLIST (placeholder)
# ==============================

def update_playlist():
    # QUI POI INSERIAMO LA TUA LOGICA VERA (Playwright ecc)
    log("Aggiornamento playlist (placeholder)")

# ==============================
# GIT PUSH
# ==============================

def git_push():
    try:
        subprocess.run(["git", "add", "."], cwd=GIT_REPO_DIR)

        commit_msg = f"update playlist {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=GIT_REPO_DIR)

        subprocess.run(["git", "push"], cwd=GIT_REPO_DIR)

        log("Push Git completato")

    except Exception as e:
        log(f"Errore Git: {e}")

# ==============================
# MAIN
# ==============================

def main():
    log("=== AVVIO SCRIPT ===")

    backup_playlist()
    update_playlist()
    git_push()

    log("=== FINE SCRIPT ===")

if __name__ == "__main__":
    main()