#!/system/bin/sh
# Run once after installing and opening Termux. Discover its UID; never hard-code it.
set -eu
[ "$(id -u)" = 0 ] || exit 1
HOME_DIR=/data/user/0/com.termux/files/home
[ -d "$HOME_DIR" ] || { echo 'Install and open Termux first.' >&2; exit 1; }
OWNER=$(stat -c '%u:%g' "$HOME_DIR")
if ! grep -q '# BEGIN xiaoxin-linux' "$HOME_DIR/.bashrc" 2>/dev/null; then
    cat >> "$HOME_DIR/.bashrc" <<'EOF'

# BEGIN xiaoxin-linux
if [ -t 0 ] && [ "${ARCH_TERMINAL_NATIVE:-0}" != 1 ]; then
    exec /system/bin/su -c /data/adb/kde-desktop/bin/linux-terminal.sh
fi
# END xiaoxin-linux
EOF
fi
chown "$OWNER" "$HOME_DIR/.bashrc";chmod 600 "$HOME_DIR/.bashrc"
restorecon "$HOME_DIR/.bashrc" || true
