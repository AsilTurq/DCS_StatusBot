from pathlib import Path
from core.config_manager import load_config
from core.dcs_provider import install_dcs_hook

cfg = load_config()
active_count = max(1, min(5, int(cfg.get("active_bot_count", 3))))

base = Path(r"E:\DCS_Server_SaveGames")
webgui_dir = Path(r"E:\DCS_SERVER\WebGUI")

if base.exists():
    for m in base.rglob("*.miz"):
        if "\uff5c" in m.name:
            clean_name = m.name.replace("\uff5c", "-")
            target = m.parent / clean_name
            if not target.exists():
                m.rename(target)

all_servers = [
    {
        "idx": 1,
        "folder": "1_Suriye",
        "w_name": "DCS_Server_Suriye",
        "srv_name": f"DCS Server #1 - {cfg.get('bot1_map', 'Syria')}",
        "port": 10308,
        "web_port": 8088,
        "udp_port": int(cfg.get("bot1_port", 42428)),
        "max_players": int(cfg.get("bot1_max_players", 60)),
        "miz": str(next((base / "1_Suriye" / "Missions").glob("*.miz"), "")) if (base / "1_Suriye" / "Missions").exists() else "",
        "html_name": "WebGUI_1_Suriye.html",
        "title": "Server #1 - Syria (Port 10308)",
    },
    {
        "idx": 2,
        "folder": "2_Kafkas",
        "w_name": "DCS_Server_Kafkas",
        "srv_name": f"DCS Server #2 - {cfg.get('bot2_map', 'Caucasus')}",
        "port": 10309,
        "web_port": 8089,
        "udp_port": int(cfg.get("bot2_port", 42429)),
        "max_players": int(cfg.get("bot2_max_players", 60)),
        "miz": str(next((base / "2_Kafkas" / "Missions").glob("*.miz"), "")) if (base / "2_Kafkas" / "Missions").exists() else "",
        "html_name": "WebGUI_2_Kafkas.html",
        "title": "Server #2 - Caucasus (Port 10309)",
    },
    {
        "idx": 3,
        "folder": "3_Iran",
        "w_name": "DCS_Server_Iran",
        "srv_name": f"DCS Server #3 - {cfg.get('bot3_map', 'PersianGulf')}",
        "port": 10310,
        "web_port": 8090,
        "udp_port": int(cfg.get("bot3_port", 42430)),
        "max_players": int(cfg.get("bot3_max_players", 60)),
        "miz": str(next((base / "3_Iran" / "Missions").glob("*.miz"), "")) if (base / "3_Iran" / "Missions").exists() else "",
        "html_name": "WebGUI_3_Iran.html",
        "title": "Server #3 - Persian Gulf (Port 10310)",
    },
    {
        "idx": 4,
        "folder": "4_Sinai",
        "w_name": "DCS_Server_Sinai",
        "srv_name": f"DCS Server #4 - {cfg.get('bot4_map', 'Sinai')}",
        "port": 10311,
        "web_port": 8091,
        "udp_port": int(cfg.get("bot4_port", 42431)),
        "max_players": int(cfg.get("bot4_max_players", 60)),
        "miz": str(next((base / "4_Sinai" / "Missions").glob("*.miz"), "")) if (base / "4_Sinai" / "Missions").exists() else "",
        "html_name": "WebGUI_4_Sinai.html",
        "title": "Server #4 - Sinai (Port 10311)",
    },
    {
        "idx": 5,
        "folder": "5_Kola",
        "w_name": "DCS_Server_Kola",
        "srv_name": f"DCS Server #5 - {cfg.get('bot5_map', 'Kola')}",
        "port": 10312,
        "web_port": 8092,
        "udp_port": int(cfg.get("bot5_port", 42432)),
        "max_players": int(cfg.get("bot5_max_players", 60)),
        "miz": str(next((base / "5_Kola" / "Missions").glob("*.miz"), "")) if (base / "5_Kola" / "Missions").exists() else "",
        "html_name": "WebGUI_5_Kola.html",
        "title": "Server #5 - Kola (Port 10312)",
    },
]

