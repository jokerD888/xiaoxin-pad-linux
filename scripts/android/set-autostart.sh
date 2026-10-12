#!/system/bin/sh
set -eu
[ "$(id -u)" = 0 ] || exit 1
case "${1:-}" in
    on) printf '%s\n' kde > /data/adb/boot_mode;;
    off) printf '%s\n' android_always > /data/adb/boot_mode;;
    *) echo 'Usage: set-autostart.sh on|off' >&2;exit 2;;
esac
