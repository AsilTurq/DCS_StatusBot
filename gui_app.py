import math
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
from typing import Dict, Any, List, Tuple

import customtkinter as ctk
from PIL import Image, ImageDraw

from core.config_manager import (
    load_config,
    save_config,
    detect_dcs_saved_games_folders,
    verify_cryptographic_ownership,
)
from core.dcs_provider import (
    get_dcs_status,
    get_dcs_status_for_bot,
    install_dcs_hook,
    check_hook_installed,
)
from core.bot_manager import (
    DualBotManager,
    build_server_status_text,
    build_member_status_text,
    TOKEN_KEYS,
    MAX_BOTS,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

MAP_CHOICES = [
    "Syria",
    "Caucasus",
    "PersianGulf",
    "Sinai",
    "Kola",
    "MarianaIslands",
    "Afghanistan",
    "Iraq",
    "Normandy",
    "Nevada",
    "SouthAtlantic",
]


def create_colored_dot_image(rgb: Tuple[int, int, int], size: int = 14) -> ctk.CTkImage:
    """Renders a crisp, anti-aliased glowing colored round circle icon using PIL."""
    scale = 4
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = 4
    draw.ellipse([pad, pad, s - pad, s - pad], fill=(*rgb, 255))
    # Subtle inner highlight for 3D glossy look
    hl_pad = int(s * 0.22)
    hl_end = int(s * 0.48)
    draw.ellipse(
        [hl_pad, hl_pad, hl_end, hl_end],
        fill=(min(255, rgb[0] + 70), min(255, rgb[1] + 70), min(255, rgb[2] + 70), 180),
    )
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))


