#!/bin/sh
# 输出当前所有非 EFI USB 分区的机器可读信息: part|uuid|fstype|size|used|avail|usepct|mounted|alias|enabled
ALIAS_FILE="/etc/tr3000_aliases.conf"
touch "$ALIAS_FILE"
for dev in /dev/sd[a-z][0-9]*; do
    [ -b "$dev" ] || continue
    part=$(basename "$dev")
    info=$(blkid "$dev" 2>/dev/null)
    fstype=$(echo "$info" | sed -n 's/.* TYPE="\([^"]*\)".*/\1/p')
    label=$(echo "$info" | sed -n 's/.* LABEL="\([^"]*\)".*/\1/p')
    uuid=$(echo "$info" | sed -n 's/.* UUID="\([^"]*\)".*/\1/p')
    [ -z "$fstype" ] && continue
    if [ "$label" = "EFI" ] || echo "$info" | grep -q 'EFI System Partition'; then
        continue
    fi
    [ -z "$uuid" ] && uuid="$part"
    mp="/mnt/$part"
    if mount | grep -q "^$dev "; then
        mounted="1"
        dfline=$(df -h "$mp" 2>/dev/null | tail -n 1)
        size=$(echo "$dfline" | awk '{print $2}')
        used=$(echo "$dfline" | awk '{print $3}')
        avail=$(echo "$dfline" | awk '{print $4}')
        usepct=$(echo "$dfline" | awk '{print $5}')
    else
        mounted="0"
        size="-"; used="-"; avail="-"; usepct="-"
    fi
    line=$(grep "^${uuid}|" "$ALIAS_FILE" | head -n 1 || true)
    if [ -n "$line" ]; then
        alias_name=$(echo "$line" | cut -d'|' -f2)
        enabled=$(echo "$line" | cut -d'|' -f3)
    else
        alias_name="$part"
        enabled="1"
    fi
    [ -z "$alias_name" ] && alias_name="$part"
    [ -z "$enabled" ] && enabled="1"
    echo "${part}|${uuid}|${fstype}|${size}|${used}|${avail}|${usepct}|${mounted}|${alias_name}|${enabled}"
done
