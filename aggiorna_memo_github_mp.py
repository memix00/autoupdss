from pathlib import Path
import argparse
import shutil
import sys
import os
import time
import subprocess
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from playwright.sync_api import sync_playwright

BASE_DIR = Path(r"C:\Users\memixtv\Documents\IPTV_auto\autoupdss")

PLAYLIST_FILE = BASE_DIR / "memo_mp.m3u8"
BACKUP_FILE = BASE_DIR / "memo_mp_backup.m3u8"
DEBUG_FILE = BASE_DIR / "debug_streams.txt"

BRAVE_EXE = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
BRAVE_USER_DATA_DIR = r"C:\Users\memixtv\AppData\Local\BraveSoftware\Brave-Browser\User Data"
BRAVE_PROFILE_DIR_NAME = "Default"

GIT_MODE = "push"
GIT_REPO_DIR = BASE_DIR
GIT_BRANCH = "main"
GIT_REMOTE = "origin"
GIT_COMMIT_PREFIX = "auto-update playlist"
VERSION_FILE = GIT_REPO_DIR / "playlist_version.txt"

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
        "tokens": [".m3u8", ".mpd", "playlist", "manifest", "dmax", "disco", "linear", "live"],
        "aliases": ["DMAX", "DMax"],
        "wait_ms": 12000,
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


def replace_channel(content: str, aliases: list[str], url: str) -> str:
    lines = content.splitlines()
    for name in aliases:
        for i, line in enumerate(lines[:-1]):
            if not line.startswith("#EXTINF:-1"):
                continue
            if name.lower() not in line.lower():
                continue
            if name.lower() in ("dmax", "dmax es", "dmax españa", "dmax espana"):
                up = line.upper()
                if "DMAX IT" in up or "DMAX ITA" in up or "DMAX ITALIA" in up:
                    continue
            lines[i + 1] = url
            print("Aggiornato:", name, flush=True)
            return "\n".join(lines)
    print("Canale non trovato nella playlist:", aliases, flush=True)
    return content


def score_url(url: str, tokens: list[str]) -> int:
    u = url.lower()
    score = 0
    for t in tokens:
        if t.lower() in u:
            score += 1
    if ".m3u8" in u:
        score += 5
    if ".mpd" in u:
        score += 4
    if "master" in u:
        score += 2
    if "playlist" in u:
        score += 2
    if "chunklist" in u:
        score += 1
    if "manifest.mpd" in u:
        score += 3
    if "linear" in u:
        score += 3
    if "live" in u:
        score += 2
    if "manifest.webmanifest" in u:
        score -= 20
    if ".json" in u or ".js" in u or ".css" in u:
        score -= 20
    if "my-ip" in u:
        score -= 5
    return score


def is_stream_candidate(url: str) -> bool:
    u = url.lower()
    if "my-ip" in u or "manifest.webmanifest" in u:
        return False
    if u.endswith(".js") or u.endswith(".css") or u.endswith(".json"):
        return False
    return any(x in u for x in [".m3u8", ".mpd", ".isml", "chunklist", "manifest"])


def validate_stream_url(url: str) -> bool:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Range": "bytes=0-1023",
        },
    )
    try:
        with urlopen(req, timeout=12) as resp:
            code = getattr(resp, "status", 200)
            return code in (200, 206)
    except HTTPError as e:
        return e.code in (200, 206, 302, 403, 405)
    except (URLError, TimeoutError, ValueError):
        return False


def close_extra_pages(context) -> None:
    try:
        pages = context.pages
        if not pages:
            return
        main = pages[0]
        for p in pages[1:]:
            try:
                p.close()
            except Exception:
                pass
        try:
            main.bring_to_front()
        except Exception:
            pass
    except Exception:
        pass


def get_single_page(context):
    close_extra_pages(context)
    pages = context.pages
    if pages:
        return pages[0]
    return context.new_page()


