#!/usr/bin/env python3
"""Package only the reviewed Android scripts and rebuilt daemon, no device data."""
from pathlib import Path
import io
import tarfile
import zipfile
root=Path(__file__).resolve().parents[1]
dist=root/'dist';dist.mkdir(exist_ok=True)
with tarfile.open(dist/'xiaoxin-host-0.1.0-preview.tar.xz','w:xz',preset=3) as tf:
    files=list((root/'scripts/android').glob('*.sh'))+[root/'templates/anland-defaults.xml']
    for p in files:
        info=tarfile.TarInfo(p.name);data=p.read_bytes();info.size=len(data);info.mode=0o755 if p.suffix=='.sh' else 0o644
        tf.addfile(info,io.BytesIO(data))
    for name in ['LICENSE','README.md']:
        p=root/name;data=p.read_bytes();info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;tf.addfile(info,io.BytesIO(data))
with zipfile.ZipFile(dist/'anland-daemon-0.1.0-preview.zip','w',zipfile.ZIP_DEFLATED) as z:
    upstream=root/'.build/anland/magisk_module'
    for name in ['module.prop','customize.sh','service.sh','sepolicy.rule']:
        p=upstream/name;info=zipfile.ZipInfo(name);info.create_system=3;info.external_attr=(0o100755 if name.endswith('.sh') else 0o100644)<<16;z.writestr(info,p.read_bytes())
    info=zipfile.ZipInfo('display_daemon');info.create_system=3;info.external_attr=0o100755<<16;z.writestr(info,(root/'.build/display_daemon').read_bytes())
    z.writestr('LICENSE',(root/'LICENSE').read_bytes())
    z.writestr('SOURCE.txt',b'Anland source and build instructions accompany this preview. See manifests/upstream.json.\n')
print('Packaged reviewed host scripts and rebuilt daemon module.')
