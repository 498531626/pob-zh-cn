"""Exercise real Lua/curl update downloads against a local HTTP fixture; no GUI."""
import ctypes
import functools
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
import xml.etree.ElementTree as ET

from release_support import RAW_CHUNK_BYTES, gitee_urls, split_archive, write_manifest, write_update_site
from sync_sources import sync
from probe_update_site import probe

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / 'runtime'


def run_lua(code):
    with os.add_dll_directory(str(RUNTIME)):
        loaded = [ctypes.WinDLL(str(path)) for path in RUNTIME.glob('*.dll') if path.name != 'msvcr100.dll']
        lib = ctypes.CDLL(str(RUNTIME / 'lua51.dll'))
        lib.luaL_newstate.restype = ctypes.c_void_p
        lib.luaL_openlibs.argtypes = [ctypes.c_void_p]
        lib.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        lib.lua_pcall.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        lib.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        lib.lua_tolstring.restype = ctypes.c_char_p
        lib.lua_close.argtypes = [ctypes.c_void_p]
        state = lib.luaL_newstate()
        try:
            lib.luaL_openlibs(state)
            prefix = 'package.path=' + quote(RUNTIME / 'lua/?.lua') + '..";"..' + quote(RUNTIME / 'lua/?/init.lua') + '..";"..package.path\n'
            prefix += 'package.cpath=' + quote(RUNTIME / '?.dll') + '..";"..package.cpath\n'
            rc = lib.luaL_loadstring(state, (prefix + code).encode('utf-8')) or lib.lua_pcall(state, 0, 0, 0)
            if rc:
                raise AssertionError(lib.lua_tolstring(state, -1, None).decode('utf-8', errors='replace'))
        finally:
            lib.lua_close(state)


