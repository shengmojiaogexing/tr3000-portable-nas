@echo off
chcp 65001 >nul
title EasyTier P2P 外网直连 TR3000 硬盘

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 创建虚拟网卡需要管理员权限。
    echo 请右键点击本文件，选择「以管理员身份运行」！
    echo.
    pause
    exit /b 1
)

echo ============================================================
echo   正在通过 EasyTier (IPv4/IPv6 P2P 打洞 + VPS 私有中继)
echo   连接你的 TR3000 便携 NAS (10.126.126.1) ...
echo ============================================================
echo.
echo   连接成功后（约 3~5 秒），不要关闭此黑框，直接在文件资源管理器输入：
echo     \\10.126.126.1\备份
echo     \\10.126.126.1\数据存储中心
echo     \\10.126.126.1\USB_Disk
echo   SMB 账号: admin   密码: 你设置的 SMB 密码 (默认 YOUR_NAS_PASSWORD)
echo.
echo   按 Ctrl + C 可随时断开退出。
echo ============================================================
echo.

"%~dp0easytier\easytier-windows-x86_64\easytier-core.exe" ^
  --network-name tr3000-nas ^
  --network-secret YOUR_NAS_PASSWORD ^
  -d ^
  -p tcp://YOUR_VPS_IP:11010 ^
  -p udp://YOUR_VPS_IP:11010

pause
