import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from archive import ArchiveError, digest, render_event
from complete_pr import finish, scoped_pull_request
from dsh_adapter import atomic_json, atomic_text, before_task

SHA = 'a' * 40
EVENT = {
    'schema_version': 1, 'event_id': 'synthetic-event', 'kind': 'experience',
    'title': '合成测试记录', 'summary': '使用固定版本读取可以保证输入一致。',
    'source': 'user-confirmed', 'confirmed': True, 'visibility': 'public',
    'approved_for_public': True, 'occurred_at': '2026-10-26T12:00:00Z',
}


class FakeAPI:
    repo = 'lenwallem-bit/personal-ai-archive'
    def __init__(self, conclusion=None, extra=False):
        self.calls = []
        self.conclusion = conclusion
        self.extra = extra
        self.pr = {'state': 'open', 'number': 1, 'draft': False, 'html_url': 'https://github.com/example/pr/1',
                   'merged': False, 'base': {'ref': 'main'},
                   'head': {'sha': SHA, 'ref': 'memory/synthetic-event', 'repo': {'full_name': self.repo}}}
    def request(self, method, suffix, payload=None, **kwargs):
        self.calls.append((method, suffix, payload))
        if suffix == '/pulls/1' and method == 'GET':
            return self.pr
        if suffix.startswith('/pulls/1/files'):
            files = [{'filename': 'memory/entries/synthetic-event.md', 'status': 'added'}]
            return files + ([{'filename': 'identity/profile.md', 'status': 'modified'}] if self.extra else [])
        if '/check-runs?' in suffix:
            return {'check_runs': [] if self.conclusion is None else [
                {'id': 1, 'name': 'archive-validation', 'app': {'slug': 'github-actions'},
                 'status': 'completed', 'conclusion': self.conclusion, 'html_url': 'https://github.com/example/run/1'}]}
        if suffix == '/pulls/1/merge' and method == 'PUT':
            return {'merged': True, 'sha': 'b' * 40}
        raise AssertionError((method, suffix))


class AdapterTests(unittest.TestCase):
    def test_changed_head_never_merges(self):
        api = FakeAPI('success')
        with self.assertRaises(ArchiveError):
            finish(api, 1, 'c' * 40, 0)
        self.assertFalse(any(c[0] == 'PUT' for c in api.calls))

    def test_unrelated_change_never_merges(self):
        api = FakeAPI('success', extra=True)
        with self.assertRaises(ArchiveError):
            finish(api, 1, SHA, 0)
        self.assertFalse(any(c[0] == 'PUT' for c in api.calls))

    def test_only_green_exact_head_merges(self):
        text = render_event(EVENT)[1]
        for conclusion, expected in [(None, 'checks-pending'), ('failure', 'checks-failed'), ('success', 'merged')]:
            api = FakeAPI(conclusion)
            with patch('complete_pr.existing_content', return_value=text):
                result = finish(api, 1, SHA, 0)
            self.assertEqual(result['status'], expected)
            puts = [c for c in api.calls if c[0] == 'PUT']
            self.assertEqual(len(puts), int(conclusion == 'success'))
            if puts:
                self.assertEqual(puts[0][2]['sha'], SHA)

    def test_cache_uses_remote_sha_without_reloading_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            text = '# AI-READONLY: synthetic cache\n'
            atomic_text(state / 'profile-context.md', text)
            atomic_json(state / 'snapshot.json', {'repository': FakeAPI.repo, 'commit': SHA, 'sha256': digest(text)})
            with patch('dsh_adapter.resolve_commit', return_value={'sha': SHA}), patch('dsh_adapter.read_snapshot') as read:
                result = before_task(FakeAPI(), state)
            self.assertEqual(result['status'], 'current')
            read.assert_not_called()

    def test_offline_cache_is_labelled_and_modified_cache_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            text = '# AI-READONLY: synthetic cache\n'
            atomic_text(state / 'profile-context.md', text)
            atomic_json(state / 'snapshot.json', {'repository': FakeAPI.repo, 'commit': SHA, 'sha256': digest(text)})
            with patch('dsh_adapter.resolve_commit', side_effect=ArchiveError('Offline')):
                self.assertEqual(before_task(FakeAPI(), state)['status'], 'offline-cache')
                (state / 'profile-context.md').write_text('changed', encoding='utf-8')
                with self.assertRaises(ArchiveError):
                    before_task(FakeAPI(), state)


if __name__ == '__main__':
    unittest.main()
