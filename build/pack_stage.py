#!/usr/bin/env python3
"""Pack an already prepared clean stage; refuse generated private identity files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
ap=argparse.ArgumentParser();ap.add_argument('stage',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args()
stage=a.stage.resolve();assert stage.parent==Path('/var/tmp') and stage.name.startswith('xiaoxin-release-')
assert not a.output.exists(),'Output already exists'
assert (stage/'usr/share/xiaoxin-linux/build-manifest.json').is_file()
assert not (stage/'etc/machine-id').read_bytes()
assert not any((stage/'etc/ssh').glob('ssh_host_*'))
assert not any((stage/'etc/pacman.d/gnupg').iterdir())
assert all(x.split(':')[1]=='!' for x in (stage/'etc/shadow').read_text().splitlines())
os.environ['PATH']='/usr/local/sbin:/usr/local/bin:/usr/bin:/bin'
tar=subprocess.Popen(['nice','-n','10','tar','--numeric-owner','--sort=name','-C',str(stage),'-cf','-','.'],stdout=subprocess.PIPE)
with a.output.open('wb') as out:
    xz=subprocess.Popen(['nice','-n','10','xz','-T2','-0','-c'],stdin=tar.stdout,stdout=out);tar.stdout.close()
    assert xz.wait()==0 and tar.wait()==0
a.output.chmod(0o644)
h=hashlib.sha256()
with a.output.open('rb') as f:
    for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
print(json.dumps({'bytes':a.output.stat().st_size,'sha256':h.hexdigest()}),flush=True)
