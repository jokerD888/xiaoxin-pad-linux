#!/system/bin/sh
# ==============================================================================
# launch_kde_desktop.sh: KDE Plasma 6 桌面两阶段启动与健康检查
# ==============================================================================
set -e
ROOTFS=/data/local/archlinux
SOCK=/data/local/tmp/display_daemon.sock
INNER_SOCK=$ROOTFS/run/display.sock
DAEMON=/data/adb/modules/anland-daemon/display_daemon
WAYLAND_SOCK=$ROOTFS/run/user/1000/wayland-0
LOG_DIR=/data/adb/kde-desktop/logs
mkdir -p "$LOG_DIR"
LOG=$LOG_DIR/start-kde.log

echo "[launch_kde] === Stage A: Environment Setup & Mounts ==="
mountpoint -q "$ROOTFS/proc" || mount -t proc proc "$ROOTFS/proc"
mountpoint -q "$ROOTFS/sys" || mount -t sysfs sys "$ROOTFS/sys"
mountpoint -q "$ROOTFS/dev" || mount -o bind /dev "$ROOTFS/dev"
mountpoint -q "$ROOTFS/dev/pts" || mount -t devpts devpts "$ROOTFS/dev/pts"
mkdir -p "$ROOTFS/dev/shm" "$ROOTFS/tmp" "$ROOTFS/run" "$ROOTFS/sdcard"
mountpoint -q "$ROOTFS/dev/shm" || mount -t tmpfs -o rw,nosuid,nodev,mode=1777 tmpfs "$ROOTFS/dev/shm"
mountpoint -q "$ROOTFS/tmp" || mount -t tmpfs -o rw,nosuid,nodev,mode=1777 tmpfs "$ROOTFS/tmp"
mkdir -p "$ROOTFS/tmp/.X11-unix"
chmod 1777 "$ROOTFS/tmp/.X11-unix"
mountpoint -q "$ROOTFS/run" || mount -t tmpfs -o rw,nosuid,nodev,mode=755 tmpfs "$ROOTFS/run"
umount -f -l "$ROOTFS/sdcard" 2>/dev/null || true
mount -o bind /data/media/0 "$ROOTFS/sdcard" 2>/dev/null || mount -o bind /sdcard "$ROOTFS/sdcard" 2>/dev/null || true
mkdir -p "$ROOTFS/run/user/1000" "$ROOTFS/run/dbus"
chown 1000:1000 "$ROOTFS/run/user/1000"
chmod 700 "$ROOTFS/run/user/1000"

# /data is nosuid. Preserve standard sudo/FUSE helpers on a dedicated tmpfs.
/data/adb/kde-desktop/bin/setup_privileged_tools.sh



if [ "$(getenforce 2>/dev/null)" = Enforcing ]; then
    [ -f "$ROOTFS/etc/xiaoxin-linux/allow-permissive" ] || { echo "This build requires explicit SELinux permissive consent." >&2; exit 1; }
    setenforce 0
fi
chmod 666 /dev/kgsl-3d0 /dev/ion /dev/dri/* /dev/video* /dev/v4l-subdev* 2>/dev/null || true

# 宿主桥独立于图形会话，桌面停止后仍能接收恢复命令；flock 保证单实例。
nohup /data/adb/kde-desktop/bin/linux-host-bridge.sh >>"$LOG_DIR/linux-host-bridge.log" 2>&1 </dev/null &

# 启动 Display Daemon
if [ ! -S "$INNER_SOCK" ] || ! pidof display_daemon >/dev/null; then
    for pid in $(pidof display_daemon); do kill "$pid" 2>/dev/null || true; done
    rm -f "$SOCK" "$INNER_SOCK"
    ln -s "$INNER_SOCK" "$SOCK"
    nohup "$DAEMON" "$INNER_SOCK" >"$LOG_DIR/anland-daemon.log" 2>&1 </dev/null &
    sleep 1
fi
chmod 666 "$INNER_SOCK" 2>/dev/null || true

# 启动 KDE Plasma 6 桌面会话
if ! pidof kwin_wayland.real >/dev/null; then
    echo "[launch_kde] Starting KDE Plasma Session in chroot..."
    nohup chroot "$ROOTFS" /bin/su - linux -c '/usr/local/bin/start-kde-session' >"$LOG" 2>&1 </dev/null &
fi

# 等待 Wayland Socket 与 KWin 建立就绪 (测量耗时)
echo "[launch_kde] === Stage A: Waiting for Wayland Socket ==="
T_START=$(date +%s)
READY=0
for i in $(seq 1 30); do
    if [ -S "$WAYLAND_SOCK" ] && pidof kwin_wayland.real >/dev/null; then
        T_NOW=$(date +%s)
        T_ELAPSED=$(( T_NOW - T_START ))
        echo "[launch_kde] Wayland Socket ready in ${T_ELAPSED}s (poll $i)"
        READY=1
        break
    fi
    sleep 1
done

if [ "$READY" -ne 1 ]; then
    echo "[launch_kde] ERROR: Wayland Socket timed out after 30s! Aborting KDE switch, staying in ZUI."
    exit 1
fi

# 后台关闭 ksplash
(
    i=0
    while [ "$i" -lt 30 ]; do
        if pidof plasmashell >/dev/null; then
            sleep 3
            for pid in $(pidof ksplashqml); do kill "$pid" 2>/dev/null || true; done
            exit 0
        fi
        i=$((i + 1))
        sleep 1
    done
) </dev/null >/dev/null 2>&1 &

# 阶段 B: 切换前台并验证握手
echo "[launch_kde] === Stage B: Switching Anland Consumer to Foreground ==="
input keyevent 224 || true
wm dismiss-keyguard || true
am start -n com.anland.consumer.desktop/com.anland.consumer.MainActivity >/dev/null 2>&1 || true

# 验证握手: 检查 Anland Consumer 是否正常存活运行
sleep 2
if ! pidof com.anland.consumer.desktop >/dev/null; then
    echo "[launch_kde] ERROR: com.anland.consumer.desktop exited unexpectedly! Fallback to ZUI."
    am start -n com.zui.launcher/.drawer.NormalLauncher >/dev/null 2>&1 || true
    exit 1
fi

echo "[launch_kde] KDE Desktop successfully launched and verified!"
if [ -f "$ROOTFS/usr/local/libexec/linux-mode-controller.py" ]; then
    chroot "$ROOTFS" /usr/bin/env PATH=/usr/local/bin:/usr/bin:/bin /usr/bin/python /usr/local/libexec/linux-mode-controller.py status || true
fi
exit 0
