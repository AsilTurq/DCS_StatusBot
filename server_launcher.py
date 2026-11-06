import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from core.config_manager import load_config, save_config

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent


def is_udp_or_tcp_listening(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.25)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False
    finally:
        s.close()


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def start_server(w_name: str, label: str, lang: str = "en") -> None:
    print(f"\n  [+] Starting {label} (-w {w_name})..." if lang == "en" else f"\n  [+] {label} başlatılıyor (-w {w_name})...")
    subprocess.Popen(
        [r"E:\DCS_SERVER\bin\DCS_server.exe", "-w", w_name],
        cwd=r"E:\DCS_SERVER",
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )


def open_webguis(lang: str = "en") -> None:
    print(
        "\n  [+] Opening 3 Server WebGUI Control Panels in browser..."
        if lang == "en"
        else "\n  [+] 3 Sunucunun ayrı WebGUI kontrol panelleri tarayıcıda açılıyor..."
    )
    for html in ("WebGUI_1_Suriye.html", "WebGUI_2_Kafkas.html", "WebGUI_3_Iran.html"):
        p = Path(r"E:\DCS_SERVER\WebGUI") / html
        if p.exists():
            os.startfile(str(p))
            time.sleep(0.5)


def start_dcsserverbot(lang: str = "en") -> None:
    check_dcssb = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*DCSServerBot*run.py*' } | Select-Object -ExpandProperty ProcessId",
        ],
        capture_output=True,
        text=True,
    )
    if not check_dcssb.stdout.strip():
        print(
            "\n  [+] Starting AsilTurq DCSServerBot Management Panel..."
            if lang == "en"
            else "\n  [+] AsilTurq DCSServerBot Yönetim Paneli başlatılıyor..."
        )
        bot_bat = Path(r"E:\DCSServerBot\run.cmd")
        if bot_bat.exists():
            os.startfile(str(bot_bat))
        elif Path(r"E:\DCSSERVERBOT_BASLAT.bat").exists():
            os.startfile(r"E:\DCSSERVERBOT_BASLAT.bat")
    else:
        print("\n  [i] AsilTurq DCSServerBot is already running." if lang == "en" else "\n  [i] AsilTurq DCSServerBot zaten çalışıyor.")


