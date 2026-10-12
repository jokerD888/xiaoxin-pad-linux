#!/usr/bin/python
"""Keep one on-demand I420 bridge per Anland NV21 camera in linux's PipeWire."""
import fcntl
import os
from pathlib import Path
import signal
import subprocess
import time
from pipewire_monitor import PipeWireMonitor, PipeWireUnavailable

runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
directory = runtime / "anland-cameras"
directory.mkdir(mode=0o700, parents=True, exist_ok=True)
lock = (directory / "manager.lock").open("a+")
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    raise SystemExit(0)
lock.seek(0)
lock.truncate()
lock.write(str(os.getpid()))
lock.flush()
running = True
children = {}
failures = {}
retry_at = {}
spawned_at = {}
# SIGCHLD wakes select when a bridge dies, without periodic idle checks.
wakeup_read, wakeup_write = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
signal.set_wakeup_fd(wakeup_write)
signal.signal(signal.SIGCHLD, lambda signum, frame: None)
# Auxiliary camera 2/3 currently return uniform grey frames on this tablet.
enabled_ids = set(os.environ.get("ANLAND_CAMERA_IDS", "0,1").split(","))


def stop(signum, frame):
    global running
    running = False


def retire(name):
    child, dimensions, logfile = children.pop(name)
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
    logfile.close()


signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
try:
    while running:
        try:
            with PipeWireMonitor() as monitor:
                while running:
                    now = time.monotonic()
                    timeout = max(0, min(retry_at.values()) - now) if retry_at else None
                    monitor.poll(timeout=timeout, wakeup_fd=wakeup_read)
                    now = time.monotonic()
                    sources = {}
                    for info in monitor.nodes.values():
                        props = info.get("props", {})
                        name = props.get("node.name", "")
                        if props.get("media.class") != "Video/Source" or not name.startswith("anland-camera-") or name.endswith("-webrtc"):
                            continue
                        if name.removeprefix("anland-camera-") not in enabled_ids:
                            continue
                        for fmt in info.get("params", {}).get("EnumFormat", []):
                            size = fmt.get("size", {})
                            if fmt.get("format") == "NV21" and isinstance(size, dict) and "width" in size and "height" in size:
                                sources[name] = (int(size["width"]), int(size["height"]))
                                break
                    for name in list(children):
                        child, dimensions, logfile = children[name]
                        exited = child.poll() is not None
                        if exited or sources.get(name) != dimensions:
                            retire(name)
                            if exited and sources.get(name) == dimensions:
                                count = 1 if now - spawned_at.get(name, now) > 5 else failures.get(name, 0) + 1
                                failures[name] = count
                                # Recover an isolated failure immediately. Repeated
                                # failures back off instead of creating a fork storm.
                                retry_at[name] = now + (0 if count == 1 else min(30, 5 * (count - 1)))
                    for name in list(retry_at):
                        if name not in sources:
                            retry_at.pop(name)
                            failures.pop(name, None)
                    for name, dimensions in sorted(sources.items()):
                        if name in children:
                            continue
                        if retry_at.get(name, 0) > now:
                            continue
                        retry_at.pop(name, None)
                        # Current sensors are 4:3. Keep aspect ratio for other modes too.
                        width, height = dimensions
                        output_width = min(1280, width)
                        output_height = output_width * height // width
                        if output_width % 2 or output_height % 2 or output_width * height != output_height * width:
                            output_width, output_height = width, height
                        logfile = (directory / f"{name}.log").open("a", buffering=1)
                        args = ["/usr/local/bin/anland-camera-bridge", name,
                                str(width), str(height), str(output_width), str(output_height)]
                        child = subprocess.Popen(args, stdin=subprocess.DEVNULL,
                                                 stdout=logfile, stderr=logfile)
                        children[name] = (child, dimensions, logfile)
                        spawned_at[name] = now
                        print(f"Started {name}: {width}x{height} -> {output_width}x{output_height}, pid={child.pid}", flush=True)
        except (OSError, ValueError, PipeWireUnavailable) as error:
            print(f"Waiting for PipeWire/Anland: {error}", flush=True)
            for name in list(children):
                retire(name)
            retry_at.clear()
        for _ in range(5):
            if not running:
                break
            time.sleep(1)
finally:
    for name in list(children):
        retire(name)
    signal.set_wakeup_fd(-1)
    os.close(wakeup_read)
    os.close(wakeup_write)
