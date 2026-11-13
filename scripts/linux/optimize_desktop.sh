#!/bin/bash
# ==============================================================================
# optimize_desktop.sh: KDE Plasma 6 桌面轻量化与低功耗调优脚本
# 适用: Arch Linux ARM @ Lenovo Xiaoxin Pad Pro 2021 (TB-J716F)
# ==============================================================================

set -e

echo "=== 1. 禁用 Baloo 文件语义索引器 (彻底根除 CPU 偷跑与闪存写入) ==="
balooctl6 disable 2>/dev/null || true
kwriteconfig6 --file baloofilerc --group 'Basic Settings' --key 'Indexing-Enabled' false
pkill -9 -f baloo 2>/dev/null || true
echo "Baloo 已彻底禁用。"

echo "=== 2. 关闭 KWin 沉重特效与毛玻璃效果 (大幅降低 GPU/CPU 渲染功耗) ==="
kwriteconfig6 --file kwinrc --group Compositing --key AnimationSpeed 0
kwriteconfig6 --file kwinrc --group Plugins --key blurEnabled false
kwriteconfig6 --file kwinrc --group Plugins --key contrastEnabled false
kwriteconfig6 --file kwinrc --group Plugins --key fadingpopupsEnabled false
kwriteconfig6 --file kwinrc --group Plugins --key scaleEnabled false
kwriteconfig6 --file kwinrc --group Plugins --key slideEnabled false
kwriteconfig6 --file kwinrc --group Plugins --key slidingpopupsEnabled false
kwriteconfig6 --file kwinrc --group Plugins --key squashEnabled false
kwriteconfig6 --file kwinrc --group Plugins --key translucencyEnabled false

echo "=== 3. 优化全局动画速度 ==="
kwriteconfig6 --file kdeglobals --group KDE --key AnimationDurationFactor 0.2 2>/dev/null || true

echo "KDE Plasma 6 性能调优完成！重启桌面或注销后生效。"
