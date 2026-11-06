# 📂 Configuration Templates / Örnek Yapılandırma Şablonları (EN / TR)

## <img src="../docs/flag_en.png" width="22" valign="middle"/> ENGLISH — Template Guide

These sanitized example YAML files are provided for server administrators who also run **DCSServerBot** alongside **`DCS_StatusBot`**. Every file contains bilingual (`[EN]` & `[TR]`) comments and zero personal credentials:

1. **[`bot.example.yaml`](bot.example.yaml)** -> Copy to `config/services/bot.yaml`
   * Paste your Discord `guild_id` (Server ID), main bot `token`, `owner` User ID, admin role names/IDs, and `audit_channel` ID.
2. **[`nodes.example.yaml`](nodes.example.yaml)** -> Copy to `config/nodes.yaml`
   * Set `locale: en` (or `tr`), your server `public_ip`, `DCS` installation folder, and your server instances (`10308`, `10309`, `10310` and WebGUI `8088`, `8089`, `8090`).
3. **[`servers.example.yaml`](servers.example.yaml)** -> Copy to `config/servers.yaml`
   * Paste your Discord `status`, `chat`, and `admin` channel IDs for each DCS server.

---

## <img src="../docs/flag_tr.png" width="22" valign="middle"/> TÜRKÇE — Şablon Kılavuzu

Bu klasördeki örnek YAML dosyaları, **`DCS_StatusBot`** ile birlikte **DCSServerBot** kullanan sunucu yöneticileri için hazırlanmış temiz (tokensız) şablonlardır. Her dosyanın içinde hem İngilizce (`[EN]`) hem Türkçe (`[TR]`) açıklamalar yer alır:

1. **[`bot.example.yaml`](bot.example.yaml)** -> `config/services/bot.yaml` konumuna kopyalayın
   * Discord `guild_id` (Sunucu ID), `token` (Ana Bot Token), `owner` (Kurucu Kullanıcı ID), yönetici rol adları/ID'leri ve `audit_channel` (Denetim Kanalı ID) bilgilerinizi girin.
2. **[`nodes.example.yaml`](nodes.example.yaml)** -> `config/nodes.yaml` konumuna kopyalayın
   * `locale: tr` (veya `en`), sunucu `public_ip` adresi, `DCS` kurulum dizini ve sunucu profillerinizi (`10308`, `10309`, `10310` ve WebGUI `8088`, `8089`, `8090`) düzenleyin.
3. **[`servers.example.yaml`](servers.example.yaml)** -> `config/servers.yaml` konumuna kopyalayın
   * Her DCS sunucusu için Discord `status` (durum tablosu), `chat` (oyun içi sohbet) ve `admin` (yönetici komut) kanal ID numaralarını yapıştırın.