def create_uk_flag_image(width: int = 28, height: int = 18) -> ctk.CTkImage:
    """Renders a crisp Union Jack (EN) flag icon using PIL."""
    scale = 4
    w, h = width * scale, height * scale
    img = Image.new("RGBA", (w, h), (1, 33, 105, 255))
    draw = ImageDraw.Draw(img)

    draw.line([(0, 0), (w, h)], fill=(255, 255, 255, 255), width=int(h * 0.22))
    draw.line([(0, h), (w, 0)], fill=(255, 255, 255, 255), width=int(h * 0.22))
    draw.line([(0, 0), (w, h)], fill=(200, 16, 46, 255), width=int(h * 0.10))
    draw.line([(0, h), (w, 0)], fill=(200, 16, 46, 255), width=int(h * 0.10))

    cw = int(h * 0.34)
    draw.rectangle([0, (h - cw) // 2, w, (h + cw) // 2], fill=(255, 255, 255, 255))
    draw.rectangle([(w - cw) // 2, 0, (w + cw) // 2, h], fill=(255, 255, 255, 255))

    rw = int(h * 0.20)
    draw.rectangle([0, (h - rw) // 2, w, (h + rw) // 2], fill=(200, 16, 46, 255))
    draw.rectangle([(w - rw) // 2, 0, (w + rw) // 2, h], fill=(200, 16, 46, 255))

    img = img.resize((width, height), Image.Resampling.LANCZOS)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(width, height))


def create_tr_flag_image(width: int = 28, height: int = 18) -> ctk.CTkImage:
    """Renders a crisp Turkish Flag (Crescent & Star) icon using PIL."""
    scale = 4
    w, h = width * scale, height * scale
    img = Image.new("RGBA", (w, h), (227, 10, 23, 255))
    draw = ImageDraw.Draw(img)

    cx, cy = int(w * 0.42), h // 2
    r_out = int(h * 0.28)
    draw.ellipse([cx - r_out, cy - r_out, cx + r_out, cy + r_out], fill=(255, 255, 255, 255))

    ix = cx + int(h * 0.07)
    r_in = int(h * 0.22)
    draw.ellipse([ix - r_in, cy - r_in, ix + r_in, cy + r_in], fill=(227, 10, 23, 255))

    sx, sy = int(w * 0.64), cy
    sr_out = int(h * 0.14)
    sr_in = int(sr_out * 0.40)
    pts = []
    for i in range(10):
        angle = math.radians(-18 + i * 36 - 18)
        r = sr_out if i % 2 == 0 else sr_in
        pts.append((sx + r * math.cos(angle), sy + r * math.sin(angle)))
    draw.polygon(pts, fill=(255, 255, 255, 255))

    img = img.resize((width, height), Image.Resampling.LANCZOS)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(width, height))


class AsilTurqDCSBotApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.cfg: Dict[str, Any] = load_config()
        self.lang: str = str(self.cfg.get("language", "en")).lower().strip()
        if self.lang not in ("en", "tr"):
            self.lang = "en"

        self.geometry("1360x860")
        self.minsize(1240, 780)

        self.flag_en_img = create_uk_flag_image(26, 17)
        self.flag_tr_img = create_tr_flag_image(26, 17)

        # True-Color Graphical Round Dots (Never gray in Tkinter!)
        self.dot_green = create_colored_dot_image((34, 197, 94), 14)
        self.dot_yellow = create_colored_dot_image((234, 179, 8), 14)
        self.dot_orange = create_colored_dot_image((249, 115, 22), 14)
        self.dot_blue = create_colored_dot_image((59, 130, 246), 14)
        self.dot_red = create_colored_dot_image((239, 68, 68), 14)
        self.dot_white = create_colored_dot_image((226, 232, 240), 14)

        self.dot_sm_green = create_colored_dot_image((34, 197, 94), 11)
        self.dot_sm_red = create_colored_dot_image((239, 68, 68), 11)
        self.dot_sm_yellow = create_colored_dot_image((234, 179, 8), 11)

        self.bot_manager = DualBotManager(
            config=self.cfg,
            log_callback=self.append_log_threadsafe,
            state_callback=self.refresh_preview_threadsafe,
        )

        self.bot_rows: List[Dict[str, Any]] = []
        self.preview_cards: List[Dict[str, Any]] = []
        self._saved_logs: List[str] = []

        self._rebuild_entire_ui()
        self.bind("<Control-Shift-V>", self._show_crypto_certificate)
        self.bind("<Control-Shift-v>", self._show_crypto_certificate)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _show_crypto_certificate(self, _event=None) -> None:
        cert = verify_cryptographic_ownership()
        msg = (
            f"Verified Owner : {cert['owner']}\n"
            f"Algorithm      : {cert['algorithm']}\n"
            f"Fingerprint    : {cert['fingerprint']}\n"
            f"HMAC-SHA256    : {cert['hmac_signature'][:32]}...\n"
            f"Signature Valid: {cert['valid']}"
        )
        messagebox.showinfo("Cryptographic Ownership Verification", msg)

    def _t(self, en_text: str, tr_text: str) -> str:
        return en_text if self.lang == "en" else tr_text

    def _collect_current_form_into_cfg(self) -> None:
        if not hasattr(self, "mode_var"):
            return
        try:
            cnt_val = self.bot_count_seg.get().strip()
            if cnt_val.isdigit():
                self.cfg["active_bot_count"] = max(1, min(MAX_BOTS, int(cnt_val)))
            self.cfg["connection_mode"] = self.mode_var.get()
            self.cfg["dcs_saved_games_path"] = self.local_path_combo.get().strip()
            self.cfg["remote_ip"] = self.remote_ip_entry.get().strip() or "127.0.0.1"
            p_str = self.remote_port_entry.get().strip()
            if p_str.isdigit():
                self.cfg["remote_port"] = int(p_str)
            self.cfg["remote_secret_key"] = self.secret_key_entry.get().strip()
            mp_str = self.manual_players_entry.get().strip()
            if mp_str.isdigit():
                self.cfg["manual_players"] = int(mp_str)
            mmax_str = self.manual_max_entry.get().strip()
            if mmax_str.isdigit():
                self.cfg["manual_max_players"] = int(mmax_str)
            self.cfg["manual_map"] = self.manual_map_combo.get().strip() or "Syria"
            self.cfg["discord_guild_id"] = self.guild_id_entry.get().strip()

            for idx, row in enumerate(self.bot_rows, start=1):
                t_key = TOKEN_KEYS[idx - 1]
                self.cfg[t_key] = row["token_entry"].get().strip()
                mode_val = row["type_combo"].get()
                b_type = "member" if ("Member" in mode_val or "Üye" in mode_val) else "dcs"
                self.cfg[f"bot{idx}_type"] = b_type
                if idx == 2:
                    self.cfg["second_bot_type"] = b_type
                self.cfg[f"bot{idx}_map"] = row["map_combo"].get().strip() or "Syria"
                maxp_str = row["maxp_entry"].get().strip()
                if maxp_str.isdigit() and int(maxp_str) > 0:
                    self.cfg[f"bot{idx}_max_players"] = int(maxp_str)
                prt = row["port_entry"].get().strip()
                if prt.isdigit():
                    self.cfg[f"bot{idx}_port"] = int(prt)

            self.cfg["server_status_template"] = self.srv_tpl_entry.get().strip()
            self.cfg["server_offline_text"] = self.srv_off_entry.get().strip()
            self.cfg["member_status_template"] = self.mem_tpl_entry.get().strip()
            self.cfg["append_haritasi_suffix"] = bool(self.suffix_switch.get())
            intv = self.interval_entry.get().strip()
            if intv.isdigit():
                self.cfg["update_interval_seconds"] = max(5, int(intv))
        except Exception:
            pass

    def _rebuild_entire_ui(self) -> None:
        self.title(
            self._t(
                "DCS_StatusBot — Multi-Server & Discord Status Bot Manager (1-5 Servers)",
                "DCS_StatusBot — Çoklu Sunucu & Discord Durum Botu Yöneticisi (1-5 Sunucu)",
            )
        )
        for child in self.winfo_children():
            child.destroy()

        self.bot_rows.clear()
        self.preview_cards.clear()

        self.grid_columnconfigure(0, weight=3, uniform="main_cols")
        self.grid_columnconfigure(1, weight=2, uniform="main_cols")
        self.grid_rowconfigure(1, weight=1)

        # Top Header Bar
        header = ctk.CTkFrame(self, height=62, corner_radius=10, fg_color="#161922")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=(12, 6))
        header.grid_columnconfigure(0, weight=1)

        self.title_lbl = ctk.CTkLabel(
            header,
            text=self._t(
                "  DCS_StatusBot — Multi-Server & Discord Status Manager",
                "  DCS_StatusBot — Çoklu Sunucu & Discord Durum Yöneticisi",
            ),
            image=self.dot_green,
            compound="left",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#f0f4f8",
        )
        self.title_lbl.grid(row=0, column=0, padx=16, pady=14, sticky="w")

        # Flag Buttons Frame (With Real UK & TR Graphical Flags!)
        lang_frame = ctk.CTkFrame(header, fg_color="#0f1117", corner_radius=8)
        lang_frame.grid(row=0, column=1, padx=8, pady=10, sticky="e")

        self.btn_lang_en = ctk.CTkButton(
            lang_frame,
            text="EN",
            image=self.flag_en_img,
            compound="left",
            width=74,
            height=32,
            corner_radius=6,
            fg_color="#2563eb" if self.lang == "en" else "transparent",
            hover_color="#1d4ed8",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: self._switch_language("en"),
        )
        self.btn_lang_en.grid(row=0, column=0, padx=(4, 2), pady=4)

        self.btn_lang_tr = ctk.CTkButton(
            lang_frame,
            text="TR",
            image=self.flag_tr_img,
            compound="left",
            width=74,
            height=32,
            corner_radius=6,
            fg_color="#dc2626" if self.lang == "tr" else "transparent",
            hover_color="#b91c1c",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: self._switch_language("tr"),
        )
        self.btn_lang_tr.grid(row=0, column=1, padx=(2, 4), pady=4)

        is_run = self.bot_manager.is_running
        self.status_badge = ctk.CTkLabel(
            header,
            text=(
                self._t("  RUNNING", "  ÇALIŞIYOR")
                if is_run
                else self._t("  STOPPED", "  DURDURULDU")
            ),
            image=self.dot_green if is_run else self.dot_red,
            compound="left",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#22c55e" if is_run else "#ef4444",
        )
        self.status_badge.grid(row=0, column=2, padx=16, pady=14, sticky="e")

        # Left Panel: Configuration Tabs
        left_frame = ctk.CTkFrame(self, corner_radius=10)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(14, 7), pady=6)
        left_frame.grid_rowconfigure(0, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(left_frame)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=8)

        tab1_name = self._t("1. Discord Bots & Servers (1-5)", "1. Discord Botları & Sunucular (1-5)")
        tab2_name = self._t("2. DCS Connection Mode", "2. DCS Bağlantı Modu")
        tab3_name = self._t("3. Templates & Appearance", "3. Görünüm & Şablonlar")

        self.tab_tokens = self.tabview.add(tab1_name)
        self.tab_source = self.tabview.add(tab2_name)
        self.tab_format = self.tabview.add(tab3_name)

        self._build_tokens_tab()
        self._build_source_tab()
        self._build_format_tab()

        # Bottom Action Buttons
        btn_bar = ctk.CTkFrame(left_frame, fg_color="transparent")
        btn_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=(2, 10))
        btn_bar.grid_columnconfigure((0, 1, 2), weight=1)

        self.save_btn = ctk.CTkButton(
            btn_bar,
            text=self._t("  Save & Apply Settings", "  Ayarları Kaydet & Uygula"),
            image=self.dot_yellow,
            compound="left",
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.on_save_config,
        )
        self.save_btn.grid(row=0, column=0, padx=5, sticky="ew")

        self.start_btn = ctk.CTkButton(
            btn_bar,
            text=self._t("  Start Bots", "  Botları Başlat"),
            image=self.dot_green,
            compound="left",
            fg_color="#16a34a",
            hover_color="#15803d",
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            state="disabled" if is_run else "normal",
            command=self.on_start_bots,
        )
        self.start_btn.grid(row=0, column=1, padx=5, sticky="ew")

        self.stop_btn = ctk.CTkButton(
            btn_bar,
            text=self._t("  Stop Bots", "  Botları Durdur"),
            image=self.dot_red,
            compound="left",
            fg_color="#dc2626",
            hover_color="#b91c1c",
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            state="normal" if is_run else "disabled",
            command=self.on_stop_bots,
        )
        self.stop_btn.grid(row=0, column=2, padx=5, sticky="ew")

        # Right Panel: Live Preview + Live Log
        right_frame = ctk.CTkFrame(self, corner_radius=10)
        right_frame.grid(row=1, column=1, sticky="nsew", padx=(7, 14), pady=6)
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        self._build_discord_preview_card(right_frame)
        self._build_log_panel(right_frame)

        self._load_values_into_ui()
        self._update_bot_count_visibility()
        self._update_mode_visibility()
        self._update_live_preview()

    def _switch_language(self, new_lang: str) -> None:
        if new_lang == self.lang:
            return
        self._collect_current_form_into_cfg()
        self.lang = new_lang
        self.cfg["language"] = new_lang
        save_config(self.cfg)
        self.bot_manager.update_config(self.cfg)
        self._rebuild_entire_ui()

    def _build_tokens_tab(self) -> None:
        tab = self.tab_tokens
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        top_info = ctk.CTkFrame(tab, corner_radius=8)
        top_info.grid(row=0, column=0, sticky="ew", padx=6, pady=(4, 6))
        top_info.grid_columnconfigure(1, weight=1)

        # Row 0: Active Server / Bot Count Selector (1 to 5)
        ctk.CTkLabel(
            top_info,
            text=self._t("  Active Server / Bot Count:", "  Aktif Sunucu / Bot Sayısı:"),
            image=self.dot_green,
            compound="left",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=0, padx=10, pady=(8, 4), sticky="w")

        self.bot_count_seg = ctk.CTkSegmentedButton(
            top_info,
            values=["1", "2", "3", "4", "5"],
            command=self._on_bot_count_changed,
            height=28,
        )
        self.bot_count_seg.set(str(self.cfg.get("active_bot_count", 5)))
        self.bot_count_seg.grid(row=0, column=1, padx=(0, 8), pady=(8, 4), sticky="w")

        clear_all_btn = ctk.CTkButton(
            top_info,
            text=self._t("  Clear All Tokens", "  Tüm Tokenları Temizle"),
            image=self.dot_red,
            compound="left",
            width=150,
            height=28,
            fg_color="#7f1d1d",
            hover_color="#991b1b",
            command=self._on_clear_all_tokens,
        )
        clear_all_btn.grid(row=0, column=2, padx=8, pady=(8, 4), sticky="e")

        # Row 1: Discord Server (Guild) ID
        ctk.CTkLabel(
            top_info,
            text=self._t("  Discord Server (Guild) ID:", "  Discord Sunucu (Guild) ID:"),
            image=self.dot_yellow,
            compound="left",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=1, column=0, padx=10, pady=(4, 8), sticky="w")

        self.guild_id_entry = ctk.CTkEntry(
            top_info,
            placeholder_text=self._t(
                "Optional: Right-click Discord Server -> Copy Server ID (Auto-detected if empty)",
                "Opsiyonel: Discord Sunucusuna Sağ Tık -> Sunucu ID Kopyala (Boşsa otomatik bulur)",
            ),
        )
        self.guild_id_entry.grid(row=1, column=1, columnspan=2, padx=(0, 8), pady=(4, 8), sticky="ew")

        # Scrollable 5-Bot Configuration List
        scroll = ctk.CTkScrollableFrame(
            tab,
            corner_radius=8,
            label_text=self._t(
                "Configure Discord Status Bots & Server Player Capacities (e.g. 0/60, 0/15, 0/32)",
                "Discord Durum Botlarını ve Sunucu Oyuncu Kapasitelerini Ayarlayın (Örn: 0/60, 0/15, 0/32)",
            ),
        )
        scroll.grid(row=1, column=0, sticky="nsew", padx=6, pady=4)
        scroll.grid_columnconfigure(0, weight=1)

        dot_imgs = [self.dot_green, self.dot_yellow, self.dot_orange, self.dot_blue, self.dot_white]
        for i in range(1, MAX_BOTS + 1):
            card = ctk.CTkFrame(scroll, corner_radius=8, fg_color="#181b24")
            card.grid(row=i - 1, column=0, sticky="ew", padx=4, pady=5)
            card.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                card,
                text=self._t(f"  BOT #{i}", f"  {i}. BOT"),
                image=dot_imgs[i - 1],
                compound="left",
                font=ctk.CTkFont(size=13, weight="bold"),
                width=84,
                anchor="w",
            ).grid(row=0, column=0, padx=(10, 4), pady=(8, 4), sticky="w")

            tok_entry = ctk.CTkEntry(
                card,
                show="•",
                placeholder_text=self._t(
                    f"Paste Discord Bot #{i} Token here...",
                    f"{i}. Discord Bot Token'ını buraya yapıştırın...",
                ),
            )
            tok_entry.grid(row=0, column=1, padx=4, pady=(8, 4), sticky="ew")

            paste_btn = ctk.CTkButton(
                card,
                text=self._t("Paste", "Yapıştır"),
                width=62,
                height=26,
                fg_color="#334155",
                hover_color="#475569",
                command=lambda e=tok_entry: self._paste_into_entry(e),
            )
            paste_btn.grid(row=0, column=2, padx=2, pady=(8, 4))

            show_btn = ctk.CTkButton(
                card,
                text=self._t("Show", "Göster"),
                width=58,
                height=26,
                fg_color="#334155",
                hover_color="#475569",
            )
            show_btn.configure(command=lambda e=tok_entry, b=show_btn: self._toggle_token_visibility(e, b))
            show_btn.grid(row=0, column=3, padx=2, pady=(8, 4))

            clr_btn = ctk.CTkButton(
                card,
                text="✕",
                width=30,
                height=26,
                fg_color="#7f1d1d",
                hover_color="#991b1b",
                command=lambda e=tok_entry: (e.delete(0, "end"), self._update_live_preview()),
            )
            clr_btn.grid(row=0, column=4, padx=(2, 10), pady=(8, 4))

            # Row 2 of Bot Card: Role | Map | Max Players (0/60, 0/15) | UDP Port
            sub = ctk.CTkFrame(card, fg_color="transparent")
            sub.grid(row=1, column=0, columnspan=5, sticky="ew", padx=10, pady=(2, 8))

            ctk.CTkLabel(
                sub,
                text=self._t("Role:", "Görev:"),
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=(0, 4))

            role_values = (
                ["DCS Server Status", "Discord Member Count"]
                if self.lang == "en"
                else ["DCS Sunucu Durumu", "Discord Üye Sayısı"]
            )
            type_combo = ctk.CTkComboBox(
                sub,
                values=role_values,
                width=172,
                state="readonly",
                command=lambda _: self._update_live_preview(),
            )
            type_combo.pack(side="left", padx=(0, 8))

            ctk.CTkLabel(
                sub,
                text=self._t("Map:", "Harita:"),
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=(0, 4))

            map_combo = ctk.CTkComboBox(
                sub,
                values=MAP_CHOICES,
                width=118,
                command=lambda _: self._update_live_preview(),
            )
            map_combo.pack(side="left", padx=(0, 8))

            ctk.CTkLabel(
                sub,
                text=self._t("Max Players (0/X):", "Kapasite (0/X):"),
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#38bdf8",
            ).pack(side="left", padx=(0, 4))

            maxp_entry = ctk.CTkEntry(sub, width=48)
            maxp_entry.pack(side="left", padx=(0, 8))
            maxp_entry.bind("<KeyRelease>", lambda _: self._update_live_preview())

            ctk.CTkLabel(
                sub,
                text=self._t("UDP Port:", "UDP Port:"),
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=(0, 4))

            port_entry = ctk.CTkEntry(sub, width=62)
            port_entry.pack(side="left")

            self.bot_rows.append(
                {
                    "card": card,
                    "token_entry": tok_entry,
                    "type_combo": type_combo,
                    "map_combo": map_combo,
                    "maxp_entry": maxp_entry,
                    "port_entry": port_entry,
                }
            )

    def _on_bot_count_changed(self, _val: str) -> None:
        self._update_bot_count_visibility()
        self._update_live_preview()

    def _update_bot_count_visibility(self) -> None:
        cnt_str = self.bot_count_seg.get().strip()
        active_cnt = int(cnt_str) if cnt_str.isdigit() else MAX_BOTS
        for idx, row in enumerate(self.bot_rows, start=1):
            if idx <= active_cnt:
                row["card"].grid()
            else:
                row["card"].grid_remove()
        for idx, pcard in enumerate(self.preview_cards, start=1):
            if idx <= active_cnt:
                pcard["frame"].grid()
            else:
                pcard["frame"].grid_remove()

    def _build_source_tab(self) -> None:
        tab = self.tab_source
        tab.grid_columnconfigure(0, weight=1)

        mode_box = ctk.CTkFrame(tab, corner_radius=8)
        mode_box.grid(row=0, column=0, sticky="ew", padx=8, pady=8)

        ctk.CTkLabel(
            mode_box,
            text=self._t(
                "  DCS Data Source Mode (Local, Remote VDS, or Manual):",
                "  DCS Veri Kaynağı Seçimi (Yerel, Uzak Sunucu VDS veya Manuel):",
            ),
            image=self.dot_yellow,
            compound="left",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, padx=12, pady=(10, 6), sticky="w")

        self.mode_var = tk.StringVar(value=self.cfg.get("connection_mode", "local"))

        modes = [
            (
                "local",
                self._t(
                    "Local Server (Bot runs on the same PC as DCS Server)",
                    "Yerel Sunucu (Bot ile DCS Sunucusu aynı bilgisayarda çalışıyor)",
                ),
            ),
            (
                "remote",
                self._t(
                    "Remote Server / VDS (Connect to DCS on another machine via IP:Port)",
                    "Uzak Sunucu / VDS (DCS farklı bir makinede, IP:Port üzerinden bağlan)",
                ),
            ),
            (
                "manual",
                self._t(
                    "Manual / Test Mode (Display custom static map & player count)",
                    "Manuel / Test Modu (İstediğiniz harita ve oyuncu sayısını sabit gösterir)",
                ),
            ),
        ]

        for idx, (val, text) in enumerate(modes, start=1):
            rb = ctk.CTkRadioButton(
                mode_box,
                text=text,
                variable=self.mode_var,
                value=val,
                command=self._update_mode_visibility,
            )
            rb.grid(row=idx, column=0, padx=16, pady=5, sticky="w")

        # 1. Local Mode Frame
        self.local_frame = ctk.CTkFrame(tab, corner_radius=8)
        self.local_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=6)
        self.local_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.local_frame,
            text=self._t("  Local DCS Saved Games Folder:", "  Yerel DCS Saved Games Klasörü:"),
            image=self.dot_green,
            compound="left",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=12, pady=(10, 4), sticky="w")

        detected_folders = detect_dcs_saved_games_folders()
        self.local_path_combo = ctk.CTkComboBox(self.local_frame, values=detected_folders)
        self.local_path_combo.grid(row=1, column=0, padx=(12, 6), pady=6, sticky="ew")

        browse_btn = ctk.CTkButton(
            self.local_frame,
            text=self._t("Browse...", "Gözat..."),
            width=90,
            command=self._on_browse_saved_games,
        )
        browse_btn.grid(row=1, column=1, padx=(0, 12), pady=6)

        self.hook_status_lbl = ctk.CTkLabel(
            self.local_frame,
            text="",
            image=self.dot_green,
            compound="left",
            font=ctk.CTkFont(size=12),
        )
        self.hook_status_lbl.grid(row=2, column=0, columnspan=2, padx=12, pady=2, sticky="w")

        hook_btn_bar = ctk.CTkFrame(self.local_frame, fg_color="transparent")
        hook_btn_bar.grid(row=3, column=0, columnspan=2, sticky="ew", padx=12, pady=(6, 12))
        hook_btn_bar.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            hook_btn_bar,
            text=self._t("  Auto-Install / Update DCS Hook Script", "  DCS Hook Scriptini Otomatik Kur / Güncelle"),
            image=self.dot_green,
            compound="left",
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=self._on_install_hook_local,
        ).grid(row=0, column=0, padx=(0, 5), sticky="ew")

        ctk.CTkButton(
            hook_btn_bar,
            text=self._t("  Test Live Local DCS Data Now", "  Yerel DCS Verisini Şimdi Test Et"),
            image=self.dot_blue,
            compound="left",
            fg_color="#475569",
            hover_color="#334155",
            command=self._on_test_dcs_connection,
        ).grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # 2. Remote Mode Frame
        self.remote_frame = ctk.CTkFrame(tab, corner_radius=8)
        self.remote_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=6)
        self.remote_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.remote_frame,
            text=self._t("  Remote DCS Server (VDS) UDP Settings:", "  Uzak DCS Sunucu (VDS) UDP Ayarları:"),
            image=self.dot_yellow,
            compound="left",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=12, pady=(10, 6), sticky="w")

        ctk.CTkLabel(self.remote_frame, text=self._t("Server IP Address:", "Sunucu IP Adresi:")).grid(
            row=1, column=0, padx=12, pady=4, sticky="w"
        )
        self.remote_ip_entry = ctk.CTkEntry(self.remote_frame, placeholder_text="127.0.0.1")
        self.remote_ip_entry.grid(row=1, column=1, padx=12, pady=4, sticky="ew")

        ctk.CTkLabel(self.remote_frame, text=self._t("Hook UDP Port:", "Hook UDP Portu:")).grid(
            row=2, column=0, padx=12, pady=4, sticky="w"
        )
        self.remote_port_entry = ctk.CTkEntry(self.remote_frame, placeholder_text="42428")
        self.remote_port_entry.grid(row=2, column=1, padx=12, pady=4, sticky="ew")

        ctk.CTkLabel(self.remote_frame, text=self._t("Shared Secret Key:", "Güvenlik Anahtarı:")).grid(
            row=3, column=0, padx=12, pady=(4, 10), sticky="w"
        )
        self.secret_key_entry = ctk.CTkEntry(self.remote_frame)
        self.secret_key_entry.grid(row=3, column=1, padx=12, pady=(4, 10), sticky="ew")

        # 3. Manual Mode Frame
        self.manual_frame = ctk.CTkFrame(tab, corner_radius=8)
        self.manual_frame.grid(row=3, column=0, sticky="ew", padx=8, pady=6)
        self.manual_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.manual_frame,
            text=self._t("  Manual / Static Display Settings:", "  Manuel / Sabit Gösterim Ayarları:"),
            image=self.dot_orange,
            compound="left",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=12, pady=(10, 6), sticky="w")

        ctk.CTkLabel(self.manual_frame, text=self._t("Active Players:", "Aktif Oyuncu:")).grid(
            row=1, column=0, padx=12, pady=4, sticky="w"
        )
        self.manual_players_entry = ctk.CTkEntry(self.manual_frame)
        self.manual_players_entry.grid(row=1, column=1, padx=12, pady=4, sticky="ew")

        ctk.CTkLabel(self.manual_frame, text=self._t("Max Players:", "Maksimum Oyuncu:")).grid(
            row=2, column=0, padx=12, pady=4, sticky="w"
        )
        self.manual_max_entry = ctk.CTkEntry(self.manual_frame)
        self.manual_max_entry.grid(row=2, column=1, padx=12, pady=4, sticky="ew")

        ctk.CTkLabel(self.manual_frame, text=self._t("Active Map:", "Harita Adı:")).grid(
            row=3, column=0, padx=12, pady=(4, 10), sticky="w"
        )
        self.manual_map_combo = ctk.CTkComboBox(self.manual_frame, values=MAP_CHOICES)
        self.manual_map_combo.grid(row=3, column=1, padx=12, pady=(4, 10), sticky="ew")

    def _build_format_tab(self) -> None:
        tab = self.tab_format
        tab.grid_columnconfigure(0, weight=1)

        box = ctk.CTkFrame(tab, corner_radius=8)
        box.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        box.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            box,
            text=self._t("  Status Format & Refresh Settings", "  Görünüm Şablonları ve Yenileme Ayarları"),
            image=self.dot_blue,
            compound="left",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=12, pady=(12, 8), sticky="w")

        ctk.CTkLabel(box, text=self._t("Server Status Template:", "Sunucu Durum Şablonu:")).grid(
            row=1, column=0, padx=12, pady=6, sticky="w"
        )
        self.srv_tpl_entry = ctk.CTkEntry(box)
        self.srv_tpl_entry.grid(row=1, column=1, padx=12, pady=6, sticky="ew")

        ctk.CTkLabel(box, text=self._t("Offline Status Text:", "Çevrimdışı Durum Yazısı:")).grid(
            row=2, column=0, padx=12, pady=6, sticky="w"
        )
        self.srv_off_entry = ctk.CTkEntry(box)
        self.srv_off_entry.grid(row=2, column=1, padx=12, pady=6, sticky="ew")

        ctk.CTkLabel(box, text=self._t("Member Bot Template:", "Üye Sayısı Bot Şablonu:")).grid(
            row=3, column=0, padx=12, pady=6, sticky="w"
        )
        self.mem_tpl_entry = ctk.CTkEntry(box)
        self.mem_tpl_entry.grid(row=3, column=1, padx=12, pady=6, sticky="ew")

        ctk.CTkLabel(box, text=self._t("Refresh Interval (sec):", "Yenileme Sıklığı (sn):")).grid(
            row=4, column=0, padx=12, pady=6, sticky="w"
        )
        self.interval_entry = ctk.CTkEntry(box, width=100)
        self.interval_entry.grid(row=4, column=1, padx=12, pady=6, sticky="w")

        self.suffix_switch = ctk.CTkSwitch(
            box,
            text=self._t(
                "Append 'Map' / 'Haritası' suffix to map names automatically",
                "Harita adlarının sonuna otomatik 'Haritası' / 'Map' ekle",
            ),
            command=self._update_live_preview,
        )
        self.suffix_switch.grid(row=5, column=0, columnspan=2, padx=12, pady=(8, 12), sticky="w")

    def _build_discord_preview_card(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(parent, corner_radius=10, fg_color="#1e1f22")
        card.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text=self._t(
                "  DISCORD SIDEBAR LIVE PREVIEW",
                "  DISCORD ÜYE LİSTESİ CANLI ÖNİZLEME",
            ),
            image=self.dot_green,
            compound="left",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#949ba4",
        ).grid(row=0, column=0, padx=14, pady=(10, 4), sticky="w")

        for i in range(1, MAX_BOTS + 1):
            row_frame = ctk.CTkFrame(card, corner_radius=7, fg_color="#2b2d31")
            row_frame.grid(row=i, column=0, sticky="ew", padx=12, pady=3)
            row_frame.grid_columnconfigure(1, weight=1)

            dot_lbl = ctk.CTkLabel(
                row_frame,
                text="",
                image=self.dot_red,
                width=24,
            )
            dot_lbl.grid(row=0, column=0, rowspan=2, padx=(10, 4), pady=4)

            name_lbl = ctk.CTkLabel(
                row_frame,
                text=f"Bot #{i}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#a855f7",
                anchor="w",
            )
            name_lbl.grid(row=0, column=1, sticky="w", padx=4, pady=(3, 0))

            badge_lbl = ctk.CTkLabel(
                row_frame,
                text="APP" if self.lang == "en" else "UYG",
                font=ctk.CTkFont(size=9, weight="bold"),
                fg_color="#5865f2",
                text_color="#ffffff",
                corner_radius=4,
                width=32,
                height=16,
            )
            badge_lbl.grid(row=0, column=2, padx=8, pady=(3, 0), sticky="e")

            # Rich multi-color status line with true green & red graphical dots!
            st_line = ctk.CTkFrame(row_frame, fg_color="transparent")
            st_line.grid(row=1, column=1, columnspan=2, sticky="w", padx=4, pady=(0, 4))

            g_dot = ctk.CTkLabel(st_line, text="", image=self.dot_sm_green, width=13)
            g_dot.pack(side="left", padx=(0, 2))

            part1_lbl = ctk.CTkLabel(
                st_line,
                text="『0/60』•",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#f0f4f8",
            )
            part1_lbl.pack(side="left", padx=(0, 3))

            r_dot = ctk.CTkLabel(st_line, text="", image=self.dot_sm_red, width=13)
            r_dot.pack(side="left", padx=(0, 3))

            part2_lbl = ctk.CTkLabel(
                st_line,
                text="Syria Map",
                font=ctk.CTkFont(size=11),
                text_color="#dbdee1",
            )
            part2_lbl.pack(side="left")

            self.preview_cards.append(
                {
                    "frame": row_frame,
                    "dot": dot_lbl,
                    "name": name_lbl,
                    "part1": part1_lbl,
                    "part2": part2_lbl,
                }
            )

    def _build_log_panel(self, parent: ctk.CTkFrame) -> None:
        log_frame = ctk.CTkFrame(parent, corner_radius=10)
        log_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(6, 12))
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            log_frame,
            text=self._t("  System & Connection Logs (Live)", "  Sistem & Bağlantı Kayıtları (Canlı Log)"),
            image=self.dot_yellow,
            compound="left",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, padx=12, pady=(8, 4), sticky="w")

        self.log_box = ctk.CTkTextbox(
            log_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#0f1117",
            text_color="#e2e8f0",
        )
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        for line in self._saved_logs[-120:]:
            self.log_box.insert("end", line + "\n")
        self.log_box.see("end")

    def _load_values_into_ui(self) -> None:
        self.bot_count_seg.set(str(self.cfg.get("active_bot_count", MAX_BOTS)))
        self.guild_id_entry.delete(0, "end")
        self.guild_id_entry.insert(0, str(self.cfg.get("discord_guild_id", "")))

        default_maps = {1: "Syria", 2: "Caucasus", 3: "PersianGulf", 4: "Sinai", 5: "Kola"}
        default_ports = {1: 42428, 2: 42429, 3: 42430, 4: 42431, 5: 42432}

        for idx, row in enumerate(self.bot_rows, start=1):
            t_key = TOKEN_KEYS[idx - 1]
            tok_val = str(self.cfg.get(t_key, "")).strip()
            row["token_entry"].delete(0, "end")
            if tok_val:
                row["token_entry"].insert(0, tok_val)

            b_type = str(self.cfg.get(f"bot{idx}_type", "member" if idx == 5 else "dcs")).lower()
            if self.lang == "en":
                row["type_combo"].set("Discord Member Count" if b_type == "member" else "DCS Server Status")
            else:
                row["type_combo"].set("Discord Üye Sayısı" if b_type == "member" else "DCS Sunucu Durumu")

            row["map_combo"].set(str(self.cfg.get(f"bot{idx}_map", default_maps[idx])))

            row["maxp_entry"].delete(0, "end")
            row["maxp_entry"].insert(0, str(self.cfg.get(f"bot{idx}_max_players", 60)))

            row["port_entry"].delete(0, "end")
            row["port_entry"].insert(0, str(self.cfg.get(f"bot{idx}_port", default_ports[idx])))

        self.local_path_combo.set(str(self.cfg.get("dcs_saved_games_path", "")))
        self.remote_ip_entry.delete(0, "end")
        self.remote_ip_entry.insert(0, str(self.cfg.get("remote_ip", "127.0.0.1")))
        self.remote_port_entry.delete(0, "end")
        self.remote_port_entry.insert(0, str(self.cfg.get("remote_port", 42428)))
        self.secret_key_entry.delete(0, "end")
        self.secret_key_entry.insert(0, str(self.cfg.get("remote_secret_key", "")))

        self.manual_players_entry.delete(0, "end")
        self.manual_players_entry.insert(0, str(self.cfg.get("manual_players", 0)))
        self.manual_max_entry.delete(0, "end")
        self.manual_max_entry.insert(0, str(self.cfg.get("manual_max_players", 60)))
        self.manual_map_combo.set(str(self.cfg.get("manual_map", "Syria")))

        self.srv_tpl_entry.delete(0, "end")
        self.srv_tpl_entry.insert(0, str(self.cfg.get("server_status_template", "🟢『{players}/{max_players}』• 🔴 {map}")))
        self.srv_off_entry.delete(0, "end")
        self.srv_off_entry.insert(
            0,
            str(
                self.cfg.get(
                    "server_offline_text",
                    "🔴 Server Offline" if self.lang == "en" else "🔴 Sunucu Çevrimdışı",
                )
            ),
        )
        self.mem_tpl_entry.delete(0, "end")
        self.mem_tpl_entry.insert(
            0,
            str(
                self.cfg.get(
                    "member_status_template",
                    "🟢『{members}』• 🔴 Members" if self.lang == "en" else "🟢『{members}』• 🔴 Üye",
                )
            ),
        )
        self.interval_entry.delete(0, "end")
        self.interval_entry.insert(0, str(self.cfg.get("update_interval_seconds", 8)))
        if self.cfg.get("append_haritasi_suffix", True):
            self.suffix_switch.select()
        else:
            self.suffix_switch.deselect()

        self._refresh_hook_status_label()

    def _update_mode_visibility(self) -> None:
        m = self.mode_var.get()
        self.local_frame.grid_remove()
        self.remote_frame.grid_remove()
        self.manual_frame.grid_remove()
        if m == "local":
            self.local_frame.grid()
        elif m == "remote":
            self.remote_frame.grid()
        else:
            self.manual_frame.grid()
        self._update_live_preview()

    def _refresh_hook_status_label(self) -> None:
        p = self.local_path_combo.get().strip()
        if p and check_hook_installed(p):
            self.hook_status_lbl.configure(
                text=self._t(
                    f"  AsilTurq_DCS_StatusHook.lua installed ({p}\\Scripts\\Hooks)",
                    f"  AsilTurq_DCS_StatusHook.lua kurulu ({p}\\Scripts\\Hooks)",
                ),
                image=self.dot_green,
                text_color="#22c55e",
            )
        else:
            self.hook_status_lbl.configure(
                text=self._t(
                    "  Hook script not installed in this folder yet (Click button below to install)",
                    "  Bu klasörde henüz Hook kurulu değil (Kurmak için aşağıdaki butona tıklayın)",
                ),
                image=self.dot_yellow,
                text_color="#eab308",
            )

    def _update_live_preview(self) -> None:
        self._collect_current_form_into_cfg()
        for idx, card in enumerate(self.preview_cards, start=1):
            t_key = TOKEN_KEYS[idx - 1]
            has_tok = bool(str(self.cfg.get(t_key, "")).strip())
            b_state = self.bot_manager.bot_states.get(idx, {})
            b_type = str(self.cfg.get(f"bot{idx}_type", "dcs")).lower()
            map_raw = str(self.cfg.get(f"bot{idx}_map", "Syria"))

            if b_state.get("online"):
                card["dot"].configure(image=self.dot_green)
            elif has_tok:
                card["dot"].configure(image=self.dot_yellow)
            else:
                card["dot"].configure(image=self.dot_red)

            if b_type == "member":
                title_str = b_state.get("name") if b_state.get("online") else self._t(f"Bot #{idx} — Member Count", f"Bot #{idx} — Üye Sayısı")
                cnt = self.bot_manager.last_member_count or 3011
                p1 = f"『{cnt}』•"
                p2 = "Members" if self.lang == "en" else "Üye"
            else:
                title_str = b_state.get("name") if b_state.get("online") else f"Bot #{idx} — DCS {map_raw}"
                st = get_dcs_status_for_bot(self.cfg, idx)
                p1 = f"『{st.players}/{st.max_players}』•"
                p2 = st.formatted_map

            if not has_tok:
                p2 = f"{p2}   [{self._t('Ready — Enter Token', 'Hazır — Token Girin')}]"

            card["name"].configure(text=title_str)
            card["part1"].configure(text=p1)
            card["part2"].configure(text=p2)

    def _paste_into_entry(self, entry: ctk.CTkEntry) -> None:
        try:
            clip = self.clipboard_get().strip()
            if clip:
                entry.delete(0, "end")
                entry.insert(0, clip)
                self._update_live_preview()
        except Exception:
            pass

    def _toggle_token_visibility(self, entry: ctk.CTkEntry, btn: ctk.CTkButton) -> None:
        if entry.cget("show") == "•":
            entry.configure(show="")
            btn.configure(text=self._t("Hide", "Gizle"))
        else:
            entry.configure(show="•")
            btn.configure(text=self._t("Show", "Göster"))

    def _on_clear_all_tokens(self) -> None:
        for row in self.bot_rows:
            row["token_entry"].delete(0, "end")
        for k in TOKEN_KEYS:
            self.cfg[k] = ""
        save_config(self.cfg)
        self._update_live_preview()
        self.append_log_threadsafe(
            self._t("🟢 All bot tokens cleared from configuration.", "🟢 Tüm bot tokenları temizlendi.")
        )

    def _on_browse_saved_games(self) -> None:
        chosen = filedialog.askdirectory(title=self._t("Select Saved Games\\DCS Folder", "Saved Games\\DCS Klasörü Seçin"))
        if chosen:
            self.local_path_combo.set(chosen)
            self._refresh_hook_status_label()

    def _on_install_hook_local(self) -> None:
        target = self.local_path_combo.get().strip()
        if not target:
            return
        ok, msg = install_dcs_hook(target, allow_remote=False, lang=self.lang)
        self._refresh_hook_status_label()
        self.append_log_threadsafe(f"{'🟢' if ok else '🔴'} {msg}")

    def _on_test_dcs_connection(self) -> None:
        self._collect_current_form_into_cfg()
        st = get_dcs_status(self.cfg)
        txt = build_server_status_text(self.cfg, st)
        self.append_log_threadsafe(
            self._t(
                f"🔵 [TEST] Mode={st.source_mode} | Online={st.online} | Status={txt}",
                f"🔵 [TEST] Mod={st.source_mode} | Online={st.online} | Durum={txt}",
            )
        )
        self._update_live_preview()

    def on_save_config(self) -> None:
        self._collect_current_form_into_cfg()
        save_config(self.cfg)
        self.bot_manager.update_config(self.cfg)
        self._update_live_preview()
        self.append_log_threadsafe(
            self._t("🟢 Settings saved and applied successfully!", "🟢 Ayarlar başarıyla kaydedildi ve uygulandı!")
        )

    def on_start_bots(self) -> None:
        self._collect_current_form_into_cfg()
        save_config(self.cfg)
        self.bot_manager.config = self.cfg
        ok, msg = self.bot_manager.start_in_background()
        if not ok:
            messagebox.showwarning(self._t("Warning", "Uyarı"), msg)
            return
        self.status_badge.configure(
            text=self._t("  RUNNING", "  ÇALIŞIYOR"),
            image=self.dot_green,
            text_color="#22c55e",
        )
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.append_log_threadsafe(f"🟢 {msg}")

    def on_stop_bots(self) -> None:
        self.bot_manager.stop()
        self.status_badge.configure(
            text=self._t("  STOPPED", "  DURDURULDU"),
            image=self.dot_red,
            text_color="#ef4444",
        )
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self._update_live_preview()

    def append_log_threadsafe(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {message}"
        self._saved_logs.append(line)
        try:
            self.after(0, lambda: self._append_log_ui(line))
        except Exception:
            pass

    def _append_log_ui(self, line: str) -> None:
        if hasattr(self, "log_box") and self.log_box.winfo_exists():
            self.log_box.insert("end", line + "\n")
            self.log_box.see("end")

    def refresh_preview_threadsafe(self) -> None:
        try:
            self.after(0, self._update_live_preview)
        except Exception:
            pass

    def _on_close(self) -> None:
        try:
            if self.bot_manager.is_running:
                self.bot_manager.stop()
        except Exception:
            pass
        self.destroy()
