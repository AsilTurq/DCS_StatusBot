import base64
import hashlib
import hmac
import json
import os
import secrets
import subprocess
import zlib
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
ENV_PATH = BASE_DIR / ".env"

# ==============================================================================
# EMBEDDED CRYPTOGRAPHIC OWNERSHIP WATERMARK (HMAC-SHA256 + ZLIB + BASE85)
# ==============================================================================
_CRYPTO_KEY = b"\x41\x73\x69\x6c\x54\x75\x72\x71\x5f\x44\x43\x53\x5f\x32\x30\x32\x36"
_CRYPTO_PAYLOAD_B85 = (
    b"c-n@d%&t;V3;+r80~8e4F)}k^A^8LVF*P(I6951J7X(bL82$lR6Z6I~B5Z!7"
    b"W@&6x00000"
)
_OWNERSHIP_CLAIM = "owner=AsilTurq|github=https://github.com/AsilTurq|suite=DCS-StatusBot-v2"
_OWNERSHIP_HMAC = hmac.new(_CRYPTO_KEY, _OWNERSHIP_CLAIM.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_cryptographic_ownership() -> Dict[str, str]:
    """Verifies and returns the embedded cryptographic ownership certificate."""
    calc_sig = hmac.new(_CRYPTO_KEY, _OWNERSHIP_CLAIM.encode("utf-8"), hashlib.sha256).hexdigest()
    valid = hmac.compare_digest(calc_sig, _OWNERSHIP_HMAC)
    fp = hashlib.sha256((_OWNERSHIP_CLAIM + ":" + calc_sig).encode("utf-8")).hexdigest().upper()
    return {
        "valid": "TRUE" if valid else "FALSE",
        "owner": "AsilTurq (https://github.com/AsilTurq)",
        "algorithm": "HMAC-SHA256 / SHA-256",
        "hmac_signature": calc_sig,
        "fingerprint": f"{fp[:8]}-{fp[8:16]}-{fp[16:24]}-{fp[24:32]}",
    }


DEFAULT_CONFIG: Dict[str, Any] = {
    "language": "en",
    "discord_guild_id": "",
    "connection_mode": "local",
    "second_bot_type": "dcs",
    "dcs_saved_games_path": str(Path.home() / "Saved Games" / "DCS"),
    "remote_ip": "127.0.0.1",
    "remote_port": 42428,
    "remote_timeout": 3.0,
    "manual_players": 0,
    "manual_max_players": 60,
    "manual_map": "Syria",
    "manual_mission": "Operation",
    "fallback_max_players": 60,
    "force_max_players": 60,
    "number_style": "bold",
    "server_status_template": "🟢『{players}/{max_players}』• 🔴 {map}",
    "server_offline_text": "🔴 Server Offline",
    "server_activity_type": "custom",
    "server_online_presence": "online",
    "server_empty_presence": "online",
    "member_status_template": "🟢『{members}』• 🔴 Members",
    "member_activity_type": "custom",
    "member_bot_presence": "idle",
    "append_haritasi_suffix": True,
    "update_interval_seconds": 8,
    "multi_server_enabled": False,
    "rotate_member_count_on_single_bot": False,
    "multi_server_template": "🟢 {tag}『{players}/{max_players}』• 🔴 {map}",
    # Active Bot / Server Count (1 to 5) & Individual Bot Settings
    "active_bot_count": 5,
    "bot1_type": "dcs",
    "bot1_map": "Syria",
    "bot1_port": 42428,
    "bot1_max_players": 60,
    "bot2_type": "dcs",
    "bot2_map": "Caucasus",
    "bot2_port": 42429,
    "bot2_max_players": 60,
    "bot3_type": "dcs",
    "bot3_map": "PersianGulf",
    "bot3_port": 42430,
    "bot3_max_players": 60,
    "bot4_type": "dcs",
    "bot4_map": "Sinai",
    "bot4_port": 42431,
    "bot4_max_players": 60,
    "bot5_type": "member",
    "bot5_map": "Kola",
    "bot5_port": 42432,
    "bot5_max_players": 60,
    "servers": [
        {
            "enabled": True,
            "tag": "S1",
            "mode": "local",
            "dcs_saved_games_path": str(Path.home() / "Saved Games" / "DCS"),
            "remote_ip": "127.0.0.1",
            "remote_port": 42428,
            "manual_players": 0,
            "manual_max_players": 60,
            "manual_map": "Syria",
        },
        {
            "enabled": False,
            "tag": "S2",
            "mode": "remote",
            "dcs_saved_games_path": "",
            "remote_ip": "127.0.0.1",
            "remote_port": 42429,
            "manual_players": 0,
            "manual_max_players": 60,
            "manual_map": "Caucasus",
        },
        {
            "enabled": False,
            "tag": "S3",
            "mode": "remote",
            "dcs_saved_games_path": "",
            "remote_ip": "127.0.0.1",
            "remote_port": 42430,
            "manual_players": 0,
            "manual_max_players": 60,
            "manual_map": "PersianGulf",
        },
        {
            "enabled": False,
            "tag": "S4",
            "mode": "remote",
            "dcs_saved_games_path": "",
            "remote_ip": "127.0.0.1",
            "remote_port": 42431,
            "manual_players": 0,
            "manual_max_players": 60,
            "manual_map": "Sinai",
        },
        {
            "enabled": False,
            "tag": "S5",
            "mode": "remote",
            "dcs_saved_games_path": "",
            "remote_ip": "127.0.0.1",
            "remote_port": 42432,
            "manual_players": 0,
            "manual_max_players": 60,
            "manual_map": "Kola",
        },
    ],
}

THEATRE_MAP_NAMES: Dict[str, str] = {
    "Syria": "Suriye",
    "Caucasus": "Kafkas",
    "PersianGulf": "İran",
    "Persian": "İran",
    "SinaiMap": "Sina",
    "Sinai": "Sina",
    "MarianaIslands": "Mariana",
    "Nevada": "Nevada",
    "Normandy": "Normandiya",
    "TheChannel": "Manş",
    "Falklands": "Güney Atlantik",
    "SouthAtlantic": "Güney Atlantik",
    "Kola": "Kola",
    "Afghanistan": "Afganistan",
    "Iraq": "Irak",
}

THEATRE_MAP_NAMES_EN: Dict[str, str] = {
    "Syria": "Syria",
    "Caucasus": "Caucasus",
    "PersianGulf": "Persian Gulf",
    "Persian": "Persian Gulf",
    "SinaiMap": "Sinai",
    "Sinai": "Sinai",
    "MarianaIslands": "Marianas",
    "Nevada": "Nevada",
    "Normandy": "Normandy",
    "TheChannel": "The Channel",
    "Falklands": "South Atlantic",
    "SouthAtlantic": "South Atlantic",
    "Kola": "Kola",
    "Afghanistan": "Afghanistan",
    "Iraq": "Iraq",
}


def mask_secret(secret_str: str, lang: str = "en") -> str:
    """Never reveals any characters of a configured token on screen."""
    s = (secret_str or "").strip()
    if not s or s.startswith("PASTE_") or s.startswith("BURAYA_"):
        return "🔴 [NOT SET]" if lang == "en" else "🔴 [TANIMLANMADI]"
    return "🟢 [LOCKED / HIDDEN]" if lang == "en" else "🟢 [KİLİTLİ / GİZLİ]"


def lock_file_permissions(file_path: Path) -> None:
    if not file_path.exists() or os.name != "nt":
        return
    try:
        username = os.environ.get("USERNAME", "")
        if username:
            subprocess.run(
                ["icacls", str(file_path), "/inheritance:r", "/grant:r", f"{username}:(F)"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
    except Exception:
        pass


def load_env_secrets() -> Dict[str, str]:
    secrets_dict = {
        "SERVER_BOT_TOKEN": os.environ.get("SERVER_BOT_TOKEN", ""),
        "MEMBER_BOT_TOKEN": os.environ.get("MEMBER_BOT_TOKEN", ""),
        "THIRD_BOT_TOKEN": os.environ.get("THIRD_BOT_TOKEN", ""),
        "FOURTH_BOT_TOKEN": os.environ.get("FOURTH_BOT_TOKEN", ""),
        "FIFTH_BOT_TOKEN": os.environ.get("FIFTH_BOT_TOKEN", ""),
        "REMOTE_SECRET_KEY": os.environ.get("REMOTE_SECRET_KEY", ""),
    }
    if ENV_PATH.exists():
        try:
            for line in ENV_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if v.startswith("PASTE_") or v.startswith("BURAYA_"):
                    v = ""
                if k in secrets_dict:
                    secrets_dict[k] = v
        except Exception:
            pass

    if not secrets_dict["REMOTE_SECRET_KEY"]:
        secrets_dict["REMOTE_SECRET_KEY"] = secrets.token_hex(16)

    return secrets_dict


def save_env_secrets(
    server_token: str,
    member_token: str,
    remote_secret: str,
    third_token: str = "",
    fourth_token: str = "",
    fifth_token: str = "",
) -> None:
    if not remote_secret:
        remote_secret = secrets.token_hex(16)
    content = (
        "# ==================================================================\n"
        "# DCS Status Bot - SECURITY FILE (.env)\n"
        "# WARNING: Never share this file or upload it to Git!\n"
        f"# SIG: {_OWNERSHIP_HMAC[:32]}\n"
        "# ==================================================================\n"
        f"SERVER_BOT_TOKEN={server_token.strip()}\n"
        f"MEMBER_BOT_TOKEN={member_token.strip()}\n"
        f"THIRD_BOT_TOKEN={third_token.strip()}\n"
        f"FOURTH_BOT_TOKEN={fourth_token.strip()}\n"
        f"FIFTH_BOT_TOKEN={fifth_token.strip()}\n"
        f"REMOTE_SECRET_KEY={remote_secret.strip()}\n"
    )
    ENV_PATH.write_text(content, encoding="utf-8")
    lock_file_permissions(ENV_PATH)


def detect_dcs_saved_games_folders() -> List[str]:
    saved_games = Path.home() / "Saved Games"
    found: List[str] = []
    if saved_games.exists():
        for item in saved_games.iterdir():
            if item.is_dir() and item.name.upper().startswith("DCS"):
                found.append(str(item))
    for custom_dir in (
        Path("E:/1-DCSSERVERKAFKAS"),
        Path("E:/2-DCSSERVERSYRIA"),
        Path("E:/3-DCSSERVERPERSIANGULF"),
    ):
        if custom_dir.exists() and str(custom_dir) not in found:
            found.append(str(custom_dir))
    if not found:
        found.append(str(saved_games / "DCS"))
    return found


def load_config() -> Dict[str, Any]:
    cfg = DEFAULT_CONFIG.copy()
    detected = detect_dcs_saved_games_folders()
    if detected:
        cfg["dcs_saved_games_path"] = detected[0]

    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    for k, v in loaded.items():
                        if isinstance(v, str) and (v.startswith("PASTE_") or v.startswith("BURAYA_")):
                            continue
                        cfg[k] = v
        except Exception as e:
            print(f"[Config] Error reading config.json, using defaults: {e}")

    env_secrets = load_env_secrets()
    cfg["server_bot_token"] = env_secrets["SERVER_BOT_TOKEN"]
    cfg["member_bot_token"] = env_secrets["MEMBER_BOT_TOKEN"]
    cfg["third_bot_token"] = env_secrets["THIRD_BOT_TOKEN"]
    cfg["fourth_bot_token"] = env_secrets["FOURTH_BOT_TOKEN"]
    cfg["fifth_bot_token"] = env_secrets["FIFTH_BOT_TOKEN"]
    cfg["remote_secret_key"] = env_secrets["REMOTE_SECRET_KEY"]

    if not CONFIG_PATH.exists():
        save_config(cfg)

    return cfg


def save_config(cfg: Dict[str, Any]) -> bool:
    try:
        srv_tok = str(cfg.get("server_bot_token", "")).strip()
        mem_tok = str(cfg.get("member_bot_token", "")).strip()
        tok3 = str(cfg.get("third_bot_token", "")).strip()
        tok4 = str(cfg.get("fourth_bot_token", "")).strip()
        tok5 = str(cfg.get("fifth_bot_token", "")).strip()
        sec_key = str(cfg.get("remote_secret_key", "")).strip()
        save_env_secrets(srv_tok, mem_tok, sec_key, tok3, tok4, tok5)

        safe_cfg = {
            k: v
            for k, v in cfg.items()
            if k
            not in (
                "server_bot_token",
                "member_bot_token",
                "third_bot_token",
                "fourth_bot_token",
                "fifth_bot_token",
                "remote_secret_key",
            )
        }
        safe_cfg["_sig"] = _OWNERSHIP_HMAC[:24]
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(safe_cfg, f, indent=4, ensure_ascii=False)
        lock_file_permissions(CONFIG_PATH)
        return True
    except Exception as e:
        print(f"[Config] Save error: {e}")
        return False


def format_map_name(raw_theatre: str, append_suffix: bool = True, lang: str = "en") -> str:
    lang = (lang or "en").lower().strip()
    if not raw_theatre or raw_theatre in ("Bilinmiyor", "Unknown"):
        return "Waiting for Map" if lang == "en" else "Harita Bekleniyor"
    if lang == "en":
        clean_name = THEATRE_MAP_NAMES_EN.get(raw_theatre, raw_theatre)
        if append_suffix and not clean_name.lower().endswith("map"):
            return f"{clean_name} Map"
        return clean_name
    clean_name = THEATRE_MAP_NAMES.get(raw_theatre, raw_theatre)
    if append_suffix and not clean_name.lower().endswith("haritası") and not clean_name.lower().endswith("haritasi"):
        return f"{clean_name} Haritası"
    return clean_name
