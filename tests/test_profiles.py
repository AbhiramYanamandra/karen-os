import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import profiles  # noqa: E402

DATA = json.loads(profiles.PROFILES.read_text(encoding='utf-8'))
CANDIDATES = json.loads((ROOT / 'docs/organisation/skill-candidates.json').read_text(encoding='utf-8'))
EVERY_SKILL = {skill
               for rules in list(DATA['profiles'].values()) + list(DATA['flags'].values()) + list(DATA['review_by_risk'].values())
               for stage in (rules.get('stages') or {'review': rules}).values()
               for skill in stage.get('skills', {})}


def resolve(type_, risk='low', flags=(), registry=EVERY_SKILL, **kw):
    return profiles.resolve(DATA, type_, risk, flags, registry=registry, **kw)


class Profiles(unittest.TestCase):
    """The seven approved profiles, as data."""

    def test_the_seven_profiles(self):
        self.assertEqual(sorted(DATA['profiles']),
                         ['bug', 'chore', 'docs', 'feature', 'security', 'testing', 'ui'])

    def test_every_profile_resolves_with_the_fixed_lifecycle(self):
        for name in DATA['profiles']:
            with self.subTest(profile=name):
                result = resolve(name)
                self.assertEqual(result['always'], DATA['always'])
                self.assertIn('owner merges', result['always'])
                self.assertIn('principle-prove-it-works', result['stages']['verify']['skills'])
                self.assertEqual(result['conflicts'], [])

    def test_every_named_skill_is_owner_approved_in_the_catalogue(self):
        approved = {c['id'] for c in CANDIDATES['candidates'] if c['state'] == 'approved'}
        self.assertEqual(EVERY_SKILL - approved, set())

    def test_ponytail_required_for_code_profiles_only(self):
        for name in DATA['profiles']:
            with self.subTest(profile=name):
                level = resolve(name)['stages']['implement']['skills'].get('ponytail-plugin')
                self.assertEqual(level, 'required' if name in {'feature', 'ui', 'bug', 'chore', 'security'} else None)

    def test_issue_type_aliases(self):
        self.assertEqual(resolve('feat')['profiles'], ['feature'])
        self.assertEqual(resolve('fix')['profiles'], ['bug'])
        self.assertEqual(resolve('test')['profiles'], ['testing'])

    def test_unknown_input_is_refused(self):
        for args in (('nope', 'low', ()), ('ui', 'extreme', ()), ('ui', 'low', ('nope',))):
            with self.subTest(args=args), self.assertRaises(profiles.InvalidInput):
                profiles.resolve(DATA, *args)


class Risk(unittest.TestCase):
    """Risk is declared, then only ever raised."""

    def test_floors_raise_the_declared_risk(self):
        self.assertEqual(resolve('security')['risk'], 'high')
        self.assertEqual(resolve('chore', flags=['ci_change'])['risk'], 'medium')
        self.assertEqual(resolve('chore', flags=['new_dependency'])['risk'], 'high')
        self.assertEqual(resolve('docs', flags=['public_text'])['risk'], 'high')

    def test_declared_risk_is_never_lowered(self):
        self.assertEqual(resolve('docs', risk='high')['risk'], 'high')

    def test_review_depends_on_final_risk(self):
        low = resolve('docs')['stages']['review']
        self.assertEqual(low['skills'], {})
        self.assertIn('self-review, labelled as such in the PR', low['gates'])
        self.assertEqual(resolve('feature', 'medium')['stages']['review']['skills'], {'code-review': 'required'})
        self.assertEqual(resolve('feature', 'high')['stages']['review']['skills'],
                         {'code-review': 'required', 'thermo-nuclear-code-quality-review': 'required'})


