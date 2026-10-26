"""Offline risk tests; no real GitHub request, credential read, or publication."""
from __future__ import annotations

import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "archive.py"
spec = importlib.util.spec_from_file_location("archive", MODULE)
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)

SHA = "a" * 40
TREE = "b" * 40
OLD = "c" * 40
OLD_TREE = "d" * 40
BRANCH = "e" * 40


def event(**updates):
    value = {"schema_version": 1, "event_id": "test-public-event", "kind": "experience",
             "title": "公开测试经验", "summary": "记录可重复验证的结果。", "source": "user-confirmed",
             "confirmed": True, "visibility": "public", "approved_for_public": True,
             "occurred_at": "2026-10-26T20:00:00+08:00"}
    value.update(updates)
    return value


def content(text):
    return {"type": "file", "encoding": "base64", "size": len(text.encode()),
            "content": base64.b64encode(text.encode()).decode()}


class FakeAPI:
    repo = "lenwallem-bit/personal-ai-archive"

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def request(self, method, suffix, payload=None, missing_ok=False):
        self.calls.append((method, suffix, payload))
        key = (method, suffix)
        if key not in self.routes:
            raise AssertionError("Unexpected API operation: " + str(key))
        result = self.routes[key]
        if isinstance(result, Exception):
            raise result
        return result


def commit(sha=SHA, tree=TREE):
    return {"sha": sha, "commit": {"tree": {"sha": tree}}}


class EventTests(unittest.TestCase):
    def test_private_unconfirmed_and_extra_data_are_rejected(self):
        for value in (event(visibility="private"), event(confirmed=False),
                      event(approved_for_public=False), event(confirmed=1), event(raw_chat="private")):
            with self.subTest(value=value), self.assertRaises(archive.ArchiveError):
                archive.render_event(value)

    def test_path_traversal_and_invalid_event_id_rejected(self):
        for name in ("../secret", "x/y", "C:\\secret", "a..", "$(command)"):
            with self.subTest(name=name), self.assertRaises(archive.ArchiveError):
                archive.render_event(event(event_id=name))
        for name in ("../x", "/tmp/x", "x/../y", "x//y", "x\\y", "C:/x"):
            with self.subTest(name=name), self.assertRaises(archive.ArchiveError):
                archive.validate_relpath(name)

    def test_secret_and_local_evidence_rejected(self):
        for value in (event(summary="credential ghp_" + "A" * 30),
                      event(summary=r"C:\Users\example\notes"),
                      event(source="https://127.0.0.1/data"),
                      event(source="https://user:password@example.org/data")):
            with self.subTest(value=value), self.assertRaises(archive.ArchiveError):
                archive.render_event(value)

    def test_privacy_gate_scans_raw_fields_and_rendered_output(self):
        for summary in ('password="' + 'z' * 30 + '"', r'\\fileserver\private-share\notes.md',
                        'file:///private/notes.md', 'smb://fileserver/share/notes.md',
                        'https://example.org/?access_token=synthetic-secret-value',
                        'https://example.org/?tok%65n=synthetic-value'):
            with self.subTest(summary=summary), self.assertRaises(archive.ArchiveError):
                archive.render_event(event(summary=summary))
        archive.scan_public('Never place passwords or UNC paths in public archives; use {{API_TOKEN}}.', 'rule')
        archive.scan_public('Example: https://example.org/?token=YOUR_TOKEN', 'example')

    def test_timestamp_normalization_and_metadata_integrity(self):
        value, text, hashed = archive.render_event(event())
        self.assertEqual(value["occurred_at"], "2026-10-26T12:00:00Z")
        self.assertEqual(archive.parse_event(text), value)
        self.assertEqual(len(hashed), 64)
        with self.assertRaises(archive.ArchiveError):
            archive.parse_event(text + "\nExtra instructions\n")

    def test_record_is_idempotent_and_conflict_does_not_replace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = archive.record_event(root, event())
            self.assertEqual(first["status"], "recorded")
            self.assertEqual(archive.record_event(root, event())["status"], "unchanged")
            path = root / first["path"]
            original = path.read_bytes()
            with self.assertRaises(archive.ArchiveError):
                archive.record_event(root, event(summary="Different content"))
            self.assertEqual(path.read_bytes(), original)

    def test_invalid_record_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(archive.ArchiveError):
                archive.record_event(root, event(visibility="private"))
            self.assertEqual(list(root.iterdir()), [])

    @unittest.skipIf(os.name == "nt", "Creating symlinks may require Windows privileges")
    def test_symlink_memory_directory_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            (root / "memory").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(archive.ArchiveError):
                archive.record_event(root, event())
            self.assertEqual(list(Path(outside).iterdir()), [])

    def test_automatic_changes_cannot_modify_identity_or_delete_memory(self):
        for changes in ([('M', 'identity/profile.md')], [('D', 'memory/entries/test-event.md')],
                        [('M', 'memory/entries/test-event.md')], [('A', 'scripts/evil.py')]):
            with self.subTest(changes=changes), self.assertRaises(archive.ArchiveError):
                archive.check_auto_changes(changes)
        archive.check_auto_changes([('A', 'memory/entries/test-event.md')])


