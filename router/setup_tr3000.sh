#!/bin/sh
set -e

SMB_USER="${1:-smbuser}"
SMB_PASS="${2:-Tr3000@1234}"
SMB_EXT_PORT="${3:-1445}"
MOUNT_POINT="/mnt/usb_disk"

echo "============================================================"
echo "  Cudy TR3000 (ImmortalWrt 24.10.7) 一键自动配置脚本"
echo "  SMB 账号: ${SMB_USER}"
echo "  IPv6/外网非标 SMB 端口: ${SMB_EXT_PORT} -> 445"
echo "============================================================"

echo "[1/6] 更新软件源并安装 USB 硬盘驱动、文件系统与 Samba4..."
opkg update || {
    echo "警告：默认源更新失败，请确认 TR3000 的 WAN 口已连上外网！"
    exit 1
}

opkg install \
    kmod-usb-storage \
    kmod-usb-storage-uas \
    kmod-usb3 \
    block-mount \
    blkid \
    kmod-fs-exfat \
    kmod-fs-ntfs3 \
    kmod-fs-ext4 \
    kmod-fs-vfat \
    kmod-nls-utf8 \
    samba4-server \
    luci-app-samba4 \
    luci-i18n-samba4-zh-cn \
    luci-i18n-base-zh-cn \
    luci-i18n-firewall-zh-cn \
    kmod-tun

