#!/system/bin/sh
# Prepare a fresh chroot for firstboot/CLI without starting the desktop.
set -eu
ROOTFS=/data/local/archlinux
[ "$(id -u)" = 0 ] && [ -x "$ROOTFS/usr/bin/bash" ] || exit 1
mountpoint -q "$ROOTFS/proc" || mount -t proc proc "$ROOTFS/proc"
mountpoint -q "$ROOTFS/sys" || mount -t sysfs sys "$ROOTFS/sys"
mountpoint -q "$ROOTFS/dev" || mount -o bind /dev "$ROOTFS/dev"
mkdir -p "$ROOTFS/dev/pts" "$ROOTFS/dev/shm" "$ROOTFS/run" "$ROOTFS/tmp"
mountpoint -q "$ROOTFS/dev/pts" || mount -t devpts devpts "$ROOTFS/dev/pts"
mountpoint -q "$ROOTFS/dev/shm" || mount -t tmpfs -o rw,nosuid,nodev,mode=1777 tmpfs "$ROOTFS/dev/shm"
mountpoint -q "$ROOTFS/run" || mount -t tmpfs -o rw,nosuid,nodev,mode=755 tmpfs "$ROOTFS/run"
mountpoint -q "$ROOTFS/tmp" || mount -t tmpfs -o rw,nosuid,nodev,mode=1777 tmpfs "$ROOTFS/tmp"
mkdir -p "$ROOTFS/run/user/1000" "$ROOTFS/run/dbus"
chown 1000:1000 "$ROOTFS/run/user/1000";chmod 700 "$ROOTFS/run/user/1000"
