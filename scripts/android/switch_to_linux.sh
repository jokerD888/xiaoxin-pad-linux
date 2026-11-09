#!/system/bin/sh
# TB-J716F: 切换为 Linux 独占模式并重启
echo "linux" > /data/adb/boot_mode
echo "已设置开机引导为 Linux 独占模式，正在重启..."
sync
reboot
