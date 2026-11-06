import asyncio
import asyncio.sslproto
import socket
import struct
import threading
import traceback
from datetime import datetime
from typing import Callable, Dict, Any, Optional, Tuple, List

_orig_process_outgoing = asyncio.sslproto.SSLProtocol._process_outgoing


def _patched_process_outgoing(self):
    if not getattr(self, "_sni_split_done", False):
        self._sni_split_done = True
        data = self._outgoing.read()
        if data:
            idx = data.find(b"discord")
            if idx != -1 and data[0] == 0x16 and self._transport is not None:
                sock = self._transport.get_extra_info("socket")
                if sock:
                    try:
                        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    except Exception:
                        pass
                rec_ver = data[1:3]
                rec_len = struct.unpack("!H", data[3:5])[0]
                payload = data[5 : 5 + rec_len]
                rest = data[5 + rec_len :]
                p_idx = payload.find(b"discord") + 2
                part1 = b"\x16" + rec_ver + struct.pack("!H", p_idx) + payload[:p_idx]
                part2 = b"\x16" + rec_ver + struct.pack("!H", len(payload) - p_idx) + payload[p_idx:] + rest
                self._transport.write(part1)
                self._loop.call_later(0.01, self._transport.write, part2)
                return
            elif self._transport is not None:
                self._transport.write(data)
                return
    _orig_process_outgoing(self)


asyncio.sslproto.SSLProtocol._process_outgoing = _patched_process_outgoing

import aiohttp

_orig_tcp_init = aiohttp.TCPConnector.__init__


def _patched_tcp_init(self, *args, **kwargs):
    kwargs["family"] = socket.AF_INET
    _orig_tcp_init(self, *args, **kwargs)


aiohttp.TCPConnector.__init__ = _patched_tcp_init

import discord
from core.config_manager import load_config
from core.dcs_provider import get_dcs_status, get_dcs_status_for_bot, DCSServerStatus

MAX_BOTS = 5
TOKEN_KEYS = [
    "server_bot_token",
    "member_bot_token",
    "third_bot_token",
    "fourth_bot_token",
    "fifth_bot_token",
]


def detect_vpn_local_ip() -> Optional[str]:
    return None


def create_discord_activity(activity_type: str, text: str) -> discord.BaseActivity:
    act_type = (activity_type or "custom").lower().strip()
    if act_type == "custom":
        return discord.CustomActivity(name=text)
    elif act_type == "watching":
        return discord.Activity(type=discord.ActivityType.watching, name=text)
    elif act_type == "listening":
        return discord.Activity(type=discord.ActivityType.listening, name=text)
    else:
        return discord.Game(name=text)


def create_discord_status(presence_str: str) -> discord.Status:
    p = (presence_str or "online").lower().strip()
    if p == "idle":
        return discord.Status.idle
    elif p in ("dnd", "do_not_disturb"):
        return discord.Status.dnd
    return discord.Status.online


DIGIT_STYLES = {
    "bold": str.maketrans("0123456789", "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"),
    "double": str.maketrans("0123456789", "𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡"),
    "mono": str.maketrans("0123456789", "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"),
}


def stylize_number(val: Any, style: str = "bold") -> str:
    s = str(val)
    trans = DIGIT_STYLES.get((style or "bold").lower().strip())
    return s.translate(trans) if trans else s


def build_server_status_text(cfg: Dict[str, Any], dcs_state: DCSServerStatus, tag: str = "") -> str:
    lang = str(cfg.get("language", "en")).lower().strip()
    if not dcs_state.online:
        prefix = f"{tag} " if tag else ""
        default_off = "🔴 Server Offline" if lang == "en" else "🔴 Sunucu Çevrimdışı"
        off_txt = cfg.get("server_offline_text", default_off)
        if lang == "en" and off_txt == "🔴 Sunucu Çevrimdışı":
            off_txt = "🔴 Server Offline"
        elif lang == "tr" and off_txt == "🔴 Server Offline":
            off_txt = "🔴 Sunucu Çevrimdışı"
        return f"{prefix}{off_txt}"

    num_style = str(cfg.get("number_style", "bold"))
    p_str = stylize_number(dcs_state.players, num_style)
    mp_str = stylize_number(dcs_state.max_players, num_style)

    if tag:
        template = str(cfg.get("multi_server_template", "🟢 {tag}『{players}/{max_players}』• 🔴 {map}"))
    else:
        template = str(cfg.get("server_status_template", "🟢『{players}/{max_players}』• 🔴 {map}"))

    try:
        text = template.format(
            tag=tag,
            players=p_str,
            max_players=mp_str,
            map=dcs_state.formatted_map,
            raw_map=dcs_state.raw_map,
            mission=dcs_state.mission_name or dcs_state.formatted_map,
            server_name=dcs_state.server_name,
        )
        return text
    except Exception:
        return f"🟢 {tag + ' ' if tag else ''}『{p_str}/{mp_str}』• 🔴 {dcs_state.formatted_map}"


