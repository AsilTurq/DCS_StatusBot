import json
import re
import shutil
import socket
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from core.config_manager import format_map_name

HOOK_SOURCE_FILE = Path(__file__).resolve().parent.parent / "dcs_hook" / "AsilTurq_DCS_StatusHook.lua"


@dataclass
class DCSServerStatus:
    online: bool = False
    paused: bool = False
    players: int = 0
    max_players: int = 60
    raw_map: str = "Syria"
    formatted_map: str = "Syria Map"
    mission_name: str = ""
    server_name: str = "DCS Server"
    source_mode: str = "local"
    error_message: str = ""


def install_dcs_hook(
    dcs_saved_games_path: str,
    allow_remote: bool = False,
    udp_port: int = 42428,
    secret_key: str = "",
    lang: str = "en",
) -> Tuple[bool, str]:
    """
    Installs AsilTurq_DCS_StatusHook.lua and security config into the target
    Saved Games\\DCS folder.
    """
    try:
        if not HOOK_SOURCE_FILE.exists():
            msg = (
                f"Source Hook file not found: {HOOK_SOURCE_FILE}"
                if lang == "en"
                else f"Kaynak Hook dosyası bulunamadı: {HOOK_SOURCE_FILE}"
            )
            return False, msg

        base_dir = Path(dcs_saved_games_path)
        hooks_dir = base_dir / "Scripts" / "Hooks"
        config_dir = base_dir / "Config"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        config_dir.mkdir(parents=True, exist_ok=True)

        target_file = hooks_dir / "AsilTurq_DCS_StatusHook.lua"
        shutil.copy2(HOOK_SOURCE_FILE, target_file)

        bind_host = "0.0.0.0" if allow_remote else "127.0.0.1"
        sec_cfg_file = config_dir / "asilturq_hook_security.cfg"
        sec_cfg_content = (
            f"BIND_HOST={bind_host}\n"
            f"UDP_PORT={int(udp_port)}\n"
            f"SECRET_KEY={secret_key.strip() if allow_remote else ''}\n"
        )
        sec_cfg_file.write_text(sec_cfg_content, encoding="utf-8")

        msg = (
            f"Secure DCS Hook installed successfully: {target_file}"
            if lang == "en"
            else f"Güvenli DCS Hook başarıyla kuruldu: {target_file}"
        )
        return True, msg
    except Exception as e:
        msg = f"Hook installation error: {e}" if lang == "en" else f"Hook kurulum hatası: {e}"
        return False, msg


def check_hook_installed(dcs_saved_games_path: str) -> bool:
    target_file = Path(dcs_saved_games_path) / "Scripts" / "Hooks" / "AsilTurq_DCS_StatusHook.lua"
    return target_file.exists()


def _extract_theatre_from_miz(miz_path_str: str) -> Optional[str]:
    try:
        miz_path = Path(miz_path_str)
        if not miz_path.exists():
            return None
        with zipfile.ZipFile(miz_path, "r") as zf:
            if "theatre" in zf.namelist():
                raw = zf.read("theatre").decode("utf-8", errors="ignore").strip()
                if raw:
                    return raw
    except Exception:
        pass
    return None


def _read_local_server_settings_fallback(dcs_dir: Path) -> Dict[str, Any]:
    result = {
        "max_players": 60,
        "server_name": "DCS Server",
        "theatre": "Syria",
        "mission_name": "",
    }
    settings_file = dcs_dir / "Config" / "serverSettings.lua"
    if not settings_file.exists():
        return result

    try:
        content = None
        for enc in ("utf-8", "cp1254", "latin-1"):
            try:
                content = settings_file.read_text(encoding=enc)
                break
            except Exception:
                continue
        if not content:
            return result

        mp_match = re.search(r'\["maxPlayers"\]\s*=\s*(\d+)', content)
        if mp_match:
            result["max_players"] = int(mp_match.group(1))

        name_match = re.search(r'\["name"\]\s*=\s*"([^"]*)"', content)
        if name_match and name_match.group(1):
            result["server_name"] = name_match.group(1)

        miz_match = re.search(r'\["lastSelectedMission"\]\s*=\s*"([^"]+)"', content)
        if miz_match:
            miz_raw = miz_match.group(1).replace("\\\\", "\\")
            miz_file = Path(miz_raw)
            result["mission_name"] = miz_file.stem
            theatre = _extract_theatre_from_miz(miz_raw)
            if theatre:
                result["theatre"] = theatre
    except Exception:
        pass

    return result


