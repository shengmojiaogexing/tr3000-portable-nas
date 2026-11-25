#!/bin/sh
# 读取 /etc/tr3000_aliases.conf (格式: UUID|共享名称|启用1或0) 并同步 ksmbd 共享
ALIAS_FILE="/etc/tr3000_aliases.conf"
touch "$ALIAS_FILE"

while uci -q delete ksmbd.@share[0]; do :; done

# 先保留一个总目录 USB_Disk，方便查看全部挂载盘
uci add ksmbd share >/dev/null
uci set ksmbd.@share[-1].name='USB_Disk'
uci set ksmbd.@share[-1].path='/mnt'
uci set ksmbd.@share[-1].users='admin'
uci set ksmbd.@share[-1].read_only='no'
uci set ksmbd.@share[-1].guest_ok='no'
uci set ksmbd.@share[-1].create_mask='0666'
uci set ksmbd.@share[-1].dir_mask='0777'
uci set ksmbd.@share[-1].force_root='1'

for dev in /dev/sd[a-z][0-9]*; do
    [ -b "$dev" ] || continue
    part=$(basename "$dev")
    mp="/mnt/$part"
    mount | grep -q "^$dev " || continue
    info=$(blkid "$dev" 2>/dev/null)
    uuid=$(echo "$info" | sed -n 's/.* UUID="\([^"]*\)".*/\1/p')
    [ -z "$uuid" ] && uuid="$part"

    line=$(grep "^${uuid}|" "$ALIAS_FILE" | head -n 1 || true)
    if [ -n "$line" ]; then
        sname=$(echo "$line" | cut -d'|' -f2)
        enabled=$(echo "$line" | cut -d'|' -f3)
    else
        sname="$part"
        enabled="1"
    fi
    [ -z "$sname" ] && sname="$part"
    [ "$enabled" = "0" ] && continue

    uci add ksmbd share >/dev/null
    uci set ksmbd.@share[-1].name="$sname"
    uci set ksmbd.@share[-1].path="$mp"
    uci set ksmbd.@share[-1].users='admin'
    uci set ksmbd.@share[-1].read_only='no'
    uci set ksmbd.@share[-1].guest_ok='no'
    uci set ksmbd.@share[-1].create_mask='0666'
    uci set ksmbd.@share[-1].dir_mask='0777'
    uci set ksmbd.@share[-1].force_root='1'
done

uci commit ksmbd
/etc/init.d/ksmbd restart >/dev/null 2>&1 || true
