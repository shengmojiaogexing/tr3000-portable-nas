#!/usr/bin/env python3
import http.server
import json
import mimetypes
import os
import re
import secrets
import subprocess
import time
import urllib.parse
from datetime import datetime
from http import cookies

PORT = 18089
ROOT_VIEW = "/srv/tr3000_files"
ROOT_RAW = "/mnt/tr3000_raw"
CRED_FILE = "/opt/tr3000-panel/smb.cred"
SESSION_FILE = "/opt/tr3000-panel/sessions_files.json"
SHARES_FILE = "/opt/tr3000-panel/shares.json"

mimetypes.add_type("video/mp4", ".mp4")
mimetypes.add_type("video/webm", ".webm")
mimetypes.add_type("video/quicktime", ".mov")
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("application/pdf", ".pdf")
mimetypes.add_type("text/plain", ".log")
mimetypes.add_type("text/plain", ".md")

def load_json_file(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json_file(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

SESSIONS = set(load_json_file(SESSION_FILE, []))
SHARES = load_json_file(SHARES_FILE, {})
if not isinstance(SHARES, dict):
    SHARES = {}

def save_sessions():
    save_json_file(SESSION_FILE, list(SESSIONS))

def save_shares():
    save_json_file(SHARES_FILE, SHARES)

def get_file_pass():
    if os.path.exists(CRED_FILE):
        with open(CRED_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("password="):
                    return line.split("=", 1)[1].strip()
    return "YOUR_NAS_PASSWORD"

def resolve_safe_path(rel_path, base_dir=ROOT_VIEW):
    rel_path = urllib.parse.unquote(rel_path or "").strip("/")
    parts = [p for p in rel_path.split("/") if p and p not in (".", "..")]
    full = os.path.join(base_dir, *parts) if parts else base_dir
    real = os.path.realpath(full)
    allowed_bases = [os.path.realpath(base_dir)]
    if base_dir == ROOT_VIEW:
        allowed_bases.append(os.path.realpath(ROOT_RAW))
    if not any(real == a or real.startswith(a + os.sep) for a in allowed_bases):
        return None
    return real

def get_valid_share(token):
    global SHARES
    SHARES = load_json_file(SHARES_FILE, {})
    sh = SHARES.get(token)
    if not sh:
        return None
    exp = sh.get("expires_at", 0)
    if exp and time.time() > exp:
        return None
    base_real = resolve_safe_path(sh.get("path", ""), ROOT_VIEW)
    if not base_real or not os.path.exists(base_real):
        return None
    return sh, base_real


_V6_CACHE = {"ip": "", "ts": 0}
def get_tr3000_ipv6():
    now = time.time()
    if now - _V6_CACHE["ts"] < 60 and _V6_CACHE["ip"]:
        return _V6_CACHE["ip"]
    try:
        p = subprocess.run(
            ["ssh", "-i", "/root/.ssh/id_ed25519", "-o", "StrictHostKeyChecking=no",
             "-o", "ConnectTimeout=3", "-o", "BatchMode=yes", "root@10.126.126.1",
             "/usr/bin/tr3000-get-v6.sh"],
            capture_output=True, text=True, timeout=5
        )
        ip = p.stdout.strip().splitlines()[0].strip() if p.stdout.strip() else ""
        _V6_CACHE["ip"] = ip
        _V6_CACHE["ts"] = now
        return ip
    except Exception:
        return _V6_CACHE["ip"]

def human_size(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024.0:
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024.0
    return f"{n:.1f} PB"

HTML_LOGIN = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>ZERO CLOUD | 私有云存储</title>
<style>
:root{
  --bg:#161a21;
  --card:rgba(30,34,43,.72);
  --card-solid:#1e222b;
  --border:rgba(255,255,255,.08);
  --border-hover:rgba(255,255,255,.16);
  --teal:#6fa8a5;
  --teal-hover:#85c4c1;
  --pink:#e2bac8;
  --khaki:#c4c698;
  --text:#eef0f4;
  --muted:#8b92a5;
  --danger:#e07a7a;
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{
  margin:0;
  min-height:100vh;
  background:
    radial-gradient(circle at 18% 0%, rgba(111,168,165,.14) 0%, transparent 45%),
    radial-gradient(circle at 85% 100%, rgba(226,186,200,.12) 0%, transparent 45%),
    var(--bg);
  color:var(--text);
  font-family:'Montserrat','Noto Sans SC',-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;
  line-height:1.5;
  overflow-x:hidden;
}
body::before{
  content:"";position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.12;mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 300 300' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}
.z-wrap{position:relative;z-index:10;max-width:1080px;margin:0 auto;padding:18px}
.z-nav{
  position:sticky;top:0;z-index:30;
  background:rgba(22,26,33,.78);
  backdrop-filter:blur(22px);-webkit-backdrop-filter:blur(22px);
  border-bottom:1px solid var(--border);
  padding:12px 18px;
}
.z-nav-inner{max-width:1080px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.z-brand{display:flex;align-items:center;gap:10px}
.z-logo{font-weight:900;font-size:16px;letter-spacing:.28em;color:#fff;text-transform:uppercase}
.z-tag{font-size:10px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;padding:3px 10px;border-radius:999px;background:rgba(111,168,165,.14);color:var(--teal);border:1px solid rgba(111,168,165,.3)}
.z-tag-pink{background:rgba(226,186,200,.14);color:var(--pink);border-color:rgba(226,186,200,.3)}
.z-tag-khaki{background:rgba(196,198,152,.14);color:var(--khaki);border-color:rgba(196,198,152,.3)}
.z-card{
  background:var(--card);
  border:1px solid var(--border);
  border-radius:24px;
  backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  box-shadow:0 16px 40px rgba(0,0,0,.28);
  transition:border-color .3s ease,transform .3s cubic-bezier(.16,1,.3,1);
}
.z-btn{
  display:inline-flex;align-items:center;justify-content:center;gap:6px;
  padding:8px 16px;border-radius:999px;border:1px solid transparent;
  font-size:12px;font-weight:700;letter-spacing:.08em;cursor:pointer;text-decoration:none;
  transition:all .25s cubic-bezier(.16,1,.3,1);white-space:nowrap;
}
.z-btn:active{transform:scale(.96)}
.z-btn-teal{background:var(--teal);color:#161a21}
.z-btn-teal:hover{background:var(--teal-hover)}
.z-btn-pink{background:rgba(226,186,200,.16);color:var(--pink);border-color:rgba(226,186,200,.35)}
.z-btn-pink:hover{background:var(--pink);color:#161a21}
.z-btn-khaki{background:rgba(196,198,152,.16);color:var(--khaki);border-color:rgba(196,198,152,.35)}
.z-btn-khaki:hover{background:var(--khaki);color:#161a21}
.z-btn-ghost{background:rgba(255,255,255,.04);color:var(--text);border-color:var(--border)}
.z-btn-ghost:hover{background:rgba(255,255,255,.1);border-color:var(--border-hover)}
.z-btn-danger{background:rgba(224,122,122,.14);color:var(--danger);border-color:rgba(224,122,122,.35)}
.z-btn-danger:hover{background:var(--danger);color:#161a21}
input[type=text],input[type=password],input[type=search],select{
  padding:10px 14px;border-radius:14px;border:1px solid var(--border);
  background:rgba(15,18,24,.75);color:var(--text);font-size:14px;outline:none;
  transition:border-color .25s ease;
}
input:focus,select:focus{border-color:var(--teal)}
.z-toast{
  position:fixed;top:18px;right:18px;z-index:300;display:none;
  padding:11px 18px;border-radius:999px;font-size:13px;font-weight:700;letter-spacing:.04em;
  background:var(--teal);color:#161a21;box-shadow:0 12px 32px rgba(0,0,0,.4);
}

.gate-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;position:relative;z-index:10}
.gate-card{width:100%;max-width:400px;padding:36px 28px;text-align:center}
.gate-sub{font-size:12px;color:var(--muted);letter-spacing:.12em;margin:8px 0 24px}
.gate-err{color:var(--danger);font-size:12px;margin-bottom:12px;display:none}
</style></head><body>
<div class="gate-wrap">
  <div class="z-card gate-card">
    <div class="z-logo" style="font-size:22px;margin-bottom:10px">ZERO STUDIO</div>
    <span class="z-tag">Cloud Archive · TR3000</span>
    <div class="gate-sub">私有影像与文件云端浏览 · 30天免密记忆</div>
    <div id="err" class="gate-err">访问密码不正确，请重试</div>
    <input id="pwd" type="password" placeholder="请输入访问密码" style="width:100%;margin-bottom:16px;font-size:16px" onkeydown="if(event.key==='Enter')login()">
    <button class="z-btn z-btn-teal" style="width:100%;padding:12px;font-size:13px" onclick="login()">进入云盘</button>
  </div>
</div>
<script>
async function login(){
  const pwd=document.getElementById('pwd').value;
  const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pwd})});
  if(r.ok){location.reload();}else{document.getElementById('err').style.display='block';}
}
</script></body></html>"""

HTML_APP = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>ZERO CLOUD | 文件预览、下载与分享</title>
<style>
:root{
  --bg:#161a21;
  --card:rgba(30,34,43,.72);
  --card-solid:#1e222b;
  --border:rgba(255,255,255,.08);
  --border-hover:rgba(255,255,255,.16);
  --teal:#6fa8a5;
  --teal-hover:#85c4c1;
  --pink:#e2bac8;
  --khaki:#c4c698;
  --text:#eef0f4;
  --muted:#8b92a5;
  --danger:#e07a7a;
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{
  margin:0;
  min-height:100vh;
  background:
    radial-gradient(circle at 18% 0%, rgba(111,168,165,.14) 0%, transparent 45%),
    radial-gradient(circle at 85% 100%, rgba(226,186,200,.12) 0%, transparent 45%),
    var(--bg);
  color:var(--text);
  font-family:'Montserrat','Noto Sans SC',-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;
  line-height:1.5;
  overflow-x:hidden;
}
body::before{
  content:"";position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.12;mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 300 300' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}
.z-wrap{position:relative;z-index:10;max-width:1080px;margin:0 auto;padding:18px}
.z-nav{
  position:sticky;top:0;z-index:30;
  background:rgba(22,26,33,.78);
  backdrop-filter:blur(22px);-webkit-backdrop-filter:blur(22px);
  border-bottom:1px solid var(--border);
  padding:12px 18px;
}
.z-nav-inner{max-width:1080px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.z-brand{display:flex;align-items:center;gap:10px}
.z-logo{font-weight:900;font-size:16px;letter-spacing:.28em;color:#fff;text-transform:uppercase}
.z-tag{font-size:10px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;padding:3px 10px;border-radius:999px;background:rgba(111,168,165,.14);color:var(--teal);border:1px solid rgba(111,168,165,.3)}
.z-tag-pink{background:rgba(226,186,200,.14);color:var(--pink);border-color:rgba(226,186,200,.3)}
.z-tag-khaki{background:rgba(196,198,152,.14);color:var(--khaki);border-color:rgba(196,198,152,.3)}
.z-card{
  background:var(--card);
  border:1px solid var(--border);
  border-radius:24px;
  backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  box-shadow:0 16px 40px rgba(0,0,0,.28);
  transition:border-color .3s ease,transform .3s cubic-bezier(.16,1,.3,1);
}
.z-btn{
  display:inline-flex;align-items:center;justify-content:center;gap:6px;
  padding:8px 16px;border-radius:999px;border:1px solid transparent;
  font-size:12px;font-weight:700;letter-spacing:.08em;cursor:pointer;text-decoration:none;
  transition:all .25s cubic-bezier(.16,1,.3,1);white-space:nowrap;
}
.z-btn:active{transform:scale(.96)}
.z-btn-teal{background:var(--teal);color:#161a21}
.z-btn-teal:hover{background:var(--teal-hover)}
.z-btn-pink{background:rgba(226,186,200,.16);color:var(--pink);border-color:rgba(226,186,200,.35)}
.z-btn-pink:hover{background:var(--pink);color:#161a21}
.z-btn-khaki{background:rgba(196,198,152,.16);color:var(--khaki);border-color:rgba(196,198,152,.35)}
.z-btn-khaki:hover{background:var(--khaki);color:#161a21}
.z-btn-ghost{background:rgba(255,255,255,.04);color:var(--text);border-color:var(--border)}
.z-btn-ghost:hover{background:rgba(255,255,255,.1);border-color:var(--border-hover)}
.z-btn-danger{background:rgba(224,122,122,.14);color:var(--danger);border-color:rgba(224,122,122,.35)}
.z-btn-danger:hover{background:var(--danger);color:#161a21}
input[type=text],input[type=password],input[type=search],select{
  padding:10px 14px;border-radius:14px;border:1px solid var(--border);
  background:rgba(15,18,24,.75);color:var(--text);font-size:14px;outline:none;
  transition:border-color .25s ease;
}
input:focus,select:focus{border-color:var(--teal)}
.z-toast{
  position:fixed;top:18px;right:18px;z-index:300;display:none;
  padding:11px 18px;border-radius:999px;font-size:13px;font-weight:700;letter-spacing:.04em;
  background:var(--teal);color:#161a21;box-shadow:0 12px 32px rgba(0,0,0,.4);
}

.toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:14px 18px;margin-bottom:16px}
.crumb{display:flex;gap:6px;align-items:center;flex:1;font-size:13px;overflow-x:auto;white-space:nowrap}
.crumb a{color:var(--teal);text-decoration:none;cursor:pointer;font-weight:600}
.crumb a:hover{text-decoration:underline}
.table-wrap{overflow:hidden}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{padding:13px 16px;text-align:left;border-bottom:1px solid rgba(255,255,255,.05)}
th{font-size:11px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);background:rgba(15,18,24,.35)}
tr:last-child td{border-bottom:0}
tbody tr:hover td{background:rgba(255,255,255,.03)}
.name-cell{display:flex;align-items:center;gap:10px;cursor:pointer;color:var(--text);font-weight:500;word-break:break-all}
.name-cell:hover{color:var(--teal)}
.icon{font-size:18px;flex-shrink:0}
.muted{color:var(--muted);font-size:12px;white-space:nowrap}
.actions{display:flex;gap:6px;justify-content:flex-end;white-space:nowrap}
.modal{position:fixed;inset:0;background:rgba(10,12,16,.84);backdrop-filter:blur(10px);display:none;align-items:center;justify-content:center;z-index:100;padding:14px}
.modal.show{display:flex}
.modal-box{width:900px;max-width:95vw;max-height:90vh;display:flex;flex-direction:column;overflow:hidden}
.modal-box.sm{width:480px}
.modal-head{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;border-bottom:1px solid var(--border);gap:10px}
.modal-title{font-weight:700;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.modal-body{padding:18px;overflow:auto;max-height:76vh;background:rgba(15,18,24,.55)}
.modal-body.center{display:flex;align-items:center;justify-content:center;min-height:260px}
.modal-body img,.modal-body video{max-width:100%;max-height:70vh;border-radius:12px}
.modal-body iframe{width:100%;height:70vh;border:0;background:#fff;border-radius:12px}
.modal-body pre{width:100%;margin:0;color:var(--text);font-size:13px;white-space:pre-wrap;word-break:break-all;font-family:Consolas,monospace}
.field{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}
.field label{font-size:12px;color:var(--muted);letter-spacing:.06em}
.result-box{background:rgba(111,168,165,.08);border:1px solid rgba(111,168,165,.3);border-radius:16px;padding:14px;margin-top:14px;display:none}
.result-url{font-family:Consolas,monospace;color:var(--teal);word-break:break-all;font-size:13px;margin-bottom:8px}
@media(max-width:720px){
  .z-nav{padding:10px 14px}
  .z-wrap{padding:12px}
  .z-logo{font-size:14px;letter-spacing:.2em}
  .toolbar{padding:12px;border-radius:18px}
  input[type=search],input[type=text],select{width:100%;font-size:16px}
  .table-wrap{background:transparent;border:0;box-shadow:none;backdrop-filter:none;border-radius:0}
  table,tbody,tr,td{display:block;width:100%}
  thead{display:none}
  tbody tr{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:14px;margin-bottom:10px;backdrop-filter:blur(18px)}
  tbody td{padding:0;border:0}
  tbody td:nth-child(1){margin-bottom:6px}
  .name-cell{font-size:15px;line-height:1.4}
  tbody td:nth-child(2),tbody td:nth-child(3){display:inline-block;width:auto;margin-right:12px;margin-bottom:10px}
  tbody td:nth-child(4){display:block;width:100%}
  .actions{justify-content:flex-start;gap:8px}
  .actions .z-btn{flex:1;padding:9px 10px}
  .modal{padding:8px}
  .modal-box,.modal-box.sm{width:100%;max-width:100%;max-height:92vh;border-radius:18px}
  .modal-body{padding:12px;max-height:80vh}
}
</style></head><body>
<div id="toast" class="z-toast"></div>
<header class="z-nav">
  <div class="z-nav-inner">
    <div class="z-brand">
      <span class="z-logo">ZERO</span>
      <span class="z-tag">Cloud Archive</span><span id="v6Badge" class="z-tag z-tag-khaki" style="display:none"><svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="display:inline-block;vertical-align:-2px;flex-shrink:0"><path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z"/></svg> IPv6 直连</span>
    </div>
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
      <button class="z-btn z-btn-pink" onclick="openMyShares()">我的分享</button>
      <a class="z-btn z-btn-ghost" href="https://panel.nas.example.com" target="_blank">设备管理</a>
      <button class="z-btn z-btn-ghost" onclick="logout()">退出</button>
    </div>
  </div>
</header>

<main class="z-wrap">
  <div class="z-card toolbar">
    <div class="crumb" id="crumb"></div>
    <input type="search" id="kw" placeholder="搜索当前目录..." oninput="render()" style="width:220px">
    <button class="z-btn z-btn-ghost" onclick="loadDir(curPath)">刷新</button>
  </div>
  <div class="z-card table-wrap">
    <table>
      <thead><tr><th>文件 / 文件夹</th><th style="width:105px">大小</th><th style="width:155px">修改时间</th><th style="width:220px;text-align:right">操作</th></tr></thead>
      <tbody id="listBody"><tr><td colspan="4" class="muted" style="text-align:center;padding:28px">正在加载文件列表...</td></tr></tbody>
    </table>
  </div>
</main>

<div id="modal" class="modal" onclick="if(event.target===this)closeModal()">
  <div class="z-card modal-box">
    <div class="modal-head">
      <div class="modal-title" id="mTitle">预览</div>
      <div style="display:flex;gap:8px">
        <a id="mDown" class="z-btn z-btn-teal" href="#" download>下载原件</a>
        <button class="z-btn z-btn-ghost" onclick="closeModal()">关闭</button>
      </div>
    </div>
    <div class="modal-body center" id="mBody"></div>
  </div>
</div>

<div id="shareModal" class="modal" onclick="if(event.target===this)closeShareModal()">
  <div class="z-card modal-box sm">
    <div class="modal-head">
      <div class="modal-title" id="sTitle">创建分享链接</div>
      <button class="z-btn z-btn-ghost" onclick="closeShareModal()">关闭</button>
    </div>
    <div class="modal-body">
      <div class="field">
        <label>分享路径</label>
        <div id="sPathShow" style="color:var(--teal);font-size:13px;word-break:break-all"></div>
      </div>
      <div class="field">
        <label>链接有效期</label>
        <select id="sExpire">
          <option value="1">1 天</option>
          <option value="7" selected>7 天</option>
          <option value="30">30 天</option>
          <option value="0">永久有效</option>
        </select>
      </div>
      <div class="field">
        <label>提取码（留空免密直开，填写后需凭码提取）</label>
        <input type="text" id="sCode" placeholder="例如 6688（选填）" maxlength="16">
      </div>
      <button class="z-btn z-btn-pink" style="width:100%;padding:11px" onclick="createShare()">生成专属分享链接</button>
      <div id="sResult" class="result-box">
        <div style="font-size:11px;color:var(--muted);letter-spacing:.1em;margin-bottom:4px">SHARE LINK READY</div>
        <div id="sUrl" class="result-url"></div>
        <div id="sCodeInfo" style="font-size:12px;color:var(--khaki);margin-bottom:10px"></div>
        <button class="z-btn z-btn-teal" style="width:100%;padding:10px" onclick="copyShareText()">一键复制发给好友</button>
      </div>
    </div>
  </div>
</div>

<div id="mySharesModal" class="modal" onclick="if(event.target===this)closeMyShares()">
  <div class="z-card modal-box">
    <div class="modal-head">
      <div class="modal-title">我的分享链接管理</div>
      <button class="z-btn z-btn-ghost" onclick="closeMyShares()">关闭</button>
    </div>
    <div class="modal-body" id="mySharesBody">正在加载...</div>
  </div>
</div>

<script>
let curPath="",curItems=[],pendingSharePath="",pendingShareName="",lastShareCopyText="";
function toast(msg,isErr=false){
  const t=document.getElementById('toast');t.textContent=msg;
  t.style.background=isErr?'var(--danger)':'var(--teal)';
  t.style.display='block';setTimeout(()=>t.style.display='none',3000);
}
function esc(s){return String(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
function joinPath(a,b){return a?(a+'/'+b):b;}
function extOf(name){const i=name.lastIndexOf('.');return i>=0?name.slice(i+1).toLowerCase():'';}
function iconFor(item){
  if(item.is_dir)return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:-2px;flex-shrink:0;color:#6fa8a5"><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/></svg>';const e=extOf(item.name);
  if(['jpg','jpeg','png','gif','webp','bmp','svg'].includes(e))return '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="display:inline-block;vertical-align:-2px;flex-shrink:0"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/></svg>';
  if(['mp4','webm','mov','mkv','avi'].includes(e))return '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="display:inline-block;vertical-align:-2px;flex-shrink:0"><path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z"/></svg>';
  if(['mp3','wav','ogg','m4a','flac'].includes(e))return '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="display:inline-block;vertical-align:-2px;flex-shrink:0"><path d="M12 3v10.55A4 4 0 1014 17V7h4V3h-6z"/></svg>';
  if(e==='pdf')return '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="display:inline-block;vertical-align:-2px;flex-shrink:0"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-9.5 8.5c0 .8-.7 1.5-1.5 1.5H7v2H5.5V9H8c.8 0 1.5.7 1.5 1.5v1zm5 2c0 .8-.7 1.5-1.5 1.5h-2.5V9H13c.8 0 1.5.7 1.5 1.5v3zm4-3H17v1h1.5V13H17v2h-1.5V9h3v1.5z"/></svg>';if(['xls','xlsx','csv'].includes(e))return '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="display:inline-block;vertical-align:-2px;flex-shrink:0"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/></svg>';
  if(['zip','rar','7z','tar','gz'].includes(e))return '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="display:inline-block;vertical-align:-2px;flex-shrink:0"><path d="M20 6h-8l-2-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-6 10h-4v-2h4v2zm0-4h-4v-2h4v2z"/></svg>';return '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="display:inline-block;vertical-align:-2px;flex-shrink:0"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 7V3.5L18.5 9H13z"/></svg>';
}
function previewType(name){
  const e=extOf(name);
  if(['jpg','jpeg','png','gif','webp','bmp','svg'].includes(e))return 'image';
  if(['mp4','webm','mov','m4v'].includes(e))return 'video';
  if(['mp3','wav','ogg','m4a','flac'].includes(e))return 'audio';
  if(e==='pdf')return 'pdf';
  if(['txt','md','json','log','csv','py','js','css','html','xml','ini','conf','sh','bat','yml','yaml'].includes(e))return 'text';
  return 'none';
}
function renderCrumb(){
  const parts=curPath?curPath.split('/'):[];
  let html=`<a onclick="loadDir('')">全部硬盘</a>`,acc='';
  for(const p of parts){acc=joinPath(acc,p);const t=acc;html+=` <span class="muted">/</span> <a onclick="loadDir('${esc(t)}')">${esc(p)}</a>`;}
  document.getElementById('crumb').innerHTML=html;
}
function render(){
  const kw=document.getElementById('kw').value.trim().toLowerCase();
  const tb=document.getElementById('listBody');let rows='';
  if(curPath){
    const parent=curPath.includes('/')?curPath.slice(0,curPath.lastIndexOf('/')):'';
    rows+=`<tr><td colspan="4"><div class="name-cell" onclick="loadDir('${esc(parent)}')"><span class="icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="display:inline-block;vertical-align:-2px;flex-shrink:0"><path d="M19 7v4H5.83l3.58-3.59L8 6l-6 6 6 6 1.41-1.41L5.83 13H21V7z"/></svg></span><span>返回上一级目录</span></div></td></tr>`;
  }
  const filtered=curItems.filter(x=>!kw||x.name.toLowerCase().includes(kw));
  if(filtered.length===0){
    rows+=`<tr><td colspan="4" class="muted" style="text-align:center;padding:28px">当前目录为空或无匹配文件</td></tr>`;
  }else{
    for(const item of filtered){
      const p=joinPath(curPath,item.name),encP=encodeURIComponent(p);
      const shareBtn=`<button class="z-btn z-btn-pink" onclick="openShare('${esc(p)}','${esc(item.name)}')">分享</button>`;
      if(item.is_dir){
        rows+=`<tr>
          <td><div class="name-cell" onclick="loadDir('${esc(p)}')"><span class="icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:-2px;flex-shrink:0;color:#6fa8a5"><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/></svg></span><span>${esc(item.name)}</span></div></td>
          <td class="muted">文件夹</td><td class="muted">${esc(item.mtime)}</td>
          <td class="actions">${shareBtn}<a class="z-btn z-btn-khaki" href="/download-zip?path=${encP}">打包下载</a><button class="z-btn z-btn-teal" onclick="loadDir('${esc(p)}')">打开</button></td>
        </tr>`;
      }else{
        const pt=previewType(item.name);
        const pvBtn=pt!=='none'?`<button class="z-btn z-btn-ghost" onclick="openPreview('${esc(p)}','${esc(item.name)}','${pt}')">预览</button>`:'';
        rows+=`<tr>
          <td><div class="name-cell" onclick="${pt!=='none'?`openPreview('${esc(p)}','${esc(item.name)}','${pt}')`:`window.open('/download?path=${encP}','_blank')`}"><span class="icon">${iconFor(item)}</span><span>${esc(item.name)}</span></div></td>
          <td class="muted">${esc(item.size_str)}</td><td class="muted">${esc(item.mtime)}</td>
          <td class="actions">${shareBtn}${pvBtn}<a class="z-btn z-btn-teal" href="${directUrl(p, true)}" download>下载</a></td>
        </tr>`;
      }
    }
  }
  tb.innerHTML=rows;
}
async function loadDir(path){
  curPath=path||"";document.getElementById('kw').value='';renderCrumb();
  document.getElementById('listBody').innerHTML='<tr><td colspan="4" class="muted" style="text-align:center;padding:24px">正在读取目录...</td></tr>';
  const r=await fetch('/api/list?path='+encodeURIComponent(curPath));
  if(r.status===401){location.reload();return;}
  curItems=(await r.json()).items||[];render();
}
async function openPreview(path,name,type){
  const encP=encodeURIComponent(path),rawUrl=directUrl(path,false),dlUrl=directUrl(path,true);
  document.getElementById('mTitle').textContent=name;document.getElementById('mDown').href=dlUrl;
  const body=document.getElementById('mBody');body.innerHTML='<div class="muted">加载中...</div>';
  document.getElementById('modal').classList.add('show');
  if(type==='image')body.innerHTML=`<img src="${rawUrl}" alt="${esc(name)}">`;
  else if(type==='video')body.innerHTML=`<video src="${rawUrl}" controls autoplay playsinline webkit-playsinline></video>`;
  else if(type==='audio')body.innerHTML=`<audio src="${rawUrl}" controls autoplay style="width:100%"></audio>`;
  else if(type==='pdf')body.innerHTML=`<iframe src="${rawUrl}"></iframe>`;
  else if(type==='text'){const r=await fetch('/api/text?path='+encP);body.innerHTML=`<pre>${esc(await r.text())}</pre>`;}
}
function closeModal(){document.getElementById('modal').classList.remove('show');document.getElementById('mBody').innerHTML='';}
function openShare(path,name){
  pendingSharePath=path;pendingShareName=name;
  document.getElementById('sTitle').textContent='分享 · '+name;
  document.getElementById('sPathShow').textContent='/'+path;
  document.getElementById('sCode').value='';document.getElementById('sResult').style.display='none';
  document.getElementById('shareModal').classList.add('show');
}
function closeShareModal(){document.getElementById('shareModal').classList.remove('show');}
async function createShare(){
  const days=parseInt(document.getElementById('sExpire').value,10),code=document.getElementById('sCode').value.trim();
  const r=await fetch('/api/share/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:pendingSharePath,days,code})});
  const d=await r.json();if(!r.ok||!d.ok){toast('生成失败: '+(d.error||'未知错误'),true);return;}
  const url=location.origin+'/s/'+d.token;
  document.getElementById('sUrl').textContent=url;
  document.getElementById('sCodeInfo').textContent=code?('提取码：'+code):'免提取码 · 点开即可预览下载';
  lastShareCopyText=code?(`ZERO STUDIO 分享了「${pendingShareName}」给你：
链接：${url}
提取码：${code}`):(`ZERO STUDIO 分享了「${pendingShareName}」给你：
链接：${url}`);
  document.getElementById('sResult').style.display='block';toast('分享链接已生成');
}
function copyText(txt){
  if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(txt).then(()=>toast('已复制到剪贴板')).catch(()=>fbCopy(txt));
  else fbCopy(txt);
}
function fbCopy(txt){const ta=document.createElement('textarea');ta.value=txt;document.body.appendChild(ta);ta.select();document.execCommand('copy');document.body.removeChild(ta);toast('已复制到剪贴板');}
function copyShareText(){copyText(lastShareCopyText);}
async function openMyShares(){
  document.getElementById('mySharesModal').classList.add('show');
  const body=document.getElementById('mySharesBody');body.innerHTML='<div class="muted">正在加载...</div>';
  const list=(await (await fetch('/api/share/list')).json()).shares||[];
  if(list.length===0){body.innerHTML='<div class="muted" style="text-align:center;padding:24px">暂无分享链接，点击文件右侧「分享」即可创建</div>';return;}
  body.innerHTML=`<table><thead><tr><th>分享内容</th><th>提取码</th><th>到期时间</th><th style="text-align:right">操作</th></tr></thead><tbody>`+
    list.map(s=>{
      const url=location.origin+'/s/'+s.token,cp=s.code?(`链接：${url}  提取码：${s.code}`):url;
      return `<tr>
        <td><b>${esc(s.name)}</b><div class="muted" style="font-size:11px;margin-top:2px">${esc(url)}</div></td>
        <td>${s.code?`<span style="color:var(--khaki);font-weight:700">${esc(s.code)}</span>`:'<span class="muted">免密</span>'}</td>
        <td class="muted">${esc(s.expire_str)}</td>
        <td class="actions">
          <button class="z-btn z-btn-teal" onclick="copyText('${esc(cp)}')">复制</button>
          <a class="z-btn z-btn-ghost" href="/s/${esc(s.token)}" target="_blank">打开</a>
          <button class="z-btn z-btn-danger" onclick="delShare('${esc(s.token)}')">取消</button>
        </td>
      </tr>`;
    }).join('')+`</tbody></table>`;
}
function closeMyShares(){document.getElementById('mySharesModal').classList.remove('show');}
async function delShare(token){const r=await fetch('/api/share/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token})});if(r.ok){toast('已取消该分享');openMyShares();}}
async function logout(){await fetch('/api/logout',{method:'POST'});location.reload();}

let v6Base = "";
function directUrl(relPath, isDownload){
  if(v6Base){
    const encoded = relPath.split('/').map(encodeURIComponent).join('/');
    return v6Base + '/' + encoded;
  }
  return (isDownload ? '/download?path=' : '/raw?path=') + encodeURIComponent(relPath);
}
async function probeV6(){
  try{
    const d = await (await fetch('/api/v6info')).json();
    if(!d.base) return;
    const ctrl = new AbortController();
    const timer = setTimeout(()=>ctrl.abort(), 1500);
    const r = await fetch(d.base + '/ping.txt', {mode:'no-cors', signal:ctrl.signal});
    clearTimeout(timer);
    v6Base = d.base;
    const b = document.getElementById('v6Badge');
    if(b){ b.style.display='inline-block'; b.title='已直连 ' + d.base; }
    render();
  }catch(e){}
}
probeV6();

loadDir('');
</script></body></html>"""

HTML_SHARE_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>ZERO STUDIO | 专属文件分享</title>
<style>
:root{
  --bg:#161a21;
  --card:rgba(30,34,43,.72);
  --card-solid:#1e222b;
  --border:rgba(255,255,255,.08);
  --border-hover:rgba(255,255,255,.16);
  --teal:#6fa8a5;
  --teal-hover:#85c4c1;
  --pink:#e2bac8;
  --khaki:#c4c698;
  --text:#eef0f4;
  --muted:#8b92a5;
  --danger:#e07a7a;
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{
  margin:0;
  min-height:100vh;
  background:
    radial-gradient(circle at 18% 0%, rgba(111,168,165,.14) 0%, transparent 45%),
    radial-gradient(circle at 85% 100%, rgba(226,186,200,.12) 0%, transparent 45%),
    var(--bg);
  color:var(--text);
  font-family:'Montserrat','Noto Sans SC',-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;
  line-height:1.5;
  overflow-x:hidden;
}
body::before{
  content:"";position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.12;mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 300 300' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}
.z-wrap{position:relative;z-index:10;max-width:1080px;margin:0 auto;padding:18px}
.z-nav{
  position:sticky;top:0;z-index:30;
  background:rgba(22,26,33,.78);
  backdrop-filter:blur(22px);-webkit-backdrop-filter:blur(22px);
  border-bottom:1px solid var(--border);
  padding:12px 18px;
}
.z-nav-inner{max-width:1080px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.z-brand{display:flex;align-items:center;gap:10px}
.z-logo{font-weight:900;font-size:16px;letter-spacing:.28em;color:#fff;text-transform:uppercase}
.z-tag{font-size:10px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;padding:3px 10px;border-radius:999px;background:rgba(111,168,165,.14);color:var(--teal);border:1px solid rgba(111,168,165,.3)}
.z-tag-pink{background:rgba(226,186,200,.14);color:var(--pink);border-color:rgba(226,186,200,.3)}
.z-tag-khaki{background:rgba(196,198,152,.14);color:var(--khaki);border-color:rgba(196,198,152,.3)}
.z-card{
  background:var(--card);
  border:1px solid var(--border);
  border-radius:24px;
  backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  box-shadow:0 16px 40px rgba(0,0,0,.28);
  transition:border-color .3s ease,transform .3s cubic-bezier(.16,1,.3,1);
}
.z-btn{
  display:inline-flex;align-items:center;justify-content:center;gap:6px;
  padding:8px 16px;border-radius:999px;border:1px solid transparent;
  font-size:12px;font-weight:700;letter-spacing:.08em;cursor:pointer;text-decoration:none;
  transition:all .25s cubic-bezier(.16,1,.3,1);white-space:nowrap;
}
.z-btn:active{transform:scale(.96)}
.z-btn-teal{background:var(--teal);color:#161a21}
.z-btn-teal:hover{background:var(--teal-hover)}
.z-btn-pink{background:rgba(226,186,200,.16);color:var(--pink);border-color:rgba(226,186,200,.35)}
.z-btn-pink:hover{background:var(--pink);color:#161a21}
.z-btn-khaki{background:rgba(196,198,152,.16);color:var(--khaki);border-color:rgba(196,198,152,.35)}
.z-btn-khaki:hover{background:var(--khaki);color:#161a21}
.z-btn-ghost{background:rgba(255,255,255,.04);color:var(--text);border-color:var(--border)}
.z-btn-ghost:hover{background:rgba(255,255,255,.1);border-color:var(--border-hover)}
.z-btn-danger{background:rgba(224,122,122,.14);color:var(--danger);border-color:rgba(224,122,122,.35)}
.z-btn-danger:hover{background:var(--danger);color:#161a21}
input[type=text],input[type=password],input[type=search],select{
  padding:10px 14px;border-radius:14px;border:1px solid var(--border);
  background:rgba(15,18,24,.75);color:var(--text);font-size:14px;outline:none;
  transition:border-color .25s ease;
}
input:focus,select:focus{border-color:var(--teal)}
.z-toast{
  position:fixed;top:18px;right:18px;z-index:300;display:none;
  padding:11px 18px;border-radius:999px;font-size:13px;font-weight:700;letter-spacing:.04em;
  background:var(--teal);color:#161a21;box-shadow:0 12px 32px rgba(0,0,0,.4);
}

.gate{max-width:400px;margin:12vh auto;padding:34px 26px;text-align:center}
.pad{padding:22px}
.sub{color:var(--muted);font-size:12px;letter-spacing:.08em;margin-top:6px}
.toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:12px 18px;border-top:1px solid var(--border);border-bottom:1px solid var(--border);background:rgba(15,18,24,.35)}
.crumb{display:flex;gap:6px;align-items:center;flex:1;font-size:13px;overflow-x:auto;white-space:nowrap}
.crumb a{color:var(--teal);text-decoration:none;cursor:pointer;font-weight:600}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{padding:13px 16px;text-align:left;border-bottom:1px solid rgba(255,255,255,.05)}
th{font-size:11px;font-weight:700;letter-spacing:.14em;color:var(--muted)}
tbody tr:hover td{background:rgba(255,255,255,.03)}
.name-cell{display:flex;align-items:center;gap:10px;cursor:pointer;color:var(--text);font-weight:500;word-break:break-all}
.name-cell:hover{color:var(--teal)}
.muted{color:var(--muted);font-size:12px;white-space:nowrap}
.actions{display:flex;gap:8px;justify-content:flex-end;white-space:nowrap}
.modal{position:fixed;inset:0;background:rgba(10,12,16,.86);backdrop-filter:blur(10px);display:none;align-items:center;justify-content:center;z-index:100;padding:12px}
.modal.show{display:flex}
.modal-box{width:900px;max-width:95vw;max-height:92vh;display:flex;flex-direction:column;overflow:hidden}
.modal-head{display:flex;justify-content:space-between;align-items:center;padding:14px 16px;border-bottom:1px solid var(--border);gap:10px}
.modal-body{padding:16px;overflow:auto;background:rgba(15,18,24,.6);display:flex;align-items:center;justify-content:center;min-height:260px;max-height:78vh}
.modal-body img,.modal-body video{max-width:100%;max-height:72vh;border-radius:12px}
.modal-body iframe{width:100%;height:72vh;border:0;background:#fff;border-radius:12px}
.modal-body pre{width:100%;margin:0;color:var(--text);font-size:13px;white-space:pre-wrap;word-break:break-all;font-family:Consolas,monospace}
@media(max-width:720px){
  .z-wrap{padding:12px}
  .pad{padding:16px}
  .toolbar{padding:10px 12px}
  input[type=search],input[type=text]{width:100%!important;font-size:16px}
  table,tbody,tr,td{display:block;width:100%}
  thead{display:none}
  tbody{padding:10px}
  tbody tr{background:rgba(15,18,24,.55);border:1px solid var(--border);border-radius:16px;padding:13px;margin-bottom:10px}
  tbody td{padding:0;border:0}
  tbody td:nth-child(1){margin-bottom:6px}
  .name-cell{font-size:15px}
  tbody td:nth-child(2),tbody td:nth-child(3){display:inline-block;width:auto;margin-right:12px;margin-bottom:10px}
  tbody td:nth-child(4){display:block;width:100%}
  .actions{justify-content:flex-start;gap:8px}
  .actions .z-btn{flex:1;padding:9px 10px}
  .modal{padding:8px}
  .modal-box{width:100%;max-width:100%;border-radius:18px}
}
</style></head><body>
<header class="z-nav">
  <div class="z-nav-inner">
    <div class="z-brand">
      <span class="z-logo">ZERO STUDIO</span>
      <span class="z-tag z-tag-pink">Shared Archive</span>
    </div>
  </div>
</header>
<div class="z-wrap" id="root"><div class="z-card gate"><div class="sub">正在加载分享内容...</div></div></div>

<div id="modal" class="modal" onclick="if(event.target===this)closeModal()">
  <div class="z-card modal-box">
    <div class="modal-head">
      <div id="mTitle" style="font-weight:700;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">预览</div>
      <div style="display:flex;gap:8px">
        <a id="mDown" class="z-btn z-btn-teal" href="#" download>下载原件</a>
        <button class="z-btn z-btn-ghost" onclick="closeModal()">关闭</button>
      </div>
    </div>
    <div class="modal-body" id="mBody"></div>
  </div>
</div>

<script>
const TOKEN=location.pathname.split('/').filter(Boolean)[1]||'';
let shareCode=sessionStorage.getItem('sc_'+TOKEN)||'',shareInfo=null,curSub='',curItems=[];
function esc(s){return String(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
function joinPath(a,b){return a?(a+'/'+b):b;}
function extOf(name){const i=name.lastIndexOf('.');return i>=0?name.slice(i+1).toLowerCase():'';}
function previewType(name){
  const e=extOf(name);
  if(['jpg','jpeg','png','gif','webp','bmp','svg'].includes(e))return 'image';
  if(['mp4','webm','mov','m4v'].includes(e))return 'video';
  if(['mp3','wav','ogg','m4a','flac'].includes(e))return 'audio';
  if(e==='pdf')return 'pdf';
  if(['txt','md','json','log','csv','py','js','css','html','xml','ini','conf'].includes(e))return 'text';
  return 'none';
}
function qsAuth(sub){let q='?sub='+encodeURIComponent(sub||'');if(shareCode)q+='&code='+encodeURIComponent(shareCode);return q;}
async function init(){
  const r=await fetch('/api/s/'+encodeURIComponent(TOKEN)+'/info'+qsAuth(''));
  const d=await r.json(),root=document.getElementById('root');
  if(r.status===404){root.innerHTML=`<div class="z-card gate"><h2 style="margin:0 0 8px">分享链接已失效</h2><div class="sub">该链接不存在、已过期或已被主人取消</div></div>`;return;}
  if(r.status===403&&d.need_code){
    root.innerHTML=`<div class="z-card gate">
      <span class="z-tag z-tag-pink" style="margin-bottom:14px;display:inline-block">LOCKED ARCHIVE</span>
      <h2 style="margin:0 0 6px;font-size:19px">请输入提取码</h2>
      <div class="sub" style="margin-bottom:18px">${esc(d.name||'加密分享内容')}</div>
      <div style="color:var(--danger);font-size:12px;margin-bottom:10px;display:${shareCode?'block':'none'}">提取码不正确，请重试</div>
      <input id="codeIn" type="text" placeholder="请输入提取码" style="width:100%;margin-bottom:14px;font-size:16px" onkeydown="if(event.key==='Enter')submitCode()">
      <button class="z-btn z-btn-teal" style="width:100%;padding:12px" onclick="submitCode()">立即提取</button>
    </div>`;return;
  }
  shareInfo=d;
  if(!d.is_dir){
    const pt=previewType(d.name),dlUrl=`/s/${encodeURIComponent(TOKEN)}/download`+qsAuth('');
    const pvBtn=pt!=='none'?`<button class="z-btn z-btn-ghost" style="padding:11px 22px" onclick="openPreview('','${esc(d.name)}','${pt}')">在线预览</button>`:'';
    root.innerHTML=`<div class="z-card pad" style="max-width:560px;margin:8vh auto;text-align:center">
      <div style="margin-bottom:12px;color:var(--teal)"><svg width="44" height="44" viewBox="0 0 24 24" fill="currentColor"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 7V3.5L18.5 9H13z"/></svg></div>
      <h2 style="margin:0;font-size:19px;word-break:break-all">${esc(d.name)}</h2>
      <div class="sub">大小：${esc(d.size_str)} · 有效期：${esc(d.expire_str)}</div>
      <div style="display:flex;gap:12px;justify-content:center;margin-top:24px;flex-wrap:wrap">
        ${pvBtn}<a class="z-btn z-btn-teal" style="padding:11px 26px" href="${dlUrl}" download>立即下载</a>
      </div>
    </div>`;
  }else{
    root.innerHTML=`<div class="z-card" style="overflow:hidden">
      <div class="pad" style="padding-bottom:14px">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
          <h2 style="margin:0;font-size:19px">${esc(d.name)}</h2>
          <span class="z-tag z-tag-khaki">有效期 · ${esc(d.expire_str)}</span><a class="z-btn z-btn-teal" style="margin-left:auto" href="/s/${encodeURIComponent(TOKEN)}/download-zip${qsAuth('')}"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="display:inline-block;vertical-align:-2px;flex-shrink:0"><path d="M20 6h-8l-2-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-6 10h-4v-2h4v2zm0-4h-4v-2h4v2z"/></svg> 打包下载全部 (.zip)</a>
        </div>
      </div>
      <div class="toolbar">
        <div class="crumb" id="crumb"></div>
        <input type="search" id="kw" placeholder="搜索文件..." oninput="renderDir()" style="width:200px">
      </div>
      <table>
        <thead><tr><th>文件名</th><th style="width:105px">大小</th><th style="width:155px">修改时间</th><th style="width:160px;text-align:right">操作</th></tr></thead>
        <tbody id="listBody"><tr><td colspan="4" class="muted" style="text-align:center;padding:24px">加载中...</td></tr></tbody>
      </table>
    </div>`;
    loadSub('');
  }
}
function submitCode(){shareCode=document.getElementById('codeIn').value.trim();sessionStorage.setItem('sc_'+TOKEN,shareCode);init();}
async function loadSub(sub){
  curSub=sub||'';const parts=curSub?curSub.split('/'):[];
  let html=`<a onclick="loadSub('')">${esc(shareInfo.name)}</a>`,acc='';
  for(const p of parts){acc=joinPath(acc,p);const t=acc;html+=` <span class="muted">/</span> <a onclick="loadSub('${esc(t)}')">${esc(p)}</a>`;}
  document.getElementById('crumb').innerHTML=html;
  curItems=(await (await fetch(`/api/s/${encodeURIComponent(TOKEN)}/list`+qsAuth(curSub))).json()).items||[];
  renderDir();
}
function renderDir(){
  const kw=(document.getElementById('kw')?.value||'').trim().toLowerCase(),tb=document.getElementById('listBody');let rows='';
  if(curSub){const parent=curSub.includes('/')?curSub.slice(0,curSub.lastIndexOf('/')):'';rows+=`<tr><td colspan="4"><div class="name-cell" onclick="loadSub('${esc(parent)}')"><svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="display:inline-block;vertical-align:-2px;flex-shrink:0"><path d="M19 7v4H5.83l3.58-3.59L8 6l-6 6 6 6 1.41-1.41L5.83 13H21V7z"/></svg> 返回上一级</div></td></tr>`;}
  const filtered=curItems.filter(x=>!kw||x.name.toLowerCase().includes(kw));
  if(filtered.length===0){rows+=`<tr><td colspan="4" class="muted" style="text-align:center;padding:24px">目录为空</td></tr>`;}
  else{
    for(const item of filtered){
      const p=joinPath(curSub,item.name);
      if(item.is_dir){
        rows+=`<tr><td><div class="name-cell" onclick="loadSub('${esc(p)}')"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:-2px;flex-shrink:0;color:#6fa8a5"><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/></svg> ${esc(item.name)}</div></td><td class="muted">文件夹</td><td class="muted">${esc(item.mtime)}</td><td class="actions"><a class="z-btn z-btn-khaki" href="/s/${encodeURIComponent(TOKEN)}/download-zip${qsAuth(p)}">打包下载</a><button class="z-btn z-btn-teal" onclick="loadSub('${esc(p)}')">打开</button></td></tr>`;
      }else{
        const pt=previewType(item.name),dlUrl=`/s/${encodeURIComponent(TOKEN)}/download`+qsAuth(p);
        const pvBtn=pt!=='none'?`<button class="z-btn z-btn-ghost" onclick="openPreview('${esc(p)}','${esc(item.name)}','${pt}')">预览</button>`:'';
        rows+=`<tr><td><div class="name-cell" onclick="${pt!=='none'?`openPreview('${esc(p)}','${esc(item.name)}','${pt}')`:`window.open('${dlUrl}','_blank')`}"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="display:inline-block;vertical-align:-2px;flex-shrink:0"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 7V3.5L18.5 9H13z"/></svg> ${esc(item.name)}</div></td><td class="muted">${esc(item.size_str)}</td><td class="muted">${esc(item.mtime)}</td><td class="actions">${pvBtn}<a class="z-btn z-btn-teal" href="${dlUrl}" download>下载</a></td></tr>`;
      }
    }
  }
  tb.innerHTML=rows;
}
async function openPreview(sub,name,type){
  const rawUrl=`/s/${encodeURIComponent(TOKEN)}/raw`+qsAuth(sub),dlUrl=`/s/${encodeURIComponent(TOKEN)}/download`+qsAuth(sub);
  document.getElementById('mTitle').textContent=name;document.getElementById('mDown').href=dlUrl;
  const body=document.getElementById('mBody');body.innerHTML='<div class="muted">加载中...</div>';
  document.getElementById('modal').classList.add('show');
  if(type==='image')body.innerHTML=`<img src="${rawUrl}" alt="${esc(name)}">`;
  else if(type==='video')body.innerHTML=`<video src="${rawUrl}" controls autoplay playsinline webkit-playsinline></video>`;
  else if(type==='audio')body.innerHTML=`<audio src="${rawUrl}" controls autoplay style="width:100%"></audio>`;
  else if(type==='pdf')body.innerHTML=`<iframe src="${rawUrl}"></iframe>`;
  else if(type==='text'){const r=await fetch(`/s/${encodeURIComponent(TOKEN)}/text`+qsAuth(sub));body.innerHTML=`<pre>${esc(await r.text())}</pre>`;}
}
function closeModal(){document.getElementById('modal').classList.remove('show');document.getElementById('mBody').innerHTML='';}
init();
</script></body></html>"""

class FileHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def is_authed(self):
        c = cookies.SimpleCookie(self.headers.get("Cookie", ""))
        return "fsid" in c and c["fsid"].value in SESSIONS

    def send_json(self, code, obj, extra=None):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        if extra:
            for k, v in extra.items():
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

    def list_dir_items(self, real):
        items = []
        try:
            for entry in os.scandir(real):
                name = entry.name
                if name in ("$RECYCLE.BIN", "System Volume Information") or name.startswith("._"):
                    continue
                try:
                    st = entry.stat(follow_symlinks=True)
                    is_dir = entry.is_dir(follow_symlinks=True)
                    mtime = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
                    items.append({
                        "name": name,
                        "is_dir": is_dir,
                        "size": 0 if is_dir else st.st_size,
                        "size_str": "-" if is_dir else human_size(st.st_size),
                        "mtime": mtime,
                    })
                except OSError:
                    continue
        except OSError:
            pass
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return items

    def serve_text(self, real):
        if not real or not os.path.isfile(real):
            self.send_response(404)
            self.end_headers()
            return
        with open(real, "rb") as f:
            data = f.read(524288)
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("gbk", errors="replace")
        raw = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def serve_zip_dir(self, real_dir, zip_name=None):
        if not real_dir or not os.path.isdir(real_dir):
            self.send_response(404)
            self.end_headers()
            return
        parent = os.path.dirname(real_dir.rstrip("/"))
        folder = os.path.basename(real_dir.rstrip("/"))
        dl_name = (zip_name or folder or "archive") + ".zip"
        qname = urllib.parse.quote(dl_name)
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{qname}")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        proc = subprocess.Popen(
            ["zip", "-0", "-q", "-r", "-", folder, "-x", "*/$RECYCLE.BIN/*", "*/System Volume Information/*", "*/._*"],
            cwd=parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        try:
            while True:
                chunk = proc.stdout.read(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            proc.kill()
        finally:
            try:
                proc.stdout.close()
                proc.wait(timeout=5)
            except Exception:
                proc.kill()

    def serve_file(self, real_path, as_download=False):
        if not real_path or not os.path.isfile(real_path):
            self.send_response(404)
            self.end_headers()
            return
        fsize = os.path.getsize(real_path)
        ctype = mimetypes.guess_type(real_path)[0] or "application/octet-stream"
        fname = os.path.basename(real_path)
        range_hdr = self.headers.get("Range")
        start, end = 0, fsize - 1
        status = 200
        if range_hdr and fsize > 0:
            m = re.match(r"bytes=(\d*)-(\d*)", range_hdr)
            if m:
                if m.group(1):
                    start = int(m.group(1))
                if m.group(2):
                    end = min(int(m.group(2)), fsize - 1)
                if start <= end < fsize:
                    status = 206
        length = max(0, end - start + 1)
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{fsize}")
        if as_download:
            qname = urllib.parse.quote(fname)
            self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{qname}")
        self.end_headers()
        try:
            with open(real_path, "rb") as f:
                f.seek(start)
                remain = length
                while remain > 0:
                    chunk = f.read(min(65536, remain))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remain -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def check_share_access(self, token, qs):
        res = get_valid_share(token)
        if not res:
            self.send_json(404, {"error": "not_found"})
            return None
        sh, base_real = res
        req_code = qs.get("code", [""])[0]
        if sh.get("code") and req_code != sh.get("code"):
            self.send_json(403, {"need_code": True, "name": sh.get("name", "")})
            return None
        sub = qs.get("sub", [""])[0]
        target = base_real if not sub else resolve_safe_path(sub, base_real)
        if not target:
            self.send_json(403, {"error": "forbidden"})
            return None
        return sh, base_real, target

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        rel = qs.get("path", [""])[0]

        # 公开分享页入口: /s/<token>
        m_share_page = re.match(r"^/s/([A-Za-z0-9_-]+)/?$", parsed.path)
        if m_share_page:
            self.send_html(HTML_SHARE_PAGE)
            return

        # 公开分享 API & 下载: /api/s/<token>/info, /api/s/<token>/list, /s/<token>/(raw|download|text)
        m_sapi = re.match(r"^/api/s/([A-Za-z0-9_-]+)/(info|list)$", parsed.path)
        if m_sapi:
            token, action = m_sapi.group(1), m_sapi.group(2)
            chk = self.check_share_access(token, qs)
            if not chk:
                return
            sh, base_real, target = chk
            if action == "info":
                is_dir = os.path.isdir(base_real)
                exp = sh.get("expires_at", 0)
                exp_str = "永久有效" if not exp else datetime.fromtimestamp(exp).strftime("%Y-%m-%d %H:%M")
                self.send_json(200, {
                    "name": sh.get("name", os.path.basename(base_real)),
                    "is_dir": is_dir,
                    "size_str": "-" if is_dir else human_size(os.path.getsize(base_real)),
                    "expire_str": exp_str,
                })
            else:
                if not os.path.isdir(target):
                    self.send_json(404, {"items": []})
                    return
                self.send_json(200, {"items": self.list_dir_items(target)})
            return

        m_sfile = re.match(r"^/s/([A-Za-z0-9_-]+)/(raw|download|text|download-zip)$", parsed.path)
        if m_sfile:
            token, action = m_sfile.group(1), m_sfile.group(2)
            chk = self.check_share_access(token, qs)
            if not chk:
                return
            _, _, target = chk
            if action == "text":
                self.serve_text(target)
            elif action == "download-zip":
                self.serve_zip_dir(target)
            else:
                self.serve_file(target, as_download=(action == "download"))
            return

        # 主人网盘入口
        if parsed.path == "/api/v6info":
            ip6 = get_tr3000_ipv6()
            self.send_json(200, {"ipv6": ip6, "port": 18099, "base": f"http://[{ip6}]:18099" if ip6 else ""})
            return
        if parsed.path == "/":
            self.send_html(HTML_APP if self.is_authed() else HTML_LOGIN)
            return
        if not self.is_authed():
            self.send_json(401, {"error": "unauthorized"})
            return

        if parsed.path == "/api/list":
            real = resolve_safe_path(rel)
            if not real or not os.path.isdir(real):
                self.send_json(404, {"items": []})
                return
            self.send_json(200, {"items": self.list_dir_items(real)})
            return

        if parsed.path == "/api/share/list":
            global SHARES
            SHARES = load_json_file(SHARES_FILE, {})
            now = time.time()
            out = []
            for tok, sh in list(SHARES.items()):
                exp = sh.get("expires_at", 0)
                if exp and now > exp:
                    continue
                out.append({
                    "token": tok,
                    "name": sh.get("name", ""),
                    "path": sh.get("path", ""),
                    "code": sh.get("code", ""),
                    "expire_str": "永久有效" if not exp else datetime.fromtimestamp(exp).strftime("%Y-%m-%d %H:%M"),
                    "created_at": sh.get("created_at", 0),
                })
            out.sort(key=lambda x: x["created_at"], reverse=True)
            self.send_json(200, {"shares": out})
            return

        if parsed.path == "/api/text":
            self.serve_text(resolve_safe_path(rel))
            return
        if parsed.path == "/raw":
            self.serve_file(resolve_safe_path(rel), as_download=False)
            return
        if parsed.path == "/download":
            self.serve_file(resolve_safe_path(rel), as_download=True)
            return
        if parsed.path == "/download-zip":
            self.serve_zip_dir(resolve_safe_path(rel))
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        ln = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(ln).decode("utf-8", "ignore") or "{}") if ln > 0 else {}
        if self.path == "/api/login":
            if body.get("password") == get_file_pass():
                sid = secrets.token_hex(24)
                SESSIONS.add(sid)
                save_sessions()
                self.send_json(200, {"ok": True}, {"Set-Cookie": f"fsid={sid}; Path=/; Max-Age=2592000; HttpOnly; SameSite=None; Secure"})
            else:
                self.send_json(403, {"ok": False})
            return
        if self.path == "/api/logout":
            c = cookies.SimpleCookie(self.headers.get("Cookie", ""))
            if "fsid" in c:
                SESSIONS.discard(c["fsid"].value)
                save_sessions()
            self.send_json(200, {"ok": True}, {"Set-Cookie": "fsid=; Path=/; Max-Age=0"})
            return
        if not self.is_authed():
            self.send_json(401, {"error": "unauthorized"})
            return

        if self.path == "/api/share/create":
            rel = str(body.get("path", "")).strip("/")
            real = resolve_safe_path(rel)
            if not real or not os.path.exists(real):
                self.send_json(404, {"ok": False, "error": "文件或目录不存在"})
                return
            days = int(body.get("days", 7) or 0)
            code = str(body.get("code", "")).strip()[:16]
            token = secrets.token_urlsafe(6).replace("-", "a").replace("_", "b")
            now = int(time.time())
            SHARES[token] = {
                "path": rel,
                "name": os.path.basename(rel) or rel,
                "code": code,
                "created_at": now,
                "expires_at": (now + days * 86400) if days > 0 else 0,
            }
            save_shares()
            self.send_json(200, {"ok": True, "token": token})
            return

        if self.path == "/api/share/delete":
            tok = str(body.get("token", "")).strip()
            if tok in SHARES:
                del SHARES[tok]
                save_shares()
            self.send_json(200, {"ok": True})
            return

        self.send_response(404)
        self.end_headers()

if __name__ == "__main__":
    os.makedirs(ROOT_VIEW, exist_ok=True)
    srv = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), FileHandler)
    srv.serve_forever()