def get_dcs_status(cfg: Dict[str, Any]) -> DCSServerStatus:
    """
    Returns live DCS server status based on connection_mode ('local', 'remote', 'manual').
    """
    mode = cfg.get("connection_mode", "local")
    lang = str(cfg.get("language", "en")).lower().strip()
    append_suffix = bool(cfg.get("append_haritasi_suffix", True))
    fallback_max = int(cfg.get("fallback_max_players", 60) or 60)
    force_max = int(cfg.get("force_max_players", 60) or 0)
    secret_key = str(cfg.get("remote_secret_key", "")).strip()

    # 1. MANUAL / STATIC MODE
    if mode == "manual":
        raw_map = str(cfg.get("manual_map", "Syria"))
        return DCSServerStatus(
            online=True,
            paused=False,
            players=int(cfg.get("manual_players", 5) or 0),
            max_players=int(cfg.get("manual_max_players", 60) or 60),
            raw_map=raw_map,
            formatted_map=format_map_name(raw_map, append_suffix, lang),
            mission_name=str(cfg.get("manual_mission", "Operation" if lang == "en" else "Operasyon")),
            server_name="DCS Server",
            source_mode="manual",
        )

    # 2. REMOTE SERVER (UDP + SHARED SECRET) MODE
    if mode == "remote":
        ip = str(cfg.get("remote_ip", "127.0.0.1")).strip()
        port = int(cfg.get("remote_port", 42428) or 42428)
        timeout = float(cfg.get("remote_timeout", 3.0) or 3.0)

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        try:
            packet = f"STATUS:{secret_key}".encode("utf-8") if secret_key else b"STATUS"
            sock.sendto(packet, (ip, port))
            data, _ = sock.recvfrom(4096)
            payload = json.loads(data.decode("utf-8", errors="replace"))

            raw_map = str(payload.get("theatre", "Syria"))
            max_p = int(payload.get("max_players", fallback_max) or fallback_max)
            return DCSServerStatus(
                online=bool(payload.get("online", True)),
                paused=bool(payload.get("paused", False)),
                players=int(payload.get("players", 0) or 0),
                max_players=max_p,
                raw_map=raw_map,
                formatted_map=format_map_name(raw_map, append_suffix, lang),
                mission_name=str(payload.get("mission_name", "")),
                server_name=str(payload.get("server_name", "DCS Server")),
                source_mode="remote",
            )
        except Exception as e:
            return DCSServerStatus(
                online=False,
                players=0,
                max_players=fallback_max,
                raw_map="Unknown" if lang == "en" else "Bilinmiyor",
                formatted_map="Server Offline" if lang == "en" else "Sunucu Çevrimdışı",
                source_mode="remote",
                error_message=(
                    f"Could not reach remote server ({ip}:{port}): {e}"
                    if lang == "en"
                    else f"Uzak sunucuya ({ip}:{port}) ulaşılamadı: {e}"
                ),
            )
        finally:
            sock.close()

    # 3. LOCAL SERVER MODE
    primary_dir = Path(cfg.get("dcs_saved_games_path", str(Path.home() / "Saved Games" / "DCS")))
    saved_games_root = Path.home() / "Saved Games"
    extra_dirs = [
        saved_games_root / "DCS.dcs_serverrelease",
        saved_games_root / "DCS.release_server",
        saved_games_root / "DCS.dcs_server",
        saved_games_root / "DCS",
    ]

    candidate_dirs = [primary_dir]
    for d in extra_dirs:
        if d not in candidate_dirs and d.exists():
            candidate_dirs.append(d)

    dcs_dir = primary_dir
    for cand in candidate_dirs:
        sf = cand / "Logs" / "asilturq_dcs_status.json"
        if sf.exists():
            dcs_dir = cand
            break
    else:
        for cand in candidate_dirs:
            if (cand / "Config" / "serverSettings.lua").exists():
                dcs_dir = cand
                break

    status_file = dcs_dir / "Logs" / "asilturq_dcs_status.json"
    fallback_info = _read_local_server_settings_fallback(dcs_dir)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.4)
        packet = f"STATUS:{secret_key}".encode("utf-8") if secret_key else b"STATUS"
        sock.sendto(packet, ("127.0.0.1", int(cfg.get("remote_port", 42428) or 42428)))
        data, _ = sock.recvfrom(4096)
        sock.close()
        payload = json.loads(data.decode("utf-8", errors="replace"))
        raw_map = str(payload.get("theatre") or fallback_info["theatre"])
        if raw_map in ("Bilinmiyor", "Unknown"):
            raw_map = fallback_info["theatre"]
        max_p = (
            force_max
            if force_max > 0
            else int(payload.get("max_players") or fallback_info["max_players"] or fallback_max)
        )
        return DCSServerStatus(
            online=bool(payload.get("online", True)),
            paused=bool(payload.get("paused", False)),
            players=int(payload.get("players", 0) or 0),
            max_players=max_p,
            raw_map=raw_map,
            formatted_map=format_map_name(raw_map, append_suffix, lang),
            mission_name=str(payload.get("mission_name") or fallback_info["mission_name"]),
            server_name=str(payload.get("server_name") or fallback_info["server_name"]),
            source_mode="local",
        )
    except Exception:
        pass

    if status_file.exists():
        try:
            raw_text = status_file.read_text(encoding="utf-8", errors="replace")
            payload = json.loads(raw_text)
            ts = int(payload.get("timestamp", 0) or 0)
            age = abs(time.time() - ts)
            is_fresh = age < 30

            raw_map = str(payload.get("theatre") or fallback_info["theatre"])
            if raw_map in ("Bilinmiyor", "Unknown"):
                raw_map = fallback_info["theatre"]
            max_p = (
                force_max
                if force_max > 0
                else int(payload.get("max_players") or fallback_info["max_players"] or fallback_max)
            )

            online_flag = bool(payload.get("online", False)) and is_fresh
            return DCSServerStatus(
                online=online_flag,
                paused=bool(payload.get("paused", False)),
                players=int(payload.get("players", 0) or 0) if online_flag else 0,
                max_players=max_p,
                raw_map=raw_map,
                formatted_map=format_map_name(raw_map, append_suffix, lang),
                mission_name=str(payload.get("mission_name") or fallback_info["mission_name"]),
                server_name=str(payload.get("server_name") or fallback_info["server_name"]),
                source_mode="local",
            )
        except Exception:
            pass

    if bool(cfg.get("show_zero_when_dcs_closed", True)):
        return DCSServerStatus(
            online=True,
            paused=False,
            players=0,
            max_players=force_max if force_max > 0 else fallback_info["max_players"],
            raw_map=fallback_info["theatre"],
            formatted_map=format_map_name(fallback_info["theatre"], append_suffix, lang),
            mission_name=fallback_info["mission_name"],
            server_name=fallback_info["server_name"],
            source_mode="local (standby)" if lang == "en" else "local (beklemede)",
        )


