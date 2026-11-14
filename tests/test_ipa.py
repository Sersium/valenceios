import importlib.util
import json
import os
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('ipa', Path(__file__).resolve().parents[1] / 'scripts/ipa.py')
ipa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ipa)


def binary(commands=b'', count=0):
    return struct.pack('<8I', 0xfeedfacf, 0x100000c, 0, 6, count, len(commands), 0, 0) + commands


class PackagingTests(unittest.TestCase):
    def test_native_symbol_definitions_and_unresolved_calls(self):
        strings = b'\0_ValencedCore_FreeString\0_ValencedCore_Missing\0'
        table = struct.pack('<IBBHQ', 1, 0xf, 1, 0, 100) + struct.pack('<IBBHQ', strings.index(b'_ValencedCore_Missing'), 1, 0, 0, 0)
        command = struct.pack('<6I', 2, 24, 56, 2, 88, len(strings))
        defined, undefined = ipa.symbols(binary(command, 1) + table + strings)
        self.assertEqual(defined, {'_ValencedCore_FreeString'})
        self.assertEqual(undefined, {'_ValencedCore_Missing'})
        with self.assertRaises(AssertionError):
            ipa.verify_symbols(binary(command, 1) + table + strings, [])

    def test_rejects_encrypted_or_malformed_binary(self):
        encrypted = struct.pack('<6I', 0x2c, 24, 0, 0, 1, 0)
        for data in (b'bad', binary(encrypted, 1), binary(struct.pack('<II', 0xc, 100), 1)):
            with self.assertRaises(ValueError):
                list(ipa.libraries(data))

    def test_reads_injected_library(self):
        name = b'@rpath/ValencedTweak.dylib\0'
        size = (24 + len(name) + 7) // 8 * 8
        command = struct.pack('<6I', 0xc, size, 24, 0, 0, 0) + name
        self.assertEqual(list(ipa.libraries(binary(command.ljust(size, b'\0'), 1))), ['@rpath/ValencedTweak.dylib'])

    def test_bytecode_version(self):
        self.assertEqual(ipa.bytecode_version(ipa.HERMES_MAGIC + struct.pack('<I', 98)), 98)
        with self.assertRaises(ValueError):
            ipa.bytecode_version(b'javascript')

    def test_system_swift_requires_its_runtime_search_path(self):
        path = b'/usr/lib/swift\0'
        size = (12 + len(path) + 7) // 8 * 8
        command = struct.pack('<III', 0x8000001c, size, 12) + path
        paths = list(ipa.runpaths(binary(command.ljust(size, b'\0'), 1)))
        self.assertTrue(ipa.system_library('@rpath/libswiftCore.dylib', paths))
        self.assertFalse(ipa.system_library('@rpath/libswiftCore.dylib', []))
        self.assertFalse(ipa.system_library('@rpath/ValencedTweak.dylib', paths))
        self.assertFalse(ipa.system_library('@rpath/libswift/other.dylib', paths))

    def test_rolling_feather_feed(self):
        with tempfile.TemporaryDirectory() as directory:
            original = os.getcwd()
            try:
                os.chdir(directory)
                Path('output.ipa').write_bytes(b'ipa')
                with patch.object(ipa, 'metadata', return_value=('', {'CFBundleIdentifier': 'com.hammerandchisel.discord', 'CFBundleShortVersionString': '353.0'})), patch.object(zipfile, 'ZipFile'), patch.dict(os.environ, GITHUB_REPOSITORY='Sersium/valenceios'):
                    ipa.feed('output.ipa', '353.0.7', 'abc123')
                    data = json.loads(Path('feather.json').read_text())
                    app = data['apps'][0]
                    self.assertEqual(app['version'], '353.0.7')
                    self.assertEqual(app['size'], 3)
                    self.assertEqual(len(app['versions']), 1)
                    self.assertEqual(data['sourceURL'], 'https://github.com/Sersium/valenceios/releases/download/latest/feather.json')
                    self.assertIn('/download/latest/', app['downloadURL'])
            finally:
                os.chdir(original)
