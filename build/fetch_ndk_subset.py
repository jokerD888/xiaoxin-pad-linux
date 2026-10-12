"""Fetch only the official NDK files needed for a native arm64 C build via HTTPS ranges."""
import io,json,pathlib,requests,struct,zipfile
URL='https://dl.google.com/android/repository/android-ndk-r27d-windows.zip'
SIZE=781506724
ROOT=pathlib.Path('.anland-native-tools')
class Remote(io.RawIOBase):
    def __init__(self):self.pos=0;self.cache={};self.session=requests.Session()
    def seekable(self):return True
    def tell(self):return self.pos
    def seek(self,off,whence=0):
        self.pos=off if whence==0 else self.pos+off if whence==1 else SIZE+off
        return self.pos
    def fetch(self,start,end):
        r=self.session.get(URL,headers={'Range':f'bytes={start}-{end}','Accept-Encoding':'identity'},stream=True,timeout=60)
        assert r.status_code==206 and r.headers['Content-Range'].startswith(f'bytes {start}-'), r.status_code
        b=r.raw.read(decode_content=False);assert len(b)==end-start+1
        return b
    def read(self,n=-1):
        if n<0:n=SIZE-self.pos
        if n==0:return b''
        start=self.pos;self.pos+=n
        if n>8*1024*1024:return self.fetch(start,start+n-1)
        result=b''
        while len(result)<n:
            pos=start+len(result);block=pos//(8*1024*1024)*(8*1024*1024)
            if block not in self.cache:self.cache[block]=self.fetch(block,min(SIZE-1,block+8*1024*1024-1))
            buf=self.cache[block];off=pos-block;result+=buf[off:off+n-len(result)]
        return result

remote=Remote();z=zipfile.ZipFile(remote)
prefix='android-ndk-r27d/toolchains/llvm/prebuilt/windows-x86_64/'
infos=z.infolist()
bins=[i for i in infos if i.filename.startswith(prefix+'bin/') and ('clang' in i.filename or i.filename.endswith('.dll') or 'lld' in i.filename)]
print('Compiler files:',[(i.filename.rsplit('/',1)[-1],i.file_size) for i in bins],flush=True)
if __import__('sys').argv[-1]=='list':raise SystemExit()
chosen=[]
for i in infos:
    name=i.filename
    if not name.startswith(prefix) or name.endswith('/'):continue
    rel=name[len(prefix):]
    if (rel in ('bin/clang.exe','bin/ld.lld.exe','bin/libwinpthread-1.dll','bin/libc++.dll')
        or rel.startswith('sysroot/usr/include/')
        or rel.startswith('lib/clang/18/include/')
        or rel.startswith('lib/clang/18/lib/linux/aarch64/')
        or rel.startswith('sysroot/usr/lib/aarch64-linux-android/33/')
        or (rel.startswith('sysroot/usr/lib/aarch64-linux-android/') and '/' not in rel[len('sysroot/usr/lib/aarch64-linux-android/'):])):
        chosen.append(i)
print('Selected',len(chosen),'files;',round(sum(i.compress_size for i in chosen)/1048576,1),'MiB compressed',flush=True)
for n,i in enumerate(chosen):
    destination=ROOT/i.filename[len(prefix):]
    if not destination.exists():
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(z.read(i)) # zipfile verifies each member's CRC.
    if n%250==0:print('Extracted',n,'of',len(chosen),flush=True)
print('Native compiler ready',flush=True)
