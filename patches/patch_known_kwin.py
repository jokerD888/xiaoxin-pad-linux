"""Apply only to the verified ARM64 KWin 6.7.4 Anland build; atomic and reversible.

The source equivalent removes completion-driven repaint and eager spare-buffer
repaint. Existing processes keep their mapped inode; this installs future launches.
"""
import hashlib, json, os, pathlib, shutil, struct, sys
P=pathlib.Path
LIB=P('/usr/lib/libkwin.so.6.7.4')
BACKUP=P('/var/backups/kwin-repaint-20261001')
ORIGINAL='e9e008bda3e04be951e5555fa7730c744c87d392decaf0c07437fd6ba0533556'
PATCHES=((0x7367a4,0xd61f0200,0xd65f03c0),(0x73684c,0xd61f0200,0xd65f03c0),(0x73293c,0xd63f0040,0xd503201f))
def sha(data): return hashlib.sha256(data).hexdigest()
mode=sys.argv[1]
assert mode in ('install','restore-file')
current=LIB.read_bytes()
if mode=='install':
    assert sha(current)==ORIGINAL, 'Unknown or already modified build: refusing to patch'
    assert current[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',current,18)[0]==183
    phoff=struct.unpack_from('<Q',current,32)[0]
    phsize,phnum=struct.unpack_from('<HH',current,54)
    for address,old,new in PATCHES:
        # Require executable PT_LOAD with virtual address == file offset.
        assert any(struct.unpack_from('<IIQQQQQQ',current,phoff+i*phsize)[0]==1
                   and struct.unpack_from('<IIQQQQQQ',current,phoff+i*phsize)[1]&1
                   and struct.unpack_from('<IIQQQQQQ',current,phoff+i*phsize)[2]==struct.unpack_from('<IIQQQQQQ',current,phoff+i*phsize)[3]
                   and struct.unpack_from('<IIQQQQQQ',current,phoff+i*phsize)[2]<=address<struct.unpack_from('<IIQQQQQQ',current,phoff+i*phsize)[2]+struct.unpack_from('<IIQQQQQQ',current,phoff+i*phsize)[5]
                   for i in range(phnum)), 'Unsupported ELF layout'
        assert struct.unpack_from('<I',current,address)[0]==old, hex(address)
    BACKUP.mkdir(mode=0o700,parents=True,exist_ok=True)
    original=BACKUP/(LIB.name+'.original')
    if original.exists(): assert sha(original.read_bytes())==ORIGINAL
    else: shutil.copy2(LIB,original)
    data=bytearray(current)
    for address,old,new in PATCHES: struct.pack_into('<I',data,address,new)
    expected=sha(data)
    metadata={'library':str(LIB),'original_sha256':ORIGINAL,'patched_sha256':expected,
              'patches':[{'offset':hex(a),'old':hex(o),'new':hex(n)} for a,o,n in PATCHES],
              'method':'Three source-equivalent instruction changes; 90 Hz retained'}
    (BACKUP/'manifest.json').write_text(json.dumps(metadata,indent=2))
else:
    metadata=json.loads((BACKUP/'manifest.json').read_text())
    assert sha(current)==metadata['patched_sha256'], 'Unknown current build'
    data=(BACKUP/(LIB.name+'.original')).read_bytes()
    assert sha(data)==ORIGINAL
    expected=ORIGINAL
# Atomic inode replacement: never truncate a library mapped by a live process.
temp=LIB.with_name(LIB.name+'.repaint-new')
assert not temp.exists(), 'Unexpected staging file'
shutil.copy2(LIB,temp)
with temp.open('wb') as f:
    f.write(data);f.flush();os.fsync(f.fileno())
assert sha(temp.read_bytes())==expected
os.replace(temp,LIB)
fd=os.open(LIB.parent,os.O_RDONLY);os.fsync(fd);os.close(fd)
print(json.dumps({'mode':mode,'sha256':expected,'backup':str(BACKUP)}))
