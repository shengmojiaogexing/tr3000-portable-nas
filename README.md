<div align="center">

# ZERO STUDIO · TR3000 Portable NAS & Cloud Stack

**面向个人摄影工作室与移动创作场景的「Cudy TR3000 便携路由器刷 ImmortalWrt → 双盘位大硬盘热插拔挂载 → 内核态 SMB3 + EasyTier IPv4/IPv6 P2P 打洞 → 公网免脚本 FTP + 在线云盘预览/打包/分享 → 全站 HTTPS 与 Studio 中控台原生集成」一体化开源方案。**

无需昂贵成品 NAS，一台 200 元级 **Cudy TR3000 (MT7981B / 512MB RAM / 2.5G WAN + USB 3.0)** 搭配双盘位移动硬盘盒与一台入门公网 VPS，即可拥有 **局域网高速 SMB、外网 P2P 打洞直连、公网免脚本 FTP、网页在线看图/看视频/整文件夹流式 `.zip` 打包下载、带提取码的公开分享链接**，并可原生无缝接入 [`zero-studio-automation`](https://github.com/shengmojiaogexing/zero-studio-automation) 工作室中控台。

[![License](https://img.shields.io/badge/license-GPL--3.0-blue)](LICENSE)
[![Firmware](https://img.shields.io/badge/ImmortalWrt-24.10.7%20Filogic-6fa8a5)](#一tr3000-刷机与硬件适配)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](#三公网-vps-端部署)
[![P2P](https://img.shields.io/badge/P2P-EasyTier%20%2B%20IPv6%20Direct-c4c698)](#核心特性)
[![UI](https://img.shields.io/badge/UI-ZERO%20STUDIO%20Glassmorphism-e2bac8)](#核心特性)
[![Sponsor](https://img.shields.io/badge/Sponsor-%E8%B5%9E%E8%B5%8F%E6%94%AF%E6%8C%81-ff69b4?logo=githubsponsors)](#支持与赞赏)

</div>

---

> [!CAUTION]
> **刷机与安全提示**
> 1. **闪存批次校验**：2025 年 11 月起生产的 Cudy TR3000 V1（SN 2543 及之后）更换了 `F50L1G41LC` 闪存芯片，**必须**使用 Cudy 官方新版过渡固件与 **OpenWrt / ImmortalWrt 24.10.5 及以上版本**（本方案实测使用 `24.10.7`），切勿刷入老版本固件以防无法启动。
> 2. **445 端口与隐私红线**：国内运营商普遍封锁公网 445 端口且裸露 SMB 存在极高风险，本方案严禁直接暴露 445 到公网，外网 SMB 统一走 **EasyTier 端到端加密 P2P 隧道**。
> 3. **仓库脱敏**：本仓库所有脚本与配置模板均已清除真实 IP、域名、Wi-Fi 密码、SSH 凭据与 Token，部署前请务必替换 `YOUR_*` 占位符并设置强密码。

---

## 📖 目录

- [这是什么](#这是什么)
- [核心特性](#核心特性)
- [系统架构与工作原理](#系统架构与工作原理)
- [服务与端口矩阵](#服务与端口矩阵)
- [快速开始](#快速开始)
  - [一、TR3000 刷机与硬件适配](#一tr3000-刷机与硬件适配)
  - [二、TR3000 端硬盘挂载与 SMB / EasyTier 配置](#二tr3000-端硬盘挂载与-smb--easytier-配置)
  - [三、公网 VPS 端部署（云盘 / 分享 / FTP / 控制面板）](#三公网-vps-端部署云盘--分享--ftp--控制面板)
  - [四、多域名 HTTPS 与 443 端口 SNI 透明分流](#四多域名-https-与-443-端口-sni-透明分流)
  - [五、原生接入 ZERO STUDIO 中控台](#五原生接入-zero-studio-中控台)
- [项目结构](#项目结构)
- [常见问题](#常见问题)
- [支持与赞赏](#支持与赞赏)
- [开源协议](#开源协议)

---

## 💡 这是什么

摄影师出外景、跑漫展或在家修图时，常面临几个痛点：
- 移动硬盘盒接电脑来回拔插麻烦，多设备无法同时访问；
- 成品多盘位 NAS 体积大、价格贵、带不出门；
- 家宽没有公网 IPv4，想让外网朋友免装软件直接预览/下载几 GB 的成片文件夹很困难。

本项目用一台巴掌大的 **Cudy TR3000 V1** 便携路由器 + 双盘位 USB 3.0 硬盘盒 + 一台低配公网 VPS，打通了从底层固件、硬件挂载到公网分享与工作室中控台原生集成的完整链路。

---

## ✨ 核心特性

| 特性 | 说明 |
|---|---|
| ⚡ **内核态高速 SMB3 (`ksmbd`)** | 放弃臃肿的 37MB Samba4，改用 Linux 6.6 内核态 `ksmbd`（仅占 ~300KB 闪存），关闭冲突锁机制完美兼容 WPS / Office 直接打开文档 |
| 💾 **双盘位大硬盘智能热插拔** | 自动识别 4TB / 8TB 等大容量 NTFS / exFAT / ext4 硬盘，自动跳过无用 `EFI` 分区，开启 `ntfs3 force + utf8` 解决 Windows 未安全弹出导致的 dirty 拒挂与中文乱码 |
| 🏷️ **UUID 永久中文别名三端同步** | 按硬盘分区 UUID 绑定自定义中文共享名（如 `对外备份`、`数据存储中心`），修改后 **SMB + FTP + 在线云盘** 三端实时同步，拔插盘符互换不串名 |
| 🌐 **IPv4/IPv6 P2P 打洞 + 私有中继** | 内置 **EasyTier v2.6.4** 私有打洞节点（IPv4/IPv6 优先 P2P 直连，打不通自动走 VPS 加密中继），外网原生 445 端口直接挂载 SMB；预装 **Lucky v2.19.5** 备用 STUN / DDNS |
| ☁️ **ZERO STUDIO 风格在线云盘与分享** | 莫兰迪暗夜毛玻璃 UI + 中空线性 SVG 图标 + 竖屏手机卡片自适应；支持图片/视频（Range 拖动）/音频/PDF/文本在线预览、**整文件夹 `zip -0` 零压缩流式打包下载**、**单文件/文件夹分享链接（支持有效期与提取码）**、**30 天持久化免登录** |
| 🚀 **IPv6 自动探测满速直连** | TR3000 端以原生 C 语言 `uhttpd` 开启 `[::]:18099` 只读高速通道；网页自动探测访客 IPv6 连通性，打通时直连家宽跑满上行（不绕道 VPS），不通则无感回退 |
| 📂 **公网免脚本直连 FTP** | 基于 `pyftpdlib` + `mount --bind` 实体目录绑定 + **GB18030 / UTF-8 自动协商**，Windows 资源管理器、FileZilla 与手机端均中文无乱码，朋友无需跑任何脚本 |
| 🎛️ **TR3000 Web 控制面板 + Studio 原生集成** | 网页一键改硬盘共享名、改 SMB/FTP 密码、改 TR3000 自身 Wi-Fi 热点与上级中继 Wi-Fi；提供 FastAPI `nas_routes.py` 模块**零 iframe 原生集成**进 `zero-studio-automation` 桌面与手机中控台（无微信/QQ 时手机端自动切换显示云盘） |

---

## ⚙️ 系统架构与工作原理

```text
┌───────────────────────────────┐        USB 3.0 (NTFS force+utf8 / exFAT / ext4)
│   双盘位移动硬盘盒 (4TB + 8TB)  │ ─────────────────────────────────────────────┐
└───────────────────────────────┘                                               ▼
                                                        ┌────────────────────────────────────┐
                                                        │   Cudy TR3000 V1 (ImmortalWrt)     │
                                                        │  • ksmbd 内核 SMB3 (:445)          │
                                                        │  • uhttpd IPv6 直连通道 (:18099)   │
                                                        │  • EasyTier 隧道 (10.126.126.1)    │
                                                        │  • Lucky STUN / DDNS (:16601)      │
                                                        └─────────────────┬──────────────────┘
                                                                          │ EasyTier 加密隧道
                                                                          │ + 原生 UTF-8 SSHFS
                                                                          ▼
┌───────────────────────────────┐                       ┌────────────────────────────────────┐
│  监控机 (微信 / QQ / 修图机)   │ ── FRP (:7000) ────▶  │       公网 VPS (Ubuntu 22.04)       │
│  • im-gateway (:8090->18090)  │ ◀─ Worker (:8083) ─── │  • Nginx 443 SNI 透明分流 + HTTPS   │
│  • PS 自动修图 / 拷卡入库      │                       │  • booking-site 官网/预约 (:8080)  │
└───────────────────────────────┘                       │  • control-center 中控台 (:8081)   │
                                                        │  • file_server 云盘/分享 (:18089)  │
                                                        │  • panel_server 设备面板 (:18088)  │
                                                        │  • ftp_server 免脚本 FTP (:2121)   │
                                                        └────────────────────────────────────┘
```

---

## 🧩 服务与端口矩阵

| 模块 | 监听端口 | 推荐域名 | 作用 |
|---|---:|---|---|
| **ZERO STUDIO 对外官网与预约** | `8080` | `https://booking.example.com` | 摄影服务报价、作品图库、自助预约、客户选图 |
| **ZERO STUDIO 统一中控台** | `8081` | `https://studio.booking.example.com`<br>`https://studio.nas.example.com` | 桌面/手机中控台（原生集成 NAS 与分享管理） |
| **修图机 / Worker 专口** | `8083` | — | Nginx 反代至 8080（支持 500MB 大文件回传） |
| **TR3000 在线云盘与分享站** | `18089` | `https://nas.example.com` | 在线预览、整文件夹流式 ZIP、公开分享链接 `/s/<token>` |
| **TR3000 设备控制面板** | `18088` | `https://panel.nas.example.com` | 硬盘重命名、改共享密码、改 Wi-Fi 热点与中继 |
| **公网免脚本 FTP** | `2121` | `ftp://nas.example.com:2121` | 被动端口 `30100-30150`，GB18030/UTF-8 自动协商 |
| **EasyTier 私有 P2P 节点** | `11010` | — | TCP/UDP 私有打洞信令与加密中继 |
| **TR3000 IPv6 直连通道** | `18099` | — | TR3000 本地 `[::]:18099` 只读高速直连下载 |

---

## 🚀 快速开始

### 一、TR3000 刷机与硬件适配

1. **避免插网线时电脑 Wi-Fi 断网**：
   在管理员 PowerShell 中锁定网卡跃点数（或运行 `windows/01_修复同时连网线和WiFi上网.bat`）：
   ```powershell
   Set-NetIPInterface -InterfaceAlias "WLAN" -AddressFamily IPv4 -AutomaticMetric Disabled -InterfaceMetric 5
   Set-NetIPInterface -InterfaceAlias "以太网" -AddressFamily IPv4 -AutomaticMetric Disabled -InterfaceMetric 500
   ```
2. **获取官方固件**（本仓库不分发二进制固件）：
   - Cudy 官方新版过渡固件（解除签名限制）：前往 [Cudy OpenWrt FAQ](https://www.cudy.com/blogs/faq/openwrt-software-download) 下载对应 `TR3000 V1`（128MB）或 `256MB` 过渡包。
   - ImmortalWrt 正式固件：前往 [ImmortalWrt 24.10.7 Filogic](https://downloads.immortalwrt.org/releases/24.10.7/targets/mediatek/filogic/) 下载 `cudy_tr3000-v1-squashfs-sysupgrade.bin`。
3. **两步刷入**：
   - 电脑网线插 TR3000 **1G LAN 口**，登录原厂 `http://192.168.10.1` → 固件升级 → 上传官方过渡固件。
   - 重启后登录 `http://192.168.1.1`（无密码）→ `System → Backup / Flash Firmware` → 上传 ImmortalWrt `24.10.7` 正式版（**务必取消勾选 Keep settings**）。

### 二、TR3000 端硬盘挂载与 SMB / EasyTier 配置

1. 将 `router/` 下的 4 个核心脚本上传至 TR3000 的 `/usr/bin/` 并赋予可执行权限：
   - `tr3000-mount.sh`（NTFS `force + utf8` 热插拔自动挂载，跳过 EFI 分区）
   - `tr3000-sync-shares.sh`（按 `/etc/tr3000_aliases.conf` UUID 别名同步 `ksmbd` 共享）
   - `tr3000-disk-info.sh`（输出分区容量与挂载状态）
   - `tr3000-get-v6.sh`（获取实时公网 IPv6）
2. 在 TR3000 上安装核心组件：
   ```sh
   opkg update
   opkg install ksmbd-server luci-app-ksmbd luci-i18n-ksmbd-zh-cn kmod-tun openssh-sftp-server
   ```
3. 安装 [EasyTier](https://github.com/EasyTier/luci-app-easytier/releases)（`easytier-noweb` + `luci-app-easytier`）与 [Lucky](https://github.com/gdy666/luci-app-lucky/releases)（`arm64`），并在 `/etc/ksmbd/ksmbd.conf.template` 中关闭 `smb2 leases`、`oplocks`、`store dos attributes` 以完美兼容 WPS / Office 直接打开文档。

### 三、公网 VPS 端部署（云盘 / 分享 / FTP / 控制面板）

1. 在 Ubuntu 22.04+ VPS 上安装基础依赖并部署 EasyTier 私有节点（监听 `11010` TCP/UDP，分配内网段 `10.126.126.0/24`）：
   ```bash
   apt-get update && apt-get install -y sshfs zip python3-pyftpdlib nginx
   ```
2. 配置 VPS 到 TR3000 (`10.126.126.1`) 的 SSH 免密登录，将 `vps/tr3000-vps-sync.sh` 放到 `/usr/local/bin/`，它会自动通过原生 UTF-8 **SSHFS** 挂载 `/mnt/tr3000_raw`，再用 `mount --bind` 映射为真实实体中文目录 `/srv/tr3000_files/<别名>`。
3. 将 `vps/panel_server.py`（`18088`）、`vps/file_server.py`（`18089`）、`vps/ftp_server.py`（`2121`）放到 `/opt/tr3000-panel/`，替换其中的占位符后配置 systemd 常驻守护即可。

### 四、多域名 HTTPS 与 443 端口 SNI 透明分流

- 使用 `acme.sh` 通过 `/var/www/acme` 为所有域名签发免费 ECC SSL 证书并自动续期。
- 如果 VPS 的 443 端口已运行其他服务（如代理节点），可参考 `deploy/nginx-https-sni.example.conf` 使用 Nginx `ngx_stream_module` (`ssl_preread on`) 在 443 端口按 SNI 域名透明分流：网站域名进本地 `127.0.0.1:10443` HTTPS，其余流量原样透传给 `127.0.0.1:4443`，互不干扰。

### 五、原生接入 ZERO STUDIO 中控台

将 `studio-integration/nas_routes.py` 放入 `zero-studio-automation/apps/control-center/`，并在 `main.py` 的 `create_app()` 返回前挂载：
```python
from nas_routes import register_nas_routes
register_nas_routes(app, require_session)
```
即可复用中控台登录态，实现无 `iframe`、免二次登录的纯原生云盘浏览、分享与 TR3000 设备管理；手机端中控台在检测到微信/QQ IM 网关离线时，自动隐藏消息页并切换显示原生云盘。

---

## 📂 项目结构

```text
.
├── README.md                              # 项目总览与完整部署文档
├── .gitignore                             # 严格过滤固件、二进制、数据库与个人凭据
├── router/                                # TR3000 (ImmortalWrt) 端脚本
│   ├── setup_tr3000.sh                    # 一键安装与防火墙初始化脚本
│   ├── tr3000-mount.sh                    # 双硬盘 NTFS force+utf8 / exFAT 热插拔挂载
│   ├── tr3000-sync-shares.sh              # 按 UUID 同步中文共享别名到 ksmbd
│   ├── tr3000-disk-info.sh                # 硬盘分区与空间采集脚本
│   └── tr3000-get-v6.sh                   # 公网 IPv6 地址采集脚本
├── vps/                                   # 公网 VPS 端服务源码（全脱敏）
│   ├── file_server.py                     # 在线云盘、流式 ZIP 打包、分享链接与 IPv6 直连
│   ├── panel_server.py                    # TR3000 网页控制面板（改名/改密/改 Wi-Fi）
│   ├── ftp_server.py                      # 免脚本公网 FTP（GB18030/UTF-8 智能协商）
│   └── tr3000-vps-sync.sh                 # UTF-8 SSHFS + mount --bind 实体目录同步
├── studio-integration/                    # ZERO STUDIO 中控台原生集成模块
│   └── nas_routes.py                      # FastAPI 原生 /api/nas/* 路由模块
├── deploy/                                # 部署配置模板（全脱敏）
│   ├── monitor_frpc.example.toml          # 监控机微信/QQ IM 网关穿透模板
│   └── nginx-https-sni.example.conf       # 443 SNI 透明分流 + 多域名 HTTPS 模板
└── windows/                               # Windows 端辅助批处理工具
    ├── 01_修复同时连网线和WiFi上网.bat     # 锁定网卡跃点，插网线刷机不断 Wi-Fi
    ├── 03_外网电脑SMB挂载助手.bat          # 外网电脑快捷挂载 SMB 盘符
    ├── 99_恢复默认网络跃点数.bat           # 还原默认网卡优先级
    └── start_easytier.example.bat         # EasyTier 客户端一键 P2P 直连模板
```

---

## ❓ 常见问题

1. **为什么 8TB NTFS 硬盘插上 TR3000 读不出来？**
   Windows 默认开启快速启动或未安全弹出时，NTFS 分区会带 `dirty` 标志，Linux `ntfs3` 驱动默认拒绝挂载。使用 `router/tr3000-mount.sh` 中的 `-o rw,force,iocharset=utf8` 参数即可强制安全读写并解决中文文件名乱码。
2. **为什么 WPS 直接打开 SMB 里的 `.xls` 报错“文件已损坏或无权限”？**
   `ksmbd` 默认开启的 `smb2 leases`、`oplocks` 和 `store dos attributes` 与 WPS 文件锁存在冲突，在 `/etc/ksmbd/ksmbd.conf.template` 中将这三项设为 `no` 并重启 `ksmbd` 即可解决。
3. **为什么 Windows 资源管理器连 FTP 中文乱码且文件夹显示为快捷方式？**
   Windows 自带 FTP 客户端默认按 GBK 解码且不识别软链接。本方案通过 `mount --bind` 暴露实体文件夹，并在 `vps/ftp_server.py` 中默认使用 `gb18030`、收到 `OPTS UTF8 ON` 时自动切 `utf-8`，同时兼容 Windows 资源管理器与 FileZilla。
4. **外网下载速度慢怎么办？**
   经过海外 VPS 中转时速度受跨国线路限制（约 1~2 MB/s）；给 TR3000 接入支持公网 IPv6（光猫改桥接）的高上行宽带后，网页端会自动触发 **IPv6 直连加速**，或通过 EasyTier 国内 P2P 直连打洞跑满家宽物理上行。

---

## ☕ 支持与赞赏

如果这个便携 NAS 与摄影工作室云端方案帮到了你、为你省下了买成品 NAS 或折腾刷机的时间，欢迎请作者喝杯咖啡，感谢支持开源维护！

<div align="center">
<table>
  <tr>
    <td align="center">
      <img src="docs/sponsor/wechat.jpg" width="220" alt="微信赞赏码" /><br/>
      <sub><b>微信赞赏</b></sub>
    </td>
    <td align="center">
      <img src="docs/sponsor/alipay.jpg" width="220" alt="支付宝赞赏码" /><br/>
      <sub><b>支付宝赞赏</b></sub>
    </td>
  </tr>
</table>
</div>

---

## 📄 开源协议

本项目基于 **[GNU General Public License v3.0 (GPL-3.0)](LICENSE)** 协议开源，配套工作室全链路自动化系统参见 [shengmojiaogexing/zero-studio-automation](https://github.com/shengmojiaogexing/zero-studio-automation)。
