-- ============================================================================
-- AsilTurq DCS World Status Hook (GÜVENLİK KURALLARINA UYGUN SALT-OKUNUR KÖPRÜ)
-- ============================================================================
-- GÜVENLİK ÖNLEMLERİ:
-- 1. SALT-OKUNUR (Read-Only): Dışarıdan hiçbir Lua komutu (dostring vb.) çalıştırmaz.
--    Sadece oyuncu sayısı, maksimum oyuncu ve harita adını okur.
-- 2. RATE-LIMIT (Hız Sınırı): Saniyede en fazla 2 UDP sorgusuna yanıt verir (DDoS/Flood koruması).
-- 3. DOĞRULAMA ANAHTARI (Shared Secret): Uzak sunucu sorgularında yalnızca doğru
--    güvenlik anahtarına ("STATUS:<ANAHTAR>") sahip isteklere yanıt döner.
-- ============================================================================

local lfs = require("lfs")
local socket = require("socket")

local AsilTurqStatus = {}
AsilTurqStatus.udpHost = "127.0.0.1" -- Yerel mod için varsayılan güvenli adres (Uzak erişim için 0.0.0.0 yapılır)
AsilTurqStatus.udpPort = 42428
AsilTurqStatus.secretKey = ""        -- Uzak sunucu modu kullanılıyorsa config ile eşleşen gizli anahtar
AsilTurqStatus.updateInterval = 3.0  -- Saniye
AsilTurqStatus.lastUpdate = 0
AsilTurqStatus.lastUdpReplyTime = 0
AsilTurqStatus.udpSocket = nil

AsilTurqStatus.statusFilePath = lfs.writedir() .. "Logs\\asilturq_dcs_status.json"
AsilTurqStatus.hookConfigPath = lfs.writedir() .. "Config\\asilturq_hook_security.cfg"
AsilTurqStatus.serverSettingsPath = lfs.writedir() .. "Config\\serverSettings.lua"

AsilTurqStatus.state = {
    online = false,
    paused = false,
    players = 0,
    max_players = 60,
    theatre = "Syria",
    mission_name = "Görev Yok",
    server_name = "DCS Server",
    timestamp = 0
}

local function jsonEscape(str)
    if not str then return "" end
    str = tostring(str)
    str = string.gsub(str, "\\", "\\\\")
    str = string.gsub(str, '"', '\\"')
    str = string.gsub(str, "\n", "\\n")
    str = string.gsub(str, "\r", "\\r")
    str = string.gsub(str, "\t", "\\t")
    return str
end

-- Güvenlik yapılandırma dosyasını oku (Uzak mod IP bind ve Secret Key ayarları)
local function loadSecurityConfig()
    pcall(function()
        local f = io.open(AsilTurqStatus.hookConfigPath, "r")
        if f then
            for line in f:lines() do
                local k, v = string.match(line, "^%s*([%w_]+)%s*=%s*(.-)%s*$")
                if k == "BIND_HOST" and v ~= "" then
                    AsilTurqStatus.udpHost = v
                elseif k == "UDP_PORT" and tonumber(v) then
                    AsilTurqStatus.udpPort = tonumber(v)
                elseif k == "SECRET_KEY" then
                    AsilTurqStatus.secretKey = v
                end
            end
            f:close()
        end
    end)
end

local function readServerSettings()
    local maxP = 60
    local srvName = "DCS Server"
    pcall(function()
        local f = io.open(AsilTurqStatus.serverSettingsPath, "r")
        if f then
            local content = f:read("*all")
            f:close()
            if content then
                local mp = string.match(content, '%["maxPlayers"%]%s*=%s*(%d+)')
                if mp then maxP = tonumber(mp) or 60 end
                local sn = string.match(content, '%["name"%]%s*=%s*"([^"]*)"')
                if sn and sn ~= "" then srvName = sn end
            end
        end
    end)
    return maxP, srvName
end

local function buildStatusJson()
    local s = AsilTurqStatus.state
    return string.format(
        '{"online":%s,"paused":%s,"players":%d,"max_players":%d,"theatre":"%s","mission_name":"%s","server_name":"%s","timestamp":%d}',
        s.online and "true" or "false",
        s.paused and "true" or "false",
        s.players or 0,
        s.max_players or 60,
        jsonEscape(s.theatre),
        jsonEscape(s.mission_name),
        jsonEscape(s.server_name),
        os.time()
    )
