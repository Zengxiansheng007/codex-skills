import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import stat
from scripts.package_integrity import digest, verify_package, reject_link


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='完整性 with space ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'scripts').mkdir()
        (self.root/'SKILL.md').write_text('name: fixture',encoding='utf-8')
        (self.root/'scripts/main.py').write_text('# inert test fixture',encoding='utf-8')
        self.files = {n:digest(self.root/n) for n in ('SKILL.md','scripts/main.py')}
        self.save(self.files)

    def save(self, files):
        (self.root/'MANIFEST.json').write_text(json.dumps({'files':files}),encoding='utf-8')

    def test_original_and_host_metadata_both_pass(self):
        self.assertFalse(verify_package(self.root)['host_metadata_present'])
        (self.root/'_user_meta.json').write_text('{"source":"userImport"}',encoding='utf-8')
        self.assertTrue(verify_package(self.root)['host_metadata_present'])
        self.assertEqual(verify_package(self.root)['files'],2)

    def test_modified_code_with_metadata_still_rejected(self):
        (self.root/'_user_meta.json').write_text('{}',encoding='utf-8')
        (self.root/'scripts/main.py').write_text('# changed',encoding='utf-8')
        with self.assertRaises(ValueError): verify_package(self.root)

    def test_missing_file_rejected(self):
        (self.root/'scripts/main.py').unlink()
        with self.assertRaises(ValueError): verify_package(self.root)

    def test_extra_code_rejected(self):
        (self.root/'scripts/extra.py').write_text('# unexpected',encoding='utf-8')
        with self.assertRaises(ValueError): verify_package(self.root)

    def test_nested_metadata_not_exempt(self):
        (self.root/'scripts/_user_meta.json').write_text('{}',encoding='utf-8')
        with self.assertRaises(ValueError): verify_package(self.root)

    def test_metadata_directory_not_exempt(self):
        (self.root/'_user_meta.json').mkdir()
        with self.assertRaises(ValueError): verify_package(self.root)

    def test_unsafe_manifest_paths(self):
        for name in ('../outside','/absolute','scripts\\main.py','C:/outside','scripts/./main.py','a/../b','scripts/main.py.','scripts/main.py ', '_user_meta.json', 'MANIFEST.json'):
            with self.subTest(name=name):
                self.save({**self.files,name:'0'*64})
                with self.assertRaises(ValueError): verify_package(self.root)

    def test_case_colliding_names_rejected(self):
        self.save({**self.files,'skill.md':self.files['SKILL.md']})
        with self.assertRaises(ValueError): verify_package(self.root)

    def test_metadata_symlink_rejected(self):
        try:
            (self.root/'_user_meta.json').symlink_to(self.root/'SKILL.md')
        except OSError:
            self.skipTest('OS does not permit unprivileged symlinks')
        with self.assertRaises(ValueError): verify_package(self.root)

    def test_code_directory_symlink_rejected(self):
        try:
            (self.root/'alias').symlink_to(self.root/'scripts', target_is_directory=True)
        except OSError:
            self.skipTest('OS does not permit unprivileged symlinks')
        with self.assertRaises(ValueError): verify_package(self.root)

    def test_windows_reparse_attribute_rejected_without_privilege(self):
        with patch.object(Path,'lstat',return_value=SimpleNamespace(st_mode=stat.S_IFREG,st_file_attributes=0x400)):
            with self.assertRaises(ValueError): reject_link(self.root/'_user_meta.json')


if __name__ == '__main__': unittest.main()
