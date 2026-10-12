#!/system/bin/sh
set -eu
ROOTFS=/data/local/archlinux
unset LD_PRELOAD LD_LIBRARY_PATH PREFIX TMPDIR
export PATH=/system/bin:/system/xbin:/vendor/bin
export TERM=${TERM:-xterm-256color}
if ! grep -q " $ROOTFS/proc proc " /proc/mounts; then
    echo 'Linux 环境尚未准备好，请先从 Android 启动一次 Linux 桌面。' >&2
    exit 1
fi
printf '\nArch Linux · linux\nCtrl+B，再按 W：选择任务；再按 C：新建任务\n恢复桌面：linux-mode desktop\n\n'
# Android/Magisk and the chroot use different devpts views. Allocate a Linux
# PTY so tmux can resolve ttyname(), render correctly and receive resize events.
exec chroot "$ROOTFS" /bin/su - linux -c '/usr/local/libexec/arch-terminal-pty'
