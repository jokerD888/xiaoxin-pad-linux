#!/system/bin/sh
# Fresh install only. Existing systems and Android applications are not removed.
set -eu
export PATH=/system/bin:/system/xbin:/vendor/bin
BASE=/data/adb/kde-desktop
ROOTFS=/data/local/archlinux
HERE=$(CDPATH= cd -- "${0%/*}" && pwd)
[ "$(id -u)" = 0 ] || { echo 'Run through Android root.' >&2; exit 1; }
case "$(getprop ro.product.model) $(getprop ro.product.device)" in *J716F*|*j716f*) ;; *) echo 'Only TB-J716F is supported by this preview.' >&2; exit 1;; esac
[ "$(getprop ro.build.version.sdk)" = 33 ] || { echo 'This preview targets Android 13 only.' >&2; exit 1; }
[ "${1:-}" = --allow-permissive ] || { echo 'Usage: install.sh --allow-permissive ROOTFS.tar.xz SHA256 CLIENT.apk' >&2; exit 1; }
ARCHIVE=${2:?};EXPECTED=${3:?};APK=${4:?}
[ ! -e "$ROOTFS" ] && [ ! -L "$ROOTFS" ] || { echo 'Existing Linux found; refusing to overwrite.' >&2; exit 1; }
[ ! -e "$BASE" ] && [ ! -L "$BASE" ] || { echo 'Existing host integration found; refusing to overwrite.' >&2; exit 1; }
[ -d /data/adb/modules/anland-daemon ] || { echo 'Install the included Anland daemon module in Magisk and reboot first.' >&2; exit 1; }
BB=/data/adb/magisk/busybox
[ -x "$BB" ] || { echo 'Magisk BusyBox is required.' >&2; exit 1; }
[ "${#EXPECTED}" = 64 ] || exit 1
case "$EXPECTED" in *[!0-9a-fA-F]*) exit 1;; esac
[ "$(sha256sum "$ARCHIVE" | cut -d ' ' -f 1)" = "$EXPECTED" ] || { echo 'Rootfs SHA256 mismatch.' >&2; exit 1; }
[ -f "$APK" ] && [ -f "$HERE/anland-defaults.xml" ] || exit 1
# Every release archive must first pass the host-side archive verifier.
umask 077
STAGE=/data/local/archlinux.install-$$
[ ! -e "$STAGE" ] && [ ! -L "$STAGE" ] || exit 1
mkdir "$STAGE"
"$BB" tar -xJpf "$ARCHIVE" -C "$STAGE"
[ -x "$STAGE/usr/bin/bash" ] && [ -x "$STAGE/usr/bin/python" ] || { echo "Incomplete image retained at $STAGE" >&2; exit 1; }
chroot "$STAGE" /usr/bin/env PATH=/usr/bin:/bin /usr/bin/python -c 'import json; d=json.load(open("/usr/share/xiaoxin-linux/build-manifest.json")); assert d["user"]=="linux" and d["uid"]==1000'
# Install the new signing identity without silently deleting an existing app.
pm install -r "$APK"
mv "$STAGE" "$ROOTFS"
mkdir -p "$BASE/bin" "$BASE/logs" /data/adb/service.d
for name in linux-host-bridge.sh linux-terminal.sh launch_kde_desktop.sh setup_privileged_tools.sh detect_boot_key.sh prepare-rootfs.sh; do
    cp "$HERE/$name" "$BASE/bin/$name"
    chmod 755 "$BASE/bin/$name"
done
cp "$HERE/start_kde_boot.sh" /data/adb/service.d/90-xiaoxin-linux.sh
chmod 755 /data/adb/service.d/90-xiaoxin-linux.sh
cp "$APK" "$BASE/anland-linux.apk"
chmod 644 "$BASE/anland-linux.apk"
mkdir -p "$ROOTFS/etc/xiaoxin-linux"
touch "$ROOTFS/etc/xiaoxin-linux/allow-permissive"
printf '%s\n' android_always > /data/adb/boot_mode
pm grant com.anland.consumer.desktop android.permission.RECORD_AUDIO
pm grant com.anland.consumer.desktop android.permission.CAMERA
pm grant com.anland.consumer.desktop android.permission.POST_NOTIFICATIONS || true
APP=/data/user/0/com.anland.consumer.desktop
am force-stop com.anland.consumer.desktop
mkdir -p "$APP/shared_prefs"
cp "$HERE/anland-defaults.xml" "$APP/shared_prefs/anland_settings.xml"
OWNER=$(stat -c '%u:%g' "$APP")
chown "$OWNER" "$APP/shared_prefs" "$APP/shared_prefs/anland_settings.xml"
chmod 700 "$APP/shared_prefs";chmod 600 "$APP/shared_prefs/anland_settings.xml"
restorecon -R "$APP/shared_prefs" || true
chmod 755 "$ROOTFS"
sh "$BASE/bin/prepare-rootfs.sh"
chroot "$ROOTFS" /usr/bin/env PATH=/usr/bin:/bin /usr/local/bin/firstboot-linux
echo 'Installed. Desktop autostart is OFF. Start /data/adb/kde-desktop/bin/launch_kde_desktop.sh.'
