"""One event subscription with merged node snapshots and owned-child cleanup."""
import codecs
import json
import os
import select
import subprocess


class PipeWireUnavailable(RuntimeError):
    pass


class PipeWireMonitor:
    def __init__(self):
        self.process = subprocess.Popen(['/usr/bin/pw-dump', '-m'],
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.nodes = {}
        self.buffer = ''
        self.decoder = json.JSONDecoder()
        self.utf8 = codecs.getincrementaldecoder('utf-8')('replace')

    def poll(self, timeout=1, wakeup_fd=None, watch_fds=()):
        readers = [self.process.stdout]
        readers.extend(watch_fds)
        if wakeup_fd is not None:
            readers.append(wakeup_fd)
        ready, _, _ = select.select(readers, [], [], timeout)
        self.ready_fds = set(watch_fds).intersection(ready)
        if wakeup_fd is not None and wakeup_fd in ready:
            # The signal pipe is nonblocking; coalesce all pending notifications.
            while True:
                try:
                    if not os.read(wakeup_fd, 4096):
                        break
                except BlockingIOError:
                    break
        if self.process.stdout not in ready:
            if self.process.poll() is not None:
                raise PipeWireUnavailable('PipeWire subscription exited')
            return False
        chunk = os.read(self.process.stdout.fileno(), 65536)
        if not chunk:
            raise PipeWireUnavailable('PipeWire subscription closed')
        self.buffer += self.utf8.decode(chunk)
        changed = False
        while self.buffer.strip():
            self.buffer = self.buffer.lstrip()
            try:
                events, used = self.decoder.raw_decode(self.buffer)
            except json.JSONDecodeError:
                break
            self.buffer = self.buffer[used:]
            for event in events:
                ident = event['id']
                if 'info' in event and event['info'] is None:
                    changed |= self.nodes.pop(ident, None) is not None
                    continue
                if event.get('type') != 'PipeWire:Interface:Node' and ident not in self.nodes:
                    continue
                info = self.nodes.setdefault(ident, {})
                for key, value in (event.get('info') or {}).items():
                    if key in ('props', 'params'):
                        info.setdefault(key, {}).update(value or {})
                    else:
                        info[key] = value
                changed = True
        return changed

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.process.stdout.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
