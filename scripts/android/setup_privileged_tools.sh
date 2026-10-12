#!/system/bin/sh
# Keep only existing privilege helpers on a small executable suid tmpfs.
# Android /data remains nosuid; no system D-Bus is started.
set -e
ROOTFS=/data/local/archlinux
TOOLS=$ROOTFS/run/privileged-tools
mkdir -p "$TOOLS"
if ! mountpoint -q "$TOOLS"; then
    mount -t tmpfs -o rw,suid,nodev,mode=755,size=2m tmpfs "$TOOLS"
else
    mount -o remount,rw,suid,nodev,mode=755,size=2m "$TOOLS"
fi
for name in sudo fusermount3; do
    target=$ROOTFS/usr/bin/$name
    source=$TOOLS/$name
    if ! grep -Fq " $target " /proc/mounts; then
        cp "$target" "$source.new"
        chown 0:0 "$source.new"
        chmod 4755 "$source.new"
        mv -f "$source.new" "$source"
        mount -o bind "$source" "$target"
    fi
done
rm -f "$TOOLS/id-probe"
# Existing video-group membership grants linux access without world-writable FUSE.
if [ -c /dev/fuse ]; then
    chown 0:983 /dev/fuse
    chmod 660 /dev/fuse
fi
