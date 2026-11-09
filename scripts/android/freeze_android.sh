#!/system/bin/sh
# ==============================================================================
# freeze_android.sh: Linux 独占模式 - 深度剥离与锁死 Android
# ==============================================================================
LOG="/data/adb/kde-desktop/logs/freeze.log"
mkdir -p /data/adb/kde-desktop/logs
echo "=== Android Freeze started at $(date) ===" > "$LOG"

# 0. 屏蔽后台 ANR 弹窗与中断，强制全局全屏沉浸 (隐藏 Android 状态栏与导航栏)
settings put secure anr_show_background 0 2>/dev/null || true
settings put global show_anr_dialogs 0 2>/dev/null || true
settings put global policy_control immersive.full=* 2>/dev/null || true

# 1. 彻底禁用 Android 桌面与 FallbackHome (杜绝手势回桌面与多任务切换)
pm disable com.zui.launcher 2>/dev/null || true
pm disable com.android.settings/.FallbackHome 2>/dev/null || true
echo "[freeze] Disabled Launcher and FallbackHome." >> "$LOG"

# 2. 终止非关键后台臃肿组件
BLOAT_PKGS="
com.lenovo.leos.appstore
com.tblenovo.lenovowhatsnew
com.tblenovo.center
com.zui.weather
com.lenovo.process.weathercenter
com.zui.notes
com.zui.gallery
com.zui.recorder
com.zui.deskclock
com.zui.game.service
com.zui.udevice
com.lenovo.lsf.device
com.zui.xlog
com.zui.theme.settings
com.android.smspush
com.google.android.webview
com.baidu.map.location
com.netease.uuremote
com.motorola.mobiledesktop.core
"
for pkg in $BLOAT_PKGS; do
    am force-stop "$pkg" 2>/dev/null || true
done
echo "[freeze] Force-stopped bloat packages." >> "$LOG"

# 3. 冻结剩余已识别的用户层应用 UIDs
ANLAND_UID=$(pm list packages -U com.anland.consumer.desktop 2>/dev/null | grep -o 'uid:[0-9]*' | cut -d: -f2)
[ -z "$ANLAND_UID" ] && ANLAND_UID=10202

FROZEN_COUNT=0
TARGET_UIDS="10110 10055 10068 10017 10070 10060 10079 10082 10061 10067 10212 10129 10182 10097 10104 10062 10155"

for uid in $TARGET_UIDS; do
    if [ "$uid" != "$ANLAND_UID" ] && [ -f "/sys/fs/cgroup/uid_$uid/cgroup.freeze" ]; then
        su 1000 -c "echo 1 > /sys/fs/cgroup/uid_$uid/cgroup.freeze" 2>/dev/null || true
        FROZEN_COUNT=$((FROZEN_COUNT + 1))
    fi
done
echo "[freeze] Frozen $FROZEN_COUNT app UIDs." >> "$LOG"

# 4. 算力倾斜：限制 Android 后台 cpuset 到 CPU 0-3
echo 0-3 > /dev/cpuset/background/cpus 2>/dev/null || true
echo 0-3 > /dev/cpuset/system-background/cpus 2>/dev/null || true

# 5. 内存特权保障：确保 Linux 关键进程锁定在最高优先级 (-1000)
for pid in $(pgrep -f "kwin_wayland|plasmashell|display_daemon|start-kde|pipewire"); do
    echo -1000 > "/proc/$pid/oom_score_adj" 2>/dev/null || true
done

# 6. 清理无用缓存
echo 3 > /proc/sys/vm/drop_caches

# 7. 标记状态文件
ROOTFS=/data/local/archlinux
echo "frozen" > "$ROOTFS/run/android_freeze.status" 2>/dev/null || true
chmod 644 "$ROOTFS/run/android_freeze.status" 2>/dev/null || true

echo "=== Android Freeze completed successfully at $(date) ===" >> "$LOG"
