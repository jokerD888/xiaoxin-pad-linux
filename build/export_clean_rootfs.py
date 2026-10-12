#!/usr/bin/env python3
"""Build a package-owned, stateless preview rootfs in a NEW staging directory.

Run inside the source chroot as root. This never edits the source system.
No home, root, mutable /var state, private package keys or log files are copied.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tarfile
import time

EXCLUDED_PACKAGES = {'google-chrome', 'google-chrome-stable', 'antigravity-cli', 'clash-verge', 'clash-verge-rev'}
GENERATED_ETC = {'etc/passwd','etc/group','etc/shadow','etc/gshadow','etc/hosts','etc/resolv.conf',
                 'etc/environment','etc/locale.conf','etc/locale.gen','etc/fstab','etc/machine-id',
                 'etc/subuid','etc/subgid','etc/hostname','etc/pacman.conf','etc/pacman.d/mirrorlist',
                 'etc/sudoers','etc/logrotate.conf','etc/systemd/journald.conf','etc/ssh/sshd_config'}
VETTED_MODIFIED_ETC = {'etc/profile','etc/shells','etc/fuse.conf','etc/pam.d/su','etc/pam.d/su-l'}
EXTRA_BINARIES = ['usr/bin/kwin_wayland.real','usr/lib/locale/locale-archive',
                  'usr/local/bin/anland-camera-bridge','usr/local/libexec/arch-terminal-pty',
                  'usr/local/libexec/arch-terminal-fcitx',
                  'usr/lib/qt6/plugins/ksystemstats/ksystemstats_plugin_tablet_android.so']

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def sections(p):
    out={};key=None
    for line in p.read_text().splitlines():
        if line.startswith('%'):key=line;out[key]=[]
        elif line and key:out[key].append(line)
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--stage',type=Path,required=True)
    ap.add_argument('--overlay',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--private-patterns',type=Path,help='Local-only JSON; never added to output')
    a=ap.parse_args()
    os.environ['PATH']='/usr/local/sbin:/usr/local/bin:/usr/bin:/bin'
    assert os.geteuid()==0,'Must run as chroot root'
    stage=a.stage.absolute()
    assert stage.parent==Path('/var/tmp') and stage.name.startswith('xiaoxin-release-')
    assert not stage.exists() and not stage.is_symlink(),'Refusing existing stage'
    assert not a.output.exists(),'Refusing existing output'
    stage.mkdir(mode=0o700)
    def target(name):
        p=stage/name
        assert p.parent.resolve().is_relative_to(stage),'Symlink parent escapes staging'
        p.parent.mkdir(parents=True,exist_ok=True)
        return p
    def write(name,text,mode=0o644):
        p=target(name)
        if p.is_symlink():p.unlink()
        p.write_text(text.replace('\r\n','\n'),encoding='utf-8');p.chmod(mode);os.chown(p,0,0)
    def copy(name):
        src=Path('/')/name;dest=target(name)
        if not src.exists() and not src.is_symlink():return
        if src.is_symlink():
            if dest.is_symlink() or dest.exists():dest.unlink()
            dest.symlink_to(os.readlink(src))
        elif src.is_file():
            if dest.is_symlink():dest.unlink()
            shutil.copyfile(src,dest);dest.chmod(stat.S_IMODE(src.stat().st_mode))
            os.chown(dest,0,src.stat().st_gid)

    packages=[];owned=set();changed_rejected=[]
    version=Path('/var/lib/pacman/local/ALPM_DB_VERSION')
    if version.exists():write('var/lib/pacman/local/ALPM_DB_VERSION',version.read_text())
    for db in sorted(Path('/var/lib/pacman/local').iterdir()):
        if not (db/'desc').is_file():continue
        desc=sections(db/'desc');name=desc['%NAME%'][0]
        if name in EXCLUDED_PACKAGES:continue
        files=sections(db/'files');backup={}
        for x in files.get('%BACKUP%',[]):
            path,md5=x.split('\t');backup[path]=md5
        packages.append({'name':name,'version':desc['%VERSION%'][0],
                         'licenses':desc.get('%LICENSE%',[]),'upstream':desc.get('%URL%',[])})
        for path in files.get('%FILES%',[]):
            path=path.rstrip('/')
            if not path or not path.startswith(('usr/','etc/')):continue
            if path.startswith(('usr/local/','etc/skel/','etc/ssh/ssh_host_','etc/pacman.d/gnupg/')):continue
            if any(s in path.lower() for s in ['google-chrome','widevine','antigravity']):continue
            src=Path('/')/path
            if src.is_dir() and not src.is_symlink():continue
            if path in GENERATED_ETC:continue
            if path in backup and src.is_file() and not src.is_symlink():
                actual=hashlib.md5(src.read_bytes()).hexdigest()
                if actual!=backup[path] and path not in VETTED_MODIFIED_ETC:
                    changed_rejected.append(path);continue
            owned.add(path)
        # Installed package metadata only: sanitize local builder attribution.
        dest=target('var/lib/pacman/local/'+db.name+'/desc')
        text=(db/'desc').read_text()
        import re
        text=re.sub(r'(%PACKAGER%\n)[^\n]*',r'\1Community snapshot',text)
        dest.write_text(text)
        for n in ['files','mtree','install']:
            if (db/n).is_file():shutil.copyfile(db/n,dest.parent/n)
    for i,name in enumerate(sorted(owned)):
        copy(name)
        if i and i%10000==0:print('Copied package files',i,flush=True)
    for name in EXTRA_BINARIES:copy(name)
    # Replace all local mutable configuration with a reviewed overlay.
    with tarfile.open(a.overlay) as tf:
        for member in tf:
            assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
            content=tf.extractfile(member).read()
            if member.name.startswith('scripts/linux/'):
                name=Path(member.name).name
                mapping={'maintain_privileged_tools.sh':'usr/local/libexec/maintain-privileged-tools',
                         'linux-mode-controller.py':'usr/local/libexec/linux-mode-controller.py',
                         'anland-mic-demand.py':'usr/local/libexec/anland-mic-demand.py',
                         'anland-camera-manager.py':'usr/local/libexec/anland-camera-manager.py',
                         'pipewire_monitor.py':'usr/local/libexec/pipewire_monitor.py',
                         'linux-app-environment.py':'usr/local/libexec/linux-app-environment.py',
                         'configure_tablet_monitor.py':'usr/local/libexec/configure-tablet-monitor.py'}
                out=mapping.get(name,'usr/local/bin/'+name)
                write(out,content.decode(),0o755)
            elif member.name.startswith('templates/home/'):
                write('home/linux/'+member.name.removeprefix('templates/home/'),content.decode())
            elif member.name.startswith('templates/rootfs/'):
                write(member.name.removeprefix('templates/rootfs/'),content.decode(),member.mode)
            elif member.name.startswith('templates/') and member.name.endswith('.desktop'):
                write('usr/share/applications/'+Path(member.name).name,content.decode())
    # Recreate service accounts without original GECOS, hashes or personal users.
    accounts=[]
    for line in Path('/etc/passwd').read_text().splitlines():
        cols=line.split(':');uid=int(cols[2])
        if uid<1000 or uid==65534:
            cols[1]='x';cols[4]='';accounts.append(cols)
    accounts.append(['linux','x','1000','1000','Linux User','/home/linux','/bin/bash'])
    write('etc/passwd',''.join(':'.join(c)+'\n' for c in accounts))
    write('etc/shadow',''.join(c[0]+':!:20000:0:99999:7:::\n' for c in accounts),0o600)
    groups=[]
    for line in Path('/etc/group').read_text().splitlines():
        c=line.split(':');gid=int(c[2])
        if gid<1000 or gid==65534 or c[0] in {'aid_inet','aid_net_raw','aid_net_admin'}:
            c[1]='x';c[3]='linux' if c[0] in {'wheel','video','render','audio','aid_inet','aid_net_raw','aid_net_admin'} else ''
            groups.append(c)
    groups.append(['linux','x','1000',''])
    write('etc/group',''.join(':'.join(c)+'\n' for c in groups))
    write('etc/gshadow',''.join(c[0]+':!::'+c[3]+'\n' for c in groups),0o600)
    defaults={'hosts':'127.0.0.1 localhost\n::1 localhost\n','hostname':'xiaoxin-linux\n',
              'resolv.conf':'nameserver 1.1.1.1\nnameserver 8.8.8.8\n',
              'locale.conf':'LANG=zh_CN.UTF-8\n','locale.gen':'en_US.UTF-8 UTF-8\nzh_CN.UTF-8 UTF-8\n',
              'fstab':'# Android host prepares all mounts.\n','machine-id':'','subuid':'','subgid':'',
              'sudoers':'root ALL=(ALL:ALL) ALL\n%wheel ALL=(ALL:ALL) ALL\n',
              'logrotate.conf':'weekly\nrotate 4\ncreate\ninclude /etc/logrotate.d\n',
              'systemd/journald.conf':'[Journal]\nStorage=volatile\nRuntimeMaxUse=16M\n',
              'ssh/sshd_config':'PermitRootLogin no\nPasswordAuthentication yes\nSubsystem sftp /usr/lib/ssh/sftp-server\n'}
    for name,text in defaults.items():write('etc/'+name,text,0o440 if name=='sudoers' else 0o644)
    # Runtime, aliases and stateless directories.
    for name in ['proc','sys','dev','run','tmp','mnt','sdcard','root','boot','srv','var/cache/pacman/pkg','var/log','var/tmp','var/lib/dbus','var/lib/pacman/sync','etc/pacman.d/gnupg','etc/xiaoxin-linux']:
        p=stage/name;p.mkdir(parents=True,exist_ok=True)
        if name in ['tmp','var/tmp']:p.chmod(0o1777)
        if name=='root':p.chmod(0o700)
    for name,link in [('bin','usr/bin'),('sbin','usr/bin'),('lib','usr/lib'),('lib64','usr/lib'),('var/run','../run'),('var/lock','../run/lock'),('var/lib/dbus/machine-id','/etc/machine-id')]:
        p=stage/name
        if not p.exists() and not p.is_symlink():p.symlink_to(link)
    for p in (stage/'home/linux').rglob('*'):
        os.chown(p,1000,1000)
    os.chown(stage/'home/linux',1000,1000)
    (stage/'home/linux').chmod(0o700)
    stage.chmod(0o755)
    subprocess.run(['ldconfig','-r',str(stage)],check=True)
    def in_stage(*args):
        return subprocess.run(['chroot',str(stage),'/usr/bin/env','PATH=/usr/bin:/bin',*args],check=True,capture_output=True,text=True)
    in_stage('glib-compile-schemas','/usr/share/glib-2.0/schemas')
    in_stage('update-mime-database','/usr/share/mime')
    in_stage('update-ca-trust','extract')
    # Remove any local debug path from custom binaries, retaining executable code.
    for name in EXTRA_BINARIES:
        p=stage/name
        if p.is_file() and p.read_bytes()[:4]==b'\x7fELF':
            subprocess.run(['strip','--strip-debug',str(p)],check=True)
    report={'format':1,'type':'clean-rootfs-preview','user':'linux','uid':1000,
            'packages':packages,'excluded_packages':sorted(EXCLUDED_PACKAGES),
            'rejected_modified_package_configs':changed_rejected,
            'package_file_count':len(owned),'fresh_device_boot_test':False,
            'privacy_strategy':'package-owned files + generated accounts + reviewed config overlay'}
    write('usr/share/xiaoxin-linux/build-manifest.json',json.dumps(report,indent=2))
    manifest=a.output.with_suffix(a.output.suffix+'.manifest.json')
    manifest.write_text(json.dumps(report,indent=2))
    # Check before compression. Patterns are private inputs, never included in image.
    patterns=json.loads(a.private_patterns.read_text()) if a.private_patterns else []
    hits=[]
    for p in stage.rglob('*'):
        if p.is_symlink():continue
        if not p.is_file():continue
        overlap=b''
        with p.open('rb') as f:
            while data:=f.read(4*1024*1024):
                block=overlap+data
                if any(v.encode() in block for v in patterns):hits.append(str(p.relative_to(stage)));break
                overlap=block[-512:]
    assert not hits,{'private_pattern_hits':hits[:30]}
    assert (stage/'etc/shadow').read_text().count(':!:')==len(accounts)
    print('Privacy preflight passed; compressing with two low-priority threads.',flush=True)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    tar=subprocess.Popen(['nice','-n','10','tar','--numeric-owner','--sort=name','-C',str(stage),'-cf','-','.'],stdout=subprocess.PIPE)
    with a.output.open('wb') as out:
        xz=subprocess.Popen(['nice','-n','10','xz','-T2','-3','-c'],stdin=tar.stdout,stdout=out)
        tar.stdout.close();assert xz.wait()==0;assert tar.wait()==0
    a.output.chmod(0o644);manifest.chmod(0o644)
    sha=digest(a.output)
    a.output.with_suffix(a.output.suffix+'.sha256').write_text(sha+'  '+a.output.name+'\n')
    print(json.dumps({'output':str(a.output),'bytes':a.output.stat().st_size,'sha256':sha,'private_pattern_hits':0}),flush=True)

if __name__=='__main__':main()