servers = all_servers[:active_count]
orig_app_js = (webgui_dir / "js" / "app.js").read_text(encoding="utf-8", errors="ignore") if (webgui_dir / "js" / "app.js").exists() else ""

for s in servers:
    p = base / s["folder"]
    (p / "Config").mkdir(parents=True, exist_ok=True)
    (p / "Logs").mkdir(parents=True, exist_ok=True)
    (p / "Missions").mkdir(parents=True, exist_ok=True)
    (p / "Scripts" / "Hooks").mkdir(parents=True, exist_ok=True)

    (p / "Config" / "options.lua").write_text(
        "options={graphics={height=600,width=800},plugins={}}\n", encoding="utf-8"
    )
    (p / "Config" / "autoexec.cfg").write_text(f"webgui_port = {s['web_port']}\n", encoding="utf-8")

    miz_escaped = s["miz"].replace("\\", "\\\\")
    miz_list_entry = f'[1] = "{miz_escaped}",' if miz_escaped else ""
    ss_content = f"""cfg = 
{{
	["description"] = "{s['srv_name']}",
	["require_pure_textures"] = false,
	["listStartIndex"] = 1,
	["advanced"] = 
	{{
		["allow_change_tailno"] = true,
		["allow_dynamic_radio"] = true,
		["allow_object_export"] = false,
		["pause_on_load"] = false,
		["coalition_join_cooldown_seconds"] = 0,
		["allow_sensor_export"] = false,
		["event_Takeoff"] = true,
		["pause_without_clients"] = false,
		["client_outbound_limit"] = 0,
		["client_inbound_limit"] = 0,
		["server_can_screenshot"] = false,
		["allow_players_pool"] = true,
		["voice_chat_server"] = true,
		["allow_change_skin"] = true,
		["event_Connect"] = true,
		["event_Ejecting"] = true,
		["event_Kill"] = true,
		["event_Crash"] = true,
		["coalition_join_cooldown_save"] = false,
		["event_Role"] = true,
		["resume_mode"] = 1,
		["allow_trial_only_clients"] = true,
		["maxPing"] = 0,
		["allow_ownship_export"] = true,
		["enable_coalition_join_cooldown"] = false,
	}},
	["port"] = {s['port']},
	["mode"] = 0,
	["bind_address"] = "",
	["isPublic"] = true,
	["listShuffle"] = false,
	["lastSelectedMission"] = "{miz_escaped}",
	["version"] = 1,
	["password"] = "",
	["listLoop"] = true,
	["name"] = "{s['srv_name']}",
	["require_pure_scripts"] = false,
	["require_pure_models"] = false,
	["missionList"] = 
	{{
		{miz_list_entry}
	}},
	["require_pure_clients"] = false,
	["maxPlayers"] = {s['max_players']},
}}
"""
    (p / "Config" / "serverSettings.lua").write_text(ss_content, encoding="utf-8")
    install_dcs_hook(str(p), allow_remote=False, udp_port=s["udp_port"])

    if orig_app_js and (webgui_dir / "js").exists():
        wp = str(s["web_port"])
        custom_js_name = f"app_{wp}.js"
        custom_js = orig_app_js.replace("8088", wp)
        (webgui_dir / "js" / custom_js_name).write_text(custom_js, encoding="utf-8")

        html_content = (
            f'<!DOCTYPE html><html><head><meta charset=utf-8><meta http-equiv=X-UA-Compatible content="IE=edge">'
            f'<meta name=viewport content="width=device-width,initial-scale=1"><title>{s["title"]}</title>'
            f'<link href=js/{custom_js_name} rel=preload as=script><link href=styles.css rel=preload as=style>'
            f'<link href=styles.css rel=stylesheet></head><body><div id=app></div>'
            f'<script src=js/{custom_js_name}></script></body></html>'
        )
        (webgui_dir / s["html_name"]).write_text(html_content, encoding="utf-8")
    print(f"Ready: {s['folder']} | MaxPlayers: 0/{s['max_players']} | UDP: {s['udp_port']} | WebGUI: {s['html_name']}")
