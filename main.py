import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from core.config_manager import (
    load_config,
    save_config,
    mask_secret,
    detect_dcs_saved_games_folders,
    verify_cryptographic_ownership,
)
from core.dcs_provider import (
    install_dcs_hook,
    check_hook_installed,
    get_dcs_status,
)
from core.bot_manager import DualBotManager, build_server_status_text


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def select_language_prompt(cfg: Dict[str, Any]) -> str:
    clear_screen()
    print("=" * 78)
    print("   🟢  DCS_StatusBot — MULTI-SERVER & DISCORD STATUS BOT SUITE")
    print("=" * 78)
    print("\n   🟡 SELECT LANGUAGE / DİL SEÇİMİ:\n")
    print("     🟢 [1] ENGLISH (Default)  — Full English Interface, Logs & Status")
    print("     🔴 [2] TÜRKÇE             — Tam Türkçe Arayüz, Loglar ve Durum")
    print("\n" + "-" * 78)
    sel = input("   🟢 Select Language / Dil Seçin [1=EN, 2=TR, Enter=1]: ").strip()
    lang = "tr" if sel == "2" else "en"
    cfg["language"] = lang
    save_config(cfg)
    return lang


def auto_prepare_environment(cfg: Dict[str, Any]) -> None:
    """Automatically installs the DCS Status Lua Hook into detected Saved Games profiles."""
    lang = str(cfg.get("language", "en")).lower().strip()
    for folder in detect_dcs_saved_games_folders():
        if Path(folder).exists() and not check_hook_installed(folder):
            install_dcs_hook(folder, allow_remote=False, lang=lang)


def print_banner(cfg: Dict[str, Any]) -> None:
    lang = str(cfg.get("language", "en")).lower().strip()
    active_cnt = max(1, min(5, int(cfg.get("active_bot_count", 5) or 5)))
    if lang == "en":
        mode_map = {
            "local": f"LOCAL SERVER ({cfg.get('dcs_saved_games_path', '')})",
            "remote": f"REMOTE SERVER / VDS ({cfg.get('remote_ip', '')}:{cfg.get('remote_port', 42428)})",
            "manual": f"MANUAL / STATIC ({cfg.get('manual_players', 5)}/{cfg.get('manual_max_players', 60)} | {cfg.get('manual_map', 'Syria')})",
        }
        mode_str = mode_map.get(cfg.get("connection_mode", "local"), "LOCAL SERVER")
        print("=" * 80)
        print("   🟢  DCS_StatusBot — SERVER & DISCORD MEMBER STATUS BOT (COMMAND CENTER)")
        print("=" * 80)
        print(f"  🟢 Language         : ENGLISH (EN)  [Press 'L' to switch to Turkish]")
        print(f"  🟡 Active Bot Count : {active_cnt} / 5 Bots")
        print(f"  🔵 Connection Mode  : {mode_str}")
        t_keys = ["server_bot_token", "member_bot_token", "third_bot_token", "fourth_bot_token", "fifth_bot_token"]
        dots = ["🟢", "🟡", "🟠", "🔵", "⚪"]
        for i in range(1, active_cnt + 1):
            b_type = cfg.get(f"bot{i}_type", "member" if i == 5 else "dcs")
            b_map = "Members" if b_type == "member" else f"{cfg.get(f'bot{i}_map', 'Syria')} (0/{cfg.get(f'bot{i}_max_players', 60)})"
            print(f"  {dots[i-1]} Bot #{i} ({b_map:<14}): {mask_secret(cfg.get(t_keys[i-1], ''), 'en')}")
        print(f"  ⚪ Refresh Rate     : Every {cfg.get('update_interval_seconds', 10)} seconds")
        print("=" * 80)
    else:
        mode_map = {
            "local": f"YEREL SUNUCU ({cfg.get('dcs_saved_games_path', '')})",
            "remote": f"UZAK SUNUCU / VDS ({cfg.get('remote_ip', '')}:{cfg.get('remote_port', 42428)})",
            "manual": f"MANUEL / SABİT ({cfg.get('manual_players', 5)}/{cfg.get('manual_max_players', 60)} | {cfg.get('manual_map', 'Syria')})",
        }
        mode_str = mode_map.get(cfg.get("connection_mode", "local"), "YEREL SUNUCU")
        print("=" * 80)
        print("   🟢  DCS_StatusBot — SUNUCU & DISCORD ÜYE DURUM BOTU (KOMUT MERKEZİ)")
        print("=" * 80)
        print(f"  🟢 Aktif Dil        : TÜRKÇE (TR)   [İngilizce için 'L' tuşuna basın]")
        print(f"  🟡 Aktif Bot Sayısı : {active_cnt} / 5 Bot")
        print(f"  🔵 Çalışma Modu     : {mode_str}")
        t_keys = ["server_bot_token", "member_bot_token", "third_bot_token", "fourth_bot_token", "fifth_bot_token"]
        dots = ["🟢", "🟡", "🟠", "🔵", "⚪"]
        for i in range(1, active_cnt + 1):
            b_type = cfg.get(f"bot{i}_type", "member" if i == 5 else "dcs")
            b_map = "Üye Sayısı" if b_type == "member" else f"{cfg.get(f'bot{i}_map', 'Syria')} (0/{cfg.get(f'bot{i}_max_players', 60)})"
            print(f"  {dots[i-1]} {i}. Bot ({b_map:<14}): {mask_secret(cfg.get(t_keys[i-1], ''), 'tr')}")
        print(f"  ⚪ Yenileme Sıklığı : Her {cfg.get('update_interval_seconds', 10)} saniyede bir")
        print("=" * 80)


