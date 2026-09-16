import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tests.support import SCRIPT, m, complete_fixture


class CodeQualityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.root, self.state = self.base / 'repo', self.base / 'audit'
        self.root.mkdir()
        (self.root / 'app.py').write_text('answer = 42\n', encoding='utf-8')
        subprocess.run([sys.executable, str(SCRIPT), 'init', '--root', str(self.root),
                        '--state-dir', str(self.state)], check=True, capture_output=True)
        self.ledger = json.loads((self.state / 'ledger.json').read_text())
        self.findings = {'schema_version': 1, 'findings': []}
        complete_fixture(self.ledger)

    def check(self):
        return m['validate'](self.ledger, self.findings, m['snapshot'](self.root, self.state))

    def cli_check(self):
        m['atomic_json'](self.state / 'ledger.json', self.ledger)
        m['atomic_json'](self.state / 'findings.json', self.findings)
        return subprocess.run([sys.executable, str(SCRIPT), 'check', '--state-dir', str(self.state)],
                              capture_output=True, text=True)

    def finding(self, kind='maintainability_debt', finding_id='Q-001'):
        record = dict(id=finding_id, kind=kind, status='confirmed', priority='P2', category='maintainability',
                      confidence='high', title=f'Issue {finding_id}', quality_dimensions=['duplication'],
                      unit_ids=['module:app'], locations=[{'path':'app.py','start_line':1,'end_line':1}],
                      evidence=['app.py:1; two consumers maintain the same transition'],
                      trigger='Changing the shared behavior requires coordinated edits',
                      impact='Two implementations and regression surfaces must be maintained',
                      root_cause='One contract has multiple owners', counterevidence='Presentation differences do not change this contract',
                      verification={'method':'static','result':'confirmed','details':'Both consumers compared'},
                      recommendation='Use the existing canonical owner and keep local adapters',
                      tradeoffs='Do not couple presentation', behavior_to_preserve=['Existing external behavior'],
                      acceptance_checks=['One canonical transition serves all consumers', 'Consumer regressions pass'],
                      fix_scope=['app.py'], depends_on=[], history=[], rejection_reason='')
        self.findings['findings'].append(record)
        self.ledger['quality_review']['duplication']['finding_ids'].append(finding_id)
        return record

    def test_source_coverage_cannot_hide_pending_quality(self):
        self.ledger['quality_review'] = m['new_quality_review']()
        result = self.check()
        self.assertEqual(result['surfaces']['module']['reviewed_coverage'], 100)
        self.assertEqual(result['status'], 'in_progress')
        self.assertEqual(result['quality_review']['status'], 'in_progress')

    def test_missing_dimension_blocks_completion(self):
        del self.ledger['quality_review']['structure']
        self.assertEqual(self.check()['status'], 'in_progress')

    def test_reviewed_quality_does_not_require_finding_quota(self):
        result = self.check()
        self.assertEqual(result['status'], 'complete', result['errors'])
        self.assertEqual(result['quality_review']['finding_counts'], dict.fromkeys(m['FINDING_KINDS'], 0))

    def test_unfixed_debt_does_not_block_review_completion(self):
        self.finding()
        self.assertEqual(self.check()['status'], 'complete')

    def test_optional_improvement_is_explicitly_separate(self):
        self.finding('improvement_opportunity')
        self.assertEqual(self.check()['status'], 'complete')
        self.findings['findings'][0]['priority'] = 'P1'
        self.assertEqual(self.check()['status'], 'in_progress')

    def test_debt_requires_concrete_handoff_fields(self):
        finding = self.finding()
        for key in ('tradeoffs', 'behavior_to_preserve'):
            old = finding.pop(key)
            self.assertEqual(self.check()['status'], 'in_progress')
            finding[key] = old

    def test_unclassified_findings_block_completion(self):
        finding = self.finding()
        finding.pop('kind')
        self.assertEqual(self.check()['status'], 'in_progress')

    def test_quality_links_are_bidirectional(self):
        finding = self.finding()
        self.ledger['quality_review']['duplication']['finding_ids'] = []
        self.assertEqual(self.check()['status'], 'in_progress')
        self.ledger['quality_review']['duplication']['finding_ids'] = [finding['id']]
        finding['quality_dimensions'] = ['ownership']
        self.assertEqual(self.check()['status'], 'in_progress')

    def test_maintainability_units_cannot_disappear_from_quality_scope(self):
        unit = m['unit']('module', 'extra', ['app.py'])
        for check in unit['checks'].values():
            check.update(status='reviewed', evidence=['app.py:1; additional consumer inspected'])
        self.ledger['units'].append(unit)
        self.assertEqual(self.check()['status'], 'in_progress')

    def test_unreviewable_quality_requires_explicit_limitation(self):
        review = self.ledger['quality_review']['ownership']
        review.update(status='unreviewable', reason='Owner contract unavailable',
                      impact='Cannot verify ownership', unblock='Supply the contract')
        result = self.check()
        self.assertEqual(result['status'], 'complete_with_limitations')
        self.assertEqual(result['quality_review']['status'], 'complete_with_limitations')
        self.assertTrue(any(x['id'] == 'quality:ownership' for x in result['limitations']))
        del review['unblock']
        self.assertEqual(self.check()['status'], 'in_progress')

    def test_pending_candidate_blocks_quality_closure(self):
        finding = self.finding()
        finding['status'] = 'candidate'
        self.ledger['quality_review']['duplication']['finding_ids'] = []
        self.assertEqual(self.check()['quality_review']['status'], 'in_progress')

    def test_cli_emits_every_item_and_field_without_top_n(self):
        for i in range(24):
            self.finding(m['FINDING_KINDS'][i % 3], f'F-{i:03}')
        result = self.cli_check()
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        catalog = json.loads((self.state / 'code-quality.json').read_text())
        emitted = [f for group in catalog['groups'].values() for f in group]
        self.assertEqual({f['id'] for f in emitted}, {f['id'] for f in self.findings['findings']})
        report = (self.state / 'code-quality.md').read_text()
        for finding in self.findings['findings']:
            self.assertIn(f"### {finding['id']} ·", report)
            self.assertEqual(next(f for f in emitted if f['id'] == finding['id']), finding)
        self.assertIn('**tradeoffs**', report)
        self.assertIn('**behavior_to_preserve**', report)
        self.assertIn(str(self.root / 'app.py') + ':1', report)

    def test_catalog_regenerates_from_canonical_finding(self):
        finding = self.finding()
        self.assertEqual(self.cli_check().returncode, 0)
        finding['recommendation'] = 'A revised, scoped design'
        self.assertEqual(self.cli_check().returncode, 0)
        self.assertIn('A revised, scoped design', (self.state / 'code-quality.md').read_text())
        self.assertNotIn('Use the existing canonical owner', (self.state / 'code-quality.md').read_text())

    def test_unknown_classification_remains_visible_in_draft(self):
        self.finding()['kind'] = 'unclassified'
        self.assertEqual(self.cli_check().returncode, 2)
        catalog = json.loads((self.state / 'code-quality.json').read_text())
        self.assertEqual(catalog['pending'][0]['id'], 'Q-001')

    def test_invalid_state_cannot_leave_old_complete_quality_artifacts(self):
        self.finding()
        self.assertEqual(self.cli_check().returncode, 0)
        self.findings['findings'] = None
        result = self.cli_check()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads((self.state / 'code-quality.json').read_text())['status'], 'in_progress')
        self.assertNotIn('status: `complete`', (self.state / 'code-quality.md').read_text())

    def test_malformed_ledger_invalidates_previous_report_without_secondary_error(self):
        self.finding()
        self.assertEqual(self.cli_check().returncode, 0)
        (self.state / 'ledger.json').write_text('{invalid JSON')
        result = subprocess.run([sys.executable, str(SCRIPT), 'check', '--state-dir', str(self.state)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(json.loads((self.state / 'code-quality.json').read_text())['status'], 'in_progress')

    def test_legacy_gate_cannot_claim_new_quality_certification(self):
        self.ledger.pop('quality_contract_version')
        self.ledger.pop('quality_review')
        result = self.check()
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['quality_review']['status'], 'legacy_not_assessed')
        self.assertTrue(result['warnings'])

    def legacy_state(self):
        self.finding().pop('kind')
        self.ledger.pop('quality_contract_version')
        self.ledger.pop('quality_review')
        m['atomic_json'](self.state / 'ledger.json', self.ledger)
        m['atomic_json'](self.state / 'findings.json', self.findings)
        m['atomic_json'](self.state / 'coverage.json', {'status':'complete'})
        return {p.name:p.read_bytes() for p in self.state.iterdir() if p.is_file()}

    def test_upgrade_preserves_original_state_and_requires_new_review(self):
        original = self.legacy_state()
        result = m['upgrade_quality'](self.state)
        backup = Path(result['backup'])
        for name, content in original.items():
            self.assertEqual((backup / name).read_bytes(), content)
        new_ledger = json.loads((self.state / 'ledger.json').read_text())
        new_findings = json.loads((self.state / 'findings.json').read_text())
        self.assertEqual(new_ledger['snapshot'], self.ledger['snapshot'])
        self.assertEqual(new_ledger['units'], self.ledger['units'])
        self.assertEqual(new_findings['findings'][0]['id'], 'Q-001')
        self.assertEqual(new_findings['findings'][0]['status'], 'confirmed')
        self.assertEqual(new_findings['findings'][0]['kind'], 'unclassified')
        self.assertEqual(json.loads((self.state / 'coverage.json').read_text())['status'], 'in_progress')
        before = (self.state / 'ledger.json').read_bytes()
        self.assertEqual(m['upgrade_quality'](self.state)['status'], 'unchanged')
        self.assertEqual((self.state / 'ledger.json').read_bytes(), before)

    def test_upgrade_rolls_back_partial_write_failure(self):
        original = self.legacy_state()
        atomic = m['atomic_json']
        calls = 0
        def fail_second(path, value):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('simulated write failure')
            return atomic(path, value)
        with mock.patch.dict(m['upgrade_quality'].__globals__, atomic_json=fail_second):
            with self.assertRaises(OSError):
                m['upgrade_quality'](self.state)
        for name, content in original.items():
            self.assertEqual((self.state / name).read_bytes(), content)

    def test_report_localization_preserves_auto_language_contract(self):
        self.ledger['config']['resolved_output_language'] = 'fr'
        self.assertEqual(self.cli_check().returncode, 2)
        labels = {k:f'FR {v}' for k,v in m['QUALITY_LABELS']['en'].items()}
        m['atomic_json'](self.state / 'quality-labels.json', {'language':'fr','labels':labels})
        self.assertEqual(self.cli_check().returncode, 0)
        self.assertTrue((self.state / 'code-quality.md').read_text().startswith('# FR '))

    def test_chinese_report_headings_and_narrative(self):
        self.ledger['config']['resolved_output_language'] = 'zh-CN'
        self.finding()['title'] = '重复维护同一状态机'
        self.assertEqual(self.cli_check().returncode, 0)
        report = (self.state / 'code-quality.md').read_text()
        self.assertIn('# 代码质量逐项报告', report)
        self.assertIn('重复维护同一状态机', report)
        self.assertIn('可选结构优化（不阻断发布）', report)


if __name__ == '__main__':
    unittest.main()
