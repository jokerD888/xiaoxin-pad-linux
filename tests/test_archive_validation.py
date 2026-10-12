import importlib.util
from pathlib import Path
import io
import tarfile
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('verify',Path(__file__).resolve().parents[1]/'scripts/windows/verify_release.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

class ArchiveTests(unittest.TestCase):
    def archive(self,items):
        d=tempfile.TemporaryDirectory();self.addCleanup(d.cleanup)
        p=Path(d.name)/'host.tar.xz'
        with tarfile.open(p,'w:xz') as f:
            for name,content,link in items:
                m=tarfile.TarInfo(name)
                if link:m.type=tarfile.SYMTYPE;m.linkname=link;f.addfile(m)
                else:m.size=len(content);f.addfile(m,io.BytesIO(content))
        return p
    def test_normal(self):
        p=self.archive([('install.sh',b'echo hello\n',None)])
        self.assertTrue(v.inspect_tar(p)['archive_paths_safe'])
    def test_linux_unit_escape(self):
        self.assertEqual(v.normal(r"usr/lib/systemd/system/system-systemd\x2dcryptsetup.slice", linux_rootfs=True), r"usr/lib/systemd/system/system-systemd\x2dcryptsetup.slice")
        with self.assertRaises(AssertionError): v.normal(r"folder\escape")
    def test_linux_package_epoch(self):
        self.assertEqual(v.normal("var/lib/pacman/local/mesa-1:26.3.0-1/desc", linux_rootfs=True), "var/lib/pacman/local/mesa-1:26.3.0-1/desc")
        with self.assertRaises(AssertionError):v.normal("C:/escape", linux_rootfs=True)
    def test_traversal(self):
        with self.assertRaises(AssertionError):v.inspect_tar(self.archive([('../escape',b'x',None)]))
    def test_absolute(self):
        with self.assertRaises(AssertionError):v.inspect_tar(self.archive([('/etc/shadow',b'x',None)]))
    def test_symlink_parent(self):
        with self.assertRaises(AssertionError):v.inspect_tar(self.archive([('etc',b'','/etc'),('etc/shadow',b'x',None)]))
    def test_secret_crosses_read(self):
        p=self.archive([('config',b'x'*(4*1024*1024-3)+b'PRIVATE-TOKEN'+b'x',None)])
        with self.assertRaises(AssertionError):v.inspect_tar(p,['PRIVATE-TOKEN'])

if __name__=='__main__':unittest.main()
