#!/usr/bin/env python3
"""Read release assets without extracting/executing them. Fail on unsafe archives."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import tarfile
import zipfile

def sha256(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def normal(name, linux_rootfs=False):
    while name.startswith('./'):name=name[2:]
    if name in ('','.'):return ''
    assert not name.startswith('/') and not re.match(r'^[A-Za-z]:', name)
    assert linux_rootfs or ':' not in name
    # Linux systemd unit names use literal \\x2d escapes. This image is extracted on Linux only.
    assert linux_rootfs or '\\' not in name
    assert '..' not in PurePosixPath(name).parts
    return name.rstrip('/')

def inspect_tar(path,patterns=()):
    rootfs='rootfs' in path.name
    count=0;size=0;names=set();links=set();passwords=None;machine=None;forbidden=[]
    overlap_size=max([512]+[len(x.encode()) for x in patterns])
    with tarfile.open(path,'r|*') as tf:
        for m in tf:
            n=normal(m.name, linux_rootfs=rootfs)
            if n:
                assert n not in names,('Duplicate archive path',n)
                for p in PurePosixPath(n).parents:
                    assert str(p) not in links,('Archive writes through a symlink',n)
                names.add(n)
            assert m.isfile() or m.isdir() or m.issym() or m.islnk(),('Special file',n)
            if m.issym() or m.islnk():
                link=m.linkname
                assert (rootfs or '\\' not in link) and (rootfs or ':' not in link) and not re.match(r'^[A-Za-z]:', link)
                target=posixpath.normpath(link.lstrip('/') if link.startswith('/') or m.islnk() else posixpath.join(posixpath.dirname(n),link))
                assert target not in ('..','') and not target.startswith('../'),('Link escapes archive',n)
                links.add(n)
            if rootfs:
                allowed=('usr','etc','var','home','root','proc','sys','dev','run','tmp','mnt','sdcard','bin','sbin','lib','lib64','boot','srv')
                assert not n or PurePosixPath(n).parts[0] in allowed,('Unexpected root directory',n)
                if n.startswith(('root/','proc/','sys/','dev/','run/','tmp/','mnt/','sdcard/')):forbidden.append(n)
                if n.startswith('home/') and n not in ('home/linux',) and not n.startswith('home/linux/.config/') and not n.startswith('home/linux/.local/share/konsole/') and n not in ('home/linux/.config','home/linux/.local','home/linux/.local/share','home/linux/.local/share/konsole','home/linux/.bashrc','home/linux/.bash_profile'):forbidden.append(n)
                if any(x in n for x in ['.ssh/','.gnupg/','.gemini/','.bash_history','ssh_host_','google-chrome','widevine','antigravity','linux-maintenance']):forbidden.append(n)
                if n.startswith('etc/pacman.d/gnupg/') or n.startswith('var/log/'):forbidden.append(n)
            if m.isfile():
                f=tf.extractfile(m);overlap=b'';small=b''
                while b:=f.read(4*1024*1024):
                    data=overlap+b
                    assert not any(x.encode() in data for x in patterns),('Private pattern detected',n)
                    overlap=data[-overlap_size:]
                    if n in ['etc/shadow','etc/machine-id','usr/share/xiaoxin-linux/build-manifest.json']:small+=b
                if n=='etc/shadow':passwords=small.decode()
                if n=='etc/machine-id':machine=small
                size+=m.size
            count+=1
    assert not forbidden,('Forbidden state paths',forbidden[:15])
    if rootfs:
        assert passwords and all(x.split(':')[1]=='!' for x in passwords.splitlines())
        assert machine==b'','Distributed machine-id must be empty'
        assert {'usr/bin/bash','usr/bin/python','etc/passwd','usr/local/bin/start-kde-session','home/linux/.config/linux-terminal/tmux.conf'}<=names
    return {'file':path.name,'entries':count,'uncompressed_file_bytes':size,'private_pattern_hits':0,'archive_paths_safe':True}

def inspect_zip(path,patterns=()):
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            normal(n)
            assert not any(x in n.lower() for x in ['.jks','.keystore','signing-password'])
            data=z.read(n)
            assert not any(x.encode() in data for x in patterns),('Private pattern detected',n)
    return {'file':path.name,'entries':len(z.namelist()),'private_pattern_hits':0}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('folder',type=Path);ap.add_argument('--private-patterns',type=Path);ap.add_argument('--report',type=Path)
    a=ap.parse_args();patterns=json.loads(a.private_patterns.read_text()) if a.private_patterns else []
    manifest=a.folder/'SHA256SUMS';results=[]
    assert manifest.is_file(),'Missing SHA256SUMS'
    for line in manifest.read_text().splitlines():
        expected,name=line.split(None,1);name=name.strip().lstrip('*');normal(name)
        p=a.folder/name;assert p.is_file() and sha256(p)==expected,('Checksum mismatch',name)
        r={'file':name,'bytes':p.stat().st_size,'sha256':expected}
        if name.endswith(('.tar.xz','.tar.gz','.tar.zst')):r.update(inspect_tar(p,patterns))
        elif name.endswith(('.zip','.apk')):r.update(inspect_zip(p,patterns))
        else:
            raw=p.read_bytes();assert not any(x.encode() in raw for x in patterns),('Private pattern detected',name)
        results.append(r)
    report={'verified':True,'assets':results,'includes_private_patterns':False,'fresh_device_boot_test':False}
    if a.report:a.report.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