class Resolution(unittest.TestCase):
    """The resolution rules in the approved proposal."""

    def test_high_risk_mixed_case_takes_the_union(self):
        result = resolve('ui', flags=['substantial_ui', 'security_sensitive'])
        self.assertEqual(result['profiles'], ['ui', 'security'])
        self.assertEqual(result['risk'], 'high')
        design = result['stages']['design']
        self.assertIn('editable design revision with device variants and states, owner-approved', design['gates'])
        self.assertIn('technical proposal with data flow and threat boundaries, owner-approved revision', design['gates'])
        self.assertEqual(design['skills'], {'ui-ux-pro-max@shared-agents-skills': 'required', 'figma': 'required'})
        self.assertEqual(result['stages']['verify']['skills']['ecc:security-review'], 'required')
        self.assertEqual(result['stages']['review']['skills']['thermo-nuclear-code-quality-review'], 'required')

    def test_duplicates_collapse_at_the_strictest_level(self):
        bug = resolve('bug', flags=['unknown_cause', 'unknown_cause'])
        self.assertEqual(bug['flags'], ['unknown_cause'])
        self.assertEqual(bug['stages']['implement']['skills']['diagnosing-bugs'], 'required')
        self.assertEqual(resolve('bug')['stages']['implement']['skills']['diagnosing-bugs'], 'recommended')
        mixed = resolve('ui', flags=['security_sensitive'])
        self.assertEqual(list(mixed['stages']['implement']['skills']), ['ponytail-plugin'])

    def test_no_design_gate_without_a_trigger(self):
        self.assertEqual(resolve('ui')['stages']['design']['gates'], [])
        self.assertEqual(resolve('feature')['stages']['design']['gates'], [])
        self.assertEqual(resolve('feature', flags=['design_required'])['stages']['design']['gates'],
                         ['technical proposal, owner-approved revision'])

    def test_missing_required_skill_holds_only_its_stage(self):
        result = resolve('ui', flags=['substantial_ui'], registry=EVERY_SKILL - {'figma'})
        self.assertEqual(result['stages']['design']['holds'], ['figma'])
        self.assertEqual(result['stages']['design']['status'], 'hold')
        self.assertEqual([s for s, st in result['stages'].items() if st['status'] == 'hold'], ['design'])

    def test_missing_recommended_skill_is_a_disclosed_fallback(self):
        implement = resolve('feature', registry=EVERY_SKILL - {'tdd'})['stages']['implement']
        self.assertEqual((implement['fallbacks'], implement['holds'], implement['status']), (['tdd'], [], 'ready'))

    def test_empty_registry_holds_every_required_skill(self):
        # Decision 1: until #51 promotes approved entries, the profiles exist but are not live.
        verify = resolve('docs', registry=set())['stages']['verify']
        self.assertEqual(verify['holds'], ['principle-prove-it-works'])


class Exceptions(unittest.TestCase):
    """Only a scoped exception with an owner reference waives a required skill."""

    EXC = {'skill': 'figma', 'stage': 'design', 'scope': 'this issue only', 'reference': 'https://example.invalid/owner-comment'}

    def test_exception_with_reference_waives(self):
        design = resolve('ui', flags=['substantial_ui'], registry=set(), exceptions=[self.EXC])['stages']['design']
        self.assertEqual(design['waived'], {'figma': self.EXC['reference']})
        self.assertEqual(design['holds'], ['ui-ux-pro-max@shared-agents-skills'])

    def test_exception_without_reference_is_ignored(self):
        bare = dict(self.EXC, reference='')
        result = resolve('ui', flags=['substantial_ui'], registry=set(), exceptions=[bare])
        self.assertIn('figma', result['stages']['design']['holds'])
        self.assertEqual(len(result['ignored_exceptions']), 1)

    def test_exception_for_a_skill_that_is_not_required_is_ignored(self):
        result = resolve('feature', exceptions=[dict(self.EXC, skill='tdd', stage='implement')])
        self.assertEqual(result['ignored_exceptions'][0]['why'], 'no such required skill at that stage')


class Projects(unittest.TestCase):
    """Projects can tighten company policy, never loosen it."""

    def test_project_can_add_and_raise(self):
        project = {'profiles': {'ui': {'risk_floor': 'medium',
                                       'stages': {'verify': {'gates': ['typography matches project tokens'],
                                                             'skills': {'tdd': 'required'}}}}}}
        result = resolve('ui', project=project)
        self.assertEqual((result['risk'], result['conflicts']), ('medium', []))
        self.assertIn('typography matches project tokens', result['stages']['verify']['gates'])
        self.assertEqual(result['stages']['verify']['skills']['tdd'], 'required')

    def test_project_rules_for_untriggered_profiles_do_not_apply(self):
        project = {'profiles': {'security': {'stages': {'verify': {'skills': {'tdd': 'required'}}}}}}
        self.assertNotIn('tdd', resolve('docs', project=project)['stages']['verify']['skills'])

    def test_project_loosening_is_a_conflict(self):
        cases = {
            'lowered skill': {'profiles': {'ui': {'stages': {'implement': {'skills': {'ponytail-plugin': 'optional'}}}}}},
            'lowered floor': {'profiles': {'security': {'risk_floor': 'low'}}},
            'removal key': {'profiles': {'ui': {'remove': ['principle-prove-it-works']}}},
        }
        for name, project in cases.items():
            with self.subTest(case=name):
                result = resolve('ui', flags=['security_sensitive'], project=project)
                self.assertEqual(len(result['conflicts']), 1)
        kept = resolve('ui', project=cases['lowered skill'])['stages']['implement']['skills']['ponytail-plugin']
        self.assertEqual(kept, 'required')


class CommandLine(unittest.TestCase):

    def run_main(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = profiles.main(list(argv))
        return code, out.getvalue()

    def test_resolve_prints_json_and_exits_zero_on_holds(self):
        code, out = self.run_main('resolve', '--type', 'feat', '--risk', 'low')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['profiles'], ['feature'])

    def test_conflict_and_unknown_input_exit_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'project.json'
            path.write_text(json.dumps({'profiles': {'docs': {'risk_floor': 'low', 'drop': True}}}), encoding='utf-8')
            self.assertEqual(self.run_main('resolve', '--type', 'docs', '--risk', 'low', '--project', str(path))[0], 1)
        self.assertEqual(self.run_main('resolve', '--type', 'nope', '--risk', 'low')[0], 1)


if __name__ == '__main__':
    unittest.main()
