@echo off
chcp 65001 >nul
title DCS_StatusBot - MULTI-SERVER & DISCORD STATUS BOT SUITE
cls
cd /d "%~dp0"

echo ==============================================================================
echo   DCS_StatusBot - MULTI-SERVER ^& DISCORD STATUS BOT SUITE
echo ==============================================================================
echo.
echo   [1/3] Checking Python environment ^& required packages...
python -c "import discord, aiohttp, customtkinter, PIL" >nul 2>&1
if %errorlevel% neq 0 (
    echo   [+] Installing required Python packages ^(discord.py, aiohttp, customtkinter, Pillow^)...
    python -m pip install --upgrade -r requirements.txt
)

echo   [2/3] Preparing configuration files ^& DCS Lua Status Hooks...
if not exist "config.json" (
    if exist "config.example.json" (
        copy /Y "config.example.json" "config.json" >nul
    )
)

echo   [3/3] Launching Master Command Center...
echo.
python main.py
pause
