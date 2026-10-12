#!/usr/bin/python
"""Refresh desktop variables and the running Clash port for local launchers."""
import os
from pathlib import Path
import re
import socket
import sys

DESKTOP_KEYS = {'DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY','DISPLAY',
                'XDG_RUNTIME_DIR','XDG_CURRENT_DESKTOP','XDG_SESSION_TYPE',
                'MESA_LOADER_DRIVER_OVERRIDE','GALLIUM_DRIVER','FD_FORCE_KGSL','TURNIP_KMD'}

def environment():
    env = dict(os.environ)
    root = Path('/').stat()
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():
            continue
        try:
            r = (p / 'root').stat()
            if p.stat().st_uid != os.getuid() or (r.st_dev,r.st_ino) != (root.st_dev,root.st_ino):
                continue
            if (p / 'comm').read_text().strip() != 'plasmashell':
                continue
            for item in (p / 'environ').read_bytes().split(b'\0'):
                k,_,v = item.partition(b'=')
                if k.decode(errors='replace') in DESKTOP_KEYS:
                    env[k.decode()] = v.decode()
            env['KDE_SESSION_VERSION'] = '6'
            break
        except OSError:
            pass
    env['PATH'] = '/usr/local/bin:/usr/bin:/bin:' + env.get('PATH','')
    env['TMPDIR'] = '/tmp'
    env.setdefault('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')
    base = Path.home() / '.local/share/io.github.clash-verge-rev.clash-verge-rev'
    for filename in ('clash-verge.yaml','config.yaml'):
        try:
            match = re.search(r'^mixed-port:\s*(\d+)\s*$', (base / filename).read_text(), re.MULTILINE)
            if not match:
                continue
            port = int(match.group(1))
            with socket.create_connection(('127.0.0.1', port), timeout=.3):
                pass
            for key in ('http_proxy','https_proxy','HTTP_PROXY','HTTPS_PROXY'):
                env[key] = f'http://127.0.0.1:{port}'
            for key in ('all_proxy','ALL_PROXY'):
                env[key] = f'socks5h://127.0.0.1:{port}'
            for key in ('no_proxy','NO_PROXY'):
                env[key] = 'localhost,127.0.0.1,::1'
            break
        except (OSError,ValueError):
            pass
    return env

if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit('Usage: linux-app-environment.py PROGRAM [ARGS...]')
    env = environment()
    if Path(sys.argv[1]).name == 'agy.real':
        env['BROWSER'] = '/usr/local/bin/agy-open-browser'
        env['PATH'] = '/usr/local/libexec/agy-launchers:' + env['PATH']
    os.execvpe(sys.argv[1], sys.argv[1:], env)