def interactive_setup_menu(cfg: Dict[str, Any]) -> Dict[str, Any]:
    while True:
        lang = str(cfg.get("language", "en")).lower().strip()
        clear_screen()
        print_banner(cfg)
        if lang == "en":
            print("\n  🟡 [ BOT & SERVER CONFIGURATION WIZARD ]")
            print(f"  🟢 [1] Set Active Server / Bot Count (1 to 5) [Current: {cfg.get('active_bot_count', 5)}]")
            print("  🟢 [2] Configure Individual Bot Token, Map & Max Players (e.g. 0/60, 0/15)")
            print("  🟡 [3] Select DCS Connection Mode (Local Server / Remote VDS / Manual)")
            print("  🔵 [4] Edit Status Templates & Map Suffix Settings")
            print("  ⚪ [5] Test Live DCS Status Output Now")
            print("  🟠 [L] Switch Language (ENGLISH <-> TÜRKÇE)")
            print("  🔴 [0] SAVE & RETURN TO MAIN LAUNCHER\n")
            choice = input("  🟢 Select option (0-5, L): ").strip().upper()
        else:
            print("\n  🟡 [ BOT VE SUNUCU KURULUM SİHİRBAZI ]")
            print(f"  🟢 [1] Aktif Sunucu / Bot Sayısını Belirle (1 - 5) [Mevcut: {cfg.get('active_bot_count', 5)}]")
            print("  🟢 [2] Botların Token, Harita ve Kapasitesini Ayarla (Örn: 0/60, 0/15)")
            print("  🟡 [3] DCS Bağlantı Modunu Seç (Yerel Sunucu / Uzak Sunucu VDS / Manuel)")
            print("  🔵 [4] Görünüm Formatlarını ve Harita Yazısını Düzenle")
            print("  ⚪ [5] DCS Verisini Şimdi Test Et")
            print("  🟠 [L] Dil Değiştir (TÜRKÇE <-> ENGLISH)")
            print("  🔴 [0] KAYDET VE ANA MENÜYE DÖN\n")
            choice = input("  🟢 Seçiminiz (0-5, L): ").strip().upper()

        if choice == "L":
            cfg["language"] = "tr" if lang == "en" else "en"
            save_config(cfg)
            continue

        elif choice == "1":
            cnt_in = input(
                f"  Enter number of active bots/servers (1-5) [{cfg.get('active_bot_count', 5)}]: "
                if lang == "en"
                else f"  Kullanılacak aktif bot/sunucu sayısını girin (1-5) [{cfg.get('active_bot_count', 5)}]: "
            ).strip()
            if cnt_in.isdigit() and 1 <= int(cnt_in) <= 5:
                cfg["active_bot_count"] = int(cnt_in)
                save_config(cfg)

        elif choice == "2":
            t_keys = ["server_bot_token", "member_bot_token", "third_bot_token", "fourth_bot_token", "fifth_bot_token"]
            b_num = input(
                "  Which Bot slot do you want to configure? (1-5): "
                if lang == "en"
                else "  Kaçıncı Bot yuvasını ayarlamak istiyorsunuz? (1-5): "
            ).strip()
            if b_num.isdigit() and 1 <= int(b_num) <= 5:
                idx = int(b_num)
                tok = input(
                    f"  Paste Bot #{idx} Token (Leave empty to keep current): "
                    if lang == "en"
                    else f"  {idx}. Bot Token'ını yapıştırın (Mevcudu korumak için boş bırakın): "
                ).strip()
                if tok:
                    cfg[t_keys[idx - 1]] = tok
                role_in = input(
                    f"  Bot #{idx} Role (1=DCS Server Status, 2=Discord Member Count) [{cfg.get(f'bot{idx}_type', 'dcs')}]: "
                    if lang == "en"
                    else f"  {idx}. Bot Görevi (1=DCS Sunucu Durumu, 2=Discord Üye Sayısı) [{cfg.get(f'bot{idx}_type', 'dcs')}]: "
                ).strip()
                if role_in == "2":
                    cfg[f"bot{idx}_type"] = "member"
                elif role_in == "1":
                    cfg[f"bot{idx}_type"] = "dcs"

                if cfg.get(f"bot{idx}_type", "dcs") == "dcs":
                    mp_in = input(
                        f"  Bot #{idx} Map Name (e.g. Syria, Caucasus, PersianGulf, Sinai, Kola) [{cfg.get(f'bot{idx}_map', 'Syria')}]: "
                        if lang == "en"
                        else f"  {idx}. Bot Harita Adı (Syria, Caucasus, PersianGulf, Sinai, Kola) [{cfg.get(f'bot{idx}_map', 'Syria')}]: "
                    ).strip()
                    if mp_in:
                        cfg[f"bot{idx}_map"] = mp_in
                    cap_in = input(
                        f"  Bot #{idx} Max Player Capacity (e.g. 60, 32, 15 -> shows 0/60 or 0/15) [{cfg.get(f'bot{idx}_max_players', 60)}]: "
                        if lang == "en"
                        else f"  {idx}. Bot Sunucu Kapasitesi (Örn: 60, 32, 15 -> 0/60 veya 0/15 gösterir) [{cfg.get(f'bot{idx}_max_players', 60)}]: "
                    ).strip()
                    if cap_in.isdigit() and int(cap_in) > 0:
                        cfg[f"bot{idx}_max_players"] = int(cap_in)
                save_config(cfg)

        elif choice == "3":
            if lang == "en":
                print("\n  --- DCS CONNECTION MODE ---")
                print("  [1] LOCAL SERVER  : Bot runs on the same PC as DCS Server")
                print("  [2] REMOTE SERVER : DCS runs on another VDS/PC via UDP IP:Port")
                print("  [3] MANUAL MODE   : Displays static player count and map for testing")
                m_sel = input("  Select mode (1/2/3): ").strip()
            else:
                print("\n  --- DCS BAĞLANTI MODU SEÇİMİ ---")
                print("  [1] YEREL SUNUCU : Bot, DCS Sunucusu ile aynı bilgisayarda çalışacak")
                print("  [2] UZAK SUNUCU  : DCS farklı bir VDS/makinede, IP:Port üzerinden bağlanacak")
                print("  [3] MANUEL MOD   : İstediğiniz oyuncu sayısı ve haritayı sabit/test olarak gösterir")
                m_sel = input("  Mod seçiminiz (1/2/3): ").strip()

            if m_sel == "1":
                cfg["connection_mode"] = "local"
                folders = detect_dcs_saved_games_folders()
                print("\n  Detected Saved Games\\DCS folders:" if lang == "en" else "\n  Tespit edilen Saved Games\\DCS klasörleri:")
                for idx, fpath in enumerate(folders, 1):
                    print(f"    [{idx}] {fpath}")
                prompt_txt = (
                    "  Select folder number or enter full path [Default: 1]: "
                    if lang == "en"
                    else "  Klasör numarası seçin veya tam yol yazın [Varsayılan: 1]: "
                )
                f_sel = input(prompt_txt).strip()
                if not f_sel:
                    cfg["dcs_saved_games_path"] = folders[0]
                elif f_sel.isdigit() and 1 <= int(f_sel) <= len(folders):
                    cfg["dcs_saved_games_path"] = folders[int(f_sel) - 1]
                else:
                    cfg["dcs_saved_games_path"] = f_sel

                ok, msg = install_dcs_hook(cfg["dcs_saved_games_path"], allow_remote=False, lang=lang)
                print(f"  -> {msg}")
                input("\n  Press Enter to continue..." if lang == "en" else "\n  Devam etmek için Enter'a basın...")

            elif m_sel == "2":
                cfg["connection_mode"] = "remote"
                ip = input(
                    f"  Remote DCS Server IP [{cfg.get('remote_ip', '127.0.0.1')}]: "
                    if lang == "en"
                    else f"  Uzak DCS Sunucu IP Adresi [{cfg.get('remote_ip', '127.0.0.1')}]: "
                ).strip()
                if ip:
                    cfg["remote_ip"] = ip
                port_str = input(
                    f"  Remote DCS Hook UDP Port [{cfg.get('remote_port', 42428)}]: "
                    if lang == "en"
                    else f"  Uzak DCS Hook UDP Portu [{cfg.get('remote_port', 42428)}]: "
                ).strip()
                if port_str.isdigit():
                    cfg["remote_port"] = int(port_str)

                if lang == "en":
                    print(f"\n  [SECURITY KEY] Remote authentication key: {cfg.get('remote_secret_key')}")
                    print("  Copy dcs_hook\\AsilTurq_DCS_StatusHook.lua to the remote server's Saved Games\\DCS\\Scripts\\Hooks folder.")
                else:
                    print(f"\n  [GÜVENLİK ANAHTARI] Uzak sunucu doğrulama anahtarınız: {cfg.get('remote_secret_key')}")
                    print("  dcs_hook\\AsilTurq_DCS_StatusHook.lua dosyasını uzak sunucudaki Saved Games\\DCS\\Scripts\\Hooks klasörüne kopyalayın.")
                input("\n  Press Enter to continue..." if lang == "en" else "\n  Devam etmek için Enter'a basın...")

            elif m_sel == "3":
                cfg["connection_mode"] = "manual"
                p_str = input(
                    f"  Active Player Count [{cfg.get('manual_players', 5)}]: "
                    if lang == "en"
                    else f"  Gösterilecek Aktif Oyuncu Sayısı [{cfg.get('manual_players', 5)}]: "
                ).strip()
                if p_str.isdigit():
                    cfg["manual_players"] = int(p_str)
                mp_str = input(
                    f"  Max Players [{cfg.get('manual_max_players', 60)}]: "
                    if lang == "en"
                    else f"  Gösterilecek Maksimum Oyuncu [{cfg.get('manual_max_players', 60)}]: "
                ).strip()
                if mp_str.isdigit():
                    cfg["manual_max_players"] = int(mp_str)
                m_str = input(
                    f"  Map Name (e.g. Syria, Caucasus, PersianGulf) [{cfg.get('manual_map', 'Syria')}]: "
                    if lang == "en"
                    else f"  Gösterilecek Harita Adı (Örn: Syria, Caucasus, PersianGulf) [{cfg.get('manual_map', 'Syria')}]: "
                ).strip()
                if m_str:
                    cfg["manual_map"] = m_str
            save_config(cfg)

        elif choice == "4":
            print("\n  --- STATUS TEMPLATES ---")
            t1 = input(
                f"  Server Bot Template [{cfg.get('server_status_template')}]: "
                if lang == "en"
                else f"  Sunucu Bot Şablonu [{cfg.get('server_status_template')}]: "
            ).strip()
            if t1:
                cfg["server_status_template"] = t1

            suf = input(
                "  Append 'Map' / 'Haritası' suffix to map names? (Y/N) [Y]: "
                if lang == "en"
                else "  Harita sonuna 'Haritası' / 'Map' eklensin mi? (E/H) [E]: "
            ).strip().upper()
            if suf in ("N", "H"):
                cfg["append_haritasi_suffix"] = False
            elif suf in ("Y", "E"):
                cfg["append_haritasi_suffix"] = True

            t2 = input(
                f"  Member Bot Template [{cfg.get('member_status_template')}]: "
                if lang == "en"
                else f"  Üye Bot Şablonu [{cfg.get('member_status_template')}]: "
            ).strip()
            if t2:
                cfg["member_status_template"] = t2
            save_config(cfg)

        elif choice == "5":
            print("\n  [TEST] Querying live DCS status..." if lang == "en" else "\n  [TEST] DCS Durumu sorgulanıyor...")
            st = get_dcs_status(cfg)
            preview = build_server_status_text(cfg, st)
            if lang == "en":
                print(f"  -> Source Mode   : {st.source_mode}")
                print(f"  -> Server Online : {st.online}")
                print(f"  -> Player Count  : {st.players}/{st.max_players}")
                print(f"  -> Map           : {st.formatted_map}")
                print(f"  -> Discord Text  : {preview}")
            else:
                print(f"  -> Bağlantı Modu : {st.source_mode}")
                print(f"  -> Sunucu Online : {st.online}")
                print(f"  -> Oyuncu Sayısı : {st.players}/{st.max_players}")
                print(f"  -> Harita        : {st.formatted_map}")
                print(f"  -> Discord Yazı  : {preview}")
            if st.error_message:
                print(f"  -> Info          : {st.error_message}")
            input("\n  Press Enter to continue..." if lang == "en" else "\n  Devam etmek için Enter'a basın...")

        elif choice == "0":
            save_config(cfg)
            break

    return cfg