def quote(value):
    return json.dumps(value.as_posix() if isinstance(value, Path) else value, ensure_ascii=False)


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.startswith('/redirect/'):
            self.send_response(302)
            self.send_header('Location', self.path.replace('/redirect/', '/published/files/', 1))
            self.end_headers()
        else:
            super().do_GET()


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='PoB update QA ')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.site = self.root / 'site'
        self.site.mkdir()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=self.site))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.url = f'http://127.0.0.1:{self.server.server_port}/'
        self.old = self.root / 'old'
        (self.old / 'Modules').mkdir(parents=True)
        shutil.copy2(ROOT / 'src/Modules/UpdatePolicy.lua', self.old / 'Modules/UpdatePolicy.lua')
        for name, content in {'changed.txt': 'old', 'deleted.txt': 'obsolete', 'unchanged.txt': 'same',
                              'changelog.txt': 'release notes', 'Path of Building.exe': 'MZ fixture'}.items():
            (self.old / name).write_text(content, encoding='utf-8')
        self.new = self.root / 'new'
        shutil.copytree(self.old, self.new)
        (self.new / 'changed.txt').write_text('new translation', encoding='utf-8')
        (self.new / 'deleted.txt').unlink()
        (self.new / 'nested').mkdir()
        (self.new / 'nested/新 file.txt').write_text('新增中文', encoding='utf-8')

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def publish(self):
        write_manifest(self.old, '2.67.2', 'zh-1', 'release-stable', self.url + 'published/', self.url + 'redirect/')
        write_manifest(self.new, '2.67.2', 'zh-2', 'release-stable', self.url + 'published/', self.url + 'redirect/')
        write_update_site(self.new, self.site / 'published')
        self.personal = {'Settings.xml': 'private settings', 'Builds/mine.xml': 'private build',
                         'Localization/language.cfg': 'en'}
        for name, content in self.personal.items():
            path = self.old / name
            path.parent.mkdir(exist_ok=True)
            path.write_text(content, encoding='utf-8')
        (self.old / 'Update').mkdir()
        (self.old / 'nested').mkdir(exist_ok=True)

    def update(self, mode='normal', apply=True):
        code = 'function GetScriptPath() return ' + quote(self.old) + ' end\nGetRuntimePath=GetScriptPath\n'
        code += 'function MakeDir() end\nfunction ConPrintf() end\nfunction SpawnProcess() SPAWNED=true end\n'
        code += 'local check=assert(loadstring(' + quote((ROOT / 'src/UpdateCheck.lua').read_text(encoding='utf-8').removeprefix('#@')) + '))\n'
        code += 'local mode,err=check()\n'
        if mode == 'error':
            code += 'assert(mode==nil and err, "Expected safe update rejection")\n'
        else:
            code += 'assert(mode==' + quote(mode) + ',tostring(mode).." / "..tostring(err))\n'
        if apply and mode not in {'error', 'none'}:
            source = (ROOT / 'src/UpdateApply.lua').read_text(encoding='utf-8').removeprefix('#@')
            code += 'local apply=assert(loadstring(' + quote(source) + '))\napply(' + quote(self.old / 'Update/opFile.txt') + ')\n'
            if mode == 'basic':
                code += 'apply(' + quote(self.old / 'Update/opFileRuntime.txt') + ')\nassert(SPAWNED)\n'
        run_lua(code)

    def test_download_redirect_add_replace_remove_and_preserve_saves(self):
        self.publish()
        self.update()
        self.assertEqual((self.old / 'changed.txt').read_text(encoding='utf-8'), 'new translation')
        self.assertEqual((self.old / 'nested/新 file.txt').read_text(encoding='utf-8'), '新增中文')
        self.assertFalse((self.old / 'deleted.txt').exists())
        for name, content in self.personal.items():
            self.assertEqual((self.old / name).read_text(encoding='utf-8'), content)
        version = ET.parse(self.old / 'manifest.xml').getroot().find('Version')
        self.assertEqual(version.get('release'), 'zh-2')
        self.assertEqual(version.get('updates'), 'enabled')
        self.update(mode='none', apply=False)

    def test_runtime_update_uses_separate_operations(self):
        (self.new / 'Path of Building.exe').write_text('MZ updated fixture', encoding='utf-8')
        self.publish()
        self.update(mode='basic')
        self.assertEqual((self.old / 'Path of Building.exe').read_text(), 'MZ updated fixture')

    def test_corruption_does_not_apply(self):
        self.publish()
        (self.site / 'published/files/changed.txt').write_text('corrupt')
        self.update(mode='error')
        self.assertEqual((self.old / 'changed.txt').read_text(), 'old')
        self.assertFalse((self.old / 'Update/opFile.txt').exists())

    def test_http_404_does_not_apply(self):
        self.publish()
        (self.site / 'published/files/changed.txt').unlink()
        self.update(mode='error')
        self.assertFalse((self.old / 'Update/opFile.txt').exists())

    def test_html_response_is_not_an_update(self):
        self.publish()
        for content in ('', '<html><body>Login required</body></html>'):
            (self.site / 'published/manifest.xml').write_text(content)
            self.update(mode='error')
            self.assertFalse((self.old / 'Update/opFile.txt').exists())

    def test_anonymous_site_probe(self):
        self.publish()
        probe(self.url + 'published/manifest.xml', all_files=True)

    def test_large_file_chunks_reassemble_and_preserve_full_hash(self):
        content = os.urandom(RAW_CHUNK_BYTES + 123)
        name = 'nested/字库.bin'
        (self.new / name).write_bytes(content)
        self.publish()
        payload = self.site / 'published/files' / name
        self.assertFalse(payload.exists())
        self.assertEqual(payload.with_name(payload.name + '.part001').stat().st_size, RAW_CHUNK_BYTES)
        probe(self.url + 'published/manifest.xml', all_files=True)
        self.update()
        self.assertEqual((self.old / name).read_bytes(), content)
        node = ET.parse(self.old / 'manifest.xml').getroot().find("File[@name='" + name + "']")
        self.assertEqual(node.get('chunks'), '2')
        self.assertFalse(list((self.old / 'Update').glob('*.chunk')))
        self.update(mode='none', apply=False)

    def test_corrupt_or_missing_chunk_never_generates_apply_operations(self):
        (self.new / 'nested/large.bin').write_bytes(os.urandom(RAW_CHUNK_BYTES + 123))
        self.publish()
        last = self.site / 'published/files/nested/large.bin.part002'
        for missing in (False, True):
            if missing:
                last.unlink()
            else:
                last.write_bytes(b'corrupted final chunk')
            self.update(mode='error')
            self.assertFalse((self.old / 'Update/opFile.txt').exists())
            self.assertFalse((self.old / 'nested/large.bin').exists())

    def test_invalid_chunk_count_is_rejected(self):
        self.publish()
        manifest = self.site / 'published/manifest.xml'
        baseline = manifest.read_bytes()
        for chunks in ('0', '-1', '1.5', 'no', '1025'):
            root = ET.fromstring(baseline)
            root.find('File').set('chunks', chunks)
            ET.ElementTree(root).write(manifest, encoding='utf-8')
            self.update(mode='error')
            self.assertFalse((self.old / 'Update/opFile.txt').exists())

    def test_reject_personal_and_traversal_entries(self):
        self.publish()
        manifest = self.site / 'published/manifest.xml'
        baseline = manifest.read_bytes()
        for name in ('../outside.txt', 'Settings.xml', 'Builds/mine.xml', 'Localization/language.cfg', 'bad"name'):
            with self.subTest(name=name):
                root = ET.fromstring(baseline)
                ET.SubElement(root, 'File', name=name, part='program', sha1='0' * 40)
                ET.ElementTree(root).write(manifest, encoding='utf-8')
                self.update(mode='error')
                self.assertFalse((self.old / 'Update/opFile.txt').exists())
        self.assertFalse((self.root / 'outside.txt').exists())