def launch_browser_context(p):
    context = p.chromium.launch_persistent_context(
        user_data_dir=BRAVE_USER_DATA_DIR,
        executable_path=BRAVE_EXE,
        channel=None,
        headless=False,
        slow_mo=300,
        args=[
            "--profile-directory=" + BRAVE_PROFILE_DIR_NAME,
            "--autoplay-policy=no-user-gesture-required",
            "--window-position=50,50",
            "--window-size=1366,768",
            "--mute-audio",
            "--disable-notifications",
        ],
        no_viewport=True,
    )

    try:
        context.grant_permissions([])
    except Exception:
        pass

    close_extra_pages(context)
    return context


def hard_mute_page(page) -> None:
    try:
        page.evaluate("""
            () => {
                const muteAll = (root = document) => {
                    const videos = root.querySelectorAll('video, audio');
                    for (const v of videos) {
                        try {
                            v.muted = true;
                            v.volume = 0;
                            const p = v.play?.();
                            if (p && typeof p.catch === 'function') p.catch(() => {});
                        } catch {}
                    }
                };
                muteAll(document);
                const obs = new MutationObserver(() => muteAll(document));
                obs.observe(document.documentElement || document.body, {
                    childList: true,
                    subtree: true
                });
            }
        """)
    except Exception:
        pass

    for frame in page.frames:
        try:
            frame.evaluate("""
                () => {
                    const videos = document.querySelectorAll('video, audio');
                    for (const v of videos) {
                        try {
                            v.muted = true;
                            v.volume = 0;
                            const p = v.play?.();
                            if (p && typeof p.catch === 'function') p.catch(() => {});
                        } catch {}
                    }
                }
            """)
        except Exception:
            pass


def try_autoplay(page) -> bool:
    selectors = [
        'button[aria-label*="play" i]',
        'button[title*="play" i]',
        '[data-testid*="play" i]',
        'button:has-text("Ver ahora")',
        'button:has-text("Directo")',
        'button:has-text("Play")',
        'button:has-text("Reproducir")',
        '.vjs-big-play-button',
        '.jw-display-icon-container',
        '.jw-icon-display',
        '.atresplayer-Player-buttonPlay',
        '.player-button-play',
        '.play-button',
    ]

    for sel in selectors:
        try:
            locator = page.locator(sel).first
            if locator.is_visible(timeout=1500):
                locator.click(timeout=2000, force=True)
                print(f"Autoplay: click su {sel}", flush=True)
                hard_mute_page(page)
                return True
        except Exception:
            pass

    try:
        page.mouse.click(640, 360)
        print("Autoplay: click al centro del player", flush=True)
        hard_mute_page(page)
        return True
    except Exception:
        pass

    return False


def accept_popups(page) -> None:
    selectors = [
        '#didomi-notice-agree-button',
        'button:has-text("Aceptar todo")',
        'button:has-text("Aceptar")',
        'button:has-text("Accept")',
        'button:has-text("Agree")',
        'button:has-text("Accetta")',
    ]
    for sel in selectors:
        try:
            locator = page.locator(sel).first
            if locator.is_visible(timeout=1500):
                locator.click(timeout=2000, force=True)
                print(f"Popup chiuso: {sel}", flush=True)
                page.wait_for_timeout(1000)
                break
        except Exception:
            pass


def autoplay_frames(page) -> None:
    for frame in page.frames:
        if frame == page.main_frame:
            continue
        try:
            frame.locator("button, .vjs-big-play-button, .jw-display-icon-container, .jw-icon-display").first.click(timeout=1200, force=True)
            print(f"Autoplay iframe: {frame.url}", flush=True)
        except Exception:
            pass
        try:
            frame.evaluate("""
                () => {
                    const v = document.querySelector('video, audio');
                    if (v) {
                        v.muted = true;
                        v.volume = 0;
                        v.play().catch(() => {});
                    }
                }
            """)
        except Exception:
            pass


def prepare_page(page) -> None:
    try:
        page.goto("about:blank", wait_until="load", timeout=10000)
    except Exception:
        pass