def build_member_status_text(cfg: Dict[str, Any], member_count: int) -> str:
    lang = str(cfg.get("language", "en")).lower().strip()
    num_style = str(cfg.get("number_style", "bold"))
    m_str = stylize_number(member_count, num_style)
    default_tpl = "🟢『{members}』• 🔴 Members" if lang == "en" else "🟢『{members}』• 🔴 Üye"
    template = str(cfg.get("member_status_template", default_tpl))
    if lang == "en" and "Üye" in template:
        template = template.replace("Üye", "Members")
    elif lang == "tr" and "Members" in template:
        template = template.replace("Members", "Üye")
    try:
        return template.format(members=m_str, member_count=m_str)
    except Exception:
        return f"🟢『{m_str}』• 🔴 {'Members' if lang == 'en' else 'Üye'}"


class DCSServerStatusBot(discord.Client):
    def __init__(
        self,
        manager: "DualBotManager",
        bot_index: int = 1,
        connector: Optional[aiohttp.BaseConnector] = None,
    ):
        intents = discord.Intents.none()
        intents.guilds = True
        super().__init__(intents=intents, connector=connector)
        self.manager = manager
        self.bot_index = bot_index
        self.bg_task: Optional[asyncio.Task] = None
        self.last_status_text: str = ""

    async def setup_hook(self) -> None:
        self.bg_task = self.loop.create_task(self._status_loop())

    async def on_ready(self) -> None:
        lang = str(self.manager.config.get("language", "en")).lower().strip()
        bot_name = str(self.user.display_name if self.user else f"Bot #{self.bot_index}")
        self.manager.bot_states[self.bot_index]["name"] = bot_name
        self.manager.bot_states[self.bot_index]["online"] = True
        if lang == "en":
            self.manager.log(f"🟢 [BOT #{self.bot_index}] Online -> {self.user} (ID: {self.user.id})")
        else:
            self.manager.log(f"🟢 [{self.bot_index}. BOT] Aktif -> {self.user} (ID: {self.user.id})")
        self.manager.notify_state()

    async def refresh_once(self) -> None:
        cfg = self.manager.config
        lang = str(cfg.get("language", "en")).lower().strip()
        dcs_state = await asyncio.to_thread(get_dcs_status_for_bot, cfg, self.bot_index)
        if self.bot_index == 1:
            self.manager.last_dcs_state = dcs_state

        status_text = build_server_status_text(cfg, dcs_state)
        self.last_status_text = status_text
        self.manager.bot_states[self.bot_index]["status_text"] = status_text
        self.manager.bot_states[self.bot_index]["online"] = dcs_state.online

        if not dcs_state.online:
            presence = discord.Status.dnd
        elif dcs_state.paused or dcs_state.players == 0:
            presence = create_discord_status(cfg.get("server_empty_presence", "online"))
        else:
            presence = create_discord_status(cfg.get("server_online_presence", "online"))

        activity = create_discord_activity(cfg.get("server_activity_type", "custom"), status_text)
        await self.change_presence(status=presence, activity=activity)
        if lang == "en":
            self.manager.log(f"🟢 [BOT #{self.bot_index} - {dcs_state.raw_map.upper()}] Updated -> {status_text}")
        else:
            self.manager.log(f"🟢 [{self.bot_index}. BOT - {dcs_state.raw_map.upper()}] Güncellendi -> {status_text}")
        self.manager.notify_state()

    async def _status_loop(self) -> None:
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                self.manager.config = load_config()
                await self.refresh_once()
            except asyncio.CancelledError:
                break
            except Exception as e:
                lang = str(self.manager.config.get("language", "en")).lower().strip()
                self.manager.log(
                    f"🔴 [BOT #{self.bot_index}] Error: {e}"
                    if lang == "en"
                    else f"🔴 [{self.bot_index}. BOT] Hata: {e}"
                )

            interval = max(5, int(self.manager.config.get("update_interval_seconds", 10) or 10))
            await asyncio.sleep(interval)


