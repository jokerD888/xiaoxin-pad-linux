#!/system/bin/sh
# Fixed host commands, accessible only to root and Gold's existing group.
set -u
ROOTFS=/data/local/archlinux
umask 022
FIFO=$ROOTFS/run/host_cmd.fifo
BASE=/data/adb/kde-desktop
mkdir -p "$BASE/logs"
exec 9>"$ROOTFS/run/linux-host-bridge.lock"
flock -n 9 9>&9 || exit 0
echo $$ > "$ROOTFS/run/linux-host-bridge.pid"
if [ ! -p "$FIFO" ]; then
    [ ! -e "$FIFO" ] || exit 1
    mkfifo "$FIFO"
fi
chown 0:1000 "$FIFO"
chmod 620 "$FIFO"
# Keep the FIFO open between commands, including when desktop services stop.
exec 3<>"$FIFO"
MIC=$ROOTFS/run/anland-mic-demand
if [ -d "$ROOTFS/run" ]; then
    [ -e "$MIC" ] || printf 0 > "$MIC"
    chown 0:0 "$MIC"
    chmod 644 "$MIC"
fi
if [ -d "$ROOTFS/run" ]; then
    [ -e "$ROOTFS/run/keep-awake.status" ] || printf 1 > "$ROOTFS/run/keep-awake.status"
    chown 0:1000 "$ROOTFS/run/keep-awake.status"
    chmod 664 "$ROOTFS/run/keep-awake.status"
fi
while IFS= read -r cmd <&3; do
    case "$cmd" in
        reboot-android-once)
            echo "android_once" > /data/adb/boot_mode
            sh "$BASE/bin/unfreeze_android.sh" >/dev/null 2>&1 || true
            sync
            reboot
            ;;
        reboot-android-always)
            echo "android_always" > /data/adb/boot_mode
            sh "$BASE/bin/unfreeze_android.sh" >/dev/null 2>&1 || true
            sync
            reboot
            ;;
        reboot-linux)
            echo "linux" > /data/adb/boot_mode
            sync
            reboot
            ;;
        freeze-android)
            sh "$BASE/bin/freeze_android.sh" >/dev/null 2>&1 || true
            ;;
        unfreeze-android)
            sh "$BASE/bin/unfreeze_android.sh" >/dev/null 2>&1 || true
            ;;
        switch-to-android)
            sh "$BASE/bin/unfreeze_android.sh" >/dev/null 2>&1 || true
            am start -n com.zui.launcher/.drawer.NormalLauncher >/dev/null 2>&1
            ;;
        switch-to-kde)
            am start -n com.anland.consumer.desktop/com.anland.consumer.MainActivity >/dev/null 2>&1
            sh "$BASE/bin/freeze_android.sh" >/dev/null 2>&1 || true
            ;;
        terminal-mode)
            if chroot "$ROOTFS" /usr/bin/env PATH=/usr/local/bin:/usr/bin:/bin /usr/bin/python /usr/local/libexec/linux-mode-controller.py stop 9>&- 3>&-; then
                for pid in $(pidof display_daemon); do
                    if [ "$(readlink /proc/$pid/exe)" = /data/adb/modules/anland-daemon/display_daemon ]; then
                        kill "$pid" 2>/dev/null || true
                    fi
                done
                am force-stop com.anland.consumer.desktop
                am start -n com.termux/com.termux.app.TermuxActivity
            fi
            ;;
        desktop-mode)
            sh "$BASE/bin/launch_kde_desktop.sh" 9>&- 3>&-
            ;;
        keep-awake-on)
            svc power stayon true
            dumpsys deviceidle disable
            printf 1 > "$ROOTFS/run/keep-awake.status"
            chmod 664 "$ROOTFS/run/keep-awake.status" 2>/dev/null
            chown 0:1000 "$ROOTFS/run/keep-awake.status" 2>/dev/null
            ;;
        keep-awake-off)
            svc power stayon false
            dumpsys deviceidle enable
            printf 0 > "$ROOTFS/run/keep-awake.status"
            chmod 664 "$ROOTFS/run/keep-awake.status" 2>/dev/null
            chown 0:1000 "$ROOTFS/run/keep-awake.status" 2>/dev/null
            ;;
        mic-active|mic-idle)
            # Fixed root-owned destination on the existing /run tmpfs.
            # Only Gold/root can write the FIFO; the Android client checks a 4s lease.
            if [ -d "$ROOTFS/run" ]; then
                # printf preserves mode; do not fork chmod on every heartbeat.
                if [ ! -e "$MIC" ]; then
                    printf 0 > "$MIC"
                    chmod 644 "$MIC"
                fi
                case "$cmd" in mic-active) printf 1 > "$MIC" ;; mic-idle) printf 0 > "$MIC" ;; esac
            fi
            ;;
        *) echo "Ignoring unsupported host command: $cmd" ;;
    esac
done
