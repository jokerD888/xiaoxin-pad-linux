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

echo "=== 4. 配置 Windows 风格全局快捷键 (Win+L 保留给 Android 锁屏) ==="
# KDE 与 KWin 快捷键（依赖 Android 端开启 KeyInterceptor 无障碍服务透传 Meta / Alt+Tab）
kwriteconfig6 --file kglobalshortcutsrc --group plasmashell --key "activate application launcher" 'Meta\tAlt+F1,Meta\tAlt+F1,激活应用程序启动器' 2>/dev/null || true
kwriteconfig6 --file kglobalshortcutsrc --group plasmashell --key "show-on-mouse-pos" 'Meta+V,Meta+V,在鼠标位置显示剪贴板项目' 2>/dev/null || true
kwriteconfig6 --file kglobalshortcutsrc --group kwin --key "Show Desktop" 'Meta+D,Meta+D,暂时显示桌面' 2>/dev/null || true
kwriteconfig6 --file kglobalshortcutsrc --group kwin --key "Walk Through Windows" 'Alt+Tab,Alt+Tab\tMeta+Tab,遍历窗口' 2>/dev/null || true
kwriteconfig6 --file kglobalshortcutsrc --group kwin --key "Overview" 'Meta+W\tMeta+Tab,Meta+W,显示/隐藏桌面总览' 2>/dev/null || true
kwriteconfig6 --file kglobalshortcutsrc --group ksmserver --key "Lock Session" 'Screensaver,Screensaver\tMeta+L,锁定会话' 2>/dev/null || true
kwriteconfig6 --file kglobalshortcutsrc --group services --group org.kde.krunner.desktop --key _launch 'none' 2>/dev/null || true
kwriteconfig6 --file kglobalshortcutsrc --group services --group org.kde.plasma-systemmonitor.desktop --key _launch 'Ctrl+Shift+Esc\tMeta+Esc' 2>/dev/null || true
kwriteconfig6 --file kglobalshortcutsrc --group services --group org.kde.dolphin.desktop --key _launch 'Meta+E' 2>/dev/null || true
kwriteconfig6 --file kglobalshortcutsrc --group services --group android-lock-screen.desktop --key _launch 'Meta+L' 2>/dev/null || true

echo "=== 5. 禁用冗余 KDE 常驻进程、kded6 模块与 KRunner (释放 ~200-350MB 常驻内存) ==="
kwriteconfig6 --file kwalletrc --group Wallet --key Enabled false 2>/dev/null || true
kwriteconfig6 --file kwalletrc --group Wallet --key "First Use" false 2>/dev/null || true
kwriteconfig6 --file krunnerrc --group Plugins --key baloosearchEnabled false 2>/dev/null || true

for mod in baloosearchmodule smbwatcher remotenotifier wpad_detector donationmessage freespacenotifier lookandfeelautoswitcher browserintegrationflatpakintegrator; do
    kwriteconfig6 --file kded6rc --group "Module-$mod" --key autoload false 2>/dev/null || true
done

mkdir -p "$HOME/.config/autostart" "$HOME/.local/share/dbus-1/services"
for svc in powerdevil kaccess xembedsniproxy gmenudbusmenuproxy at-spi-dbus-bus baloo_file; do
    cat > "$HOME/.config/autostart/${svc}.desktop" <<'EOF'
[Desktop Entry]
Hidden=true
EOF
done

cat > "$HOME/.local/share/dbus-1/services/org.kde.krunner.service" <<'EOF'
[D-BUS Service]
Name=org.kde.krunner
Exec=/usr/bin/true
EOF

for p in krunner baloorunner org_kde_powerdevil kaccess xembedsniproxy gmenudbusmenuproxy at-spi-bus-launcher at-spi2-registryd ksecretd kactivitymanagerd; do
    pkill -x "$p" 2>/dev/null || pkill -f "/$p" 2>/dev/null || true
done

mkdir -p "$HOME/.local/share/applications"
if [ ! -f "$HOME/.local/share/applications/android-lock-screen.desktop" ] && [ -x /usr/local/bin/lock-android-screen ]; then
    cat > "$HOME/.local/share/applications/android-lock-screen.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Lock Screen (Android)
Name[zh_CN]=锁定屏幕 (Android)
Comment=使用 Win+L 锁定平板 Android 屏幕
NoDisplay=true
Exec=/usr/local/bin/lock-android-screen
X-KDE-Shortcuts=Meta+L
EOF
fi

echo "KDE Plasma 6 性能调优完成！重启桌面或注销后生效。"
