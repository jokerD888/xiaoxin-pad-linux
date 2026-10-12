#!/bin/bash
# pacman hooks: release helper file bind mounts before upgrades, restore afterwards.
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/bin:/bin
tools=/run/privileged-tools
[ -d "$tools" ] || exit 0
case "${1:-}" in
 pre)
  for name in sudo fusermount3; do
   # Detach only the helper's file bind; live FUSE mounts and helper processes remain.
   if grep -Fq " /usr/bin/$name " /proc/mounts; then umount -l "/usr/bin/$name"; fi
  done
  ;;
 post)
  mountpoint -q "$tools" || exit 0
  for name in sudo fusermount3; do
   target=/usr/bin/$name
   [ -f "$target" ] || continue
   if ! grep -Fq " $target " /proc/mounts; then
    install -o root -g root -m 4755 "$target" "$tools/$name.new"
    mv -f "$tools/$name.new" "$tools/$name"
    mount --bind "$tools/$name" "$target"
   fi
  done
  ;;
 *) echo 'Expected pre or post' >&2; exit 2;;
esac
