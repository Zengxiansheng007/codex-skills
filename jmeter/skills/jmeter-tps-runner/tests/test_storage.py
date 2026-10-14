import tempfile
import unittest
from pathlib import Path
from scripts.storage import Store, folder_name, write_new


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def test_paths_and_names(self):
        store=Store(self.root)
        self.addCleanup(store.finish)
        p=store.paths('提交/新增','/0/0/1',50,1)
        self.assertEqual(p['report'].parts[-3:],('50','report','run-001'))
        self.assertEqual(p['jtl'].name,'result50-run-001.jtl')
        self.assertNotEqual(folder_name('same','a'),folder_name('same','b'))
        self.assertNotIn('/',folder_name('CON/a','a'))
        self.assertTrue(folder_name('CON','a').startswith('request-'))

    def test_exclusive_lock(self):
        store=Store(self.root);self.addCleanup(store.finish)
        with self.assertRaises(FileExistsError):Store(self.root)

    def test_no_overwrite(self):
        p=self.root/'value.json';write_new(p,{'x':1})
        with self.assertRaises(FileExistsError):write_new(p,{'x':2})

    def test_event_chain_and_no_replay(self):
        store=Store(self.root)
        one=store.event('one');two=store.event('two')
        self.assertEqual(two['previous_hash'],one['hash'])
        store.finish()
        with self.assertRaises(FileExistsError):Store(self.root)


if __name__=='__main__':unittest.main()
