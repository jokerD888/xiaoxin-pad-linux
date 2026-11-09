#!/system/bin/sh
# ==============================================================================
# unfreeze_android.sh: 解冻并完全恢复 Android 系统
# ==============================================================================
LOG="/data/adb/kde-desktop/logs/freeze.log"
echo "=== Android Unfreeze started at $(date) ===" >> "$LOG"

# 1. 恢复沉浸式设置
settings delete global policy_control 2>/dev/null || true

# 2. 重新启用 Android 桌面与设置
pm enable com.zui.launcher 2>/dev/null || true
pm enable com.android.settings/.FallbackHome 2>/dev/null || true

# 3. 恢复所有 cgroup2 冻结的 UID
for d in /sys/fs/cgroup/uid_*; do
    if [ -f "$d/cgroup.freeze" ]; then
        su 1000 -c "echo 0 > $d/cgroup.freeze" 2>/dev/null || true
    fi
done

# 4. 恢复 cpuset 分配
echo 0-7 > /dev/cpuset/background/cpus 2>/dev/null || true
echo 0-7 > /dev/cpuset/system-background/cpus 2>/dev/null || true

# 5. 拉起桌面 Launcher
am start -n com.zui.launcher/.drawer.NormalLauncher >/dev/null 2>&1 || true

# 6. 标记状态文件供 Linux 桌面读取
ROOTFS=/data/local/archlinux
echo "running" > "$ROOTFS/run/android_freeze.status" 2>/dev/null || true
chmod 644 "$ROOTFS/run/android_freeze.status" 2>/dev/null || true

echo "=== Android Unfreeze completed at $(date) ===" >> "$LOG"
