#!/usr/bin/env python3
"""
Media Automation Pipeline CLI
Handles video encoding, subtitle acquisition, metadata fetching, and file renaming.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────

PATHS = {
    "gm":         Path("/datadisk/daily/gm"),
    "gm_aac":     Path("/datadisk/daily/gm/audio/aac"),
    "gm_eac3":    Path("/datadisk/daily/gm/audio/eac3"),
    "daily":      Path("/datadisk/daily"),
    "1080":       Path("/datadisk/daily/1080"),
    "1080T2":     Path("/datadisk/daily/1080/1080T2"),
    "cn":         Path("/datadisk/daily/cn"),
    "animelink":  Path("/datadisk/daily/gm/animelink.txt"),
    "cr_dl":      Path("/datadisk/unshackle/unshackle/downloads"),
    "unshackle":  Path("/datadisk/uckl/unshackle"),
    "numgen_dir": Path("/diskdata/winbackup/Desktop/mpd/pythonsubtools"),
    "bili_app":   Path("/diskdata/winbackup/Desktop/mpd/bilibilidownloader/app.py"),
    "bili_out":   Path("/diskdata/winbackup/Desktop/mpd/bilibilidownloader/animeBiliBili"),
    "bili_airing":Path("/diskdata/winbackup/Desktop/mpd/bilibilidownloader/animeBiliBili/Airing"),
}

LOG_FILE = Path.home() / ".pipeline_session.json"

# ─── Platform → extracksub flag mapping ───────────────────────────────────────

PLATFORM_FLAGS = [
    (re.compile(r'\bDSNP\b'),                    '-D'),   # Disney+
    (re.compile(r'\bABMA\b'),                    '-AB'),  # ABema
    (re.compile(r'\bHIDI\b'),                    '-H'),   # Hidive
    (re.compile(r'\bAMZN\b'),                    '-a'),   # Amazon
    (re.compile(r'\b(CR|RC)\b'),                 '-c'),   # Crunchyroll
    (re.compile(r'\b(iQ|IQ|ADN)\b'),             '-q'),   # iQIYI / ADN
    (re.compile(r'\bNF\b'),                      '-n'),   # Netflix
]

# Regex matching a fully-renamed file.
# Handles both normal:  ShowTitle_EP05_09153055.mkv
#   and paren-ep form:  Detective Conan Year 25_EP1258(1200)_09153055.mkv
# Also accepts a trailing _NNN / _NNNp / _NNNN / _NNNNp resolution suffix
# (e.g. _1080, _1080p, _720p, _2160p).
# Also accepts platform-tag suffixes: _NF / _CR / _DSNP / _AB / _HIDIVE / _AMZN / _IQ
RENAMED_MKV_RE = re.compile(
    r'^.+_EP\d{2,4}(?:\(\d+\))?_\d+'
    r'(?:_\d{3,4}[pP]?|_(?:NF|CR|DSNP|AB|HIDIVE|AMZN|IQ))?'
    r'\.mkv$',
    re.IGNORECASE
)

# Matches resolution variants to EXCLUDE from the "primary renamed" list.
# Covers _720p, _1080p, _2160p  AND  the bare _720, _1080, _2160 form.
RESOLUTION_RE  = re.compile(r'_(?:720|1080|2160)[pP]?\.mkv$', re.IGNORECASE)

# Regex for the parenthetical-episode format used in numbers.json entries
# e.g. "Detective Conan Year 25_EP1258(1200)"
PAREN_EP_NAME_RE = re.compile(r'^(.+?)_EP(\d+)\((\d+)\)$', re.IGNORECASE)

# Maps platform suffix → extracksub flag (used at process time)
_PLAT_SUFFIX_FLAG = {
    'NF':    '-n',
    'CR':    '-c',
    'DSNP':  '-D',
    'AB':    '-AB',
    'HIDIVE':'-H',
    'AMZN':  '-a',
    'IQ':    '-q',
}
_PLAT_SUFFIX_RE = re.compile(
    r'_(NF|CR|DSNP|AB|HIDIVE|AMZN|IQ)$', re.IGNORECASE
)


def detect_platform_flag(filename: str) -> str | None:
    for pattern, flag in PLATFORM_FLAGS:
        if pattern.search(filename):
            return flag
    return None


# ─── Bilibili timeline cache ───────────────────────────────────────────────────

BILI_CACHE_MAX_AGE = 4 * 3600

def _bili_cache_path(lang):
    return PATHS["gm"] / f".pipeline_bili_cache_{lang}.json"

def load_bili_cache(lang="th"):
    cache_file = _bili_cache_path(lang)
    if not cache_file.exists():
        return None
    try:
        with open(cache_file) as f:
            cache = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    age = datetime.now().timestamp() - cache.get("timestamp", 0)
    if age > BILI_CACHE_MAX_AGE:
        return None
    return cache.get("ids", [])

def save_bili_cache(ids, lang="th"):
    with open(_bili_cache_path(lang), "w") as f:
        json.dump({"timestamp": datetime.now().timestamp(), "ids": ids}, f)

def fetch_bili_timeline_ids(force=False, lang="th"):
    if not force:
        cached = load_bili_cache(lang)
        if cached is not None:
            info(f"bili {lang} timeline: using cache ({len(cached)} IDs)")
            return cached

    url = f"https://www.bilibili.tv/{lang}/timeline"
    info(f"fetching Bilibili {lang} timeline...")
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "th,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        ids = list(dict.fromkeys(re.findall(
            r'//www\.bilibili\.tv/[a-z]{2}/play/(\d+)', html
        )))

        if not ids:
            warn(f"no IDs found in {lang} timeline HTML — page structure may have changed")
            return []

        save_bili_cache(ids, lang)
        ok(f"bili {lang} timeline: fetched {len(ids)} show IDs, cached for 4h")
        return ids

    except Exception as e:
        warn(f"bili {lang} timeline fetch failed: {e}")
        cache_file = _bili_cache_path(lang)
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    stale = json.load(f).get("ids", [])
                if stale:
                    warn(f"using stale {lang} cache as fallback ({len(stale)} IDs)")
                    return stale
            except Exception:
                pass
        return []


def fetch_bili_timeline_title_ids(lang="en"):
    url = f"https://www.bilibili.tv/{lang}/timeline"
    info(f"fetching Bilibili {lang} timeline for title matching...")
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9,th;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        warn(f"timeline fetch failed: {e}")
        return {}

    id_title = {}
    card_blocks = re.findall(
        r'href="//www\.bilibili\.tv/[a-z]{2}/play/(\d+)"[^>]*>.*?'
        r'bstar-video-card__title-text[^>]*>(.*?)<',
        html, re.DOTALL
    )
    for series_id, raw_title in card_blocks:
        title = re.sub(r'<[^>]+>', '', raw_title).strip()
        if title:
            id_title[series_id] = title

    if not id_title:
        ids    = re.findall(r'href="//www\.bilibili\.tv/[a-z]{2}/play/(\d+)"', html)
        titles = re.findall(r'bstar-video-card__title-text[^>]*>\s*(.*?)\s*</', html, re.DOTALL)
        titles = [re.sub(r'<[^>]+>', '', t).strip() for t in titles if t.strip()]
        for sid, title in zip(ids, titles):
            if sid not in id_title and title:
                id_title[sid] = title

    info(f"parsed {len(id_title)} title→ID entries from {lang} timeline")
    return id_title


def match_bili_series_id(anilist_titles, lang="en"):
    id_title = fetch_bili_timeline_title_ids(lang=lang)
    if not id_title:
        return None

    def _norm(text):
        return re.sub(r'[^\w]', '', text).lower()

    norm_known = [_norm(t) for t in anilist_titles if t]

    best_id    = None
    best_score = 0
    best_title = ""

    for series_id, card_title in id_title.items():
        norm_card = _norm(card_title)
        for nk in norm_known:
            if norm_card == nk:
                info(f"exact match: '{card_title}' → ID {series_id}")
                return series_id
            tokens = [t for t in re.split(r'\s+', card_title.lower()) if len(t) > 1]
            if not tokens:
                continue
            overlap = sum(1 for t in tokens if t in nk)
            score   = overlap / len(tokens)
            if score > best_score:
                best_score = score
                best_id    = series_id
                best_title = card_title

    if best_id and best_score >= 0.5:
        info(f"best match ({best_score:.0%}): '{best_title}' → ID {best_id}")
        return best_id
    return None


# ─── Colours ──────────────────────────────────────────────────────────────────

class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"
    DIM    = "\033[2m"

def ok(msg):   print(f"{C.GREEN}[ok]{C.RESET}  {msg}")
def info(msg): print(f"{C.BLUE}[info]{C.RESET} {msg}")
def warn(msg): print(f"{C.YELLOW}[warn]{C.RESET} {msg}")
def err(msg):  print(f"{C.RED}[err]{C.RESET}  {msg}", file=sys.stderr)
def cmd(msg):  print(f"{C.DIM}$ {msg}{C.RESET}")
def head(msg): print(f"\n{C.BOLD}{C.CYAN}{'─'*50}{C.RESET}\n{C.BOLD}{msg}{C.RESET}\n")

def prompt(msg, default=None):
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"{C.YELLOW}?{C.RESET}  {msg}{suffix}: ").strip()
        return val or default
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(0)

# ─── Session log ──────────────────────────────────────────────────────────────

def load_session():
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            data = json.load(f)
        data.setdefault("originals", {})
        return data
    return {
        "source":    None,
        "route":     None,
        "romaji":    None,
        "episode":   None,
        "id":        None,
        "originals": {},
        "log":       [],
    }

def save_session(session):
    with open(LOG_FILE, "w") as f:
        json.dump(session, f, indent=2)

def log_event(session, msg):
    session["log"].append({"time": datetime.now().isoformat(), "msg": msg})
    save_session(session)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def run(command, cwd=None, check=True):
    cmd(command)
    result = subprocess.run(command, shell=True, cwd=cwd, text=True)
    if check and result.returncode != 0:
        err(f"command failed with exit code {result.returncode}")
        raise SystemExit(result.returncode)
    return result

def find_latest(directory, pattern):
    matches = sorted(Path(directory).glob(pattern), key=os.path.getmtime, reverse=True)
    return matches[0] if matches else None

def extract_season(filename):
    """Return zero-padded season number from a filename.

    Checks (in order):
      1. Standard SxxExx notation  — S02E04  → "02"
      2. "Season N" / "SeasonN" in the title  — Season2 / Season 2  → "02"
    Falls back to "01" if neither is found.
    """
    # S02E04 / s2e4 style
    m = re.search(r'[Ss](\d+)[Ee]\d+', filename)
    if m:
        return m.group(1).zfill(2)
    # "Season 2" / "Season2" embedded in show title
    m = re.search(r'[Ss]eason\s*(\d+)', filename)
    if m:
        return m.group(1).zfill(2)
    return "01"

def extract_episode(filename):
    m = re.search(r'[Ss]\d+[Ee](\d+)', filename)
    if m:
        return m.group(1).zfill(2)
    m = re.search(r'_EP(\d+)_', filename)
    if m:
        return m.group(1).zfill(2)
    m = re.search(r'[-_\s](\d{2,3})[-_\s.]', filename)
    if m:
        return m.group(1).zfill(2)
    return None

def pick_mkv(gm_mkvs, label="target"):
    if not gm_mkvs:
        return None
    gm_mkvs = sorted(gm_mkvs, key=lambda f: f.name.lower())
    if len(gm_mkvs) == 1:
        info(f"{label}: {gm_mkvs[0].name}")
        return gm_mkvs[0]
    print(f"  multiple .mkv files — pick the {label}:")
    for i, f in enumerate(gm_mkvs, 1):
        print(f"  {C.CYAN}{i}{C.RESET}  {f.name}")
    pick = prompt("choice", "1")
    try:
        chosen = gm_mkvs[int(pick) - 1]
        info(f"{label}: {chosen.name}")
        return chosen
    except (ValueError, IndexError):
        err("invalid selection")
        return None

_STOP_WORDS = {
    "the", "and", "of", "in", "a", "an", "to", "for", "on", "at",
    "by", "or", "is", "its", "my", "me", "we", "s01", "s02", "s03",
    "rc", "cr", "nf", "web", "dl", "aac", "h264", "x264", "x265",
    "mkv", "mks", "repack", "multi", "dual", "sub", "subs",
}

def show_tokens_from(stem):
    clean = re.split(r'[Ss]\d+[Ee]\d+', stem)[0]
    clean = re.split(r'[.\-_]\d{3,4}[pP]', clean)[0]
    return [
        t.lower() for t in re.split(r'[.\-_ ]+', clean)
        if len(t) > 1 and t.lower() not in _STOP_WORDS
    ]

def best_match_files(files, tokens, name_fn=lambda f: f.name):
    def score(f):
        name = name_fn(f).lower()
        return sum(1 for t in tokens if t in name)
    scored = sorted(files, key=score, reverse=True)
    top = score(scored[0]) if scored else 0
    return [f for f in scored if score(f) == top] if top > 0 else files

def read_clipboard():
    cmds = [
        "wl-paste --no-newline",
        "wl-paste",
        "xclip -selection clipboard -o",
        "xsel --clipboard --output",
    ]
    for clip_cmd in cmds:
        try:
            result = subprocess.run(
                clip_cmd, shell=True, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            continue
    return None

def run_numgen(title_ep):
    """Run numgen.py interactively via stdin, wait for it to finish,
    then read the result from the clipboard.

    numgen.py writes output like:  Awajima Hyakkei_EP04_09153055_
    We parse the 8-digit ID from that string.
    """
    info(f"running numgen.py  ←  '{title_ep}'")
    try:
        safe = title_ep.replace("'", r"'\''")
        shell_cmd = (
            f"echo '{safe}' | "
            f"script -q -c 'python3 numgen.py' /dev/null"
        )
        subprocess.run(
            shell_cmd, shell=True,
            cwd=str(PATHS["numgen_dir"]),
            timeout=20,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        warn("numgen.py timed out")
        return None
    except Exception as e:
        warn(f"numgen.py launch failed: {e}")
        return None

    time.sleep(0.5)

    clipboard = read_clipboard()
    if not clipboard:
        warn("clipboard is empty after numgen.py — is wl-paste / xclip installed?")
        return None

    info(f"clipboard: {clipboard}")

    m = re.search(r'_EP\d+\(\d+\)_(\d+)_?$', clipboard)
    if m:
        return m.group(1)

    m = re.search(r'_EP\d+_(\d+)_?$', clipboard)
    if m:
        return m.group(1)

    m = re.search(r'\b(\d{8})\b', clipboard)
    if m:
        return m.group(1)

    warn(f"could not parse ID from clipboard: {clipboard}")
    return None

# ─── mediainfo height helper ──────────────────────────────────────────────────

def get_video_height(filepath):
    """Return video height as a plain string ('1080', '720', …) via mediainfo.

    Returns None if mediainfo is unavailable or the file has no video track.
    """
    try:
        result = subprocess.run(
            f'mediainfo --Inform="Video;%Height%" "{filepath}"',
            shell=True, capture_output=True, text=True, timeout=10
        )
        height = result.stdout.strip()
        if height.isdigit():
            return height+"p"
        # mediainfo can return e.g. "1 920" with a space on some builds
        height_clean = height.replace(" ", "").replace("\n", "")
        if height_clean.isdigit():
            return height_clean+"p"
    except Exception as e:
        warn(f"mediainfo failed for {Path(filepath).name}: {e}")
    return None

def is_av1(filepath):
    """Return True if the file's video track is encoded in AV1."""
    try:
        result = subprocess.run(
            f'mediainfo --Inform="Video;%Format%" "{filepath}"',
            shell=True, capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip().upper() == "AV1"
    except Exception as e:
        warn(f"mediainfo format check failed for {Path(filepath).name}: {e}")
    return False

# ─── Internal subtitle-type probe ─────────────────────────────────────────────

def detect_internal_sub_type(filepath):
    """Return 'srt', 'ass', 'mixed', or None (no text tracks).

    Uses mediainfo to list every Text track's Format.
    NF encodes SRT / UTF-8 tracks; most other platforms use ASS/SSA.
    """
    try:
        result = subprocess.run(
            f'mediainfo --Inform="Text;%Format%\\n" "{filepath}"',
            shell=True, capture_output=True, text=True, timeout=10
        )
        formats = [
            ln.strip().upper()
            for ln in result.stdout.strip().splitlines()
            if ln.strip()
        ]
        if not formats:
            return None
        srt_like = {'UTF-8', 'SRT', 'SUBRIP'}
        ass_like = {'ASS', 'SSA', 'ADVANCED SSA'}
        if all(f in srt_like for f in formats):
            return 'srt'
        if all(f in ass_like for f in formats):
            return 'ass'
        return 'mixed'
    except Exception as e:
        warn(f"subtitle-type probe failed for {Path(filepath).name}: {e}")
        return None

# ─── Rename helper — tracks original→new in session ──────────────────────────

def do_renames(renames, session):
    """Execute a list of (src_name, dst_name) renames inside PATHS['gm'].

    Records every successful rename in session['originals'] so phase_process
    can later recover which streaming service produced each file.
    """
    originals = session.setdefault("originals", {})
    for src_name, dst_name in renames:
        src = PATHS["gm"] / src_name
        dst = PATHS["gm"] / dst_name
        if src.exists():
            src.rename(dst)
            originals[dst_name] = src_name
            ok(f"{src_name} → {dst_name}")
        else:
            warn(f"not found: {src_name}")
    save_session(session)


def pick_mkv_table(mkvs, label="target"):
    """Display MKV files as a formatted table and return the chosen file."""
    if not mkvs:
        return None
    mkvs = sorted(mkvs, key=lambda f: f.name.lower())
    if len(mkvs) == 1:
        info(f"{label}: {mkvs[0].name}")
        return mkvs[0]

    # ── Build table rows ──────────────────────────────────────────────────────
    rows = []
    for f in mkvs:
        ep  = extract_episode(f.name) or "—"
        plat_flag = detect_platform_flag(f.name)
        plat = {
            "-D": "DSNP", "-AB": "ABEMA", "-H": "HIDIVE",
            "-a": "AMZN", "-c": "CR/RC", "-q": "iQ/ADN", "-n": "NF",
        }.get(plat_flag, "—")
        if "_mux" in f.name:
            status = "mux"
        elif RENAMED_MKV_RE.match(f.name):
            status = "renamed"
        else:
            status = "orig"
        rows.append((f, ep, plat, status))

    # ── Column widths ─────────────────────────────────────────────────────────
    max_name = min(max(len(f.name) for f, *_ in rows), 72)
    w_ep     = max(len(r[1]) for r in rows)
    w_plat   = max(len(r[2]) for r in rows)
    w_status = max(len(r[3]) for r in rows)
    w_num    = len(str(len(rows)))

    # ── Box chars ─────────────────────────────────────────────────────────────
    TL, TR, BL, BR = "┌", "┐", "└", "┘"
    VL, HR         = "│", "─"
    ML, MR, MC     = "├", "┤", "┼"
    TM, BM         = "┬", "┴"

    def hr_row(left, mid, right, fill="─"):
        segs = [
            fill * (w_num + 2),
            fill * (max_name + 2),
            fill * (w_ep + 2),
            fill * (w_plat + 2),
            fill * (w_status + 2),
        ]
        return left + mid.join(segs) + right

    def data_row(num, name, ep, plat, status, num_col=None):
        name_str = (name[:max_name - 1] + "…") if len(name) > max_name else name
        n_col = num_col if num_col else f"{C.CYAN}{str(num).rjust(w_num)}{C.RESET}"
        status_col = {
            "mux":     f"{C.GREEN}{'mux'.center(w_status)}{C.RESET}",
            "renamed": f"{C.YELLOW}{'renamed'.center(w_status)}{C.RESET}",
            "orig":    f"{C.DIM}{'orig'.center(w_status)}{C.RESET}",
        }.get(status, status.center(w_status))
        return (
            f"{VL} {n_col} "
            f"{VL} {name_str:<{max_name}} "
            f"{VL} {ep.center(w_ep)} "
            f"{VL} {plat.center(w_plat)} "
            f"{VL} {status_col} {VL}"
        )

    print()
    print("  " + hr_row(TL, TM, TR))
    hdr = (
        f"{VL} {'#'.center(w_num)} "
        f"{VL} {'filename':<{max_name}} "
        f"{VL} {'ep'.center(w_ep)} "
        f"{VL} {'platform'.center(w_plat)} "
        f"{VL} {'status'.center(w_status)} {VL}"
    )
    print("  " + hdr)
    print("  " + hr_row(ML, MC, MR))
    for i, (f, ep, plat, status) in enumerate(rows, 1):
        print("  " + data_row(i, f.name, ep, plat, status))
    print("  " + hr_row(BL, BM, BR))
    print()

    pick = prompt(f"select {label}", "1")
    try:
        chosen = mkvs[int(pick) - 1]
        info(f"{label}: {chosen.name}")
        return chosen
    except (ValueError, IndexError):
        err("invalid selection")
        return None

# ─── Phase 1: Encoding ────────────────────────────────────────────────────────

SOURCE_MAP = {
    "1": ("/datadisk/daily/",             "vidori.sh",              "AV1 720p"),
    "2": ("/datadisk/daily/1080/",        "auto-boost_2.5_1080.py", "AV1 1080p"),
    "3": ("/datadisk/daily/1080/1080T2/", "vidori1080p8crf30.sh",   "AV1 1080p crf30"),
    "4": ("/datadisk/daily/cn/",          "cnvid.sh",               "CN animation"),
}

def phase_encode(session):
    head("Phase 1 — Video Encoding")
    print("Select source directory:")
    for key, (path, script, label) in SOURCE_MAP.items():
        print(f"  {C.CYAN}{key}{C.RESET}  {path}  {C.DIM}({label}){C.RESET}")
    print()

    choice = prompt("choice", "1")
    if choice not in SOURCE_MAP:
        err(f"invalid choice: {choice}")
        return

    src_dir, script, label = SOURCE_MAP[choice]
    session["source"] = src_dir
    save_session(session)

    input_file = prompt("input .mkv filename")
    if not input_file:
        err("no filename provided")
        return

    info(f"source : {Path(src_dir) / input_file}")
    info(f"script : {script}  ({label})")

    if script == "vidori.sh":
        run_cmd = "./vidori.sh"
    elif script == "auto-boost_2.5_1080.py":
        run_cmd = f'python3 auto-boost_2.5_1080.py -i "{input_file}" -gpu'
    elif script == "vidori1080p8crf30.sh":
        run_cmd = "./vidori1080p8crf30.sh"
    else:
        run_cmd = "./cnvid.sh"

    run(run_cmd, cwd=src_dir)

    if choice == "2":
        info("cleaning hidden folders in 1080p dir...")
        run("find /datadisk/daily/1080/ -maxdepth 1 -name '.*' -type d -exec rm -rf {} +", check=False)
        run("./vidori1080p4crf30r3.sh", cwd="/datadisk/daily/1080/")

    mux_name = input_file.replace(".mkv", "_mux.mkv")
    mux_src  = Path(src_dir) / mux_name
    mux_dst  = PATHS["gm"] / mux_name

    if mux_src.exists():
        shutil.move(str(mux_src), str(mux_dst))
        ok(f"moved {mux_name} → {PATHS['gm']}/")
        log_event(session, f"encoded: {mux_name} → {PATHS['gm']}/")
    else:
        warn(f"expected output not found: {mux_src} — move manually")

# ─── Phase 2A: Bilibili ───────────────────────────────────────────────────────

PV_RE = re.compile(r'(?<![A-Za-z0-9])PV(?![A-Za-z0-9])', re.IGNORECASE)

# Matches sub stem with either normal or paren-ep episode field.
# Group 1 = base title, Group 2 = full ep string (e.g. "1258(1200)" or "05")
_SUB_STEM_RE = re.compile(
    r'^(.+?)_EP(\d+(?:\(\d+\))?)_(\d+)$', re.IGNORECASE
)

def _bili_folder_id(folder_name):
    m = re.search(r'_(\d{5,})$', folder_name)
    return m.group(1) if m else None

def phase_bili(session):
    head("Phase 2A — Bilibili Subtitle Route")

    info("starting Bilibili Flask app...")
    subprocess.Popen(f"/usr/bin/python3 {PATHS['bili_app']}", shell=True)
    print(f"  {C.DIM}open http://127.0.0.1:5000, submit your URL, then press Enter{C.RESET}")
    input("  ")
    subprocess.run("fuser -k 5000/tcp", shell=True, stderr=subprocess.DEVNULL)
    info("stopped Flask app (port 5000)")

    mux_mkvs = sorted(
        [f for f in PATHS["gm"].glob("*.mkv") if "_mux" in f.name],
        key=lambda f: f.name.lower()
    )
    if not mux_mkvs:
        err("no _mux .mkv files in gm/ — run encode phase first")
        return

    target_mkv = mux_mkvs[0] if len(mux_mkvs) == 1 else pick_mkv(mux_mkvs, "target mkv for subtitle")
    if not target_mkv:
        return

    ep_num = extract_episode(target_mkv.name)
    info(f"episode: {ep_num or '(not detected)'}")
    if not ep_num:
        err("could not detect episode number")
        return

    info("querying AniList for show titles...")
    anilist_titles = fetch_anilist_all_titles(target_mkv.stem)
    if anilist_titles:
        info(f"AniList titles: {' | '.join(anilist_titles)}")
    else:
        warn("AniList returned no titles")
        anilist_titles = []

    series_id = match_bili_series_id(anilist_titles, lang="en")
    if not series_id:
        info("no EN match — trying TH timeline...")
        series_id = match_bili_series_id(anilist_titles, lang="th")
    if not series_id:
        warn("could not auto-match show to Bilibili timeline")
        warn(f"known titles: {anilist_titles}")
        series_id = prompt("enter Bilibili series ID manually (or leave blank to abort)")
        if not series_id:
            err("no series ID — aborting")
            return

    info(f"series ID: {series_id}")

    search_dirs = []
    if PATHS["bili_airing"].exists():
        search_dirs.append(PATHS["bili_airing"])
    if PATHS["bili_out"].exists():
        search_dirs.append(PATHS["bili_out"])

    target_folder = None
    for sdir in search_dirs:
        target_folder = next(
            (d for d in sdir.iterdir() if d.is_dir() and _bili_folder_id(d.name) == series_id),
            None
        )
        if target_folder:
            break

    if not target_folder:
        warn(f"no folder found with ID {series_id} in Airing/ or bili_out/")
        all_dirs = []
        for sdir in search_dirs:
            all_dirs.extend(sorted(
                [d for d in sdir.iterdir() if d.is_dir()],
                key=lambda d: d.name.lower()
            ))
        tokens = show_tokens_from(target_mkv.stem)
        if all_dirs and tokens:
            scored = sorted(all_dirs,
                            key=lambda d: sum(1 for t in tokens if t in d.name.lower()),
                            reverse=True)
        else:
            scored = all_dirs

        if not scored:
            err("no subtitle folders found at all — aborting")
            return

        print(f"  pick the subtitle folder:")
        for i, d in enumerate(scored[:20], 1):
            print(f"  {C.CYAN}{i}{C.RESET}  {d.name}  {C.DIM}({d.parent.name}){C.RESET}")
        pick = prompt("choice", "1")
        try:
            target_folder = scored[int(pick) - 1]
        except (ValueError, IndexError):
            err("invalid selection — aborting")
            return

    info(f"matched folder: {target_folder.name}")

    ep_int     = str(int(ep_num))
    ep_pattern = re.compile(rf'(?<!\d)({re.escape(ep_num)}|{re.escape(ep_int)})(?!\d)')

    def _is_sub(f):
        return f.suffix.lower() in (".srt", ".ass")

    def _ep_subs_in(root):
        return [
            f for f in root.rglob("*")
            if _is_sub(f) and not PV_RE.search(f.stem) and ep_pattern.search(f.stem)
        ]

    candidates = _ep_subs_in(target_folder)

    if not candidates:
        warn(f"no ep{ep_num} subtitle in '{target_folder.name}' — widening search to all download dirs")
        for sdir in search_dirs:
            candidates = _ep_subs_in(sdir)
            if candidates:
                info(f"found subtitle(s) under {sdir}")
                break

    chosen_sub = None
    if len(candidates) == 1:
        chosen_sub = candidates[0]
    elif len(candidates) > 1:
        candidates.sort(key=lambda f: (f.suffix.lower() != ".ass", f.name.lower()))
        chosen_sub = candidates[0]
        info(f"multiple subtitles matched — using: {chosen_sub.name}")

    if not chosen_sub:
        warn(f"no subtitle found for episode {ep_num} — showing manual picker")
        pool_roots = [target_folder] + search_dirs
        non_pv = sorted(
            {f for root in pool_roots for f in root.rglob("*")
             if _is_sub(f) and not PV_RE.search(f.stem)},
            key=lambda f: f.name.lower()
        )
        pool = non_pv or sorted(
            {f for root in pool_roots for f in root.rglob("*") if _is_sub(f)},
            key=lambda f: f.name.lower()
        )
        if not pool:
            err("no subtitle files (.srt/.ass) found anywhere — aborting")
            return
        if not non_pv:
            warn("only PV subtitles found — showing as last resort")
        print("  pick subtitle file:")
        for i, f in enumerate(pool, 1):
            print(f"  {C.CYAN}{i}{C.RESET}  {f.name}  {C.DIM}({f.parent.name}){C.RESET}")
        pick = prompt("choice", "1")
        try:
            chosen_sub = pool[int(pick) - 1]
        except (ValueError, IndexError):
            err("invalid selection — aborting")
            return

    info(f"subtitle: {chosen_sub.name}")
    dst_sub = PATHS["gm"] / chosen_sub.name
    shutil.copy(str(chosen_sub), str(dst_sub))
    ok(f"copied subtitle → {dst_sub.name}")

    # ── Parse title, ep_display, and ID from subtitle stem ───────────────────
    #
    # The subtitle stem may use the normal form   ShowTitle_EP05_12345678
    # or the paren-ep form                        ShowTitle_EP1258(1200)_12345678
    #
    # When the paren form is detected we use the FULL ep field from the subtitle
    # (e.g. "1258(1200)") instead of the bare episode number extracted from the
    # mkv, because the display-episode part is only available in the sub stem.

    sub_stem = chosen_sub.stem
    # Capture the BiliBili lang-tag so we can preserve it in the renamed file
    # e.g. "_0_tha_BiliBiliTH"  or  "_tha_BiliBiliTH"
    _bili_tag_m = re.search(r'(_\d+_[a-z]{2,3}_Bili\w+)$', sub_stem, re.IGNORECASE)
    if not _bili_tag_m:
        _bili_tag_m = re.search(r'(_[a-z]{2,3}_Bili\w+)$', sub_stem, re.IGNORECASE)
    bili_lang_tag = _bili_tag_m.group(1) if _bili_tag_m else ""
    sub_stem = re.sub(r'_\d+_[a-z]{2,3}_Bili\w+$', '', sub_stem, flags=re.IGNORECASE)
    sub_stem = re.sub(r'_[a-z]{2,3}_Bili\w+$',     '', sub_stem, flags=re.IGNORECASE)

    m_sub = _SUB_STEM_RE.match(sub_stem)
    if m_sub:
        bili_title  = m_sub.group(1).strip()
        ep_display  = m_sub.group(2)          # "1258(1200)" or "05"
        gen_id      = m_sub.group(3)
    else:
        bili_title  = re.sub(r'_EP\d.*$', '', sub_stem).strip()
        m_id        = re.search(r'_EP\d+(?:\(\d+\))?_(\d+)', sub_stem)
        gen_id      = m_id.group(1) if m_id else series_id
        # Fall back: use ep_num from mkv for the display field
        ep_display  = ep_num

    info(f"title    : {bili_title}")
    info(f"ep field : {ep_display}")
    info(f"id       : {gen_id}")

    base     = f"{bili_title}_EP{ep_display}_{gen_id}"
    tokens   = show_tokens_from(target_mkv.stem)
    gm_files = list(PATHS["gm"].glob("*.mkv"))
    matched  = best_match_files(gm_files, tokens)

    orig_file = next((f for f in matched if "_mux" not in f.name), None)
    mux_file  = next((f for f in matched if "_mux"     in f.name), None)

    # ── Height detection: only mux file gets resolution suffix ───────────────
    mux_h = get_video_height(mux_file) if mux_file else None
    info(f"mediainfo height (mux) : {mux_h or 'n/a'}")

    renames = []
    if orig_file:
        renames.append((orig_file.name, f"{base}.mkv"))
    if mux_file:
        suffix = f"_{mux_h}.mkv" if mux_h else ".mkv"
        renames.append((mux_file.name, f"{base}{suffix}"))

    sub_ext = chosen_sub.suffix.lower()
    renames.append((dst_sub.name, f"{base}{bili_lang_tag}{sub_ext}"))

    info("renaming:")
    do_renames(renames, session)

    session.update({"route": "bilibili", "romaji": bili_title,
                    "episode": ep_display, "id": gen_id})
    log_event(session, f"renamed (bili): {base}")

# ─── Shared title + ID resolver ──────────────────────────────────────────────

def resolve_title_and_id(stem, ep_num, anilist_search=None, anilist_raw=False, allow_manual=True):
    """Resolve canonical show title then get or generate the episode ID.

    Returns a 3-tuple: (romaji, gen_id, ep_display)

    * romaji      – the base show title (e.g. "Detective Conan Year 25")
    * gen_id      – the 8-digit numgen ID string
    * ep_display  – the string to embed in the filename; for most shows this
                    equals ep_num, but for long-running shows that use the
                    parenthetical format it will be e.g. "1258(1200)".
    """
    romaji = None

    cached_title, _ignored, confidence = search_numbers_json(stem)
    if confidence == 'high':
        ok(f"numbers.json title hit (high): '{cached_title}'")
        romaji = cached_title
    elif confidence == 'low':
        warn(f"numbers.json partial match: '{cached_title}'")
        ans = prompt("use this title? (y/n)", "y")
        if ans and ans.lower().startswith('y'):
            romaji = cached_title
            info(f"using cached title: {romaji}")
        else:
            info("falling through to AniList...")

    if romaji is None:
        info("querying AniList...")
        search = anilist_search or stem
        al_romaji, all_results = fetch_anilist(search, raw=anilist_raw)
        romaji = confirm_anilist_title(al_romaji, all_results, allow_manual=allow_manual)

        if not romaji:
            err("no title — aborting")
            return None, None, None

        info(f"re-checking numbers.json for: '{romaji}'")
        cached_title2, _ignored2, confidence2 = search_numbers_json(romaji)
        if confidence2 == 'high':
            ok(f"numbers.json canonical spelling: '{cached_title2}'")
            romaji = cached_title2
        elif confidence2 == 'low':
            warn(f"numbers.json partial match on AniList title: '{cached_title2}'")
            ans2 = prompt("use this numbers.json title? (y/n)", "y")
            if ans2 and ans2.lower().startswith('y'):
                romaji = cached_title2
                info(f"using numbers.json title: {romaji}")

    # ── Paren-ep detection (e.g. Detective Conan Year 25_EP1258(1200)) ───────
    #
    # Some long-running shows store episodes in numbers.json using both a
    # display-episode counter and the original air-order number in parentheses.
    # Detect this format and, if applicable, override ep_display and the numgen
    # call string accordingly.

    paren_base, ep_display, numgen_string, direct_id = find_paren_ep_info(romaji, ep_num)

    if paren_base:
        # Update romaji to the more specific year-title found in numbers.json
        # (e.g. "Detective Conan" → "Detective Conan Year 25")
        romaji = paren_base

        if direct_id:
            ok(f"numbers.json paren-ep hit: '{numgen_string}' → ID {direct_id}")
            return romaji, direct_id, ep_display

        info(f"running numgen.py with paren-ep string: '{numgen_string}'")
        gen_id = run_numgen(numgen_string)
        if gen_id:
            ok(f"generated ID: {gen_id}")
        else:
            gen_id = prompt("ID (numgen.py returned nothing)")
        return romaji, gen_id, ep_display

    # ── Normal path ───────────────────────────────────────────────────────────
    ep_display = ep_num   # default: filename ep == display ep

    exact_title, exact_id = lookup_numbers_exact(romaji, ep_num)
    if exact_id:
        ok(f"numbers.json exact match EP{ep_num}: '{exact_title}' → ID {exact_id}  (numgen skipped)")
        return exact_title, exact_id, ep_display

    info("running numgen.py...")
    gen_id = run_numgen(f"{romaji}_EP{ep_num}")
    if gen_id:
        ok(f"generated ID: {gen_id}")
    else:
        gen_id = prompt("ID (numgen.py returned nothing)")

    return romaji, gen_id, ep_display


# ─── Phase 2B: Crunchyroll + AniList ─────────────────────────────────────────

def phase_cr(session):
    head("Phase 2B — Crunchyroll / AniList Route")

    cr_url = None
    if PATHS["animelink"].exists():
        with open(PATHS["animelink"]) as f:
            lines = [l.strip() for l in f if l.strip()]
        if len(lines) == 1:
            cr_url = lines[0]
            info(f"CR URL (auto): {cr_url}")
        elif len(lines) > 1:
            for i, u in enumerate(lines, 1):
                print(f"  {C.CYAN}{i}{C.RESET}  {u}")
            choice = prompt("select URL number", "1")
            try:
                cr_url = lines[int(choice) - 1]
            except (ValueError, IndexError):
                pass

    if not cr_url:
        cr_url = prompt("crunchyroll URL (leave blank to search downloads/ for matching .mks)")

    skip_download = not cr_url

    if skip_download:
        info("no URL — skipping unshackle, will search downloads/ for best-matching .mks")

    # Include both _mux files and already-renamed files (a previous phase may
    # have renamed the target mkv before CR phase runs).
    all_mkvs = sorted(PATHS["gm"].glob("*.mkv"), key=lambda f: f.name.lower())
    if not all_mkvs:
        err("no .mkv files in gm/ — run encode phase first")
        return
    target_mkv = all_mkvs[0] if len(all_mkvs) == 1 else pick_mkv_table(all_mkvs, "target mkv to rename")
    if not target_mkv:
        return
    orig_filename = target_mkv.name

    # ── Subtitle-only fast-path ───────────────────────────────────────────────
    # Triggered when the selected target_mkv is already in the final naming
    # format (e.g. after Phase 2C nosub, or a previous bili/CR run).
    # In this case we read the base name directly from the filename and skip
    # all MKV renaming — only the subtitle file gets renamed.
    #
    # This handles the "Kill Blue" scenario: NF source file was renamed by
    # Phase 2C to  KILL BLUE_EP04_28972281_NF.mkv  and must not be touched when
    # looping back to Phase 2B to pick up a CR subtitle.
    sub_only_mode = False
    romaji = ep_display = gen_id = None

    if RENAMED_MKV_RE.match(target_mkv.name):
        # Strip optional resolution suffix (_1080p, _720p, _1080, …) and
        # platform tag suffix (_NF, _CR, …) before parsing the canonical
        # Title_EPnn_id components.
        stem_clean = re.sub(r'_\d{3,4}[pP]?$', '', target_mkv.stem)
        stem_clean = _PLAT_SUFFIX_RE.sub('', stem_clean)
        m_existing = re.match(
            r'^(.+?)_EP(\d+(?:\(\d+\))?)_(\d+)$', stem_clean, re.IGNORECASE
        )
        if m_existing:
            romaji        = m_existing.group(1).strip()
            ep_display    = m_existing.group(2)
            gen_id        = m_existing.group(3)
            sub_only_mode = True
            ok(f"already-renamed target detected — subtitle-only mode")
            ok(f"  base: {romaji}_EP{ep_display}_{gen_id}")

    # ep_num and ss_num are needed by unshackle's -w flag regardless of mode.
    if sub_only_mode:
        ep_num = re.match(r'(\d+)', ep_display).group(1).zfill(2)
        # Derive season from the romaji title (e.g. "Wistoria Wand and Sword Season2"
        # → "02") or fall back to the raw filename, then default to "01".
        ss_num = extract_season(romaji or target_mkv.name)
        tokens = show_tokens_from(romaji)
        info(f"episode: {ep_num}  season: {ss_num}  (derived from existing filename)")
    else:
        ss_num = extract_season(orig_filename)
        ep_num = extract_episode(orig_filename) or prompt("episode number")
        tokens = show_tokens_from(target_mkv.stem)
        info(f"season: {ss_num}  episode: {ep_num}")

    slug_match = re.search(r'/series/[^/]+/([^/?#]+)', cr_url) if cr_url else None
    al_search  = slug_match.group(1).replace('-', ' ') if slug_match else None
    if al_search:
        info(f"AniList search term (from CR slug): {al_search}")

    # ── Title / ID resolution (skipped in sub_only_mode) ─────────────────────
    mkv_already_final = False   # used in rename-list logic below

    if not sub_only_mode:
        # ── Case 1: AV1 already-renamed mkv → parse name directly ────────────
        mkv_already_final = RENAMED_MKV_RE.match(target_mkv.name) and is_av1(target_mkv)
        if mkv_already_final:
            stem_clean = re.sub(r'_\d{3,4}[pP]?$', '', target_mkv.stem)
            stem_clean = _PLAT_SUFFIX_RE.sub('', stem_clean)
            m_existing = re.match(
                r'^(.+?)_EP(\d+(?:\(\d+\))?)_(\d+)$', stem_clean, re.IGNORECASE
            )
            if m_existing:
                romaji     = m_existing.group(1).strip()
                ep_display = m_existing.group(2)
                gen_id     = m_existing.group(3)
                ok(f"AV1 already-renamed mkv — using existing name: "
                   f"{romaji}  EP={ep_display}  ID={gen_id}")
            else:
                warn("could not parse existing mkv name — falling through to normal route")
                mkv_already_final = False

        # ── Case 2: bili subtitle already present in gm/ ─────────────────────
        if not romaji:
            ep_int_str  = str(int(ep_num))
            bili_ep_pat = re.compile(
                rf'_EP(?:{re.escape(ep_num.zfill(4))}|{re.escape(ep_num.zfill(2))}|'
                rf'{re.escape(ep_int_str)})(?:[_(]|_)',
                re.IGNORECASE
            )
            existing_bili_sub = next(
                (f for f in PATHS["gm"].glob("*")
                 if f.suffix.lower() in (".ass", ".srt") and bili_ep_pat.search(f.name)),
                None
            )
            if existing_bili_sub:
                sub_stem = existing_bili_sub.stem
                m_sub = _SUB_STEM_RE.match(sub_stem)
                if m_sub:
                    candidate_title = m_sub.group(1).strip()
                    sub_tokens = show_tokens_from(candidate_title)
                    mkv_tokens = show_tokens_from(target_mkv.stem)
                    overlap = sum(1 for t in sub_tokens if t in mkv_tokens)
                    if overlap > 0:
                        romaji     = candidate_title
                        ep_display = m_sub.group(2)
                        gen_id     = m_sub.group(3)
                        info(f"bili subtitle found: {existing_bili_sub.name} — skipping numgen/AniList")
                        ok(f"using bili name: {romaji}  EP={ep_display}  ID={gen_id}")
                    else:
                        warn(f"bili sub title mismatch: '{candidate_title}' vs "
                             f"target '{target_mkv.stem[:40]}' — ignoring")
                else:
                    warn(f"could not parse bili sub stem: '{sub_stem}' — ignoring")

        if not romaji:
            romaji, gen_id, ep_display = resolve_title_and_id(
                target_mkv.stem,
                ep_num,
                anilist_search=al_search,
                anilist_raw=bool(al_search),
                allow_manual=False,
            )
            if not romaji:
                err("could not resolve title — aborting "
                    "(check AniList search term or enter phase manually)")
                return

    # ── Download / locate the .mks subtitle ──────────────────────────────────
    latest_mks = None
    if not skip_download:
        run(f'uv run unshackle -d dl -al ja-jp -w S{ss_num}E{ep_num} -S RC "{cr_url}"',
            cwd=str(PATHS["unshackle"]))
        latest_mks = find_latest(PATHS["cr_dl"], "**/*.mks")
        if latest_mks:
            ok(f"latest .mks: {latest_mks.name}")
            shutil.copy(str(latest_mks), str(PATHS["gm"] / latest_mks.name))
            ok(f"copied → {PATHS['gm'] / latest_mks.name}")
        else:
            warn(f"no .mks found under {PATHS['cr_dl']}")
    else:
        stem_tokens = show_tokens_from(target_mkv.stem if not sub_only_mode else romaji)
        dl_dirs = [d for d in PATHS["cr_dl"].iterdir() if d.is_dir()]

        if dl_dirs:
            best_dirs = best_match_files(dl_dirs, stem_tokens, name_fn=lambda d: d.name)
            best_dir  = best_dirs[0] if best_dirs else None

            if best_dir:
                info(f"best-matching downloads folder: {best_dir.name}")
                ep_int     = str(int(ep_num))
                ep_pattern = re.compile(
                    rf'(?<!\d)({re.escape(ep_num)}|{re.escape(ep_int)})(?!\d)'
                )
                mks_in_dir = [
                    f for f in best_dir.iterdir()
                    if f.suffix.lower() == ".mks" and ep_pattern.search(f.stem)
                ]

                if not mks_in_dir:
                    mks_in_dir = [f for f in best_dir.iterdir() if f.suffix.lower() == ".mks"]
                    if mks_in_dir:
                        warn(f"no episode-{ep_num} match; using newest .mks in folder")
                        mks_in_dir = sorted(mks_in_dir, key=os.path.getmtime, reverse=True)

                if mks_in_dir:
                    latest_mks = mks_in_dir[0]
                    ok(f"found .mks: {latest_mks.name}")
                    shutil.copy(str(latest_mks), str(PATHS["gm"] / latest_mks.name))
                    latest_mks = PATHS["gm"] / latest_mks.name
                    ok(f"copied → {latest_mks.name}")
                else:
                    warn(f"no .mks found in '{best_dir.name}' — subtitle will not be renamed")
            else:
                warn("could not match any downloads/ folder — subtitle will not be renamed")
        else:
            warn(f"no subdirectories found under {PATHS['cr_dl']} — subtitle will not be renamed")

    session.update({"route": "crunchyroll", "romaji": romaji,
                    "episode": ep_display, "id": gen_id})
    save_session(session)

    base = f"{romaji}_EP{ep_display}_{gen_id}"

    # ── Build rename list ─────────────────────────────────────────────────────
    renames = []

    if sub_only_mode:
        # MKVs are already correctly named — touch nothing except the subtitle.
        info("subtitle-only mode: all MKV files left unchanged")
    else:
        gm_files  = list(PATHS["gm"].glob("*.mkv"))
        matched   = best_match_files(gm_files, tokens)
        orig_file = next((f for f in matched if "_mux" not in f.name), None)
        mux_file  = next((f for f in matched if "_mux"     in f.name), None)

        mux_h = get_video_height(mux_file) if mux_file else None
        info(f"mediainfo height (mux) : {mux_h or 'n/a'}")

        if orig_file:
            already_named = bool(
                RENAMED_MKV_RE.match(orig_file.name) and RESOLUTION_RE.search(orig_file.name)
            )
            if mkv_already_final or (already_named and is_av1(orig_file)):
                info(f"AV1 + already renamed — skipping: {orig_file.name}")
            else:
                # Tag with _CR so phase_process can identify the platform
                renames.append((orig_file.name, f"{base}_CR.mkv"))
        if mux_file:
            suffix = f"_{mux_h}.mkv" if mux_h else ".mkv"
            renames.append((mux_file.name, f"{base}{suffix}"))

    if latest_mks:
        renames.append((latest_mks.name, f"{base}.mks"))

    if renames:
        info("renaming:")
        do_renames(renames, session)
    else:
        warn("nothing to rename — subtitle was not found or already in place")

    log_event(session, f"renamed (CR): {base}")

# ─── Phase 2C: No subtitle ────────────────────────────────────────────────────

def phase_nosub(session):
    head("Phase 2C — No Subtitle Route")
    info("use this when no Bilibili or CR subtitle is available")
    info("files will be renamed using the standard convention; no subtitle is copied")

    mux_mkvs = sorted(
        [f for f in PATHS["gm"].glob("*.mkv") if "_mux" in f.name],
        key=lambda f: f.name.lower()
    )
    all_mkvs = sorted(PATHS["gm"].glob("*.mkv"), key=lambda f: f.name.lower())
    candidates = mux_mkvs or list(all_mkvs)

    if not candidates:
        err("no .mkv files in gm/ — run encode phase first")
        return

    target_mkv = candidates[0] if len(candidates) == 1 else pick_mkv(candidates, "target mkv to rename")
    if not target_mkv:
        return

    ep_num = extract_episode(target_mkv.name) or prompt("episode number")
    tokens = show_tokens_from(target_mkv.stem)
    info(f"episode: {ep_num}")

    romaji, gen_id, ep_display = resolve_title_and_id(target_mkv.stem, ep_num)
    if not romaji:
        return
    if not gen_id:
        err("no ID — aborting")
        return

    session.update({"route": "nosub", "romaji": romaji,
                    "episode": ep_display, "id": gen_id})
    save_session(session)

    base     = f"{romaji}_EP{ep_display}_{gen_id}"
    gm_files = list(PATHS["gm"].glob("*.mkv"))
    matched  = best_match_files(gm_files, tokens)

    orig_file = next((f for f in matched if "_mux" not in f.name), None)
    mux_file  = next((f for f in matched if "_mux"     in f.name), None)

    # ── Height detection: only mux file gets resolution suffix ───────────────
    mux_h = get_video_height(mux_file) if mux_file else None
    info(f"mediainfo height (mux) : {mux_h or 'n/a'}")

    # ── Probe orig_file for internal subtitle format to auto-tag platform ─────
    plat_tag = ""
    if orig_file:
        sub_type = detect_internal_sub_type(orig_file)
        info(f"internal sub type: {sub_type or 'none'}")
        if sub_type == 'srt':
            plat_tag = "_NF"
            info("SRT-only tracks detected → tagging as _NF")

    renames = []
    if orig_file:
        renames.append((orig_file.name, f"{base}{plat_tag}.mkv"))
    if mux_file:
        suffix = f"_{mux_h}.mkv" if mux_h else ".mkv"
        renames.append((mux_file.name, f"{base}{suffix}"))

    if not renames:
        warn("no matching mkv files found to rename")
    else:
        info("renaming:")
        do_renames(renames, session)

    warn("no subtitle was copied — add one manually if needed")
    log_event(session, f"renamed (nosub): {base}")

# ─── numbers.json local cache lookup ─────────────────────────────────────────

_NUMBERS_EPISODE_MAP = None   # {(title_lower, ep_zfill2): (title, number)}
_NUMBERS_TITLE_MAP   = None   # {title_lower: (title, number)}
_NUMBERS_PAREN_EP_MAP = None  # {actual_ep_zfill4: [(base_title, display_ep, number, date)]}


def _load_numbers_raw():
    numbers_path = PATHS["numgen_dir"] / "numbers.json"
    if not numbers_path.exists():
        warn(f"numbers.json not found at {numbers_path}")
        return {}, {}, {}
    try:
        with open(numbers_path, encoding="utf-8") as f:
            raw = json.load(f)
        entries = raw.get("numgen", [])
    except Exception as e:
        warn(f"numbers.json load failed: {e}")
        return {}, {}, {}

    episode_map  = {}
    title_map    = {}
    paren_ep_map = {}   # {actual_ep_zfill4: [(base_title, display_ep, number, date)]}

    for e in entries:
        name   = (e.get("name") or "").strip()
        number = (e.get("number") or "").strip()
        date   = (e.get("date") or "")
        if not name or not number or len(number) < 4:
            continue

        # ── Parenthetical-episode format ─────────────────────────────────────
        # e.g. "Detective Conan Year 25_EP1258(1200)"
        m_paren = PAREN_EP_NAME_RE.match(name)
        if m_paren:
            base_title_p = m_paren.group(1).strip()
            display_ep   = m_paren.group(2)   # "1258"
            actual_ep    = m_paren.group(3)   # "1200"
            actual_key   = actual_ep.zfill(4)
            paren_ep_map.setdefault(actual_key, []).append(
                (base_title_p, display_ep, number, date)
            )
            # Also register in episode_map keyed by (base_title_lower, actual_ep_zfill2)
            # so lookup_numbers_exact() can find it directly.
            ep_key = (base_title_p.lower(), actual_ep.zfill(2))
            if ep_key not in episode_map:
                episode_map[ep_key] = (
                    f"{base_title_p}_EP{display_ep}({actual_ep})", number
                )
            continue   # skip the normal-format parsing below

        # ── Normal format ────────────────────────────────────────────────────
        m_ep = re.search(r'[_\s]+EP(\d+)', name, re.IGNORECASE)
        ep_str = m_ep.group(1).zfill(2) if m_ep else None

        title = re.sub(r'[_\s]+EP\d+.*$', '', name, flags=re.IGNORECASE).strip()
        title = re.sub(r'[\s_\-]+\d{1,3}$', '', title).strip()
        if not title:
            continue

        title_key = title.lower()

        if ep_str:
            ep_key = (title_key, ep_str)
            if ep_key not in episode_map:
                episode_map[ep_key] = (title, number)

        if title_key not in title_map or date > title_map[title_key][2]:
            title_map[title_key] = (title, number, date)

    return (
        episode_map,
        {k: (t, n) for k, (t, n, _) in title_map.items()},
        paren_ep_map,
    )


def _ensure_numbers_loaded():
    global _NUMBERS_EPISODE_MAP, _NUMBERS_TITLE_MAP, _NUMBERS_PAREN_EP_MAP
    if _NUMBERS_EPISODE_MAP is None:
        _NUMBERS_EPISODE_MAP, _NUMBERS_TITLE_MAP, _NUMBERS_PAREN_EP_MAP = _load_numbers_raw()


def lookup_numbers_exact(title, ep_num):
    """Return (canonical_title, number) for a known (title, episode) pair.

    Handles both normal and parenthetical-episode formats.
    Returns (None, None) on miss.
    """
    _ensure_numbers_loaded()
    ep_str    = str(ep_num).zfill(2)
    title_key = title.lower()

    # Normal lookup
    result = _NUMBERS_EPISODE_MAP.get((title_key, ep_str))
    if result:
        return result

    # Paren-format lookup: check if *title* is a base-title for paren entries
    # whose actual_ep matches ep_num.
    actual_key = str(int(ep_num)).zfill(4)
    for (base_title, display_ep, number, _) in _NUMBERS_PAREN_EP_MAP.get(actual_key, []):
        if title_key in base_title.lower() or base_title.lower().startswith(title_key[:8]):
            canonical = f"{base_title}_EP{display_ep}({int(ep_num)})"
            return canonical, number

    return None, None


# ─── Paren-ep detection & derivation ─────────────────────────────────────────

def find_paren_ep_info(title_hint, actual_ep_str):
    """For long-running shows that use EP{display}({actual}) numgen format,
    find or derive the correct information for the current episode.

    Parameters
    ----------
    title_hint      AniList / numbers.json base title hint, e.g. "Detective Conan".
    actual_ep_str   Raw episode number from the source filename, e.g. "1200".

    Returns
    -------
    (base_title, ep_display, numgen_string, direct_id)
        base_title    – the year-qualified title, e.g. "Detective Conan Year 25"
        ep_display    – the full ep field for the filename, e.g. "1258(1200)"
        numgen_string – what to pass to run_numgen, e.g.
                        "Detective Conan Year 25_EP1258(1200)"
        direct_id     – the number from numbers.json if already present, else None

    Returns (None, None, None, None) if no paren-ep pattern is found for this show.
    """
    _ensure_numbers_loaded()
    if not _NUMBERS_PAREN_EP_MAP:
        return None, None, None, None

    actual_int  = int(actual_ep_str)
    actual_key  = str(actual_int).zfill(4)
    # Normalise title_hint to alphanumeric only for fuzzy matching
    hint_norm   = re.sub(r'[^\w]', '', title_hint).lower()
    # Use only the first 8 chars as a stable prefix for long show names
    hint_prefix = hint_norm[:8]

    def _title_matches(base_title):
        bt_norm = re.sub(r'[^\w]', '', base_title).lower()
        return hint_norm in bt_norm or bt_norm.startswith(hint_prefix)

    # ── 1. Direct hit (episode already in numbers.json) ──────────────────────
    for (base_title, display_ep, number, _) in _NUMBERS_PAREN_EP_MAP.get(actual_key, []):
        if _title_matches(base_title):
            ep_display    = f"{display_ep}({actual_ep_str})"
            numgen_string = f"{base_title}_EP{ep_display}"
            ok(f"paren-ep direct hit: '{numgen_string}' → ID {number}  (numgen skipped)")
            return base_title, ep_display, numgen_string, number

    # ── 2. Derive from the nearest preceding entry of the same show ───────────
    # Collect all paren-ep entries whose base_title matches and whose actual_ep
    # is strictly less than the one we're looking for.
    candidates = []
    for key, entries in _NUMBERS_PAREN_EP_MAP.items():
        key_int = int(key)
        if key_int >= actual_int:
            continue
        for (base_title, display_ep, number, date) in entries:
            if _title_matches(base_title):
                candidates.append((key_int, base_title, int(display_ep), date))

    if not candidates:
        return None, None, None, None

    # Pick the entry with the largest actual_ep (closest predecessor)
    candidates.sort(key=lambda x: x[0], reverse=True)
    prev_actual, base_title, prev_display, _ = candidates[0]

    # Assume a constant offset between display ep and actual ep
    offset        = prev_display - prev_actual
    new_display   = actual_int + offset
    ep_display    = f"{new_display}({actual_ep_str})"
    numgen_string = f"{base_title}_EP{ep_display}"
    info(f"paren-ep derived (offset={offset:+d}): '{numgen_string}'")
    return base_title, ep_display, numgen_string, None


def search_numbers_json(stem, high_threshold=0.65, low_threshold=0.40):
    _ensure_numbers_loaded()
    if not _NUMBERS_TITLE_MAP:
        return None, None, None

    query_toks = show_tokens_from(stem)
    if not query_toks:
        return None, None, None

    results = []
    for key, (title, _number) in _NUMBERS_TITLE_MAP.items():
        key_toks = [x for x in re.split(r'[\s_\-.!?，。꞉:]+', key) if len(x) > 1]
        if not key_toks:
            continue
        matched = sum(1 for qt in query_toks if qt in key_toks)
        if matched == 0:
            continue
        score = matched / max(len(query_toks), len(key_toks))
        results.append((score, title))

    if not results:
        return None, None, None

    results.sort(reverse=True)
    score, title = results[0]

    if score >= high_threshold:
        return title, None, 'high'
    if score >= low_threshold:
        return title, None, 'low'
    return None, None, None

# ─── AniList helpers ──────────────────────────────────────────────────────────

def fetch_anilist_all_titles(filename_or_stem):
    try:
        stem = Path(filename_or_stem).stem
        stem = re.sub(r'\[.*?\]|\(.*?\)', '', stem)
        stem = re.sub(r'[._\-]\s*[Ss]\d+[Ee]\d+.*', '', stem)
        stem = re.sub(r'[._\-]\d{3,4}[pP].*', '', stem)
        search_term = stem.replace('.', ' ').replace('_', ' ').strip()
        if not search_term:
            return []
        info(f"AniList search: '{search_term}'")
        query = """
        query ($search: String!) {
          Page(perPage: 5) {
            media(type: ANIME, search: $search) {
              title { romaji english native }
            }
          }
        }"""
        payload = json.dumps({"query": query, "variables": {"search": search_term}}).encode()
        req = urllib.request.Request(
            "https://graphql.anilist.co", data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json",
                     "User-Agent": "Mozilla/5.0"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        media = data.get("data", {}).get("Page", {}).get("media", [])
        if not media:
            return []
        titles = media[0].get("title", {})
        return [t for t in [titles.get("romaji"), titles.get("english"), titles.get("native")] if t]
    except Exception as e:
        warn(f"AniList all_titles failed: {e}")
        return []

def fetch_anilist(filename, raw=False):
    try:
        if raw:
            search_term = filename.strip()
        else:
            stem = Path(filename).stem
            stem = re.sub(r'\[.*?\]|\(.*?\)', '', stem)
            stem = re.sub(r'[_\-\.]\s*(S\d+E\d+|\d{2,}).*', '', stem)
            search_term = stem.replace('.', ' ').strip()
        if not search_term:
            return None, []
        info(f"AniList search: '{search_term}'")
        query = """
        query ($search: String!) {
          Page(perPage: 8) {
            media(type: ANIME, search: $search) {
              title { romaji english native }
            }
          }
        }"""
        payload = json.dumps({"query": query, "variables": {"search": search_term}}).encode('utf-8')
        req = urllib.request.Request(
            "https://graphql.anilist.co", data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json",
                     "User-Agent": "Mozilla/5.0"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        media = data.get("data", {}).get("Page", {}).get("media", [])
        if not media:
            return None, []
        top = media[0]
        romaji = top["title"].get("romaji")
        return romaji, media
    except urllib.error.HTTPError as e:
        warn(f"AniList HTTP {e.code}: {e.reason}")
    except Exception as e:
        warn(f"AniList failed: {e}")
    return None, []


def confirm_anilist_title(romaji, all_results, allow_manual=True):
    if not romaji:
        warn("AniList returned no result")
        if not allow_manual:
            err("no AniList match — aborting")
            return None
        return prompt("enter romaji title manually")

    print(f"\n  {C.CYAN}AniList top result:{C.RESET}  {C.BOLD}{romaji}{C.RESET}")

    others = []
    for entry in all_results[1:]:
        t = entry.get("title", {}).get("romaji")
        if t and t != romaji:
            others.append(t)

    if others:
        print(f"  {C.DIM}other results:{C.RESET}")
        for i, t in enumerate(others, 2):
            print(f"    {C.CYAN}{i}{C.RESET}  {t}")

    ans = prompt("use this? [y] / enter number to pick another / type title to override", "y")

    if not ans or ans.lower() == "y":
        return romaji

    if ans.isdigit():
        idx = int(ans) - 1
        full_list = [romaji] + others
        if 0 <= idx < len(full_list):
            chosen = full_list[idx]
            ok(f"using: {chosen}")
            return chosen
        else:
            warn("index out of range — using manual input")
            return ans

    ok(f"using manual title: {ans}")
    return ans

# ─── Phase 3: Subtitle processing & cleanup ──────────────────────────────────

CLEANUP_SCRIPTS = [
    ("assheaderedit.py", "",   "batch edit .ass subtitle headers"),
    ("udmv4linux.py",    "",   "move and organise audio tracks"),
    ("_supnamerm.py",    "",   "clean supplementary name artifacts"),
    ("oldrm.py",         "",   "remove obsolete files"),
]


def _find_renamed_mkvs():
    """Return all MKV files in gm/ that look like fully-renamed episode files.

    Criteria:
      • filename matches  <title>_EP<nn>[(<m>)]_<id>[_<plat>|_<res>].mkv
      • does NOT end in   _720p / _1080p / _2160p / _720 / _1080 / _2160
        (those are resolution variants that extracksub should NOT be run on)
    """
    results = []
    for f in PATHS["gm"].glob("*.mkv"):
        if RENAMED_MKV_RE.match(f.name) and not RESOLUTION_RE.search(f.name):
            results.append(f)
    return sorted(results, key=lambda f: f.name.lower())


def phase_process(session):
    head("Phase 3 — Subtitle Processing & Cleanup")
    info(f"working directory: {PATHS['gm']}")

    renamed_mkvs = _find_renamed_mkvs()

    if not renamed_mkvs:
        warn("no renamed .mkv files found in gm/ — extracksub.py skipped")
    else:
        originals = session.get("originals", {})
        info(f"found {len(renamed_mkvs)} renamed MKV(s) — running extracksub per platform:")
        print()

        procs   = []
        ran_any = False
        for mkv in renamed_mkvs:

            # ── Priority 1: explicit platform-suffix tag in filename ──────────
            # e.g.  KILL BLUE_EP04_28972281_NF.mkv  or  …_CR.mkv
            m_tag = _PLAT_SUFFIX_RE.search(mkv.stem)
            if m_tag:
                suffix_tag  = m_tag.group(1).upper()
                flag        = _PLAT_SUFFIX_FLAG.get(suffix_tag)
                base_name   = mkv.stem[: m_tag.start()] + ".mkv"
                tagged_path = PATHS["gm"] / mkv.name
                base_path   = PATHS["gm"] / base_name
                info(f"  {mkv.name}")
                info(f"    platform tag _{suffix_tag} → stripping, flag={flag}")
                tagged_path.rename(base_path)
                ok(f"    renamed: {mkv.name} → {base_name}")
                actual_name = base_name
            else:
                # ── Priority 2: originals map (original filename had platform tag)
                orig_name = originals.get(mkv.name, "")
                lookup    = orig_name or mkv.name
                flag      = detect_platform_flag(lookup)
                src_label = f"orig='{orig_name}'" if orig_name else "name only"
                info(f"  {mkv.name}")
                info(f"    flag={flag}  ({src_label})")
                actual_name = mkv.name

            if not flag:
                warn(f"    no platform tag detected (checked: '{mkv.name}') — skipping")
                continue

            info(f"    launching extracksub {flag} on '{actual_name}'...")
            shell_cmd = f'echo "{actual_name}" | python3 extracksub.py {flag}'
            cmd(shell_cmd)
            proc = subprocess.Popen(
                shell_cmd, shell=True,
                cwd=str(PATHS["gm"]),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            procs.append((actual_name, proc))
            ran_any = True

        if not ran_any:
            warn("extracksub.py: no files had a recognised platform tag")
        else:
            info(f"waiting for {len(procs)} extracksub process(es) to finish...")
            for name, proc in procs:
                stdout, _ = proc.communicate()
                if stdout and stdout.strip():
                    for line in stdout.strip().splitlines():
                        print(f"  {C.DIM}[extracksub/{Path(name).stem}]{C.RESET} {line}")
                if proc.returncode != 0:
                    err(f"extracksub failed (exit {proc.returncode}) for: {name}")
                else:
                    ok(f"extracksub done: {name}")
            print()

    print()
    for script, flag, desc in CLEANUP_SCRIPTS:
        info(f"running {script}  ({desc})...")
        run(f"python3 {script} {flag}".strip(), cwd=str(PATHS["gm"]))
        ok(f"{script} done")

    ok("all cleanup scripts complete")
    log_event(session, "cleanup: extracksub + 4 scripts ran")

# ─── Phase 4: Audio extraction ───────────────────────────────────────────────

def phase_audio(session):
    head("Phase 4 — Audio Extraction (extau.py)")
    gm_mkvs  = sorted(PATHS["gm"].glob("*.mkv"), key=lambda f: f.name.lower())
    mux_mkvs = [f for f in gm_mkvs if "_mux" in f.name] or list(gm_mkvs)
    if not mux_mkvs:
        err("no .mkv files in gm/")
        return
    target = mux_mkvs[0] if len(mux_mkvs) == 1 else pick_mkv(mux_mkvs, "target mkv for audio extraction")
    if not target:
        return

    flag_map   = {"aac": "-a", "opus": "-o", "eac3": "-e"}
    audio_type = prompt("audio type (aac / opus / eac3)", "aac")
    flag       = flag_map.get(audio_type, "-a")

    run(f'python3 extau.py {flag} "{target.name}"', cwd=str(PATHS["gm"]))
    log_event(session, f"audio extracted ({audio_type}): {target.name}")

# ─── Session status ───────────────────────────────────────────────────────────

def show_status(session):
    head("Session Status")
    for label, val in [
        ("source dir", session.get("source")),
        ("sub route",  session.get("route")),
        ("romaji",     session.get("romaji")),
        ("episode",    session.get("episode")),
        ("id",         session.get("id")),
    ]:
        colour = C.GREEN if val else C.DIM
        print(f"  {label:<12} {colour}{val or '—'}{C.RESET}")

    originals = session.get("originals", {})
    if originals:
        print(f"\n  {C.DIM}rename memory ({len(originals)} file(s)):{C.RESET}")
        for new, old in list(originals.items())[-5:]:
            flag = detect_platform_flag(old) or "?"
            print(f"  {C.DIM}{flag:>4}{C.RESET}  {old}  →  {new}")

    events = session.get("log", [])
    if events:
        print(f"\n  {C.DIM}last {min(5,len(events))} events:{C.RESET}")
        for entry in events[-5:]:
            print(f"  {C.DIM}{entry['time'][:19]}{C.RESET}  {entry['msg']}")
    print()

def clear_session(session):
    session.update({"source": None, "route": None, "romaji": None,
                    "episode": None, "id": None, "originals": {}, "log": []})
    save_session(session)
    ok("session cleared")

def recache_all():
    for lang in ("th", "en"):
        fetch_bili_timeline_ids(force=True, lang=lang)

# ─── Interactive menu ─────────────────────────────────────────────────────────

MENU = [
    ("encode",  "Phase 1 — run video encoder"),
    ("bili",    "Phase 2A — bilibili subtitle route"),
    ("cr",      "Phase 2B — crunchyroll / anilist route"),
    ("nosub",   "Phase 2C — no subtitle (rename only)"),
    ("process", "Phase 3 — subtitle processing & cleanup"),
    ("audio",   "Phase 4 — audio extraction"),
    ("status",  "show session status"),
    ("recache", "force refresh Bilibili timeline cache (TH + EN)"),
    ("clear",   "clear session log"),
    ("exit",    "exit"),
]

def interactive(session):
    print(f"\n{C.BOLD}{C.CYAN}  media automation pipeline{C.RESET}")
    print(f"  {C.DIM}session: {LOG_FILE}{C.RESET}\n")
    while True:
        for i, (key, label) in enumerate(MENU, 1):
            print(f"  {C.CYAN}{i}{C.RESET}  {label}")
        print()
        choice  = prompt("select", "1")
        actions = {str(i): key for i, (key, _) in enumerate(MENU, 1)}
        actions.update({key: key for key, _ in MENU})
        action  = actions.get(choice)
        dispatch = {
            "encode":  lambda: phase_encode(session),
            "bili":    lambda: phase_bili(session),
            "cr":      lambda: phase_cr(session),
            "nosub":   lambda: phase_nosub(session),
            "process": lambda: phase_process(session),
            "audio":   lambda: phase_audio(session),
            "status":  lambda: show_status(session),
            "recache": recache_all,
            "clear":   lambda: clear_session(session),
            "exit":    sys.exit,
        }
        fn = dispatch.get(action)
        if fn:
            fn()
        else:
            warn(f"unknown option: {choice}")
        print()

# ─── CLI entry point ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="pipeline",
        description="Media automation pipeline CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
phases:
  encode    run video encoder
  bili      bilibili subtitle route
  cr        crunchyroll/anilist route
  nosub     no subtitle — rename files only
  process   subtitle processing & cleanup
  audio     extract audio track
  status    print session state
  recache   force-refresh Bilibili TH+EN timeline caches
  clear     reset session log
        """,
    )
    parser.add_argument(
        "phase", nargs="?",
        choices=["encode", "bili", "cr", "nosub", "process", "audio", "status", "recache", "clear"],
        help="jump directly to a phase (default: interactive menu)",
    )
    args    = parser.parse_args()
    session = load_session()
    dispatch = {
        "encode":  lambda: phase_encode(session),
        "bili":    lambda: phase_bili(session),
        "cr":      lambda: phase_cr(session),
        "nosub":   lambda: phase_nosub(session),
        "process": lambda: phase_process(session),
        "audio":   lambda: phase_audio(session),
        "status":  lambda: show_status(session),
        "recache": recache_all,
        "clear":   lambda: clear_session(session),
    }
    if args.phase:
        dispatch[args.phase]()
    else:
        interactive(session)

if __name__ == "__main__":
    main()