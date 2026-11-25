#!/usr/bin/env python3
import http.server
import json
import os
import secrets
import subprocess
from http import cookies

PORT = 18088
TR_HOST = "10.126.126.1"
PASS_FILE = "/opt/tr3000-panel/panel_pass.txt"
SESSION_FILE = "/opt/tr3000-panel/sessions_panel.json"
def load_sessions():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as sf:
                return set(json.load(sf))
        except Exception:
            return set()
    return set()

def save_sessions(s):
    os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
    with open(SESSION_FILE, "w", encoding="utf-8") as sf:
        json.dump(list(s), sf)

SESSIONS = load_sessions()

def get_panel_pass():
    if os.path.exists(PASS_FILE):
        with open(PASS_FILE, "r", encoding="utf-8") as f:
            p = f.read().strip()
            if p:
                return p
    return "YOUR_NAS_PASSWORD"

def set_panel_pass(new_pass):
    os.makedirs(os.path.dirname(PASS_FILE), exist_ok=True)
    with open(PASS_FILE, "w", encoding="utf-8") as f:
        f.write(new_pass.strip())

def ssh_tr(cmd, timeout=15):
    full = [
        "ssh", "-i", "/root/.ssh/id_ed25519",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=6",
        "-o", "BatchMode=yes",
        f"root@{TR_HOST}", cmd
    ]
    p = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr

def get_et_status():
    p = subprocess.run(["easytier-cli", "peer"], capture_output=True, text=True, timeout=5)
    return p.stdout.strip()

