#!/system/bin/sh
# ==============================================================================
# Magisk 开机自启服务：开机双桌面模式调度器 (Dual Desktop Modes Dispatcher)
# ==============================================================================
BASE="/data/adb/kde-desktop"
mkdir -p "$BASE/logs"
LOG="$BASE/logs/boot_dispatcher.log"
MODE_FILE="/data/adb/boot_mode"

# 1. 等待 Android 核心系统完全启动并完成首次解锁 (CE 存储就绪)
while [ "$(getprop sys.boot_completed)" != "1" ]; do
    sleep 1
done
while [ "$(getprop sys.user.0.ce_available)" != "true" ]; do
    sleep 1
done

# 记录启动时间戳
echo "=== Boot Dispatcher Started at $(date) ===" > "$LOG"

# 确保 /data/local/tmp/boot_mode 软链接存在
ln -sf "$MODE_FILE" /data/local/tmp/boot_mode 2>/dev/null || true

# 2. 第一防御线: 检查模式标记文件 (持久化 / 单次文件标记)
if [ -f "$MODE_FILE" ]; then
    REQ_MODE=$(cat "$MODE_FILE" 2>/dev/null | tr -d ' \r\n')
    echo "Configured boot_mode: '$REQ_MODE'" >> "$LOG"
    case "$REQ_MODE" in
        "android_once")
            echo "kde" > "$MODE_FILE"
            echo "Mode: android_once triggered. Reset to 'kde'. Staying in ZUI." >> "$LOG"
            exit 0
            ;;
        "android_always")
            echo "Mode: android_always active. Staying in ZUI." >> "$LOG"
            exit 0
            ;;
        "kde"|"")
            echo "Mode: kde. Proceeding to key check." >> "$LOG"
            ;;
        *)
            echo "Mode: unknown ('$REQ_MODE'). Fallback safety: staying in ZUI." >> "$LOG"
            exit 0
            ;;
    esac
else
    echo "No boot_mode file. Default to KDE mode." >> "$LOG"
fi

# 3. 第二防御线: 检查物理音量下键 (开机后 3 秒硬件按键检测窗口)
if [ -f "$BASE/bin/detect_boot_key.sh" ]; then
    echo "Starting 3-second physical Volume Down check..." >> "$LOG"
    if sh "$BASE/bin/detect_boot_key.sh" 3 >> "$LOG" 2>&1; then
        echo "Volume Down detected! User selected ZUI. Staying in ZUI." >> "$LOG"
        exit 0
    fi
fi

# 4. 进入两阶段启动与健康检查
echo "Proceeding to launch KDE Desktop..." >> "$LOG"
if [ -f "$BASE/bin/launch_kde_desktop.sh" ]; then
    sh "$BASE/bin/launch_kde_desktop.sh" >> "$LOG" 2>&1
    EXIT_CODE=$?
    if [ "$EXIT_CODE" -ne 0 ]; then
        echo "ERROR: launch_kde_desktop.sh exited with code $EXIT_CODE! Fallback to ZUI." >> "$LOG"
        am start -n com.zui.launcher/.drawer.NormalLauncher >/dev/null 2>&1 || true
    fi
fi