def main_launcher_hub(cfg: Dict[str, Any]) -> None:
    while True:
        lang = str(cfg.get("language", "en")).lower().strip()
        clear_screen()
        print_banner(cfg)
        if lang == "en":
            print("\n  🟡 [ MASTER LAUNCHER MENU ]")
            print("  🟢 [1] Start Discord Status Bots (Live Console Mode)")
            print("  🔵 [2] Open Desktop Graphical Control Panel (GUI)")
            print("  🟡 [3] Configure Bot Tokens, Server IP/Ports & Templates")
            print("  🟠 [4] Auto-Setup 3 DCS Dedicated Server Profiles & Hooks")
            print("  🟢 [5] Open 3-Server & DCSServerBot Control Center")
            print("  ⚪ [L] Switch Language: ENGLISH -> TÜRKÇE")
            print("  🔴 [0] Exit\n")
            sel = input("  🟢 Select operation [1-5, L, 0] (Enter=1): ").strip().upper()
        else:
            print("\n  🟡 [ ANA BAŞLATICI MENÜSÜ ]")
            print("  🟢 [1] Discord Durum Botlarını Başlat (Canlı Konsol Modu)")
            print("  🔵 [2] Masaüstü Grafiksel Kontrol Panelini (GUI) Aç")
            print("  🟡 [3] Bot Token, Sunucu IP/Port ve Şablon Ayarlarını Düzenle")
            print("  🟠 [4] 3'lü DCS Sunucu Profillerini ve Hook Köprüsünü Otomatik Kur")
            print("  🟢 [5] 3'lü DCS Sunucu & DCSServerBot Kontrol Merkezini Aç")
            print("  ⚪ [L] Dil Değiştir: TÜRKÇE -> ENGLISH")
            print("  🔴 [0] Çıkış\n")
            sel = input("  🟢 Seçiminiz [1-5, L, 0] (Enter=1): ").strip().upper()

        if sel == "CRYPTO":
            cert = verify_cryptographic_ownership()
            print("\n  🔒 [CRYPTOGRAPHIC OWNERSHIP CERTIFICATE]")
            for k, v in cert.items():
                print(f"    {k.upper():<16}: {v}")
            input("\n  Press Enter...")
            continue

        if sel == "" or sel == "1":
            has_any_token = bool(
                str(cfg.get("server_bot_token", "")).strip()
                or str(cfg.get("member_bot_token", "")).strip()
                or str(cfg.get("third_bot_token", "")).strip()
            )
            if not has_any_token:
                print(
                    "\n  [!] No Discord Bot Token configured yet. Opening Setup Wizard..."
                    if lang == "en"
                    else "\n  [!] Henüz Discord Bot Token girilmemiş. Kurulum Sihirbazı açılıyor..."
                )
                cfg = interactive_setup_menu(cfg)
                continue

            clear_screen()
            print_banner(cfg)
            print(
                "  [INFO] Starting Discord Status Bots... Press Ctrl+C to stop and return to menu.\n"
                if lang == "en"
                else "  [BİLGİ] Discord Durum Botları başlatılıyor... Durdurmak için Ctrl+C tuşlarına basın.\n"
            )
            manager = DualBotManager(config=cfg)
            try:
                asyncio.run(manager.run_console_forever())
            except KeyboardInterrupt:
                print("\n  [System] Stopped by user (Ctrl+C)." if lang == "en" else "\n  [Sistem] Kullanıcı tarafından durduruldu.")
                input("  Press Enter to return to menu..." if lang == "en" else "  Menüye dönmek için Enter'a basın...")

        elif sel == "2":
            from gui_app import AsilTurqDCSBotApp
            app = AsilTurqDCSBotApp()
            app.mainloop()
            cfg = load_config()

        elif sel == "3":
            cfg = interactive_setup_menu(cfg)

        elif sel == "4":
            print(
                "\n  [+] Running 3-Server Profile & Hook Auto-Installer..."
                if lang == "en"
                else "\n  [+] 3'lü Sunucu Profili ve Hook Otomatik Kurucu çalıştırılıyor..."
            )
            subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "setup_3_servers.py")], check=False)
            input("\n  Press Enter to continue..." if lang == "en" else "\n  Devam etmek için Enter'a basın...")

        elif sel == "5":
            import server_launcher
            server_launcher.main()

        elif sel == "L":
            cfg["language"] = "tr" if lang == "en" else "en"
            save_config(cfg)

        elif sel == "0":
            break


def main() -> None:
    if "--verify-owner" in sys.argv:
        cert = verify_cryptographic_ownership()
        print("🔒 CRYPTOGRAPHIC OWNERSHIP CERTIFICATE:")
        for k, v in cert.items():
            print(f"  {k.upper():<16}: {v}")
        return

    cfg = load_config()
    auto_prepare_environment(cfg)

    if "--gui" in sys.argv:
        from gui_app import AsilTurqDCSBotApp
        app = AsilTurqDCSBotApp()
        app.mainloop()
        return

    if "--setup" in sys.argv:
        select_language_prompt(cfg)
        interactive_setup_menu(cfg)
        return

    if "--autostart" in sys.argv:
        manager = DualBotManager(config=cfg)
        asyncio.run(manager.run_console_forever())
        return

    # Always allow language selection at startup (Default = 1: English)
    select_language_prompt(cfg)
    main_launcher_hub(cfg)


if __name__ == "__main__":
    main()
