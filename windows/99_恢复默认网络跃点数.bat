@echo off
chcp 65001 >nul
title 恢复默认网络跃点数

:: 自动检测并请求管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在请求管理员权限...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo 正在恢复「WLAN」和「以太网」为 Windows 自动跃点数...
netsh interface ipv4 set interface "WLAN" metric=auto >nul 2>&1
netsh interface ipv6 set interface "WLAN" metric=auto >nul 2>&1
netsh interface ipv4 set interface "以太网" metric=auto >nul 2>&1
netsh interface ipv6 set interface "以太网" metric=auto >nul 2>&1

echo.
echo 已恢复默认网络设置！
pause