def force_page_reload(page, label: str, wait_ms: int = 3500) -> None:
    try:
        print(f"{label}: refresh automatico", flush=True)
        page.reload(wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(wait_ms)
        accept_popups(page)
        hard_mute_page(page)
    except Exception as e:
        print(f"{label}: refresh fallito -> {e}", flush=True)


def extract_live_stream(page, channel_name: str, page_url: str, tokens: list[str], wait_ms: int, frame_autoplay: bool = False) -> str:
    found_urls = []

    def add_url(url: str):
        if url and url not in found_urls:
            found_urls.append(url)

    def on_request(request):
        if is_stream_candidate(request.url):
            add_url(request.url)

    def on_response(response):
        if is_stream_candidate(response.url):
            add_url(response.url)

    page.on("request", on_request)
    page.on("response", on_response)

    try:
        prepare_page(page)
        print(f"\nApro pagina: {page_url}", flush=True)
        page.goto(page_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)

        accept_popups(page)
        hard_mute_page(page)

        autoplay_ok = try_autoplay(page)
        if not autoplay_ok:
            print(f">>> AUTOPLAY NON TROVATO: CLICCA TU SUL PLAYER ({channel_name}) <<<", flush=True)
        else:
            print(f"Autoplay tentato su {channel_name}", flush=True)

        if frame_autoplay:
            autoplay_frames(page)

        hard_mute_page(page)

        print(f"attendo {wait_ms // 1000} secondi...", flush=True)
        page.wait_for_timeout(wait_ms)

        if frame_autoplay and not found_urls:
            for _ in range(3):
                try_autoplay(page)
                autoplay_frames(page)
                hard_mute_page(page)
                page.wait_for_timeout(2500)
                if found_urls:
                    break

    finally:
        try:
            page.remove_listener("request", on_request)
        except Exception:
            pass
        try:
            page.remove_listener("response", on_response)
        except Exception:
            pass

    with DEBUG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"\n===== {channel_name} =====\n")
        for u in found_urls:
            f.write(u + "\n")

    preferred = [u for u in found_urls if is_stream_candidate(u)]
    if not preferred:
        return ""

    ranked = sorted(preferred, key=lambda x: score_url(x, tokens), reverse=True)
    fallback = ranked[0]

    for candidate in ranked[:8]:
        if validate_stream_url(candidate):
            print("Stream validato:", candidate, flush=True)
            return candidate

    print("Validazione HTTP non conclusiva, uso miglior candidato trovato", flush=True)
    return fallback


