#!/usr/bin/python
"""Fixed desktop lifecycle operations, invoked by the existing Android root bridge."""
import json
import os
from pathlib import Path
import signal
import re
import subprocess
import sys
import time

STATE = Path('/run/linux-mode.json')
ROOT = os.stat('/')
GUI_NAMES = {
    'pipewire', 'pipewire-pulse', 'wireplumber', 'fcitx5', 'ksystemstats',
    'xdg-desktop-portal', 'xdg-desktop-portal-kde', 'xdg-document-portal',
    'xdg-permission-store', 'at-spi-bus-launcher', 'at-spi2-registryd',
    'kded6', 'kactivitymanagerd', 'baloo_file', 'baloo_file_extractor',
    'org_kde_powerdevil', 'gmenudbusmenuproxy', 'xembedsniproxy',
    'polkit-kde-authentication-agent-1', 'kioworker', 'dconf-service',
    'gvfsd', 'gvfsd-fuse', 'gvfsd-metadata', 'chrome', 'chrome_crashpad_handler',
    'anland-camera-bridge', 'kaccess', 'kglobalacceld',
}

def processes():
    result = []
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():
            continue
        try:
            r = (p / 'root').stat()
            if (r.st_dev, r.st_ino) != (ROOT.st_dev, ROOT.st_ino):
                continue
            status = (p / 'status').read_text()
            uid = next(s for s in status.splitlines() if s.startswith('Uid:')).split()[1]
            if uid != '1000':
                continue
            args = (p / 'cmdline').read_bytes().decode(errors='replace').rstrip('\0').split('\0')
            stat = (p / 'stat').read_text().rsplit(')', 1)[1].split()
            if stat[0] == 'Z' or not args[0]:
                continue
            try:
                pss = sum(int(s.split()[1]) for s in (p / 'smaps_rollup').read_text().splitlines() if s.startswith('Pss:'))
            except OSError:
                pss = 0
            result.append(dict(pid=int(p.name), start=stat[19], ppid=int(stat[1]), sid=stat[3], name=Path(args[0]).name,
                               args=args, pss_KiB=pss))
        except (OSError, StopIteration, IndexError):
            pass
    return result

def write_state(mode, detail, **extra):
    nodes = processes()
    data = dict(mode=mode, detail=detail, updated=time.time(),
                linux_user_PSS_MiB=round(sum(p['pss_KiB'] for p in nodes) / 1024, 1),
                linux_user_processes=len(nodes), **extra)
    temp = STATE.with_suffix('.new')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    temp.chmod(0o644)
    temp.replace(STATE)
    print(json.dumps(data, ensure_ascii=False), flush=True)

def is_desktop(nodes):
    return any(p['name'] in {'kwin_wayland.real', 'plasmashell'} for p in nodes)

def terminate(p, sig):
    # Revalidate filesystem scope, UID and PID start time before signaling.
    if any(q['pid'] == p['pid'] and q['start'] == p['start'] for q in processes()):
        try:
            os.kill(p['pid'], sig)
        except ProcessLookupError:
            pass

def unprotected_konsole_sessions(nodes, env):
    """Fail closed for old/raw Konsole shells, including background jobs.

    Managed tmux servers have independent process trees. Only the view/client
    belongs to Konsole; it is safe to log that view out.
    """
    if not any(p['name'] == 'konsole' for p in nodes):
        return []
    def query(*args):
        result = subprocess.run(['/bin/su', '-m', 'linux', '-s', '/bin/bash', '-c',
                                 'exec /usr/bin/qdbus6 "$@"', '--', 'qdbus6', *args],
                                env=env, text=True, capture_output=True, timeout=8)
        if result.returncode:
            raise RuntimeError('Konsole D-Bus query failed')
        return result.stdout.strip()
    try:
        services = [s.strip() for s in query().splitlines()
                    if re.fullmatch(r'org\.kde\.konsole(?:-\d+)?', s.strip())]
        if not services:
            return ['无法检查 Konsole 会话'] if any(p['name'] == 'konsole' for p in processes()) else []
        unsafe = []
        inspected = 0
        for service in services:
            objects = [s.strip() for s in query(service).splitlines()
                       if re.fullmatch(r'/Sessions/\d+', s.strip())]
            if not objects:
                unsafe.append(service)
            for obj in objects:
                inspected += 1
                pid = int(query(service, obj, 'org.kde.konsole.Session.processId'))
                if pid <= 0:  # Finished tabs have no command process to protect.
                    continue
                current_nodes = processes()  # A newly opened tab may finish attaching during D-Bus queries.
                tree = {pid}
                while True:
                    expanded = tree | {p['pid'] for p in current_nodes if p['ppid'] in tree}
                    if expanded == tree:
                        break
                    tree = expanded
                children = [p for p in current_nodes if p['pid'] in tree]
                clients = [p for p in children if p['name'] == 'tmux']
                other = [p for p in children if p['name'] != 'tmux' and
                         '/usr/local/bin/arch-terminal' not in p['args'] and
                         not (p['pid'] == pid and p['name'] in {'bash', 'zsh', 'fish', 'sh'})]
                if not clients or other:
                    unsafe.append(f'{service}{obj}')
        return unsafe if inspected else ['无法检查 Konsole 标签页']
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        return (['无法检查 Konsole 会话；为保护任务保留桌面']
                if any(p['name'] == 'konsole' for p in processes()) else [])