echo "[2/6] 安装离线推送的 Lucky（IPv4 STUN打洞 + IPv6 DDNS/转发）与 EasyTier（IPv4/IPv6 P2P组网原生SMB）..."
if ls /tmp/tr3000_pkgs/*.ipk >/dev/null 2>&1; then
    opkg install /tmp/tr3000_pkgs/lucky_*.ipk /tmp/tr3000_pkgs/luci-app-lucky*.ipk /tmp/tr3000_pkgs/luci-i18n-lucky*.ipk --force-overwrite || true
    opkg install /tmp/tr3000_pkgs/easytier-noweb_*.ipk /tmp/tr3000_pkgs/luci-app-easytier*.ipk /tmp/tr3000_pkgs/luci-i18n-easytier*.ipk --force-overwrite || true
else
    echo "提示：未检测到 /tmp/tr3000_pkgs 离线包，跳过本地 ipk 安装。"
fi

echo "[3/6] 配置 USB 硬盘盒自动挂载..."
mkdir -p "${MOUNT_POINT}"
uci set fstab.@global[0].anon_mount='1'
uci set fstab.@global[0].auto_mount='1'
uci set fstab.@global[0].delay_root='5'
uci commit fstab

# 写入热插拔脚本：无论插拔哪块 NTFS/exFAT/ext4 硬盘，自动同步链接到 /mnt/usb_disk
cat << 'EOF' > /etc/hotplug.d/block/99-tr3000-usb-link
#!/bin/sh
[ "$ACTION" = "add" ] || [ "$ACTION" = "remove" ] || exit 0
sleep 2
mkdir -p /mnt/usb_disk
# 如果已有 /mnt/sd* 挂载点，自动挂载/软链管理方便 Samba 统一暴露 /mnt
EOF
chmod +x /etc/hotplug.d/block/99-tr3000-usb-link
/etc/init.d/fstab enable || true
/etc/init.d/fstab restart || true

echo "[4/6] 配置 Samba4 (SMB 共享) 与专用访问账号..."
# 创建系统用户（无 Shell 登录权限，仅用于 SMB）
if ! grep -q "^${SMB_USER}:" /etc/passwd; then
    echo "${SMB_USER}:x:1001:1001:SMB User:/mnt:/bin/false" >> /etc/passwd
fi
if ! grep -q "^${SMB_USER}:" /etc/shadow; then
    echo "${SMB_USER}:*:0:0:99999:7:::" >> /etc/shadow
fi
if ! grep -q "^${SMB_USER}:" /etc/group; then
    echo "${SMB_USER}:x:1001:" >> /etc/group
fi

# 设置 Samba 密码
printf "%s\n%s\n" "${SMB_PASS}" "${SMB_PASS}" | smbpasswd -s -a "${SMB_USER}"

# 写入 UCI Samba4 配置：共享整个 /mnt 目录（插上硬盘盒自动出现在子目录里）
uci set samba4.@samba[0].name='TR3000-NAS'
uci set samba4.@samba[0].workgroup='WORKGROUP'
uci set samba4.@samba[0].description='TR3000 Portable NAS'
uci set samba4.@samba[0].interface='lan'
uci set samba4.@samba[0].allow_legacy_protocols='0'

# 清理旧的同路径共享，避免重复
while uci -q delete samba4.@sambashare[0]; do :; done

uci add samba4 sambashare >/dev/null
uci set samba4.@sambashare[-1].name='USB_Disk'
uci set samba4.@sambashare[-1].path='/mnt'
uci set samba4.@sambashare[-1].users="${SMB_USER}"
uci set samba4.@sambashare[-1].read_only='no'
uci set samba4.@sambashare[-1].guest_ok='no'
uci set samba4.@sambashare[-1].create_mask='0666'
uci set samba4.@sambashare[-1].dir_mask='0777'
uci set samba4.@sambashare[-1].force_root='1'
uci commit samba4

# 重要：允许 Samba 监听所有网卡（包含 EasyTier 虚拟网卡与 IPv6 地址，配合防火墙做访问控制）
if [ -f /etc/samba/smb.conf.template ]; then
    sed -i 's/bind interfaces only = yes/bind interfaces only = no/g' /etc/samba/smb.conf.template
    sed -i 's/interfaces = |INTERFACES|/# interfaces = |INTERFACES|/g' /etc/samba/smb.conf.template
fi

/etc/init.d/samba4 enable
/etc/init.d/samba4 restart

echo "[5/6] 配置防火墙：放行 EasyTier 虚拟网口 + IPv6 非标 SMB 转发端口 (${SMB_EXT_PORT})..."
# 放行 EasyTier 虚拟网卡 (tun*) 访问路由器 SMB
uci -q delete firewall.easytier_zone
uci set firewall.easytier_zone=zone
uci set firewall.easytier_zone.name='easytier'
uci set firewall.easytier_zone.input='ACCEPT'
uci set firewall.easytier_zone.output='ACCEPT'
uci set firewall.easytier_zone.forward='ACCEPT'
uci set firewall.easytier_zone.masq='1'
uci add_list firewall.easytier_zone.device='tun+'
uci add_list firewall.easytier_zone.device='easytier+'

uci -q delete firewall.easytier_to_lan
uci set firewall.easytier_to_lan=forwarding
uci set firewall.easytier_to_lan.src='easytier'
uci set firewall.easytier_to_lan.dest='lan'

uci -q delete firewall.lan_to_easytier
uci set firewall.lan_to_easytier=forwarding
uci set firewall.lan_to_easytier.src='lan'
uci set firewall.lan_to_easytier.dest='easytier'

# 放行 IPv6/IPv4 外网访问 Lucky 转发端口（用于 IPv6 非标端口 SMB 与 Lucky 穿透）
uci -q delete firewall.allow_smb_ext
uci set firewall.allow_smb_ext=rule
uci set firewall.allow_smb_ext.name='Allow-SMB-ExtPort'
uci set firewall.allow_smb_ext.src='wan'
uci set firewall.allow_smb_ext.proto='tcp'
uci set firewall.allow_smb_ext.dest_port="${SMB_EXT_PORT}"
uci set firewall.allow_smb_ext.target='ACCEPT'

uci commit firewall
/etc/init.d/firewall restart

echo "[6/6] 启动 Lucky 服务..."
/etc/init.d/lucky enable 2>/dev/null || true
/etc/init.d/lucky restart 2>/dev/null || true

echo ""
echo "============================================================"
echo "  全部安装与基础配置已完成！"
echo "============================================================"
echo "  1. 路由器管理后台： http://192.168.1.1"
echo "  2. 局域网 SMB 地址：\\\\192.168.1.1\\USB_Disk"
echo "     SMB 用户名：${SMB_USER}"
echo "     SMB 密码：  ${SMB_PASS}"
echo "  3. Lucky 后台地址： http://192.168.1.1:16601  (默认账号/密码: 666 / 666)"
echo "     -> 在 Lucky 中可配置："
echo "        (a) STUN 内网穿透（IPv4 P2P 打洞 -> 转发到 127.0.0.1:445）"
echo "        (b) 端口转发（监听 IPv6 TCP ${SMB_EXT_PORT} -> 转发到 127.0.0.1:445）"
echo "        (c) 动态域名 DDNS（自动更新公网 IPv6）"
echo "  4. EasyTier 配置：  在 ImmortalWrt 后台 -> 服务 -> EasyTier 中启用"
echo "     -> 填好你的网络名称和密码，外网电脑/手机装 EasyTier 即可直接用"
echo "        原生 445 端口 SMB 访问：\\\\你的虚拟IP\\USB_Disk"
echo "============================================================"
