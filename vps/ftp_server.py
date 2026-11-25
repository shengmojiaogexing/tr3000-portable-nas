import asynchat
#!/usr/bin/env python3
import os
from pyftpdlib.authorizers import DummyAuthorizer, AuthenticationFailed
from pyftpdlib.filesystems import AbstractedFS
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import ThreadedFTPServer

CRED_FILE = "/opt/tr3000-panel/smb.cred"
ROOT_DIR = "/srv/tr3000_files"

def read_cred():
    user, pwd = "admin", "YOUR_NAS_PASSWORD"
    if os.path.exists(CRED_FILE):
        with open(CRED_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("username="):
                    user = line.split("=", 1)[1].strip()
                elif line.startswith("password="):
                    pwd = line.split("=", 1)[1].strip()
    return user, pwd

class DynamicAuthorizer(DummyAuthorizer):
    def validate_authentication(self, username, password, handler):
        u, p = read_cred()
        if username != u or password != p:
            raise AuthenticationFailed("Invalid credentials")

    def has_user(self, username):
        u, _ = read_cred()
        return username == u

    def get_home_dir(self, username):
        return ROOT_DIR

    def get_perms(self, username):
        return "elradfmwMT"

    def has_perm(self, username, perm, path=None):
        return perm in "elradfmwMT"

    def get_msg_login(self, username):
        return "Welcome to TR3000 Portable NAS FTP Server."

    def get_msg_quit(self, username):
        return "Goodbye."

class SmartFS(AbstractedFS):
    def format_list(self, basedir, listing, ignore_err=True):
        enc = getattr(self.cmd_channel, "client_encoding", "gb18030")
        for chunk in super().format_list(basedir, listing, ignore_err=ignore_err):
            if isinstance(chunk, bytes):
                try:
                    yield chunk.decode("utf-8").encode(enc, errors="replace")
                except Exception:
                    yield chunk
            else:
                yield chunk.encode(enc, errors="replace")

    def format_mlsx(self, basedir, listing, perms, facts, ignore_err=True):
        enc = getattr(self.cmd_channel, "client_encoding", "gb18030")
        for chunk in super().format_mlsx(basedir, listing, perms, facts, ignore_err=ignore_err):
            if isinstance(chunk, bytes):
                try:
                    yield chunk.decode("utf-8").encode(enc, errors="replace")
                except Exception:
                    yield chunk
            else:
                yield chunk.encode(enc, errors="replace")

class SmartEncodingFTPHandler(FTPHandler):
    abstracted_fs = SmartFS
    client_encoding = "gb18030"

    def __init__(self, conn, server, ioloop=None):
        super().__init__(conn, server, ioloop=ioloop)
        # Windows 资源管理器自带 FTP 默认使用 GBK/GB18030
        self.client_encoding = "gb18030"

    def decode(self, bytes_in):
        if self.client_encoding == "utf-8":
            return bytes_in.decode("utf-8", self.unicode_errors)
        try:
            return bytes_in.decode("gb18030")
        except UnicodeDecodeError:
            return bytes_in.decode("utf-8", self.unicode_errors)

    def push(self, s):
        if isinstance(s, str):
            s = s.encode(self.client_encoding, errors="replace")
        asynchat.async_chat.push(self, s)

    def push_dtp_data(self, data, isproducer=False, file=None, cmd=None):
        if not isproducer and isinstance(data, str):
            data = data.encode(self.client_encoding, errors="replace")
        elif not isproducer and isinstance(data, bytes) and cmd == "NLST":
            try:
                data = data.decode("utf-8").encode(self.client_encoding, errors="replace")
            except Exception:
                pass
        return super().push_dtp_data(data, isproducer=isproducer, file=file, cmd=cmd)

    def ftp_OPTS(self, line):
        if line.upper().strip() == "UTF8 ON":
            self.client_encoding = "utf-8"
            self.respond("200 UTF8 mode enabled.")
            return
        elif line.upper().strip() == "UTF8 OFF":
            self.client_encoding = "gb18030"
            self.respond("200 GB18030 mode enabled.")
            return
        super().ftp_OPTS(line)

def main():
    os.makedirs(ROOT_DIR, exist_ok=True)
    handler = SmartEncodingFTPHandler
    handler.authorizer = DynamicAuthorizer()
    handler.banner = "TR3000 Portable NAS FTP Ready."
    handler.masquerade_address = "YOUR_VPS_IP"
    handler.passive_ports = range(30100, 30151)
    handler.use_gmt_times = False
    server = ThreadedFTPServer(("0.0.0.0", 2121), handler)
    server.max_cons = 64
    server.max_cons_per_ip = 16
    server.serve_forever()

if __name__ == "__main__":
    main()