class MemberCountStatusBot(discord.Client):
    def __init__(
        self,
        manager: "DualBotManager",
        bot_index: int = 2,
        connector: Optional[aiohttp.BaseConnector] = None,
    ):
        intents = discord.Intents.none()
        intents.guilds = True
        super().__init__(intents=intents, connector=connector)
        self.manager = manager
        self.bot_index = bot_index
        self.bg_task: Optional[asyncio.Task] = None
        self.last_member_count: int = 0
        self.last_status_text: str = ""

    async def setup_hook(self) -> None:
        self.bg_task = self.loop.create_task(self._member_loop())

    async def on_ready(self) -> None:
        lang = str(self.manager.config.get("language", "en")).lower().strip()
        bot_name = str(self.user.display_name if self.user else f"Member Bot #{self.bot_index}")
        self.manager.bot_states[self.bot_index]["name"] = bot_name
        self.manager.bot_states[self.bot_index]["online"] = True
        if lang == "en":
            self.manager.log(f"🟢 [BOT #{self.bot_index} - MEMBERS] Online -> {self.user} (ID: {self.user.id})")
        else:
            self.manager.log(f"🟢 [{self.bot_index}. BOT - ÜYE SAYISI] Aktif -> {self.user} (ID: {self.user.id})")
        self.manager.notify_state()

    async def _resolve_member_count(self) -> int:
        cfg = self.manager.config
        target_guild_id = str(cfg.get("discord_guild_id", "")).strip()

        target_guild: Optional[discord.Guild] = None
        if target_guild_id.isdigit():
            target_guild = self.get_guild(int(target_guild_id))
            if not target_guild:
                try:
                    fetched = await self.fetch_guild(int(target_guild_id), with_counts=True)
                    if fetched and fetched.approximate_member_count is not None:
                        return fetched.approximate_member_count
                except Exception:
                    pass

        if not target_guild and self.guilds:
            target_guild = self.guilds[0]

        if target_guild:
            try:
                fetched = await self.fetch_guild(target_guild.id, with_counts=True)
                if fetched and fetched.approximate_member_count is not None:
                    return fetched.approximate_member_count
            except Exception:
                pass
            if target_guild.member_count:
                return target_guild.member_count

        return 0

    async def refresh_once(self) -> None:
        cfg = self.manager.config
        lang = str(cfg.get("language", "en")).lower().strip()
        count = await self._resolve_member_count()
        self.last_member_count = count
        self.manager.last_member_count = count

        status_text = build_member_status_text(cfg, count)
        self.last_status_text = status_text
        self.manager.bot_states[self.bot_index]["status_text"] = status_text
        self.manager.bot_states[self.bot_index]["online"] = True

        presence = create_discord_status(cfg.get("member_bot_presence", "idle"))
        activity = create_discord_activity(cfg.get("member_activity_type", "custom"), status_text)
        await self.change_presence(status=presence, activity=activity)
        if lang == "en":
            self.manager.log(f"🟡 [BOT #{self.bot_index} - MEMBERS] Updated -> {status_text}")
        else:
            self.manager.log(f"🟡 [{self.bot_index}. BOT - ÜYE] Güncellendi -> {status_text}")
        self.manager.notify_state()

    async def _member_loop(self) -> None:
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                self.manager.config = load_config()
                await self.refresh_once()
            except asyncio.CancelledError:
                break
            except Exception as e:
                lang = str(self.manager.config.get("language", "en")).lower().strip()
                self.manager.log(
                    f"🔴 [BOT #{self.bot_index}] Error: {e}"
                    if lang == "en"
                    else f"🔴 [{self.bot_index}. BOT] Hata: {e}"
                )

            interval = max(10, int(self.manager.config.get("update_interval_seconds", 10) or 10))
            await asyncio.sleep(interval)