def get_dcs_status_for_bot(cfg: Dict[str, Any], bot_index: int = 1) -> DCSServerStatus:
    """
    bot_index=1 -> Bot 1 (Default: Syria -> Syria Map / Suriye Haritası)
    bot_index=2 -> Bot 2 (Default: Caucasus -> Caucasus Map / Kafkas Haritası)
    bot_index=3 -> Bot 3 (Default: PersianGulf -> Persian Gulf Map / İran Haritası)
    bot_index=4 -> Bot 4 (Default: Sinai -> Sinai Map / Sina Haritası)
    bot_index=5 -> Bot 5 (Default: Kola -> Kola Map / Kola Haritası)
    """
    default_maps = {1: "Syria", 2: "Caucasus", 3: "PersianGulf", 4: "Sinai", 5: "Kola"}
    target_map = str(cfg.get(f"bot{bot_index}_map", default_maps.get(bot_index, "Syria")))
    lang = str(cfg.get("language", "en")).lower().strip()
    append_suffix = bool(cfg.get("append_haritasi_suffix", True))
    default_max = int(cfg.get("force_max_players", 60) or 60)
    force_max = int(cfg.get(f"bot{bot_index}_max_players", default_max) or default_max)

    mode = str(cfg.get(f"bot{bot_index}_connection_mode", cfg.get("connection_mode", "local")))

    if mode == "remote":
        ip = str(cfg.get("remote_ip" if bot_index == 1 else "bot2_remote_ip", cfg.get("remote_ip", "127.0.0.1"))).strip()
        port = int(cfg.get(f"bot{bot_index}_port", 42427 + bot_index))
        sub_cfg = cfg.copy()
        sub_cfg["connection_mode"] = "remote"
        sub_cfg["remote_ip"] = ip
        sub_cfg["remote_port"] = port
        sub_cfg["force_max_players"] = force_max
        st = get_dcs_status(sub_cfg)
        if not st.online and bool(cfg.get("show_zero_when_dcs_closed", True)):
            return DCSServerStatus(
                online=True,
                players=0,
                max_players=force_max,
                raw_map=target_map,
                formatted_map=format_map_name(target_map, append_suffix, lang),
                source_mode="remote (standby)" if lang == "en" else "remote (beklemede)",
            )
        return st

    server_dir_map = {
        1: [Path("E:/2-DCSSERVERSYRIA"), Path("E:/DCS_Server_SaveGames/1_Suriye")],
        2: [Path("E:/1-DCSSERVERKAFKAS"), Path("E:/DCS_Server_SaveGames/2_Kafkas")],
        3: [Path("E:/3-DCSSERVERPERSIANGULF"), Path("E:/DCS_Server_SaveGames/3_Iran")],
    }
    candidate_dirs = server_dir_map.get(
        bot_index,
        [
            Path("E:/1-DCSSERVERKAFKAS"),
            Path("E:/2-DCSSERVERSYRIA"),
            Path("E:/3-DCSSERVERPERSIANGULF"),
            Path("E:/DCS_Server_SaveGames/1_Suriye"),
            Path("E:/DCS_Server_SaveGames/2_Kafkas"),
            Path("E:/DCS_Server_SaveGames/3_Iran"),
        ],
    )

    for cand in candidate_dirs:
        status_file = cand / "Logs" / "asilturq_dcs_status.json"
        if status_file.exists():
            try:
                payload = json.loads(status_file.read_text(encoding="utf-8", errors="replace"))
                ts = int(payload.get("timestamp", 0) or 0)
                if abs(time.time() - ts) < 30 and bool(payload.get("online", False)):
                    th = str(payload.get("theatre", ""))
                    if th.lower() == target_map.lower():
                        return DCSServerStatus(
                            online=True,
                            paused=bool(payload.get("paused", False)),
                            players=int(payload.get("players", 0) or 0),
                            max_players=force_max,
                            raw_map=target_map,
                            formatted_map=format_map_name(target_map, append_suffix, lang),
                            mission_name=str(payload.get("mission_name", "")),
                            server_name=str(payload.get("server_name", "DCS Server")),
                            source_mode=f"local ({cand.name})",
                        )
            except Exception:
                pass

    return DCSServerStatus(
        online=True,
        paused=False,
        players=0,
        max_players=force_max,
        raw_map=target_map,
        formatted_map=format_map_name(target_map, append_suffix, lang),
        mission_name="",
        server_name="DCS Server",
        source_mode="local (active)" if lang == "en" else "local (aktif)",
    )
