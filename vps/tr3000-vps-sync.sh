#!/bin/bash
set -e
RAW_DIR="/mnt/tr3000_raw"
VIEW_DIR="/srv/tr3000_files"
mkdir -p "$RAW_DIR" "$VIEW_DIR"

if mount | grep -q "on $RAW_DIR type cifs"; then
    umount -l "$RAW_DIR" 2>/dev/null || true
fi

if ! mountpoint -q "$RAW_DIR"; then
    sshfs root@10.126.126.1:/mnt "$RAW_DIR" \
      -o IdentityFile=/root/.ssh/id_ed25519 \
      -o StrictHostKeyChecking=no \
      -o allow_other \
      -o reconnect \
      -o ServerAliveInterval=15 \
      -o ServerAliveCountMax=3 \
      -o cache=yes
fi

INFO=$(ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=6 -o BatchMode=yes root@10.126.126.1 "/usr/bin/tr3000-disk-info.sh" 2>/dev/null || true)

# 清理旧软链与旧 bind 挂载目录
for item in "$VIEW_DIR"/*; do
    [ -e "$item" ] || [ -L "$item" ] || continue
    if [ -L "$item" ]; then
        rm -f "$item"
    elif mountpoint -q "$item"; then
        umount -l "$item" 2>/dev/null || true
        rmdir "$item" 2>/dev/null || true
    fi
done

if [ -n "$INFO" ]; then
    echo "$INFO" | while IFS='|' read -r part uuid fstype size used avail usepct mounted alias enabled; do
        [ "$mounted" = "1" ] || continue
        [ "$enabled" = "1" ] || continue
        [ -z "$alias" ] && alias="$part"
        if [ -d "$RAW_DIR/$part" ]; then
            mkdir -p "$VIEW_DIR/$alias"
            mount --bind "$RAW_DIR/$part" "$VIEW_DIR/$alias"
        fi
    done
fi
