from pathlib import Path
import runpy

SCRIPT = Path(__file__).resolve().parents[1] / 'skills' / 'full-repo-audit' / 'scripts' / 'audit_state.py'
m = runpy.run_path(str(SCRIPT))


def complete_fixture(ledger):
    for record in ledger['surfaces'].values():
        record.update(status='not_applicable', reason='Fixture has no such registrations',
                      evidence=['Full fixture inventory: app.py only'])
    for name in ('file', 'module', 'cross_reference'):
        ledger['surfaces'][name].update(status='complete')
    for surface in ('module', 'cross_reference'):
        ledger['units'].append(m['unit'](surface, 'app', ['app.py']))
    for unit in ledger['units']:
        for check in unit['checks'].values():
            check.update(status='reviewed', evidence=['app.py:1; inspected concrete behavior in test fixture'])
    for dimension, review in ledger['quality_review'].items():
        review.update(status='reviewed', unit_ids=['module:app'], finding_ids=[],
                      evidence=[f'app.py:1; {dimension}: fixture review found no actionable issue'])