def start_status_bots(lang: str = "en") -> None:
    check_bot = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*AsilTurq_DCS_Bot*main.py*' } | Select-Object -ExpandProperty ProcessId",
        ],
        capture_output=True,
        text=True,
    )
    if not check_bot.stdout.strip():
        print(
            "  [+] Starting AsilTurq Discord Status Bots..."
            if lang == "en"
            else "  [+] AsilTurq Discord Durum Botları başlatılıyor..."
        )
        subprocess.Popen(
            ["cmd", "/c", "python", "main.py", "--autostart"],
            cwd=str(BASE_DIR),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    else:
        print(
            "  [i] AsilTurq Discord Status Bots are already running."
            if lang == "en"
            else "  [i] AsilTurq Discord Durum Botları zaten arka planda aktif çalışıyor."
        )


def main() -> None:
    os.system("title ASILTURQ : MULTI-SERVER & BOT CONTROL CENTER")
    while True:
        cfg = load_config()
        lang = str(cfg.get("language", "en")).lower().strip()
        clear_screen()

        on_txt = "🟢 ONLINE (ACTIVE)" if lang == "en" else "🟢 AÇIK (AKTİF)"
        off_txt = "🔴 OFFLINE" if lang == "en" else "🔴 KAPALI"

        s1_up = on_txt if is_udp_or_tcp_listening(8088) else off_txt
        s2_up = on_txt if is_udp_or_tcp_listening(8089) else off_txt
        s3_up = on_txt if is_udp_or_tcp_listening(8090) else off_txt
        dcssb_dir = Path(r"E:\DCSServerBot")
        dcssb_up = on_txt if (dcssb_dir.exists() and any(dcssb_dir.glob("dcssb_*.pid"))) else off_txt

        if lang == "en":
            print("=" * 90)
            print("   🟢 TC | ASIL TURQ - DCSSERVERBOT & 3x DCS DEDICATED SERVER CONTROL CENTER")
            print("=" * 90)
            print(f"  🟢 DCSServerBot Dir  : E:\\DCSServerBot   |  Bot: AsilTurq  |  Status: [{dcssb_up}]")
            print("  🟡 Main Server Binary: E:\\DCS_SERVER\\bin\\DCS_server.exe")
            print("  🔵 Saved Games Root  : E:\\DCS_Server_SaveGames")
            print("-" * 90)
            print(f"  🟢 [SERVER 1 - SYRIA]          Status: [{s1_up}]")
            print("    * Server Name     : TC | Asil Turq - Syria (60 Players)")
            print("    * Ports           : Game 10308  |  WebGUI 8088  |  DCSServerBot 6666  |  StatusHook 42428")
            print("-" * 90)
            print(f"  🟡 [SERVER 2 - CAUCASUS]       Status: [{s2_up}]")
            print("    * Server Name     : TC | Asil Turq - Kafkas (60 Players)")
            print("    * Ports           : Game 10309  |  WebGUI 8089  |  DCSServerBot 6667  |  StatusHook 42429")
            print("-" * 90)
            print(f"  🟠 [SERVER 3 - PERSIAN GULF]   Status: [{s3_up}]")
            print("    * Server Name     : TC | Asil Turq - Persian Gulf (60 Players)")
            print("    * Ports           : Game 10310  |  WebGUI 8090  |  DCSServerBot 6668  |  StatusHook 42430")
            print("=" * 90)
            print("\n  🟢 [1] LAUNCH FULL SUITE (AsilTurq DCSServerBot + 3 DCS Servers + 3 Status Bots)")
            print("  🔵 [2] Launch Only AsilTurq DCSServerBot Management Panel")
            print("  🟢 [3] Launch Only Server 1 Manually (Syria        - Port: 10308)")
            print("  🟡 [4] Launch Only Server 2 Manually (Caucasus     - Port: 10309)")
            print("  🟠 [5] Launch Only Server 3 Manually (Persian Gulf - Port: 10310)")
            print("  🔵 [6] Open All 3 WebGUI Control Panels in Browser (8088, 8089, 8090)")
            print("  ⚪ [7] Open E:\\DCSServerBot and E:\\DCS_Server_SaveGames Folders")
            print("  🟢 [8] Launch Only 3 Discord Status Bots (Syria, Caucasus, Persian Gulf)")
            print("  🔴 [9] Stop All Running DCS Servers (DCS_server.exe)")
            print("  🟡 [L] Switch Language: ENGLISH -> TÜRKÇE")
            print("  ⚪ [R] Refresh Status")
            print("  🔴 [0] Return / Exit\n")
            choice = input("  🟢 Select option: ").strip().upper()
        else:
            print("=" * 90)
            print("   🟢 TC | ASIL TURQ - DCSSERVERBOT (TÜRKÇE) & 3'LÜ DCS DEDICATED SERVER KONTROL PANELİ")
            print("=" * 90)
            print(f"  🟢 DCSServerBot Dizini : E:\\DCSServerBot   |  Bot: AsilTurq  |  Durum: [{dcssb_up}]")
            print("  🟡 Ana Sunucu Dizini   : E:\\DCS_SERVER\\bin\\DCS_server.exe")
            print("  🔵 Tüm Kayıtlar (Save) : E:\\DCS_Server_SaveGames")
            print("-" * 90)
            print(f"  🟢 [1. SUNUCU - SURİYE]   Durum: [{s1_up}]")
            print("    * Sunucu Adı      : TC | Asil Turq - Syria (60 Kişilik)")
            print("    * Portlar         : Oyun 10308  |  WebGUI 8088  |  DCSServerBot 6666  |  Durum Botu 42428")
            print("-" * 90)
            print(f"  🟡 [2. SUNUCU - KAFKAS]   Durum: [{s2_up}]")
            print("    * Sunucu Adı      : TC | Asil Turq - Kafkas (60 Kişilik)")
            print("    * Portlar         : Oyun 10309  |  WebGUI 8089  |  DCSServerBot 6667  |  Durum Botu 42429")
            print("-" * 90)
            print(f"  🟠 [3. SUNUCU - İRAN]     Durum: [{s3_up}]")
            print("    * Sunucu Adı      : TC | Asil Turq - Persian Gulf (60 Kişilik)")
            print("    * Portlar         : Oyun 10310  |  WebGUI 8090  |  DCSServerBot 6668  |  Durum Botu 42430")
            print("=" * 90)
            print("\n  🟢 [1] TÜM SİSTEMİ BAŞLAT (AsilTurq DCSServerBot + 3 DCS Sunucusu + 3 Durum Botu)")
            print("  🔵 [2] Sadece AsilTurq DCSServerBot Yönetim Panelini Başlat")
            print("  🟢 [3] Sadece 1. Sunucuyu Manuel Başlat (Suriye  - Port: 10308)")
            print("  🟡 [4] Sadece 2. Sunucuyu Manuel Başlat (Kafkas  - Port: 10309)")
            print("  🟠 [5] Sadece 3. Sunucuyu Manuel Başlat (İran    - Port: 10310)")
            print("  🔵 [6] 3 Sunucunun Ayrı WebGUI Kontrol Panellerini Tarayıcıda Aç (8088, 8089, 8090)")
            print("  ⚪ [7] E:\\DCSServerBot ve E:\\DCS_Server_SaveGames Klasörlerini Aç")
            print("  🟢 [8] Sadece 3 Discord Durum Botunu Başlat (Suriye, Kafkas, İran)")
            print("  🔴 [9] Açık Olan Tüm DCS Sunucularını (DCS_server.exe) Kapat")
            print("  🟡 [L] Dil Değiştir: TÜRKÇE -> ENGLISH")
            print("  ⚪ [R] Durumları Yenile")
            print("  🔴 [0] Geri / Çıkış\n")
            choice = input("  🟢 Seçiminiz: ").strip().upper()

        if choice == "1":
            start_dcsserverbot(lang)
            start_status_bots(lang)
            input(
                "\n  [SUCCESS] Full suite launched! Press Enter to continue..."
                if lang == "en"
                else "\n  [BAŞARILI] Tüm sistem başlatıldı! Devam için Enter'a basın..."
            )
        elif choice == "2":
            start_dcsserverbot(lang)
        elif choice == "3":
            start_server("DCS_Server_Suriye", "Server 1 (Syria - Port 10308)", lang)
            time.sleep(2)
            if Path(r"E:\DCS_SERVER\WebGUI\WebGUI_1_Suriye.html").exists():
                os.startfile(r"E:\DCS_SERVER\WebGUI\WebGUI_1_Suriye.html")
        elif choice == "4":
            start_server("DCS_Server_Kafkas", "Server 2 (Caucasus - Port 10309)", lang)
            time.sleep(2)
            if Path(r"E:\DCS_SERVER\WebGUI\WebGUI_2_Kafkas.html").exists():
                os.startfile(r"E:\DCS_SERVER\WebGUI\WebGUI_2_Kafkas.html")
        elif choice == "5":
            start_server("DCS_Server_Iran", "Server 3 (Persian Gulf - Port 10310)", lang)
            time.sleep(2)
            if Path(r"E:\DCS_SERVER\WebGUI\WebGUI_3_Iran.html").exists():
                os.startfile(r"E:\DCS_SERVER\WebGUI\WebGUI_3_Iran.html")
        elif choice == "6":
            open_webguis(lang)
        elif choice == "7":
            if Path(r"E:\DCSServerBot").exists():
                os.startfile(r"E:\DCSServerBot")
            if Path(r"E:\DCS_Server_SaveGames").exists():
                os.startfile(r"E:\DCS_Server_SaveGames")
        elif choice == "8":
            start_status_bots(lang)
        elif choice == "9":
            subprocess.run(["taskkill", "/F", "/IM", "DCS_server.exe"], check=False)
            input(
                "\n  [+] All DCS servers stopped. Press Enter..."
                if lang == "en"
                else "\n  [+] Tüm DCS sunucuları kapatıldı. Devam için Enter'a basın..."
            )
        elif choice == "L":
            cfg["language"] = "tr" if lang == "en" else "en"
            save_config(cfg)
        elif choice == "0":
            break


if __name__ == "__main__":
    main()
