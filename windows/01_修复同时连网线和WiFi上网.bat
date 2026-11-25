@echo off
chcp 65001 >nul
title TR3000 刷机网络修复工具 (根治插网线断 Wi-Fi)

:: 自动检测并请求管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在请求管理员权限以锁定网卡跃点数...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo ============================================================
echo   TR3000 网口 + Wi-Fi 共存修复工具 (PowerShell 强力锁定版)
echo ============================================================
echo.

echo [1/4] 关闭自动跃点并锁定优先级 (WLAN=5 优先走外网, 以太网=500 仅连路由器)...
powershell -NoProfile -Command "Set-NetIPInterface -InterfaceAlias 'WLAN' -AddressFamily IPv4 -AutomaticMetric Disabled -InterfaceMetric 5; Set-NetIPInterface -InterfaceAlias 'WLAN' -AddressFamily IPv6 -AutomaticMetric Disabled -InterfaceMetric 5; Set-NetIPInterface -InterfaceAlias '以太网' -AddressFamily IPv4 -AutomaticMetric Disabled -InterfaceMetric 500; Set-NetIPInterface -InterfaceAlias '以太网' -AddressFamily IPv6 -AutomaticMetric Disabled -InterfaceMetric 500"

echo [2/4] 将「以太网」设为自动获取 IP (DHCP)...
netsh interface ip set address name="以太网" source=dhcp >nul 2>&1

echo [3/4] 移除「以太网」抢占外网的默认网关路由 (只保留访问 TR3000 的局域网路由)...
powershell -NoProfile -Command "Get-NetRoute -InterfaceAlias '以太网' -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | Remove-NetRoute -Confirm:$false -ErrorAction SilentlyContinue"

echo [4/4] 检查修复结果...
echo.
powershell -NoProfile -Command "Get-NetIPInterface -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -in @('以太网','WLAN') } | Select-Object InterfaceAlias, AutomaticMetric, InterfaceMetric, ConnectionState | Format-Table -AutoSize"
powershell -NoProfile -Command "Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' | Select-Object InterfaceAlias, NextHop, RouteMetric, InterfaceMetric | Format-Table -AutoSize"

echo.
echo 修复完成！现在插上网线连 TR3000 时，Wi-Fi 也会稳稳保持上网不掉线。
pause