def extract_dmax_stream(page) -> str:
    found_urls = []

    def add_url(url: str):
        if url and url not in found_urls:
            found_urls.append(url)

    def is_dmax_candidate(url: str) -> bool:
        u = url.lower()
        blocked = [
            "fwmrm.net", "freewheel", "/ad/", "adaptv", "doubleclick",
            "googlesyndication", "googleads", "imasdk", "ads.", "adservice",
            "manifest.webmanifest", "my-ip",
        ]
        if any(x in u for x in blocked):
            return False
        if u.endswith(".js") or u.endswith(".css") or u.endswith(".json"):
            return False
        if ".m3u8" in u or ".mpd" in u:
            return True
        if any(x in u for x in ["dmax", "disco", "discovery", "eu1-prod", "akamai", "linear", "live", "playlist", "manifest"]):
            return True
        return False

    def dmax_score(url: str) -> int:
        u = url.lower()
        score = 0
        if ".m3u8" in u:
            score += 10
        if ".mpd" in u:
            score += 8
        if "master" in u:
            score += 4
        if "playlist" in u:
            score += 3
        if "manifest.mpd" in u:
            score += 3
        if "linear" in u:
            score += 4
        if "live" in u:
            score += 4
        if "dmax" in u:
            score += 3
        if "disco" in u or "discovery" in u:
            score += 3
        if "akamai" in u:
            score += 2
        if "fwmrm.net" in u or "freewheel" in u or "/ad/" in u:
            score -= 100
        if "vod" in u:
            score -= 8
        if ".jpg" in u or ".png" in u or "image" in u or "thumb" in u:
            score -= 20
        if ".js" in u or ".css" in u or ".json" in u:
            score -= 20
        return score

    def ranked_candidates():
        preferred = [u for u in found_urls if is_dmax_candidate(u)]
        return sorted(preferred, key=dmax_score, reverse=True)

    def pick_valid_candidate():
        ranked = ranked_candidates()
        real_streams = [u for u in ranked if ".m3u8" in u.lower() or ".mpd" in u.lower()]
        for candidate in real_streams[:15]:
            if validate_stream_url(candidate):
                print("DMAX validato:", candidate, flush=True)
                return candidate
        if real_streams:
            print("DMAX fallback stream:", real_streams[0], flush=True)
            return real_streams[0]
        return ""

    def on_request(request):
        if is_dmax_candidate(request.url):
            add_url(request.url)

    def on_response(response):
        if is_dmax_candidate(response.url):
            add_url(response.url)

    page.on("request", on_request)
    page.on("response", on_response)

    try:
        prepare_page(page)
        print("\nApro pagina: DMAX", flush=True)
        page.goto("https://dmax.marca.com/en-directo", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3500)
        accept_popups(page)
        hard_mute_page(page)

        started = try_autoplay(page)
        autoplay_frames(page)
        hard_mute_page(page)

        if started:
            print("DMAX autoplay iniziale eseguito", flush=True)
        else:
            print("DMAX autoplay non trovato al primo colpo", flush=True)

        force_page_reload(page, "DMAX", wait_ms=4500)
        try_autoplay(page)
        autoplay_frames(page)
        hard_mute_page(page)

        for i in range(40):
            page.wait_for_timeout(1000)
            hard_mute_page(page)

            best = pick_valid_candidate()
            if best:
                return best

            if i in (8, 18, 28):
                try:
                    print(f"DMAX retry autoplay #{i}", flush=True)
                    try_autoplay(page)
                    autoplay_frames(page)
                    hard_mute_page(page)
                except Exception:
                    pass

            if i == 12 and not pick_valid_candidate():
                force_page_reload(page, "DMAX secondo tentativo", wait_ms=5000)
                try_autoplay(page)
                autoplay_frames(page)
                hard_mute_page(page)

    finally:
        try:
            page.remove_listener("request", on_request)
        except Exception:
            pass
        try:
            page.remove_listener("response", on_response)
        except Exception:
            pass

    with DEBUG_FILE.open("a", encoding="utf-8") as f:
        f.write("\n===== DMAX =====\n")
        for u in found_urls:
            f.write(u + "\n")

    return pick_valid_candidate()


