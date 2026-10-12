#!/usr/bin/env python3
"""Fetch the pinned public source and apply reviewed changes; never reset a tree."""
import json
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[1]
lock=json.loads((root/'manifests/upstream.json').read_text())
dest=root/'.build/anland'
assert not dest.exists(),'Refusing existing source checkout; use a separate clean build directory'
dest.parent.mkdir(exist_ok=True)
subprocess.run(['git','clone','--no-checkout',lock['url'],str(dest)],check=True)
subprocess.run(['git','-C',str(dest),'checkout','--detach',lock['commit']],check=True)
subprocess.run(['git','-C',str(dest),'apply','--check',str(root/'patches/anland-desktop.patch')],check=True)
subprocess.run(['git','-C',str(dest),'apply',str(root/'patches/anland-desktop.patch')],check=True)