class ReleaseTests(unittest.TestCase):
    def test_real_x86_update_helper_without_opening_a_window(self):
        with tempfile.TemporaryDirectory(prefix='PoB helper QA ') as directory:
            root = Path(directory)
            for name in ('Update.exe', 'msvcr100.dll'):
                shutil.copy2(RUNTIME / name, root / name)
            shutil.copy2(ROOT / 'src/UpdateApply.lua', root / 'UpdateApply.lua')
            (root / 'new.bin').write_bytes(b'new runtime fixture')
            (root / 'old.bin').write_bytes(b'old runtime fixture')
            (root / 'ops.txt').write_text('move "new.bin" "old.bin"\n', encoding='utf-8')
            result = subprocess.run([str(root / 'Update.exe'), 'UpdateApply.lua', 'ops.txt'], cwd=root,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=15,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual((root / 'old.bin').read_bytes(), b'new runtime fixture')

    def test_gitee_urls_and_reject_embedded_secrets(self):
        channel, payload = gitee_urls('https://gitee.com/example/pob.git', 'release-stable', 'zh-1')
        self.assertEqual(channel, 'https://gitee.com/example/pob/raw/release-stable/')
        self.assertEqual(payload, 'https://gitee.com/example/pob/raw/zh-1/files/')
        for url in ('http://gitee.com/a/b', 'https://token@gitee.com/a/b', 'https://gitee.com/a/b?token=x'):
            with self.assertRaises(ValueError):
                gitee_urls(url, 'release-stable', 'zh-1')

    def test_complete_volumes_join_with_windows_builtin_commands(self):
        with tempfile.TemporaryDirectory(prefix='PoB volumes QA ') as directory:
            root = Path(directory)
            archive = root / 'portable.zip'
            archive.write_bytes(os.urandom(4096))
            target = root / 'gitee'
            parts = split_archive(archive, target, 1000)
            self.assertEqual(len(parts), 5)
            # Execute only our generated join script in a disposable directory.
            result = subprocess.run(['cmd', '/c', str(target / 'Join-Portable.cmd')],
                                    input=b'\r\n', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual((target / archive.name).read_bytes(), archive.read_bytes())
            self.assertEqual(json.loads((target / 'volumes.json').read_text())['sha256'],
                             hashlib.sha256(archive.read_bytes()).hexdigest())

    def test_pushes_same_commit_to_two_local_bare_repositories(self):
        with tempfile.TemporaryDirectory(prefix='PoB source sync QA ') as directory:
            root = Path(directory)
            work = root / 'work'
            run = lambda *args, cwd=None: subprocess.run(['git', *args], cwd=cwd, check=True,
                                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            run('init', '-b', 'localization', str(work))
            (work / 'README.md').write_text('fixture')
            run('add', '.', cwd=work)
            run('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'fixture', cwd=work)
            for remote in ('origin', 'gitee'):
                bare = root / (remote + '.git')
                run('init', '--bare', str(bare))
                run('remote', 'add', remote, str(bare), cwd=work)
            sync(work, execute=True)
            head = run('rev-parse', 'HEAD', cwd=work).stdout
            for remote in ('origin', 'gitee'):
                self.assertEqual(run('--git-dir', str(root / (remote + '.git')), 'rev-parse', 'localization').stdout, head)

    def test_snapshot_mirror_preserves_contents_without_old_history(self):
        with tempfile.TemporaryDirectory(prefix='PoB compact mirror QA ') as directory:
            root = Path(directory)
            work = root / 'work'
            def run(*args):
                return subprocess.check_output(['git', '-C', str(work), *args], encoding='utf-8',
                                               stderr=subprocess.DEVNULL).strip()
            work.mkdir()
            run('init', '-b', 'localization')
            run('config', 'user.name', 'Fixture')
            run('config', 'user.email', 'fixture@example.invalid')
            (work / 'data.txt').write_text('old content', encoding='utf-8')
            run('add', '.')
            run('commit', '-m', 'old upstream history')
            old = run('rev-parse', 'HEAD')
            (work / 'data.txt').write_text('当前源码', encoding='utf-8')
            (work / 'gitee-mirror.json').write_text('{"history":"snapshot-v1"}', encoding='utf-8')
            run('add', '.')
            run('commit', '-m', 'localized source')
            for remote in ('origin', 'gitee'):
                subprocess.run(['git', 'init', '--bare', str(root / (remote + '.git'))], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                run('remote', 'add', remote, str(root / (remote + '.git')))
            sync(work, execute=True)
            mirror = run('rev-parse', 'refs/remotes/gitee/localization')
            self.assertEqual(run('rev-list', '--count', mirror), '1')
            self.assertEqual(run('rev-parse', mirror + '^{tree}'), run('rev-parse', 'HEAD^{tree}'))
            self.assertNotIn(old, run('rev-list', mirror))
            sync(work, execute=True)
            self.assertEqual(run('rev-parse', 'refs/remotes/gitee/localization'), mirror)
            (work / 'data.txt').write_text('next localization update', encoding='utf-8')
            run('add', '.')
            run('commit', '-m', 'next fix')
            source = run('rev-parse', 'HEAD')
            sync(work, execute=True)
            updated = run('rev-parse', 'refs/remotes/gitee/localization')
            self.assertEqual(run('rev-parse', updated + '^'), mirror)
            self.assertEqual(run('rev-list', '--count', updated), '2')
            self.assertEqual(run('rev-parse', updated + '^{tree}'), run('rev-parse', source + '^{tree}'))
            self.assertIn('Source-Commit: ' + source, run('show', '-s', '--format=%B', updated))
            self.assertEqual(run('rev-parse', 'refs/remotes/origin/localization'), source)
            # An unrelated branch on the remote must never be overwritten.
            run('push', '--force', 'gitee', source + ':refs/heads/localization')
            with self.assertRaises(RuntimeError):
                sync(work, execute=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
