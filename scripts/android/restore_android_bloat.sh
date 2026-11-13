#!/system/bin/sh
# ==============================================================================
# restore_android_bloat.sh: 一键恢复已精简的 Android 软件包
# ==============================================================================

if [ -n "$1" ]; then
    TARGET_PKGS="$1"
else
    # 默认恢复核心包（如搜狗输入法等）
    TARGET_PKGS="
    com.sohu.inputmethod.sogou.oem
    com.tblenovo.center
    com.tblenovo.lenovowhatsnew
    com.lenovo.leos.appstore
    "
fi

for pkg in $TARGET_PKGS; do
    echo -n "[恢复] 正在恢复 $pkg ... "
    cmd package install-existing "$pkg" 2>/dev/null && echo "成功" || echo "失败或不存在"
done

echo "恢复流程结束。"