class ApiTests(unittest.TestCase):
    def test_preview_has_no_network(self):
        api = FakeAPI({})
        result = archive.propose_event(api, event())
        self.assertEqual(result["status"], "preview")
        self.assertEqual(api.calls, [])

    def test_published_event_retry_is_noop(self):
        _, text, _ = archive.render_event(event())
        api = FakeAPI({('GET', '/commits/main'): commit(),
                       ('GET', '/contents/memory%2Fentries%2Ftest-public-event.md?ref=' + SHA): content(text)})
        result = archive.propose_event(api, event(), True)
        self.assertEqual(result['status'], 'already-present')
        self.assertTrue(all(call[0] == 'GET' for call in api.calls))

    def test_main_collision_never_mutates(self):
        api = FakeAPI({('GET', '/commits/main'): commit(),
                       ('GET', '/contents/memory%2Fentries%2Ftest-public-event.md?ref=' + SHA): content("different")})
        with self.assertRaises(archive.ArchiveError):
            archive.propose_event(api, event(), True)
        self.assertTrue(all(call[0] == 'GET' for call in api.calls))

    def test_existing_pr_is_reused(self):
        _, text, _ = archive.render_event(event())
        pr = {'number': 7, 'html_url': 'https://github.com/example/repo/pull/7', 'state': 'open',
              'head': {'ref': 'memory/test-public-event'}, 'base': {'ref': 'main'}}
        api = FakeAPI({('GET', '/commits/main'): commit(),
            ('GET', '/contents/memory%2Fentries%2Ftest-public-event.md?ref=' + SHA): None,
            ('GET', '/git/ref/heads/memory%2Ftest-public-event'): {'object': {'sha': BRANCH}},
            ('GET', '/contents/memory%2Fentries%2Ftest-public-event.md?ref=' + BRANCH): content(text),
            ('GET', '/compare/' + SHA + '...' + BRANCH): {'files': [{'filename': 'memory/entries/test-public-event.md', 'status': 'added'}]},
            ('GET', '/pulls?state=all&head=lenwallem-bit%3Amemory%2Ftest-public-event&base=main&per_page=100'): [pr]})
        result = archive.propose_event(api, event(), True)
        self.assertEqual(result['number'], 7)
        self.assertTrue(all(call[0] == 'GET' for call in api.calls))

    def test_new_proposal_creates_only_new_branch(self):
        pr = {'number': 1, 'html_url': 'https://github.com/example/repo/pull/1', 'state': 'open'}
        api = FakeAPI({('GET', '/commits/main'): commit(),
            ('GET', '/contents/memory%2Fentries%2Ftest-public-event.md?ref=' + SHA): None,
            ('GET', '/git/ref/heads/memory%2Ftest-public-event'): None,
            ('POST', '/git/trees'): {'sha': OLD_TREE},
            ('POST', '/git/commits'): {'sha': BRANCH},
            ('POST', '/git/refs'): {'ref': 'refs/heads/memory/test-public-event'},
            ('POST', '/pulls'): pr})
        result = archive.propose_event(api, event(), True)
        self.assertEqual(result['number'], 1)
        mutations = [x for x in api.calls if x[0] != 'GET']
        self.assertEqual(mutations[0][2]['tree'][0]['path'], 'memory/entries/test-public-event.md')
        self.assertEqual(mutations[1][2]['parents'], [SHA])
        self.assertEqual(mutations[2][2]['ref'], 'refs/heads/memory/test-public-event')
        self.assertFalse(any(x[0] in ('PATCH', 'PUT', 'DELETE') for x in mutations))

    def test_read_uses_immutable_blob_snapshot(self):
        routes = {('GET', '/commits/main'): commit()}
        tree = []
        for i, name in enumerate(archive.START_FILES):
            blob_sha = f'{i + 1:040x}'
            text = '{}' if name.endswith('.json') else '# AI-READONLY: test\n'
            tree.append({'path': name, 'sha': blob_sha, 'type': 'blob', 'mode': '100644', 'size': len(text)})
            routes[('GET', '/git/blobs/' + blob_sha)] = {'encoding': 'base64', 'content': base64.b64encode(text.encode()).decode()}
        routes[('GET', '/git/trees/' + TREE + '?recursive=1')] = {'tree': tree, 'truncated': False}
        api = FakeAPI(routes)
        result = archive.read_snapshot(api)
        self.assertEqual(result['commit'], SHA)
        self.assertEqual(len(result['documents']), len(archive.START_FILES))
        self.assertEqual(sum('main' in x[1] for x in api.calls), 1)

    def test_restore_requires_full_sha_and_reachable_history(self):
        api = FakeAPI({})
        with self.assertRaises(archive.ArchiveError):
            archive.restore_archive(api, 'abc')
        self.assertEqual(api.calls, [])
        api = FakeAPI({('GET', '/commits/main'): commit(), ('GET', '/commits/' + OLD): commit(OLD, OLD_TREE),
                       ('GET', '/compare/' + OLD + '...' + SHA): {'status': 'diverged'}})
        with self.assertRaises(archive.ArchiveError):
            archive.restore_archive(api, OLD, True)
        self.assertTrue(all(x[0] == 'GET' for x in api.calls))

    def test_restore_is_preview_and_scoped_to_five_directories(self):
        unchanged = [{'path': d + '/README.md', 'sha': '1' * 40, 'type': 'blob', 'mode': '100644'} for d in archive.CORE_DIRS]
        current = unchanged + [{'path': 'memory/entries/later-event.md', 'sha': '2' * 40, 'type': 'blob', 'mode': '100644'},
                               {'path': 'scripts/archive.py', 'sha': '3' * 40, 'type': 'blob', 'mode': '100644'}]
        old = unchanged + [{'path': 'scripts/archive.py', 'sha': '4' * 40, 'type': 'blob', 'mode': '100644'}]
        api = FakeAPI({('GET', '/commits/main'): commit(), ('GET', '/commits/' + OLD): commit(OLD, OLD_TREE),
            ('GET', '/compare/' + OLD + '...' + SHA): {'status': 'ahead'},
            ('GET', '/git/trees/' + TREE + '?recursive=1'): {'tree': current},
            ('GET', '/git/trees/' + OLD_TREE + '?recursive=1'): {'tree': old}})
        result = archive.restore_archive(api, OLD)
        self.assertEqual(result['status'], 'preview')
        self.assertEqual(result['changes'], [{'path': 'memory/entries/later-event.md', 'action': 'remove'}])
        self.assertTrue(all(x[0] == 'GET' for x in api.calls))

    def test_restore_rejects_existing_branch_with_unrelated_changes(self):
        shared = [{'path': d + '/README.md', 'sha': '1' * 40, 'type': 'blob', 'mode': '100644'} for d in archive.CORE_DIRS]
        current = shared + [{'path': 'memory/entries/later-event.md', 'sha': '2' * 40, 'type': 'blob', 'mode': '100644'}]
        branch = 'restore/' + OLD[:12] + '-' + SHA[:12]
        bad_tree = 'f' * 40
        api = FakeAPI({('GET', '/commits/main'): commit(), ('GET', '/commits/' + OLD): commit(OLD, OLD_TREE),
            ('GET', '/compare/' + OLD + '...' + SHA): {'status': 'ahead'},
            ('GET', '/git/trees/' + TREE + '?recursive=1'): {'tree': current},
            ('GET', '/git/trees/' + OLD_TREE + '?recursive=1'): {'tree': shared},
            ('GET', '/git/ref/heads/' + archive.quote(branch)): {'object': {'sha': BRANCH}},
            ('GET', '/commits/' + BRANCH): commit(BRANCH, bad_tree),
            ('GET', '/git/trees/' + bad_tree + '?recursive=1'): {'tree': shared + [
                {'path': 'scripts/unrelated.py', 'sha': '4' * 40, 'type': 'blob', 'mode': '100644'}]}})
        with self.assertRaisesRegex(archive.ArchiveError, 'differs'):
            archive.restore_archive(api, OLD, True)
        self.assertTrue(all(x[0] == 'GET' for x in api.calls))

    def test_gcm_is_noninteractive_and_does_not_publish_secret(self):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"login":"lenwallem-bit"}'
        secret = 'synthetic-unit-test-only'
        proc = subprocess.CompletedProcess([], 0, 'username=lenwallem-bit\npassword=' + secret + '\n', '')
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(archive.shutil, 'which', side_effect=lambda n: '/fake/git' if n == 'git' else None), \
             mock.patch.object(archive.subprocess, 'run', return_value=proc) as run, \
             mock.patch.object(archive.urllib.request, 'build_opener') as opener:
            opener.return_value.open.return_value = response
            api = archive.GitHub(archive.DEFAULT_REPO)
            api.load_gcm()
            self.assertTrue(api.gcm_owner_verified)
            self.assertEqual(api.token, secret)
            self.assertEqual(run.call_args.kwargs['env']['GCM_INTERACTIVE'], 'Never')
            self.assertEqual(run.call_args.kwargs['env']['GIT_TERMINAL_PROMPT'], '0')
            self.assertNotIn(secret, str(run.call_args))

    def test_workflow_token_does_not_use_gcm_or_user_endpoint(self):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"sha":"result"}'
        with mock.patch.dict(os.environ, {'GITHUB_TOKEN': 'synthetic-action-token'}, clear=True), \
             mock.patch.object(archive.subprocess, 'run') as run, \
             mock.patch.object(archive.urllib.request, 'build_opener') as opener:
            opener.return_value.open.return_value = response
            api = archive.GitHub(archive.DEFAULT_REPO)
            api.request('POST', '/git/trees', {'tree': []})
            self.assertFalse(run.called)
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url, 'https://api.github.com/repos/' + archive.DEFAULT_REPO + '/git/trees')


if __name__ == '__main__':
    unittest.main()
