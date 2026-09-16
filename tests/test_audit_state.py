import copy
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills' / 'full-repo-audit' / 'scripts' / 'audit_state.py'
m = runpy.run_path(str(SCRIPT))


class AuditStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = self.base / 'repo'
        self.state = self.base / 'state'
        self.root.mkdir()
        (self.root / 'app.py').write_text('answer = 42\n')
        subprocess.run([sys.executable, str(SCRIPT), 'init', '--root', str(self.root), '--state-dir', str(self.state)], check=True, capture_output=True)
        self.ledger = json.loads((self.state / 'ledger.json').read_text())
        self.findings = {'schema_version': 1, 'findings': []}

    def tearDown(self):
        self.tmp.cleanup()

    def review(self, u):
        for c in u['checks'].values():
            c.update(status='reviewed', evidence=['app.py:1; inspected concrete behavior in test fixture'])

    def completed(self):
        for r in self.ledger['surfaces'].values():
            r.update(status='not_applicable', reason='Fixture has no such registrations', evidence=['Full fixture inventory: app.py only'])
        for name in ('file', 'module', 'cross_reference'):
            self.ledger['surfaces'][name].update(status='complete')
        for surface in ('module', 'cross_reference'):
            self.ledger['units'].append(m['unit'](surface, 'app', ['app.py']))
        for u in self.ledger['units']:
            self.review(u)

    def check(self):
        return m['validate'](self.ledger, self.findings, m['snapshot'](self.root, self.state))

    def test_init_is_not_complete(self):
        self.assertEqual(self.check()['status'], 'in_progress')

    def test_full_coverage(self):
        self.completed()
        result = self.check()
        self.assertEqual(result['status'], 'complete', result['errors'])
        self.assertEqual(result['surfaces']['module']['reviewed_coverage'], 100)
        self.assertEqual(result['quality_approval'], 'not_implied')

    def test_unreviewable_never_inflates_reviewed(self):
        self.completed()
        c = self.ledger['units'][1]['checks']['contracts']
        c.update(status='unreviewable', reason='Unavailable fixture boundary', impact='Contract unknown', unblock='Supply contract')
        result = self.check()
        self.assertEqual(result['status'], 'complete_with_limitations')
        self.assertLess(result['surfaces']['module']['reviewed_coverage'], 100)
        self.assertEqual(result['surfaces']['module']['accounted_coverage'], 100)

    def test_unreviewable_requires_unblock(self):
        self.completed()
        self.ledger['units'][1]['checks']['contracts'].update(status='unreviewable', reason='Unavailable', impact='Unknown')
        self.assertEqual(self.check()['status'], 'in_progress')

    def test_large_denominator_does_not_round_up(self):
        self.completed()
        checks = self.ledger['units'][1]['checks']
        for n in range(20000):
            checks[str(n)] = {'status':'reviewed','evidence':['Fixture boundary inspected']}
        checks['contracts'].update(status='unreviewable',reason='Unavailable',impact='Unknown',unblock='Supply boundary')
        result = self.check()
        self.assertEqual(result['status'],'complete_with_limitations')
        self.assertLess(result['surfaces']['module']['reviewed_coverage'],100)

    def test_unknown_denominator(self):
        self.completed()
        self.ledger['surfaces']['api'].update(status='unreviewable', reason='Registry unavailable', impact='API count unknown', unblock='Supply registry')
        result = self.check()
        self.assertEqual(result['status'], 'complete_with_limitations')
        self.assertEqual(result['surfaces']['api']['reviewed_coverage'], 'unknown')
        self.assertEqual(result['surfaces']['api']['accounted_coverage'], 'unknown')

    def test_stale_or_pending_blocks(self):
        self.completed()
        for status in ('stale', 'pending', 'in_progress'):
            self.ledger['units'][1]['checks']['contracts']['status'] = status
            self.assertEqual(self.check()['status'], 'in_progress')

    def test_missing_required_check(self):
        self.completed()
        del self.ledger['units'][1]['checks']['contracts']
        self.assertEqual(self.check()['status'], 'in_progress')

    def test_missing_surface(self):
        self.completed()
        del self.ledger['surfaces']['permission']
        self.assertEqual(self.check()['status'], 'in_progress')

    def test_no_evidence(self):
        self.completed()
        self.ledger['units'][1]['checks']['contracts']['evidence'] = []
        self.assertEqual(self.check()['status'], 'in_progress')

    def test_source_drift(self):
        self.completed()
        (self.root / 'app.py').write_text('answer = 43\n')
        result = self.check()
        self.assertTrue(result['snapshot_changed'])
        self.assertIn('app.py', result['changed_paths'])
        self.assertEqual(result['status'], 'in_progress')

    def test_new_file_drift(self):
        self.completed()
        (self.root / 'new.py').write_text('new = True\n')
        self.assertIn('new.py', self.check()['changed_paths'])

    def test_file_mode_drift(self):
        self.completed()
        (self.root / 'app.py').chmod(0o755)
        self.assertTrue(self.check()['snapshot_changed'])

    def test_cross_reference_cannot_be_skipped(self):
        self.completed()
        self.ledger['units'].pop()
        self.ledger['surfaces']['cross_reference'].update(status='not_applicable')
        self.assertEqual(self.check()['status'], 'in_progress')

    def test_no_duplicate_ids(self):
        self.completed()
        self.ledger['units'].append(copy.deepcopy(self.ledger['units'][1]))
        self.assertEqual(self.check()['status'], 'in_progress')

    def test_unknown_dependency(self):
        self.completed()
        self.ledger['units'][1]['depends_on'] = ['module:missing']
        self.assertEqual(self.check()['status'], 'in_progress')

    def test_missing_file_classification(self):
        self.completed()
        self.ledger['units'].pop(0)
        self.assertEqual(self.check()['status'], 'in_progress')

    def test_runtime_on_cannot_be_excluded(self):
        self.completed()
        self.ledger['config']['runtime_audit'] = 'on'
        self.assertEqual(self.check()['status'], 'in_progress')

    def test_findings_handoff_and_candidates(self):
        self.completed()
        f = {k: 'Concrete fixture evidence' for k in ('title','trigger','impact','root_cause','counterevidence','recommendation')}
        f.update(id='F-001', status='confirmed', priority='P2', category='maintainability', confidence='high',
                 unit_ids=['module:app'], evidence=['app.py:1'], locations=[{'path':'app.py','start_line':1,'end_line':1}],
                 verification={'method':'static','result':'confirmed','details':'Inspected call chain'},
                 acceptance_checks=['Verify behavior'],fix_scope=['app.py'],depends_on=[])
        self.findings['findings'].append(f)
        self.assertEqual(self.check()['status'], 'complete')
        f['status'] = 'candidate'
        self.assertEqual(self.check()['status'], 'in_progress')
        f['status'] = 'confirmed'
        del f['acceptance_checks']
        self.assertEqual(self.check()['status'], 'in_progress')

    def test_init_never_overwrites(self):
        old = (self.state / 'ledger.json').read_bytes()
        result = subprocess.run([sys.executable,str(SCRIPT),'init','--root',str(self.root),'--state-dir',str(self.state)],capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(old, (self.state / 'ledger.json').read_bytes())

    def test_invalid_state_clears_old_success(self):
        (self.state / 'coverage.json').write_text('{"status":"complete"}')
        (self.state / 'ledger.json').write_text('{"schema_version":1}')
        result = subprocess.run([sys.executable,str(SCRIPT),'check','--state-dir',str(self.state)],capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads((self.state/'coverage.json').read_text())['status'], 'in_progress')

    def test_git_ignored_and_untracked_scope(self):
        subprocess.run(['git','init','--quiet',str(self.root)],check=True)
        (self.root / '.gitignore').write_text('ignored.txt\n')
        (self.root / 'ignored.txt').write_text('ignored source\n')
        snap = m['snapshot'](self.root,self.state)
        self.assertIn('app.py',snap['files'])
        self.assertNotIn('ignored.txt',snap['files'])
        extra = m['snapshot'](self.root,self.state,['ignored.txt'])
        self.assertIn('ignored.txt',extra['files'])
        self.assertNotEqual(snap['fingerprint'],extra['fingerprint'])

    def test_unsafe_extra_path_rejected(self):
        with self.assertRaises(ValueError):
            m['snapshot'](self.root,self.state,['../outside.txt'])

    def test_state_inside_root_excluded(self):
        internal = self.root / '.audit-state'
        internal.mkdir()
        (internal/'ledger.json').write_text('{}')
        snap = m['snapshot'](self.root,internal)
        self.assertEqual(set(snap['files']), {'app.py'})

    def test_state_cannot_hide_entire_root(self):
        with self.assertRaises(ValueError):
            m['snapshot'](self.root,self.root)

    def test_symlink_target_not_read(self):
        outside=self.base/'outside.txt'
        outside.write_text('A')
        (self.root/'link').symlink_to(outside)
        first=m['snapshot'](self.root,self.state)
        outside.write_text('B')
        second=m['snapshot'](self.root,self.state)
        self.assertEqual(first,second)
        self.assertTrue(first['files']['link'].startswith('symlink:'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
