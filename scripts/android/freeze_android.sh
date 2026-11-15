#!/system/bin/sh
# ==============================================================================
# freeze_android.sh: Linux 独占模式 - 深度剥离与锁死 Android + 内核调优
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

# 2. 终止非关键后台组件 & 停止 24 小时后台写盘诊断服务
BLOAT_PKGS="
com.zui.weather
com.lenovo.process.weathercenter
com.zui.notes
com.zui.gallery
com.zui.recorder
com.zui.deskclock
com.zui.theme.settings
com.google.android.webview
com.netease.uuremote
"
for pkg in $BLOAT_PKGS; do
    am force-stop "$pkg" 2>/dev/null || true
done

for svc in vendor.cnss_diag mainlog_cur eventslog_cur vendor.ipacm-diag; do
    stop "$svc" 2>/dev/null || true
done
echo "[freeze] Force-stopped bloat packages and stopped ZUI diagnostic loggers." >> "$LOG"

# 3. 冻结剩余已识别的用户层应用 UIDs (排除易触发服务拉起超时死循环的组件，需通过 debloat_android.sh 卸载)
ANLAND_UID=$(pm list packages -U com.anland.consumer.desktop 2>/dev/null | grep -o 'uid:[0-9]*' | cut -d: -f2)
[ -z "$ANLAND_UID" ] && ANLAND_UID=10202

FROZEN_COUNT=0
TARGET_UIDS="10110 10055 10068 10017 10061 10067 10212 10129 10062 10155"

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

# 6. 内核 ZRAM 与 UFS I/O 调优 (消除 ZRAM 8页预读放大，使用 deadline 调度)
echo 0 > /proc/sys/vm/page-cluster 2>/dev/null || true
echo deadline > /sys/block/sda/queue/scheduler 2>/dev/null || true
echo 128 > /sys/block/sda/queue/read_ahead_kb 2>/dev/null || true
echo 128 > /sys/block/dm-10/queue/read_ahead_kb 2>/dev/null || true

# 7. 清理无用缓存
echo 3 > /proc/sys/vm/drop_caches

# 8. 标记状态文件
ROOTFS=/data/local/archlinux
echo "frozen" > "$ROOTFS/run/android_freeze.status" 2>/dev/null || true
chmod 644 "$ROOTFS/run/android_freeze.status" 2>/dev/null || true

echo "=== Android Freeze completed successfully at $(date) ===" >> "$LOG"
