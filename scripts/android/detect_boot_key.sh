#!/system/bin/sh
# ==============================================================================
# detect_boot_key.sh: 动态检测物理音量下键 (KEY_VOLUMEDOWN)
# 返回码:
#   0 -> 检测到按键（已按住或窗口内按下），应停留在 ZUI
#   1 -> 未检测到按键，默认启动 KDE
# ==============================================================================

WINDOW_SEC=${1:-3}
LOG_DIR="/data/adb/kde-desktop/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/boot_key_sample.log"

# 1. 动态寻找 qpnp_pon 设备节点 (避免硬编码 event0)
TARGET_DEV=""
for dev in /sys/class/input/event*; do
    if [ -f "$dev/device/name" ]; then
        name=$(cat "$dev/device/name" 2>/dev/null)
        if [ "$name" = "qpnp_pon" ]; then
            dev_name=$(basename "$dev")
            TARGET_DEV="/dev/input/$dev_name"
            break
        fi
    fi
done

[ -z "$TARGET_DEV" ] && TARGET_DEV="/dev/input/event0"

# 2. 检查是否在进入检测前就已被按住 (通过 dumpsys input 查询当前 KeyDowns)
if dumpsys input 2>/dev/null | grep -A 4 "qpnp_pon" | grep -q "KeyDowns: [1-9]"; then
    echo "[detect_boot_key] ALREADY_HELD"
    exit 0
fi

# 3. 在指定时间窗口内通过后台 getevent 捕获并过滤 KEY_VOLUMEDOWN (0072) 按下事件
rm -f "$LOG"
getevent "$TARGET_DEV" > "$LOG" 2>&1 </dev/null &
GE_PID=$!

sleep "$WINDOW_SEC"
kill -9 "$GE_PID" 2>/dev/null || true

# 0001 0072 00000001 = DOWN, 00000002 = REPEAT
if grep -q "0001 0072 0000000[12]" "$LOG" 2>/dev/null; then
    rm -f "$LOG"
    echo "[detect_boot_key] PRESSED"
    exit 0
fi

rm -f "$LOG"
echo "[detect_boot_key] NONE"
exit 1
