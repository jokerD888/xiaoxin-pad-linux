#!/usr/bin/env python3
"""Package the pinned upstream Git tree plus local tracked modifications and project sources."""
import argparse, io, subprocess, tarfile
from pathlib import Path
ap=argparse.ArgumentParser(); ap.add_argument('upstream',type=Path); a=ap.parse_args()
root=Path(__file__).resolve().parents[1]
base='367a523ed591a701d98fcc49940b0b574ebd533c'
raw=subprocess.check_output(['git','-C',str(a.upstream),'archive',base])
modified=subprocess.check_output(['git','-C',str(a.upstream),'diff',base,'--name-only']).decode().splitlines()
output=root/'dist/anland-corresponding-source-0.1.0-preview.tar.xz'
with tarfile.open(output,'w:xz',preset=6) as out:
    with tarfile.open(fileobj=io.BytesIO(raw)) as baseline:
        for m in baseline:
            if m.name in modified: continue
            m.name='anland/'+m.name
            out.addfile(m,baseline.extractfile(m) if m.isfile() else None)
    for name in modified:
        p=a.upstream/name
        if p.exists(): out.add(p,arcname='anland/'+name,recursive=False)
    for folder in ['build','src','patches','scripts','templates','docs','manifests','licenses','tests']:
        d=root/folder
        if d.exists():
            for p in sorted(d.rglob('*')):
                if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':
                    out.add(p,arcname='xiaoxin-pad-linux/'+p.relative_to(root).as_posix(),recursive=False)
    for name in ['README.md','LICENSE','.gitattributes','.gitignore']:
        out.add(root/name,arcname='xiaoxin-pad-linux/'+name)
print(output.name)