class DualBotManager:
    """Manages up to 5 simultaneous Discord Status Bots cleanly."""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        state_callback: Optional[Callable[[], None]] = None,
    ):
        self.config: Dict[str, Any] = config or load_config()
        self.log_callback = log_callback
        self.state_callback = state_callback

        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self.is_running: bool = False

        self.active_clients: List[discord.Client] = []
        self.bot_states: Dict[int, Dict[str, Any]] = {
            i: {"name": f"Bot #{i}", "online": False, "status_text": ""}
            for i in range(1, MAX_BOTS + 1)
        }

        self.last_dcs_state: DCSServerStatus = DCSServerStatus()
        self.last_member_count: int = 0

    def log(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{ts}] {message}"
        try:
            print(formatted)
        except Exception:
            pass
        if self.log_callback:
            try:
                self.log_callback(message)
            except Exception:
                pass

    def notify_state(self) -> None:
        if self.state_callback:
            try:
                self.state_callback()
            except Exception:
                pass

    def update_config(self, new_config: Dict[str, Any]) -> None:
        self.config = new_config
        if self.is_running and self.loop:
            asyncio.run_coroutine_threadsafe(self.force_refresh_now(), self.loop)

    async def force_refresh_now(self) -> None:
        try:
            for client in list(self.active_clients):
                if client and client.is_ready() and hasattr(client, "refresh_once"):
                    await client.refresh_once()
            self.notify_state()
        except Exception as e:
            lang = str(self.config.get("language", "en")).lower().strip()
            self.log(f"🔴 [System] Refresh error: {e}" if lang == "en" else f"🔴 [Sistem] Yenileme hatası: {e}")

    async def run_console_forever(self) -> None:
        self.is_running = True
        try:
            await self._async_main()
        finally:
            self.is_running = False

    def start_in_background(self) -> Tuple[bool, str]:
        lang = str(self.config.get("language", "en")).lower().strip()
        if self.is_running:
            return False, "Bots are already running." if lang == "en" else "Botlar zaten çalışıyor."

        active_count = max(1, min(MAX_BOTS, int(self.config.get("active_bot_count", MAX_BOTS) or MAX_BOTS)))
        tokens = [str(self.config.get(k, "")).strip() for k in TOKEN_KEYS[:active_count]]
        non_empty = [t for t in tokens if t]

        if not non_empty:
            return (
                False,
                "Please enter at least 1 Discord Bot Token in Tab 2!"
                if lang == "en"
                else "Lütfen 2. Sekmeden en az 1 adet Discord Bot Token girin!",
            )

        if len(non_empty) != len(set(non_empty)):
            return (
                False,
                "Each Bot slot must have a unique Discord Token!"
                if lang == "en"
                else "Her Bot yuvası için farklı bir Discord Token girilmelidir!",
            )

        self.is_running = True
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()
        return (
            True,
            f"Starting {len(non_empty)} bot(s)..."
            if lang == "en"
            else f"{len(non_empty)} adet bot başlatılıyor...",
        )

    def _run_event_loop(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._async_main())
        except Exception as e:
            lang = str(self.config.get("language", "en")).lower().strip()
            self.log(f"🔴 [System] Bot loop error: {e}" if lang == "en" else f"🔴 [Sistem] Bot döngüsü hatası: {e}")
            traceback.print_exc()
        finally:
            self.is_running = False
            self.notify_state()
            try:
                self.loop.close()
            except Exception:
                pass
            self.loop = None

    async def _async_main(self) -> None:
        lang = str(self.config.get("language", "en")).lower().strip()
        active_count = max(1, min(MAX_BOTS, int(self.config.get("active_bot_count", MAX_BOTS) or MAX_BOTS)))
        self.active_clients.clear()
        tasks = []

        for idx, t_key in enumerate(TOKEN_KEYS[:active_count], start=1):
            token = str(self.config.get(t_key, "")).strip()
            if not token:
                continue
            bot_type = str(self.config.get(f"bot{idx}_type", "member" if (idx == 2 and self.config.get("second_bot_type") == "member") else "dcs")).lower()
            if bot_type == "member":
                client = MemberCountStatusBot(self, bot_index=idx)
                label = f"BOT #{idx} (MEMBERS)" if lang == "en" else f"{idx}. BOT (ÜYE SAYISI)"
            else:
                map_name = str(self.config.get(f"bot{idx}_map", "Syria")).upper()
                client = DCSServerStatusBot(self, bot_index=idx)
                label = f"BOT #{idx} ({map_name})" if lang == "en" else f"{idx}. BOT ({map_name})"
            self.active_clients.append(client)
            tasks.append(self._run_single_bot(client, token, label))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_single_bot(self, client: discord.Client, token: str, label: str) -> None:
        lang = str(self.config.get("language", "en")).lower().strip()
        try:
            self.log(
                f"🟡 [{label}] Connecting securely to Discord..."
                if lang == "en"
                else f"🟡 [{label}] Discord'a güvenli bağlantı kuruluyor..."
            )
            await client.start(token)
        except discord.LoginFailure:
            self.log(
                f"🔴 [{label}] Invalid Bot Token! Please check Token in Tab 2."
                if lang == "en"
                else f"🔴 [{label}] Geçersiz Bot Token! Lütfen Token'ı kontrol edin."
            )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.log(f"🔴 [{label}] Error: {e}" if lang == "en" else f"🔴 [{label}] Hata: {e}")
        finally:
            if not client.is_closed():
                await client.close()

    def stop(self) -> None:
        lang = str(self.config.get("language", "en")).lower().strip()
        if not self.is_running or not self.loop:
            self.is_running = False
            self.notify_state()
            return

        self.log("🟡 [System] Stopping all bots..." if lang == "en" else "🟡 [Sistem] Tüm botlar durduruluyor...")

        async def _shutdown():
            for c in list(self.active_clients):
                try:
                    if c and not c.is_closed():
                        if getattr(c, "bg_task", None):
                            c.bg_task.cancel()
                        await c.close()
                except Exception:
                    pass
            self.active_clients.clear()

        try:
            future = asyncio.run_coroutine_threadsafe(_shutdown(), self.loop)
            future.result(timeout=5.0)
        except Exception:
            pass

        for i in range(1, MAX_BOTS + 1):
            self.bot_states[i]["online"] = False

        self.is_running = False
        self.notify_state()
        self.log("🟢 [System] All bots stopped successfully." if lang == "en" else "🟢 [Sistem] Tüm botlar başarıyla durduruldu.")