def reconnect_saved_terminals():
    # Plasma's Wayland fallback restore launches a fresh app from its desktop ID.
    # After a mode switch, reopen the persistent view instead of adding a shell.
    saved = Path('/home/linux/.local/state/plasmasessionrestorestaterc')
    if saved.exists():
        original = saved.read_text()
        updated = re.sub(r'^appId=org\.kde\.konsole\.desktop$',
                         'appId=arch-terminal-resume.desktop', original, flags=re.MULTILINE)
        if updated != original:
            saved.write_text(updated)

def stop_desktop():
    nodes = processes()
    before = round(sum(p['pss_KiB'] for p in nodes) / 1024, 1)
    plasma = next((p for p in nodes if p['name'] == 'plasmashell'), None)
    session_sid = plasma['sid'] if plasma else None
    write_state('switching', '正在正常退出桌面；如有保存提示，请先处理。')
    if is_desktop(nodes):
        if plasma is None:
            write_state('desktop', '桌面状态异常，未强制关闭。')
            return 1
        env = dict(os.environ, HOME='/home/linux', USER='linux', LOGNAME='linux',
                   XDG_RUNTIME_DIR='/run/user/1000', PATH='/usr/local/bin:/usr/bin:/bin')
        for entry in Path(f"/proc/{plasma['pid']}/environ").read_bytes().split(b'\0'):
            key, _, value = entry.partition(b'=')
            if key in {b'DBUS_SESSION_BUS_ADDRESS', b'WAYLAND_DISPLAY', b'DISPLAY'}:
                env[key.decode()] = value.decode()
        unsafe = unprotected_konsole_sessions(nodes, env)
        if unsafe:
            detail = ('发现尚未接入持久会话的 Konsole 标签页，已取消切换以保护任务。'
                      '请完成旧任务后重新打开终端；新标签页默认受到保护。')
            write_state('desktop', detail, unprotected_terminals=unsafe)
            subprocess.Popen(['/bin/su', '-m', 'linux', '-s', '/bin/bash', '-c',
                              'exec /usr/bin/kdialog --title "终端任务保护" --error "$1"',
                              'terminal-guard', detail], env=env, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            return 1
        try:
            result = subprocess.run(['/bin/su', '-m', 'linux', '-s', '/bin/bash', '-c',
                                     '/usr/bin/qdbus6 org.kde.Shutdown /Shutdown logout'],
                                    env=env, timeout=12, check=False)
        except subprocess.TimeoutExpired:
            result = None
        if result is None or result.returncode:
            write_state('desktop', '无法请求正常注销，保留桌面。')
            return 1
        for _ in range(90):
            if not is_desktop(processes()):
                break
            time.sleep(1)
        else:
            write_state('desktop', '注销取消或仍等待保存；未强制关闭桌面。')
            return 1
    # A cancelled/refused logout must leave the existing terminal input service
    # intact. Stop it only after desktop exit has actually completed.
    subprocess.run(['/bin/su', '-m', 'linux', '-s', '/bin/bash', '-c',
                    'exec /usr/local/bin/arch-terminal-input stop'], check=True)
    # Desktop exit has completed. Keep tmux, shells, SSH and other CLI workloads.
    targets = [p for p in processes() if p['name'] in GUI_NAMES or
               '/usr/local/libexec/anland-camera-manager.py' in p['args'] or
               '/usr/local/libexec/anland-mic-demand.py' in p['args'] or
               (p['name'] == 'dbus-daemon' and (p['sid'] == session_sid or any('at-spi2' in a for a in p['args'])))]
    for p in targets:
        terminate(p, signal.SIGTERM)
    time.sleep(2)
    for p in targets:
        terminate(p, signal.SIGKILL)
    reconnect_saved_terminals()
    input_result = subprocess.run(['/bin/su', '-m', 'linux', '-s', '/bin/bash', '-c',
                                   'exec /usr/local/bin/arch-terminal-input start'], check=False)
    detail = '仅终端模式；Linux 环境和 SD 卡挂载保留。'
    if input_result.returncode:
        detail += ' Linux 输入法启动失败，可查看 /run/user/1000/arch-terminal-input/service.log。'
    write_state('terminal', detail, before_PSS_MiB=before)
    return 0

if __name__ == '__main__':
    if os.getuid() != 0:
        raise SystemExit('This controller is only invoked by the host bridge.')
    if sys.argv[1:] == ['stop']:
        raise SystemExit(stop_desktop())
    if sys.argv[1:] == ['status']:
        write_state('desktop' if is_desktop(processes()) else 'terminal', '当前运行状态')
    else:
        raise SystemExit('Usage: linux-mode-controller.py stop|status')
