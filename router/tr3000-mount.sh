#!/bin/sh
# 自动挂载所有 USB 硬盘分区（NTFS 启用 force + utf8，跳过 EFI 分区）
for dev in /dev/sd[a-z][0-9]*; do
    [ -b "$dev" ] || continue
    part=$(basename "$dev")
    info=$(blkid "$dev" 2>/dev/null)
    fstype=$(echo "$info" | sed -n 's/.* TYPE="\([^"]*\)".*/\1/p')
    label=$(echo "$info" | sed -n 's/.* LABEL="\([^"]*\)".*/\1/p')
    [ -z "$fstype" ] && continue
    if [ "$label" = "EFI" ] || echo "$info" | grep -q 'EFI System Partition'; then
        umount "$dev" 2>/dev/null || true
        rmdir "/mnt/$part" 2>/dev/null || true
        continue
    fi
    mp="/mnt/$part"
    mkdir -p "$mp"
    cur=$(mount | grep "^$dev " || true)
    if [ -n "$cur" ]; then
        if echo "$cur" | grep -q "utf8"; then
            continue
        fi
        umount "$dev" 2>/dev/null || umount -l "$dev" 2>/dev/null || true
    fi
    case "$fstype" in
        ntfs)
            mount -t ntfs3 -o rw,force,iocharset=utf8,uid=0,gid=0,fmask=0000,dmask=0000 "$dev" "$mp" 2>/dev/null || \
            mount -t ntfs3 -o rw,force,iocharset=utf8 "$dev" "$mp" 2>/dev/null || true
            ;;
        exfat)
            mount -t exfat -o rw,iocharset=utf8,uid=0,gid=0,fmask=0000,dmask=0000 "$dev" "$mp" 2>/dev/null || true
            ;;
        vfat)
            mount -t vfat -o rw,iocharset=utf8,fmask=0000,dmask=0000 "$dev" "$mp" 2>/dev/null || true
            ;;
        ext4|ext3|ext2)
            mount -t "$fstype" -o rw "$dev" "$mp" 2>/dev/null || true
            ;;
        *)
            mount "$dev" "$mp" 2>/dev/null || true
            ;;
    esac
done
