import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tests.support import SCRIPT, m


def finding(finding_id='F-001', **extra):
    record = dict(op='finding', id=finding_id, kind='defect', status='confirmed', priority='P2',
                  category='correctness', confidence='high', title=f'Issue {finding_id}', quality_dimensions=['state_flow'],
                  unit_ids=['module:app'], locations=[{'path': 'app.py', 'start_line': 1, 'end_line': 1}],
                  evidence=['app.py:1; answer is fixed at import time'], trigger='Any caller needs a new answer',
                  impact='Callers cannot change the value', root_cause='Module-level constant',
                  counterevidence=f'No setter exists for {finding_id}', recommendation='Pass the value in',
                  verification={'method': 'static', 'result': 'confirmed', 'details': 'Read the module'},
                  acceptance_checks=['Callers supply the value'], fix_scope=['app.py'])
    record.update(extra)
    return record


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.root, self.state = self.base / 'repo', self.base / 'audit'
        self.root.mkdir()
        (self.root / 'app.py').write_text('answer = 42\n', encoding='utf-8')

    def run_cli(self, *args, ops=None):
        text = '\n'.join(json.dumps(op, ensure_ascii=False) for op in ops or [])
        return subprocess.run([sys.executable, str(SCRIPT), *args, '--state-dir', str(self.state)],
                              input=text, capture_output=True, text=True)

    def init(self, *extra):
        result = self.run_cli('init', '--root', str(self.root), *extra)
        self.assertEqual(result.returncode, 0, result.stderr)

    def apply(self, ops):
        result = self.run_cli('apply', ops=ops)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def check(self, command='check'):
        result = self.run_cli(command)
        self.assertIn(result.returncode, (0, 2), result.stderr)
        return result.returncode, json.loads(result.stdout)

    def reviewed_audit(self, *init_args, runtime_unit=False):
        self.init(*init_args)
        (self.state / 'batches' / 'B001.md').write_text('## module-app\nRead app.py and its only consumer.\n')
        present = {'file', 'module', 'cross_reference'} | ({'runtime'} if runtime_unit else set())
        ops = [{'op': 'classify', 'pattern': '*', 'evidence': 'First-party source'},
               {'op': 'unit', 'surface': 'module', 'label': 'app', 'sources': ['app.py']},
               {'op': 'unit', 'surface': 'cross_reference', 'label': 'app', 'sources': ['app.py']},
               {'op': 'review', 'units': ['module:app', 'cross_reference:app'],
                'evidence': 'batches/B001.md#module-app; constant has no consumers beyond import'}]
        if runtime_unit:
            ops += [{'op': 'unit', 'surface': 'runtime', 'label': 'cli'},
                    {'op': 'review', 'unit': 'runtime:cli', 'status': 'unreviewable',
                     'evidence': 'No safe environment', 'reason': 'No test account',
                     'impact': 'Runtime behavior unobserved', 'unblock': 'Provide a test account'}]
        ops += [{'op': 'surface', 'surface': s, 'status': 'complete', 'evidence': 'Registry reconciled'}
                for s in present]
        ops += [{'op': 'surface', 'surface': s, 'status': 'not_applicable', 'reason': 'Not present',
                 'evidence': 'Entry point is a single module'} for s in m['CHECKS'] if s not in present]
        ops += [{'op': 'quality', 'dimension': d, 'status': 'reviewed', 'evidence': 'app.py:1; module reviewed',
                 'add_unit_ids': ['module:app']} for d in m['QUALITY_DIMENSIONS']]
        self.apply(ops)

    def test_apply_alone_reaches_completion_and_links_quality(self):
        self.reviewed_audit()
        self.apply([finding()])
        code, result = self.check()
        self.assertEqual((code, result['status']), (0, 'complete'), result['errors'])
        ledger = json.loads((self.state / 'ledger.json').read_text())
        self.assertEqual(ledger['quality_review']['state_flow']['finding_ids'], ['F-001'])

    def test_invalid_operation_aborts_the_whole_batch(self):
        self.init()
        before = (self.state / 'ledger.json').read_bytes()
        result = self.run_cli('apply', ops=[{'op': 'unit', 'surface': 'module', 'label': 'app', 'sources': ['app.py']},
                                            {'op': 'review', 'unit': 'module:missing'}])
        self.assertEqual(result.returncode, 1)
        self.assertEqual((self.state / 'ledger.json').read_bytes(), before)

    def test_audit_then_fix_lifecycle(self):
        self.reviewed_audit('--mode', 'audit-then-fix')
        self.apply([finding(), {'op': 'resolve', 'finding': 'F-001', 'status': 'fixed', 'details': 'early'}])
        _, result = self.check()
        self.assertTrue(any('after close-audit' in e for e in result['errors']))
        findings = json.loads((self.state / 'findings.json').read_text())
        findings['findings'][0].pop('resolution')
        (self.state / 'findings.json').write_text(json.dumps(findings))
        code, closed = self.check('close-audit')
        self.assertEqual((code, closed['phase']), (0, 'fix'))
        (self.root / 'app.py').write_text('def answer(value):\n    return value\n', encoding='utf-8')
        code, result = self.check()
        self.assertEqual((code, result['status'], result['remediation']['status']), (2, 'complete', 'in_progress'))
        self.assertIn('app.py', result['changed_paths'])
        self.apply([{'op': 'resolve', 'finding': 'F-001', 'status': 'fixed', 'details': 'Value is passed in'}])
        self.assertTrue(any('verification' in e for e in self.check()[1]['errors']))
        self.apply([{'op': 'resolve', 'finding': 'F-001', 'status': 'fixed', 'details': 'Value is passed in',
                     'verification': 'Unit test covers two values'}])
        code, result = self.check()
        self.assertEqual((code, result['remediation']['status']), (0, 'complete'), result['errors'])
        self.assertTrue((self.state / 'coverage-audit.json').is_file())

    def test_close_audit_refuses_report_only(self):
        self.reviewed_audit()
        self.assertEqual(self.run_cli('close-audit').returncode, 1)

    def test_runtime_gaps_do_not_set_headline_unless_required(self):
        self.reviewed_audit(runtime_unit=True)
        _, result = self.check()
        self.assertEqual(result['status'], 'complete', result['errors'])
        self.assertEqual(len(result['runtime']['limitations']), 3)
        self.assertEqual(result['limitation_groups'][0]['count'], 3)
        ledger = json.loads((self.state / 'ledger.json').read_text())
        ledger['config']['runtime_audit'] = 'on'
        (self.state / 'ledger.json').write_text(json.dumps(ledger))
        self.assertEqual(self.check()[1]['status'], 'complete_with_limitations')

    def test_batch_references_must_resolve(self):
        self.reviewed_audit()
        for evidence, message in [('batches/B001.md', 'bare batch file'), ('batches/B009.md#x; seen', 'does not exist'),
                                  ('batches/B001.md#missing; seen', 'anchor not found')]:
            with self.subTest(evidence=evidence):
                self.apply([{'op': 'review', 'unit': 'module:app', 'evidence': evidence}])
                self.assertTrue(any(message in e for e in self.check()[1]['errors']))

    def test_confirmed_finding_needs_a_reviewed_unit(self):
        self.reviewed_audit()
        self.apply([{'op': 'unit', 'surface': 'module', 'label': 'other', 'sources': ['app.py']},
                    {'op': 'review', 'unit': 'module:other', 'status': 'not_applicable', 'reason': 'Alias',
                     'evidence': 'Same file as module:app'},
                    finding(unit_ids=['module:other'])])
        self.assertTrue(any('reviewed check' in e for e in self.check()[1]['errors']))

    def test_rejected_candidate_needs_only_a_reason_and_lines_are_optional(self):
        self.reviewed_audit()
        self.apply([{'op': 'finding', 'id': 'R-001', 'kind': 'defect', 'quality_dimensions': [], 'status': 'rejected',
                     'title': 'Suspected race', 'unit_ids': ['module:app'], 'evidence': ['app.py; no threads'],
                     'locations': [{'path': 'app.py'}], 'rejection_reason': 'Module has no concurrency'}])
        code, result = self.check()
        self.assertEqual((code, result['status']), (0, 'complete'), result['errors'])
        self.assertIn('[app.py](<', (self.state / 'code-quality.md').read_text())

    def test_template_counterevidence_is_flagged(self):
        self.reviewed_audit()
        self.apply([finding(f'F-00{n}', counterevidence='Checked everything') for n in range(1, 4)])
        _, result = self.check()
        self.assertTrue(any('identical counterevidence' in w for w in result['warnings']))


if __name__ == '__main__':
    unittest.main()
