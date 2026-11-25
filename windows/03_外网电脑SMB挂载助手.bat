@echo off
chcp 65001 >nul
title 外网电脑 SMB 磁盘挂载助手 (支持非标端口 / EasyTier / IPv6)

echo ============================================================
echo   TR3000 外网 SMB 磁盘挂载助手
echo ============================================================
echo 请选择挂载方式：
echo   [1] EasyTier 组网直连 (推荐：原生 445 端口，Win10/Win11 通用)
echo   [2] IPv6 DDNS 或 Lucky IPv4 STUN 打洞非标端口 (需 Windows 11 24H2+)
echo   [3] 卸载已挂载的 Z: 盘
echo.
set /p "MODE=请输入选项 (1/2/3): "

if "%MODE%"=="3" (
    net use Z: /delete /y
    echo 已卸载 Z: 盘。
    pause
    exit /b
)

set /p "DRIVE=挂载盘符 (直接回车默认 Z:): "
if "%DRIVE%"=="" set "DRIVE=Z:"

set /p "HOST=请输入目标地址 (如 EasyTier 虚拟IP 10.126.126.1 或 DDNS 域名): "
set /p "SHARE=请输入共享文件夹名 (直接回车默认 USB_Disk): "
if "%SHARE%"=="" set "SHARE=USB_Disk"

set /p "SMB_USER=请输入 SMB 用户名 (直接回车默认 smbuser): "
if "%SMB_USER%"=="" set "SMB_USER=smbuser"

set /p "SMB_PASS=请输入 SMB 密码: "

if "%MODE%"=="1" (
    echo.
    echo 正在通过 EasyTier 虚拟网段挂载 \\%HOST%\%SHARE% 到 %DRIVE% ...
    net use %DRIVE% "\\%HOST%\%SHARE%" "%SMB_PASS%" /user:"%SMB_USER%" /persistent:yes
) else if "%MODE%"=="2" (
    set /p "PORT=请输入非标端口号 (如 IPv6 端口 1445 或 Lucky STUN 公网端口): "
    echo.
    echo 正在通过自定义端口 %PORT% 挂载 \\%HOST%\%SHARE% 到 %DRIVE% ...
    net use %DRIVE% "\\%HOST%\%SHARE%" "%SMB_PASS%" /user:"%SMB_USER%" /tcpport:%PORT% /persistent:yes
) else (
    echo 无效选项。
    pause
    exit /b 1
)

if %errorlevel% equ 0 (
    echo.
    echo 挂载成功！现在可以打开「此电脑」直接访问 %DRIVE% 盘！
) else (
    echo.
    echo 挂载失败，请检查：
    echo   1. 地址、端口、账号密码是否正确
    echo   2. 若选 [2]，请确认系统为 Windows 11 24H2 或更新版本（老系统请用方案 [1] EasyTier）
)
pause