def extract_sardegna1_stream(page) -> str:
    found_urls = []

    def add_url(url: str):
        if url and url not in found_urls:
            found_urls.append(url)

    def is_sardegna_candidate(url: str) -> bool:
        u = url.lower()
        return ".m3u8" in u and "dmcdn.net" in u

    def on_request(request):
        if is_sardegna_candidate(request.url):
            add_url(request.url)

    def on_response(response):
        if is_sardegna_candidate(response.url):
            add_url(response.url)

    page.on("request", on_request)
    page.on("response", on_response)

    try:
        prepare_page(page)
        print("\nApro pagina: Sardegna 1", flush=True)
        page.goto("https://www.sardegna1.it/live/diretta-live/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)

        accept_popups(page)
        hard_mute_page(page)

        autoplay_ok = try_autoplay(page)
        if autoplay_ok:
            print("Autoplay tentato su Sardegna 1", flush=True)
        else:
            print(">>> AUTOPLAY NON TROVATO: CLICCA TU SUL PLAYER (Sardegna 1) <<<", flush=True)

        autoplay_frames(page)
        hard_mute_page(page)

        for _ in range(24):
            preferred = [
                u for u in found_urls
                if "dmcdn.net" in u.lower()
                and ".m3u8" in u.lower()
                and "live-" in u.lower()
            ]
            if preferred:
                for u in preferred:
                    if "live-720.m3u8" in u.lower() and validate_stream_url(u):
                        return u
                for u in preferred:
                    if validate_stream_url(u):
                        return u
                return preferred[0]

            page.wait_for_timeout(500)
            hard_mute_page(page)

    finally:
        try:
            page.remove_listener("request", on_request)
        except Exception:
            pass
        try:
            page.remove_listener("response", on_response)
        except Exception:
            pass

    with DEBUG_FILE.open("a", encoding="utf-8") as f:
        f.write("\n===== Sardegna 1 =====\n")
        for u in found_urls:
            f.write(u + "\n")

    preferred = [
        u for u in found_urls
        if "dmcdn.net" in u.lower()
        and ".m3u8" in u.lower()
        and "live-" in u.lower()
    ]
    if preferred:
        for u in preferred:
            if "live-720.m3u8" in u.lower() and validate_stream_url(u):
                return u
        for u in preferred:
            if validate_stream_url(u):
                return u
        return preferred[0]

    return ""


def extract_videolina_stream(page) -> str:
    found_urls = []

    def add_url(url: str):
        if url and url not in found_urls:
            found_urls.append(url)

    def on_request(request):
        url = request.url.lower()
        if ".m3u8" in url or "dmcdn.net" in url:
            add_url(request.url)

    def on_response(response):
        url = response.url.lower()
        if ".m3u8" in url or "dmcdn.net" in url:
            add_url(response.url)

    page.on("request", on_request)
    page.on("response", on_response)

    try:
        prepare_page(page)
        print("\nApro pagina: Videolina", flush=True)
        page.goto(VIDEOLINA["page"], wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)
        hard_mute_page(page)
        try_autoplay(page)
        hard_mute_page(page)
        page.wait_for_timeout(3000)
    finally:
        try:
            page.remove_listener("request", on_request)
        except Exception:
            pass
        try:
            page.remove_listener("response", on_response)
        except Exception:
            pass

    with DEBUG_FILE.open("a", encoding="utf-8") as f:
        f.write("\n===== Videolina =====\n")
        for u in found_urls:
            f.write(u + "\n")

    preferred = [
        u for u in found_urls
        if "dmcdn.net" in u.lower()
        and ".m3u8" in u.lower()
        and "live-" in u.lower()
    ]
    if preferred:
        for u in preferred:
            if "live-720.m3u8" in u.lower() and validate_stream_url(u):
                return u
        for u in preferred:
            if validate_stream_url(u):
                return u
        return preferred[0]

    return ""


def update_version_file() -> str:
    from datetime import datetime
    version = datetime.now().strftime("%Y%m%d-%H%M%S")
    VERSION_FILE.write_text(version + "\n", encoding="utf-8")
    print(f"Versione playlist aggiornata: {version}", flush=True)
    return version


def run_git_command(args: list[str]) -> None:
    result = subprocess.run(
        args,
        cwd=str(GIT_REPO_DIR),
        text=True,
        capture_output=True,
        shell=False,
    )
    if result.stdout:
        print(result.stdout.strip(), flush=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Comando git fallito")


def publish_playlist_to_github(mode: str, version: str) -> None:
    if mode == "none":
        print("Push GitHub disattivato", flush=True)
        return
    if mode != "push":
        raise ValueError(f"Modalita GitHub non valida: {mode}")

    run_git_command([
        "git", "add",
        str(PLAYLIST_FILE.name),
        str(BACKUP_FILE.name),
        str(DEBUG_FILE.name),
        str(VERSION_FILE.name),
    ])

    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(GIT_REPO_DIR),
        text=True,
        capture_output=True,
        shell=False,
    )
    if status.returncode != 0:
        raise RuntimeError(status.stderr.strip() or "Impossibile leggere git status")

    if not status.stdout.strip():
        print("Nessuna modifica da pubblicare su GitHub", flush=True)
        return

    commit_message = f"{GIT_COMMIT_PREFIX} {version}"
    run_git_command(["git", "commit", "-m", commit_message])
    run_git_command(["git", "push", GIT_REMOTE, GIT_BRANCH])
    print("Playlist pubblicata su GitHub", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggiorna la playlist TV e opzionalmente la pubblica su GitHub")
    parser.add_argument(
        "--github",
        choices=["none", "push"],
        default=GIT_MODE,
        help="Modalita pubblicazione GitHub",
    )
    return parser.parse_args()


def force_close_runtime(context=None, page=None, playwright=None) -> None:
    try:
        if page:
            page.goto("about:blank", wait_until="load", timeout=8000)
    except Exception:
        pass

    try:
        if page:
            page.close()
    except Exception:
        pass

    try:
        close_extra_pages(context)
    except Exception:
        pass

    try:
        if context:
            context.close()
    except Exception:
        pass

    try:
        if playwright:
            playwright.stop()
    except Exception:
        pass

    time.sleep(1)


def main() -> int:
    args = parse_args()
    DEBUG_FILE.write_text("", encoding="utf-8")

    if not PLAYLIST_FILE.exists():
        print("Playlist non trovata", flush=True)
        return 1

    shutil.copy2(PLAYLIST_FILE, BACKUP_FILE)
    content = PLAYLIST_FILE.read_text(encoding="utf-8", errors="ignore")

    context = None
    page = None
    playwright = None

    try:
        playwright = sync_playwright().start()
        context = launch_browser_context(playwright)
        page = get_single_page(context)

        for channel_name, cfg in LIVE_CHANNELS.items():
            if channel_name in ("Sardegna 1", "DMAX"):
                continue

            print("\n======", channel_name, "======", flush=True)
            stream = extract_live_stream(
                page,
                channel_name,
                cfg["page"],
                cfg["tokens"],
                cfg["wait_ms"],
                cfg.get("frame_autoplay", False),
            )
            if stream:
                print("Trovato stream:", flush=True)
                print(stream, flush=True)
                content = replace_channel(content, cfg["aliases"], stream)
            else:
                print("stream non trovato", flush=True)

        print("\n====== DMAX ======", flush=True)
        dstream = extract_dmax_stream(page)
        if dstream:
            print("Trovato stream:", flush=True)
            print(dstream, flush=True)
            content = replace_channel(content, LIVE_CHANNELS["DMAX"]["aliases"], dstream)
        else:
            print("stream non trovato", flush=True)

        print("\n====== Sardegna 1 ======", flush=True)
        sstream = extract_sardegna1_stream(page)
        if sstream and validate_stream_url(sstream):
            print("Trovato stream:", flush=True)
            print(sstream, flush=True)
            content = replace_channel(content, ["Sardegna 1", "Sardegna1"], sstream)
        else:
            print("stream NON trovato -> mantengo quello attuale (Sardegna 1)", flush=True)

        print("\n====== Videolina ======", flush=True)
        vstream = extract_videolina_stream(page)
        if vstream:
            print("Trovato stream:", flush=True)
            print(vstream, flush=True)
            content = replace_channel(content, VIDEOLINA["aliases"], vstream)
        else:
            print("stream non trovato", flush=True)

        PLAYLIST_FILE.write_text(content, encoding="utf-8")
        print("\nPlaylist aggiornata", flush=True)

        try:
            version = update_version_file()
            publish_playlist_to_github(args.github, version)
        except Exception as e:
            print(f"GitHub: errore durante la pubblicazione -> {e}", flush=True)

        print("Script completato, uscita pulita", flush=True)
        return 0

    except Exception as e:
        print(f"Errore fatale: {e}", flush=True)
        return 1

    finally:
        force_close_runtime(context, page, playwright)


if __name__ == "__main__":
    code = main()
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass
    time.sleep(1)
    os._exit(code)
