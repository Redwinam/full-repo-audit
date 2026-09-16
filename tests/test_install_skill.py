from pathlib import Path
import runpy
import tempfile
import unittest
from unittest import mock

MODULE = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'tools' / 'install_skill.py'))
install = MODULE['install']


class InstallSkillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.source = self.base / 'source'
        self.source.mkdir()
        (self.source / 'SKILL.md').write_text('new skill')
        self.home = self.base / 'codex'
        self.target = self.home / 'skills' / 'full-repo-audit'

    def test_copy_does_not_change_source(self):
        result = install(self.source, self.home)
        self.assertEqual(result['mode'], 'copy')
        self.assertFalse(self.target.is_symlink())
        self.assertEqual((self.target / 'SKILL.md').read_text(), 'new skill')
        (self.source / 'SKILL.md').write_text('later source')
        self.assertEqual((self.target / 'SKILL.md').read_text(), 'new skill')

    def test_link_is_live_and_idempotent(self):
        install(self.source, self.home, link=True)
        self.assertTrue(self.target.is_symlink())
        self.assertEqual(install(self.source, self.home, link=True)['status'], 'unchanged')
        (self.source / 'SKILL.md').write_text('later source')
        self.assertEqual((self.target / 'SKILL.md').read_text(), 'later source')

    def test_existing_installation_is_protected(self):
        install(self.source, self.home)
        with self.assertRaises(FileExistsError):
            install(self.source, self.home, link=True)
        self.assertFalse(self.target.is_symlink())

    def test_link_can_be_replaced_with_independent_copy(self):
        install(self.source, self.home, link=True)
        result = install(self.source, self.home, replace=True)
        self.assertFalse(self.target.is_symlink())
        self.assertTrue(Path(result['backup']).is_symlink())
        (self.source / 'SKILL.md').write_text('later source')
        self.assertEqual((self.target / 'SKILL.md').read_text(), 'new skill')

    def test_replacement_preserves_old_files_outside_discovery(self):
        install(self.source, self.home)
        (self.target / 'local.md').write_text('preserve this')
        result = install(self.source, self.home, link=True, replace=True)
        backup = Path(result['backup'])
        self.assertEqual((backup / 'local.md').read_text(), 'preserve this')
        self.assertEqual(backup.parent, self.home / 'skill-backups')
        self.assertTrue(self.target.is_symlink())

    def test_broken_symlink_is_protected_then_backed_up(self):
        self.target.parent.mkdir(parents=True)
        self.target.symlink_to(self.base / 'missing')
        with self.assertRaises(FileExistsError):
            install(self.source, self.home)
        result = install(self.source, self.home, replace=True)
        self.assertTrue(Path(result['backup']).is_symlink())
        self.assertEqual((self.target / 'SKILL.md').read_text(), 'new skill')

    def test_relative_link_backup_preserves_original_destination(self):
        old_source = self.target.parent / 'local-source'
        old_source.mkdir(parents=True)
        (old_source / 'SKILL.md').write_text('old skill')
        self.target.symlink_to('local-source')
        result = install(self.source, self.home, replace=True)
        backup = Path(result['backup'])
        self.assertEqual(backup.resolve(), old_source)
        self.assertEqual((backup / 'SKILL.md').read_text(), 'old skill')
        self.assertEqual((self.target / 'SKILL.md').read_text(), 'new skill')

    def test_source_must_be_skill(self):
        (self.source / 'SKILL.md').unlink()
        with self.assertRaises(ValueError):
            install(self.source, self.home)
        self.assertFalse(self.home.exists())

    def test_failed_swap_restores_previous_installation(self):
        install(self.source, self.home)
        (self.target / 'local.md').write_text('preserve this')
        with mock.patch('os.replace', side_effect=OSError('test failure')):
            with self.assertRaises(OSError):
                install(self.source, self.home, link=True, replace=True)
        self.assertEqual((self.target / 'local.md').read_text(), 'preserve this')
        self.assertFalse(self.target.is_symlink())

    def test_overlap_refused(self):
        self.source.rename(self.base / 'old-source')
        self.target.mkdir(parents=True)
        (self.target / 'SKILL.md').write_text('original')
        with self.assertRaises(ValueError):
            install(self.target, self.home, replace=True)
        self.assertEqual((self.target / 'SKILL.md').read_text(), 'original')


if __name__ == '__main__':
    unittest.main()