def safe_shell_arg(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"

HTML_LOGIN = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TR3000 NAS 管理面板 - 登录</title>
<style>
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#161a21,rgba(30,34,43,.76));font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Microsoft YaHei",sans-serif;color:#f8fafc}
.card{background:rgba(30,41,59,.92);border:1px solid rgba(148,163,184,.2);border-radius:16px;padding:32px;width:90%;max-width:380px;box-shadow:0 20px 50px rgba(0,0,0,.4)}
h2{margin:0 0 8px;font-size:22px} p{margin:0 0 22px;color:#8b92a5;font-size:14px}
input{width:100%;box-sizing:border-box;padding:12px 14px;border-radius:10px;border:1px solid #334155;background:#161a21;color:#fff;font-size:15px;margin-bottom:14px}
button{width:100%;padding:12px;border:0;border-radius:10px;background:#6fa8a5;color:#161a21;font-size:15px;font-weight:600;cursor:pointer}
button:hover{background:#85c4c1}
.err{color:#f87171;font-size:13px;margin-bottom:12px;display:none}
</style></head><body>
<div class="card">
  <h2>ZERO STUDIO · TR3000</h2>
  <p>请输入管理密码登录（默认与路由器密码一致）</p>
  <div id="err" class="err">密码错误，请重试</div>
  <input id="pwd" type="password" placeholder="请输入管理密码" onkeydown="if(event.key==='Enter')login()">
  <button onclick="login()">登录面板</button>
</div>
<script>
async function login(){
  const pwd=document.getElementById('pwd').value;
  const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pwd})});
  if(r.ok){location.reload();}else{document.getElementById('err').style.display='block';}
}
</script></body></html>"""

HTML_APP = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ZERO STUDIO · TR3000 设备控制面板</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#161a21;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Microsoft YaHei",sans-serif;padding:20px}
.wrap{max-width:980px;margin:0 auto}
.header{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:20px}
h1{margin:0;font-size:22px;color:#fff}
.badge{display:inline-block;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:600}
.ok{background:rgba(34,197,94,.18);color:#4ade80;border:1px solid rgba(34,197,94,.35)}
.warn{background:rgba(245,158,11,.18);color:#e2bac8;border:1px solid rgba(245,158,11,.35)}
.card{background:rgba(30,34,43,.76);border:1px solid rgba(148,163,184,.18);border-radius:22px;backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);padding:20px;margin-bottom:18px;box-shadow:0 8px 24px rgba(0,0,0,.22)}
.card h2{margin:0 0 14px;font-size:17px;color:#f8fafc;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{padding:11px 10px;text-align:left;border-bottom:1px solid rgba(148,163,184,.15)}
th{color:#8b92a5;font-weight:500;font-size:13px}
input[type=text],input[type=password]{padding:9px 12px;border-radius:999px;border:1px solid #334155;background:#161a21;color:#fff;font-size:14px}
.btn{padding:8px 14px;border:0;border-radius:999px;background:#6fa8a5;color:#161a21;font-size:13px;font-weight:600;cursor:pointer}
.btn:hover{background:#85c4c1}
.btn-green{background:#c4c698}.btn-green:hover{background:#d2d4aa}
.btn-gray{background:#475569}.btn-gray:hover{background:#334155}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}
.kv{background:#161a21;border:1px solid #334155;border-radius:10px;padding:14px}
.kv .k{font-size:12px;color:#8b92a5;margin-bottom:6px}
.kv .v{font-family:Consolas,monospace;font-size:14px;color:#6fa8a5;word-break:break-all}
.field{display:flex;flex-direction:column;gap:6px;margin-bottom:10px}
.field label{font-size:12px;color:#8b92a5}
.toast{position:fixed;top:20px;right:20px;padding:12px 18px;border-radius:10px;background:#c4c698;color:#fff;font-weight:600;box-shadow:0 10px 30px rgba(0,0,0,.35);display:none;z-index:99}
.row-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
pre{background:#161a21;padding:12px;border-radius:10px;overflow-x:auto;font-size:12px;color:#cbd5e1;margin:8px 0 0}
@media(max-width:680px){table,thead,tbody,th,td,tr{display:block}thead{display:none}tr{border:1px solid #334155;border-radius:10px;padding:10px;margin-bottom:10px}td{border:0;padding:5px 0}}
</style></head><body>
<div id="toast" class="toast"></div>
<div class="wrap">
  <div class="header">
    <div>
      <h1>ZERO STUDIO · TR3000 设备控制面板</h1>
      <div style="font-size:13px;color:#8b92a5;margin-top:4px">一站式修改硬盘共享显示名称、SMB 密码、Wi-Fi 热点/中继密码与查看外网 P2P 状态</div>
    </div>
    <div class="row-actions">
      <span id="connBadge" class="badge ok">检测中...</span>
      <button class="btn btn-gray" onclick="logout()">退出登录</button>
    </div>
  </div>

  <div class="card">
    <h2>
      <span>1. 硬盘共享名称管理（例如把 sda1 改成「备份」）</span>
      <button class="btn btn-green" onclick="remount()">重新扫描 / 强制挂载硬盘</button>
    </h2>
    <div style="font-size:13px;color:#8b92a5;margin-bottom:12px">按硬盘 UUID 永久绑定名称，修改后点击「保存并生效」，3 秒内即可在 SMB 中看到新名称（如 <code>\\192.168.1.1\备份</code> 或 <code>\\10.126.126.1\备份</code>）。</div>
    <table>
      <thead><tr><th>设备分区</th><th>容量 / 已用</th><th>格式</th><th>SMB 共享显示名称</th><th>共享开关</th><th>操作</th></tr></thead>
      <tbody id="diskBody"><tr><td colspan="6">正在读取 TR3000 硬盘列表...</td></tr></tbody>
    </table>
  </div>

  <div class="card">
    <h2>2. Wi-Fi 热点与上级中继 Wi-Fi 密码修改</h2>
    <div class="grid">
      <div class="kv">
        <div class="k"><b>TR3000 自身发射的 Wi-Fi 热点（2.4G / 5G）</b></div>
        <div class="field"><label>2.4G Wi-Fi 名称</label><input id="ap24Ssid" type="text" placeholder="TR3000-2.4G"></div>
        <div class="field"><label>5G Wi-Fi 名称</label><input id="ap5Ssid" type="text" placeholder="TR3000-5G"></div>
        <div class="field"><label>新的 Wi-Fi 密码（至少 8 位，2.4G 与 5G 同步更新）</label><input id="apKey" type="text" placeholder="输入新热点密码（至少8位）"></div>
        <button class="btn" onclick="saveApWifi()">保存热点名称与密码</button>
      </div>
      <div class="kv">
        <div class="k"><b>TR3000 连接的上级 Wi-Fi（中继联网）</b></div>
        <div class="field"><label>上级 Wi-Fi 名称（SSID）</label><input id="staSsid" type="text" placeholder="例如 YOUR_UPSTREAM_WIFI_SSID"></div>
        <div class="field"><label>上级 Wi-Fi 密码（至少 8 位）</label><input id="staKey" type="text" placeholder="输入上级 Wi-Fi 密码"></div>
        <div style="font-size:12px;color:#e2bac8;margin-bottom:10px">提示：修改上级 Wi-Fi 后路由器会重新连接外网（约 5~10 秒），请确认名称和密码无误。</div>
        <button class="btn btn-green" onclick="saveStaWifi()">保存并重连上级 Wi-Fi</button>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>3. 一键修改 SMB 访问密码 &amp; 面板密码</h2>
    <div class="grid">
      <div class="kv">
        <div class="k">修改 SMB 共享密码（当前用户名：<b>admin</b>）</div>
        <div class="row-actions" style="margin-top:8px">
          <input id="smbPass" type="password" placeholder="输入新的 SMB 密码" style="flex:1">
          <button class="btn" onclick="changeSmbPass()">更新 SMB 密码</button>
        </div>
      </div>
      <div class="kv">
        <div class="k">修改本网页管理面板登录密码</div>
        <div class="row-actions" style="margin-top:8px">
          <input id="panelPass" type="password" placeholder="输入新的面板密码" style="flex:1">
          <button class="btn btn-gray" onclick="changePanelPass()">更新面板密码</button>
        </div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>4. 外网 P2P 打洞 &amp; SMB 快捷连接信息</h2>
    <div class="grid">
      <div class="kv"><div class="k">局域网 SMB 地址</div><div class="v" id="lanPath">\\192.168.1.1\备份</div></div>
      <div class="kv"><div class="k">外网 EasyTier P2P SMB 地址（原生 445 端口）</div><div class="v" id="wanPath">\\10.126.126.1\备份</div></div>
      <div class="kv"><div class="k">EasyTier 私有打洞/中继节点</div><div class="v">tcp://YOUR_VPS_IP:11010<br>udp://YOUR_VPS_IP:11010</div></div>
      <div class="kv"><div class="k">EasyTier 网络名称 / 网络密钥</div><div class="v">网络名: tr3000-nas<br>密钥: YOUR_NAS_PASSWORD</div></div>
    </div>
    <pre id="etStatus">正在读取 EasyTier P2P 隧道状态...</pre>
  </div>
</div>

<script>
function toast(msg, isErr=false){
  const t=document.getElementById('toast');
  t.textContent=msg;
  t.style.background=isErr?'#ef4444':'#c4c698';
  t.style.display='block';
  setTimeout(()=>t.style.display='none', 3600);
}

async function loadStatus(){
  try{
    const r=await fetch('/api/status');
    if(r.status===401){location.reload();return;}
    const d=await r.json();
    const b=document.getElementById('connBadge');
    if(d.online){
      b.className='badge ok'; b.textContent='TR3000 在线 (10.126.126.1)';
    }else{
      b.className='badge warn'; b.textContent='TR3000 离线';
    }
    document.getElementById('etStatus').textContent=d.easytier||'暂无节点信息';
    if(d.wifi){
      if(d.wifi.ap24_ssid) document.getElementById('ap24Ssid').value=d.wifi.ap24_ssid;
      if(d.wifi.ap5_ssid) document.getElementById('ap5Ssid').value=d.wifi.ap5_ssid;
      if(d.wifi.ap_key) document.getElementById('apKey').value=d.wifi.ap_key;
      if(d.wifi.sta_ssid) document.getElementById('staSsid').value=d.wifi.sta_ssid;
      if(d.wifi.sta_key) document.getElementById('staKey').value=d.wifi.sta_key;
    }
    const tb=document.getElementById('diskBody');
    if(!d.disks||d.disks.length===0){
      tb.innerHTML='<tr><td colspan="6" style="color:#8b92a5">未检测到 USB 硬盘分区，请检查硬盘盒连接后点击右上角「重新扫描」</td></tr>';
      return;
    }
    const firstShare = d.disks[0].alias || 'USB_Disk';
    document.getElementById('lanPath').textContent = '\\\\192.168.1.1\\' + firstShare;
    document.getElementById('wanPath').textContent = '\\\\10.126.126.1\\' + firstShare;
    tb.innerHTML = d.disks.map(x=>`
      <tr>
        <td><b>${x.part}</b><div style="font-size:11px;color:#64748b">UUID: ${x.uuid}</div></td>
        <td>${x.size} <span style="color:#8b92a5">(已用 ${x.used} / ${x.usepct})</span></td>
        <td>${x.fstype.toUpperCase()} ${x.mounted==='1'?'<span class="badge ok">已挂载</span>':'<span class="badge warn">未挂载</span>'}</td>
        <td><input type="text" id="name_${x.uuid}" value="${x.alias}" style="width:160px"></td>
        <td><label><input type="checkbox" id="en_${x.uuid}" ${x.enabled==='1'?'checked':''}> 开启共享</label></td>
        <td><button class="btn" onclick="saveAlias('${x.uuid}')">保存并生效</button></td>
      </tr>
    `).join('');
  }catch(e){
    toast('读取状态失败: '+e, true);
  }
}

async function saveAlias(uuid){
  const name=document.getElementById('name_'+uuid).value.trim();
  const enabled=document.getElementById('en_'+uuid).checked?'1':'0';
  if(!name){toast('共享名称不能为空',true);return;}
  if(/[\/\\:*?"<>|]/.test(name)){toast('名称不能包含 / \\ : * ? " < > | 等特殊字符',true);return;}
  const r=await fetch('/api/rename',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({uuid,name,enabled})});
  const d=await r.json();
  if(r.ok&&d.ok){toast('共享名已改为「'+name+'」并实时生效！');loadStatus();}
  else{toast('保存失败: '+(d.error||'未知错误'),true);}
}

async function remount(){
  toast('正在扫描并强制挂载所有 USB 硬盘...');
  const r=await fetch('/api/remount',{method:'POST'});
  const d=await r.json();
  if(r.ok&&d.ok){toast('硬盘扫描与挂载完成！');loadStatus();}
  else{toast('挂载失败: '+(d.error||'未知错误'),true);}
}

async function saveApWifi(){
  const ap24_ssid=document.getElementById('ap24Ssid').value.trim();
  const ap5_ssid=document.getElementById('ap5Ssid').value.trim();
  const ap_key=document.getElementById('apKey').value.trim();
  if(!ap24_ssid||!ap5_ssid){toast('Wi-Fi 名称不能为空',true);return;}
  if(ap_key.length<8){toast('Wi-Fi 密码至少需要 8 位',true);return;}
  const r=await fetch('/api/wifi_ap',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ap24_ssid,ap5_ssid,ap_key})});
  const d=await r.json();
  if(r.ok&&d.ok){toast('TR3000 热点名称与密码已更新，约 5 秒后生效！');}
  else{toast('保存失败: '+(d.error||'未知错误'),true);}
}

async function saveStaWifi(){
  const sta_ssid=document.getElementById('staSsid').value.trim();
  const sta_key=document.getElementById('staKey').value.trim();
  if(!sta_ssid){toast('上级 Wi-Fi 名称不能为空',true);return;}
  if(sta_key.length<8){toast('上级 Wi-Fi 密码至少需要 8 位',true);return;}
  const r=await fetch('/api/wifi_sta',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sta_ssid,sta_key})});
  const d=await r.json();
  if(r.ok&&d.ok){toast('上级中继 Wi-Fi 已更新，TR3000 正在重连中...');}
  else{toast('保存失败: '+(d.error||'未知错误'),true);}
}

async function changeSmbPass(){
  const p=document.getElementById('smbPass').value.trim();
  if(p.length<4){toast('SMB 密码至少需要 4 位',true);return;}
  const r=await fetch('/api/smbpass',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:p})});
  const d=await r.json();
  if(r.ok&&d.ok){document.getElementById('smbPass').value='';toast('SMB 密码已修改并重载生效！');}
  else{toast('修改失败: '+(d.error||'未知错误'),true);}
}

async function changePanelPass(){
  const p=document.getElementById('panelPass').value.trim();
  if(p.length<4){toast('面板密码至少需要 4 位',true);return;}
  const r=await fetch('/api/panelpass',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:p})});
  const d=await r.json();
  if(r.ok&&d.ok){document.getElementById('panelPass').value='';toast('网页管理面板密码已更新！');}
  else{toast('修改失败: '+(d.error||'未知错误'),true);}
}

async function logout(){
  await fetch('/api/logout',{method:'POST'});
  location.reload();
}

loadStatus();
</script></body></html>"""

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def is_authed(self):
        c = cookies.SimpleCookie(self.headers.get("Cookie", ""))
        return "sid" in c and c["sid"].value in SESSIONS

    def send_json(self, code, obj, extra_headers=None):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def send_html(self, html):
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_json(self):
        ln = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(ln).decode("utf-8", "ignore") if ln > 0 else "{}"
        return json.loads(raw)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            self.send_html(HTML_APP if self.is_authed() else HTML_LOGIN)
            return
        if self.path == "/api/status":
            if not self.is_authed():
                self.send_json(401, {"error": "unauthorized"})
                return
            cmd = (
                "/usr/bin/tr3000-disk-info.sh; echo '===WIFI==='; "
                "printf 'ap24_ssid=%s\\n' \"$(uci -q get wireless.default_radio0.ssid)\"; "
                "printf 'ap5_ssid=%s\\n' \"$(uci -q get wireless.default_radio1.ssid)\"; "
                "printf 'ap_key=%s\\n' \"$(uci -q get wireless.default_radio0.key)\"; "
                "printf 'sta_ssid=%s\\n' \"$(uci -q get wireless.wifinet_wwan.ssid)\"; "
                "printf 'sta_key=%s\\n' \"$(uci -q get wireless.wifinet_wwan.key)\""
            )
            rc, out, err = ssh_tr(cmd)
            disks = []
            wifi = {}
            if rc == 0:
                sec = "disks"
                for line in out.splitlines():
                    if line.strip() == "===WIFI===":
                        sec = "wifi"
                        continue
                    if sec == "disks":
                        parts = line.split("|")
                        if len(parts) >= 10:
                            disks.append({
                                "part": parts[0], "uuid": parts[1], "fstype": parts[2],
                                "size": parts[3], "used": parts[4], "avail": parts[5],
                                "usepct": parts[6], "mounted": parts[7],
                                "alias": parts[8], "enabled": parts[9]
                            })
                    else:
                        if "=" in line:
                            k, v = line.split("=", 1)
                            wifi[k.strip()] = v.strip()
            self.send_json(200, {"online": rc == 0, "disks": disks, "wifi": wifi, "easytier": get_et_status()})
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/login":
            body = self.read_json()
            if body.get("password") == get_panel_pass():
                sid = secrets.token_hex(24)
                SESSIONS.add(sid)
                save_sessions(SESSIONS)
                self.send_json(200, {"ok": True}, {"Set-Cookie": f"sid={sid}; Path=/; Max-Age=2592000; HttpOnly; SameSite=None; Secure"})
            else:
                self.send_json(403, {"ok": False})
            return
        if self.path == "/api/logout":
            c = cookies.SimpleCookie(self.headers.get("Cookie", ""))
            if "sid" in c:
                SESSIONS.discard(c["sid"].value)
                save_sessions(SESSIONS)
            self.send_json(200, {"ok": True}, {"Set-Cookie": "sid=; Path=/; Max-Age=0"})
            return
        if not self.is_authed():
            self.send_json(401, {"error": "unauthorized"})
            return

        if self.path == "/api/remount":
            rc, out, err = ssh_tr("/usr/bin/tr3000-mount.sh && /usr/bin/tr3000-sync-shares.sh", timeout=25)
            self.send_json(200, {"ok": rc == 0, "error": err})
            return

        if self.path == "/api/rename":
            body = self.read_json()
            uuid = str(body.get("uuid", "")).strip()
            name = str(body.get("name", "")).strip()
            enabled = "1" if str(body.get("enabled", "1")) == "1" else "0"
            if not uuid or not name or any(ch in name for ch in '|/\\:*?"<>`\'\n\r'):
                self.send_json(400, {"ok": False, "error": "非法名称或 UUID"})
                return
            cmd = (
                f"touch /etc/tr3000_aliases.conf; "
                f"grep -v '^{uuid}|' /etc/tr3000_aliases.conf > /tmp/al.tmp || true; "
                f"echo '{uuid}|{name}|{enabled}' >> /tmp/al.tmp; "
                f"mv /tmp/al.tmp /etc/tr3000_aliases.conf; "
                f"/usr/bin/tr3000-sync-shares.sh"
            )
            rc, out, err = ssh_tr(cmd, timeout=20)
            if rc == 0:
                subprocess.run(["/usr/local/bin/tr3000-vps-sync.sh"], timeout=15)
            self.send_json(200, {"ok": rc == 0, "error": err})
            return

        if self.path == "/api/wifi_ap":
            body = self.read_json()
            s24 = str(body.get("ap24_ssid", "")).strip()
            s5 = str(body.get("ap5_ssid", "")).strip()
            key = str(body.get("ap_key", "")).strip()
            if not s24 or not s5 or len(key) < 8:
                self.send_json(400, {"ok": False, "error": "名称不能为空且密码至少8位"})
                return
            cmd = (
                f"uci set wireless.default_radio0.ssid={safe_shell_arg(s24)}; "
                f"uci set wireless.default_radio0.encryption='psk2'; "
                f"uci set wireless.default_radio0.key={safe_shell_arg(key)}; "
                f"uci set wireless.default_radio1.ssid={safe_shell_arg(s5)}; "
                f"uci set wireless.default_radio1.encryption='psk2'; "
                f"uci set wireless.default_radio1.key={safe_shell_arg(key)}; "
                f"uci commit wireless; (sleep 1; wifi reload) >/dev/null 2>&1 &"
            )
            rc, out, err = ssh_tr(cmd, timeout=15)
            self.send_json(200, {"ok": rc == 0, "error": err})
            return

        if self.path == "/api/wifi_sta":
            body = self.read_json()
            ssid = str(body.get("sta_ssid", "")).strip()
            key = str(body.get("sta_key", "")).strip()
            if not ssid or len(key) < 8:
                self.send_json(400, {"ok": False, "error": "名称不能为空且密码至少8位"})
                return
            cmd = (
                f"uci set wireless.wifinet_wwan.ssid={safe_shell_arg(ssid)}; "
                f"uci set wireless.wifinet_wwan.encryption='psk2'; "
                f"uci set wireless.wifinet_wwan.key={safe_shell_arg(key)}; "
                f"uci commit wireless; (sleep 1; wifi reload) >/dev/null 2>&1 &"
            )
            rc, out, err = ssh_tr(cmd, timeout=15)
            self.send_json(200, {"ok": rc == 0, "error": err})
            return

        if self.path == "/api/smbpass":
            body = self.read_json()
            pwd = str(body.get("password", "")).strip()
            if len(pwd) < 4 or "'" in pwd or "\n" in pwd:
                self.send_json(400, {"ok": False, "error": "密码至少4位且不能含单引号"})
                return
            cmd = f"ksmbd.adduser -u admin -p {safe_shell_arg(pwd)} 2>/dev/null || ksmbd.adduser -a admin -p {safe_shell_arg(pwd)}; /etc/init.d/ksmbd restart"
            rc, out, err = ssh_tr(cmd, timeout=20)
            if rc == 0:
                with open("/opt/tr3000-panel/smb.cred", "w", encoding="utf-8") as cf:
                    cf.write(f"username=admin\npassword={pwd}\n")
                os.chmod("/opt/tr3000-panel/smb.cred", 0o600)
            self.send_json(200, {"ok": rc == 0, "error": err})
            return

        if self.path == "/api/panelpass":
            body = self.read_json()
            pwd = str(body.get("password", "")).strip()
            if len(pwd) < 4:
                self.send_json(400, {"ok": False, "error": "密码至少4位"})
                return
            set_panel_pass(pwd)
            self.send_json(200, {"ok": True})
            return

        self.send_response(404)
        self.end_headers()

if __name__ == "__main__":
    os.makedirs("/opt/tr3000-panel", exist_ok=True)
    if not os.path.exists(PASS_FILE):
        set_panel_pass("YOUR_NAS_PASSWORD")
    srv = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    srv.serve_forever()