end

local function refreshStatus(forceOnlineState)
    pcall(function()
        local maxP, srvName = readServerSettings()
        AsilTurqStatus.state.max_players = maxP
        AsilTurqStatus.state.server_name = srvName

        local isServer = DCS.isServer()
        if not isServer then return end
        local isMP = DCS.isMultiplayer()

        if forceOnlineState ~= nil then
            AsilTurqStatus.state.online = forceOnlineState
        else
            AsilTurqStatus.state.online = (isServer or isMP) and true or false
        end

        AsilTurqStatus.state.paused = DCS.getPause() and true or false

        local mission = DCS.getCurrentMission()
        if mission and mission.mission and mission.mission.theatre then
            AsilTurqStatus.state.theatre = tostring(mission.mission.theatre)
        end

        local mName = DCS.getMissionName()
        if mName and mName ~= "" then
            AsilTurqStatus.state.mission_name = tostring(mName)
        end

        local playerList = net.get_player_list()
        local count = 0
        if playerList then
            for _, pid in pairs(playerList) do
                local pInfo = net.get_player_info(pid)
                if pInfo then
                    if pid ~= 1 then
                        count = count + 1
                    end
                end
            end
        end
        AsilTurqStatus.state.players = count
        AsilTurqStatus.state.timestamp = os.time()

        local jsonStr = buildStatusJson()
        local f = io.open(AsilTurqStatus.statusFilePath, "w")
        if f then
            f:write(jsonStr)
            f:close()
        end
    end)
end

local function initUdpServer()
    if AsilTurqStatus.udpSocket then return end
    loadSecurityConfig()
    pcall(function()
        local udp = socket.udp()
        if udp then
            udp:setsockname(AsilTurqStatus.udpHost, AsilTurqStatus.udpPort)
            udp:settimeout(0)
            AsilTurqStatus.udpSocket = udp
            net.log(string.format(
                "[AsilTurq_StatusHook] Guvenli UDP Durum Sunucusu aktif (%s:%d)",
                AsilTurqStatus.udpHost,
                AsilTurqStatus.udpPort
            ))
        end
    end)
end

local function handleUdpRequests()
    if not AsilTurqStatus.udpSocket then return end
    pcall(function()
        local data, ip, port = AsilTurqStatus.udpSocket:receivefrom()
        if not data then return end

        -- Rate-limit: Saniyede maksimum 2 yanıta izin ver (Flood koruması)
        local now = os.clock()
        if (now - AsilTurqStatus.lastUdpReplyTime) < 0.5 then
            return
        end

        local expectedPrefix = "STATUS"
        if AsilTurqStatus.secretKey and AsilTurqStatus.secretKey ~= "" then
            expectedPrefix = "STATUS:" .. AsilTurqStatus.secretKey
        end

        if data == expectedPrefix or (AsilTurqStatus.secretKey == "" and string.sub(data, 1, 6) == "STATUS") then
            AsilTurqStatus.lastUdpReplyTime = now
            local response = buildStatusJson()
            AsilTurqStatus.udpSocket:sendto(response, ip, port)
        end
    end)
end

function AsilTurqStatus.onSimulationStart()
    initUdpServer()
    refreshStatus(true)
end

function AsilTurqStatus.onSimulationStop()
    refreshStatus(false)
end

function AsilTurqStatus.onSimulationPause()
    refreshStatus(true)
end

function AsilTurqStatus.onSimulationResume()
    refreshStatus(true)
end

function AsilTurqStatus.onPlayerConnect(id)
    refreshStatus(true)
end

function AsilTurqStatus.onPlayerDisconnect(id, err_code)
    refreshStatus(true)
end

function AsilTurqStatus.onPlayerChangeSlot(id)
    refreshStatus(true)
end

function AsilTurqStatus.onSimulationFrame()
    handleUdpRequests()
    local now = os.clock()
    if (now - AsilTurqStatus.lastUpdate) >= AsilTurqStatus.updateInterval then
        AsilTurqStatus.lastUpdate = now
        refreshStatus(true)
    end
end

initUdpServer()
refreshStatus(false)
DCS.setUserCallbacks(AsilTurqStatus)
net.log("[AsilTurq_StatusHook] Guvenli salt-okunur modda yuklendi.")
