#!/usr/bin/python
"""Monitor PipeWire source state; renew a four-second, fail-closed mic lease."""
import fcntl
import json
import os
from pathlib import Path
import signal
import time
from pipewire_monitor import PipeWireMonitor, PipeWireUnavailable

os.environ['XDG_RUNTIME_DIR'] = '/run/user/1000'
lock = open('/run/user/1000/anland-mic-demand.lock', 'a+')
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    raise SystemExit(0)
lock.seek(0)
lock.truncate()
lock.write(str(os.getpid()))
lock.flush()
fifo = '/run/host_cmd.fifo'

def command(active):
    try:
        fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
        try:
            os.write(fd, b'mic-active\n' if active else b'mic-idle\n')
        finally:
            os.close(fd)
    except OSError:
        pass

def stop(*args):
    raise SystemExit(0)

signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
command(False)
root = Path('/').stat()
desktop = None
desktop_fd = None

def desktop_alive():
    global desktop
    def identity(p):
        try:
            r = (p / 'root').stat()
            if p.stat().st_uid != os.getuid() or (r.st_dev, r.st_ino) != (root.st_dev, root.st_ino):
                return None
            if (p / 'comm').read_text().strip() not in ('kwin_wayland', 'kwin_wayland.re'):
                return None
            fields = (p / 'stat').read_text().rsplit(')', 1)[1].split()
            return None if fields[0] == 'Z' else fields[19]
        except (OSError, IndexError):
            return None
    if desktop is not None and identity(desktop[0]) == desktop[1]:
        return True
    desktop = None
    for p in Path('/proc').iterdir():
        if p.name.isdecimal():
            start = identity(p)
            if start is not None:
                desktop = (p, start)
                return True
    return False

started = time.monotonic()
seen_desktop = False
next_desktop_check = 0
last_status = None
try:
    while True:
        try:
            with PipeWireMonitor() as monitor:
                heartbeat = 0
                last_active = None
                while True:
                    # Idle waits for PipeWire or desktop exit. Only an active
                    # lease needs a heartbeat. Old kernels retain a 5s fallback.
                    now = time.monotonic()
                    timeout = 1 if last_active else None
                    if desktop_fd is None:
                        fallback = max(.01, next_desktop_check - now)
                        timeout = min(timeout, fallback) if timeout is not None else fallback
                    changed = monitor.poll(timeout=timeout,
                                           watch_fds=[desktop_fd] if desktop_fd is not None else [])
                    now = time.monotonic()
                    if desktop_fd is not None and desktop_fd in monitor.ready_fds:
                        os.close(desktop_fd)
                        desktop_fd = None
                        desktop = None
                        next_desktop_check = 0
                    if desktop_fd is None and now >= next_desktop_check:
                        alive = desktop_alive()
                        seen_desktop |= alive
                        if not alive and (seen_desktop or now - started > 60):
                            raise SystemExit(0)
                        next_desktop_check = now + 5
                        if alive:
                            try:
                                desktop_fd = os.pidfd_open(int(desktop[0].name))
                            except (OSError, AttributeError):
                                desktop_fd = None
                    if changed or last_active is None:
                        sources = [{'id': ident, 'state': info.get('state')}
                                   for ident, info in monitor.nodes.items()
                                   if info.get('props', {}).get('node.name') == 'anland-mic']
                        active = any(s['state'] == 'running' for s in sources)
                        status = {'active': active, 'sources': sources}
                        if status != last_status:
                            Path('/run/user/1000/anland-mic-demand.json').write_text(json.dumps(status))
                            last_status = status
                    if active != last_active or (active and now - heartbeat >= 1):
                        command(active)
                        last_active = active
                        heartbeat = now
        except (OSError, PipeWireUnavailable) as error:
            command(False)
            print(f'Waiting for PipeWire: {error}', flush=True)
            time.sleep(1)
finally:
    command(False)
    if desktop_fd is not None:
        os.close(desktop_fd)
