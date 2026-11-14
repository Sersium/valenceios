"""Check the exact Discord input and the self-contained, injected output."""
import hashlib
import json
import os
from datetime import datetime, timezone
import plistlib
import posixpath
import struct
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = json.loads((ROOT / 'ipa-source.json').read_text())
HERMES_MAGIC = bytes.fromhex('c61fbc03c103191f')


def commands(binary):
    if len(binary) < 32 or binary[:4] != b'\xcf\xfa\xed\xfe':
        raise ValueError('Expected a thin ARM64 Mach-O')
    if struct.unpack_from('<I', binary, 4)[0] != 0x100000c:
        raise ValueError('Expected ARM64 CPU')
    count, size = struct.unpack_from('<II', binary, 16)
    end = 32 + size
    if end > len(binary):
        raise ValueError('Truncated Mach-O commands')
    offset = 32
    for _ in range(count):
        if offset + 8 > end:
            raise ValueError('Truncated Mach-O command')
        command, size = struct.unpack_from('<II', binary, offset)
        if size < 8 or size % 8 or offset + size > end:
            raise ValueError('Invalid Mach-O command size')
        data = binary[offset:offset + size]
        if command == 0x2c and struct.unpack_from('<I', data, 16)[0]:
            raise ValueError('Encrypted executable')
        if command == 0x19:
            sections = struct.unpack_from('<I', data, 64)[0]
            if 72 + sections * 80 > size:
                raise ValueError('Invalid Mach-O section table')
            for index in range(sections):
                section = 72 + index * 80
                length, start = struct.unpack_from('<QI', data, section + 40)
                kind = struct.unpack_from('<I', data, section + 64)[0] & 0xff
                if length and start and kind not in (1, 12, 18) and (start < end or start + length > len(binary)):
                    raise ValueError('Mach-O section overlaps commands or exceeds file')
        yield command, data
        offset += size
    if offset != end:
        raise ValueError('Mach-O command count mismatch')


def libraries(binary):
    for command, data in commands(binary):
        if command in (0xc, 0x80000018, 0x8000001f):
            offset = struct.unpack_from('<I', data, 8)[0]
            if offset < 24 or offset >= len(data) or b'\0' not in data[offset:]:
                raise ValueError('Invalid dylib path')
            yield data[offset:].split(b'\0')[0].decode()


def sections(binary):
    result = {}
    for command, data in commands(binary):
        if command == 0x19:
            for index in range(struct.unpack_from('<I', data, 64)[0]):
                offset = 72 + index * 80
                name = data[offset:offset + 16].split(b'\0')[0].decode()
                size, start = struct.unpack_from('<QI', data, offset + 40)
                if name in ('__vbundle', '__vmanifest'):
                    result[name] = binary[start:start + size]
    return result


def bytecode_version(data):
    if len(data) < 12 or data[:8] != HERMES_MAGIC:
        raise ValueError('Expected Hermes bytecode')
    return struct.unpack_from('<I', data, 8)[0]


def metadata(ipa):
    plists = [n for n in ipa.namelist() if n.startswith('Payload/') and n.endswith('.app/Info.plist') and n.count('/') == 2]
    if len(plists) != 1:
        raise ValueError('Expected one main app')
    return plists[0][:-10], plistlib.loads(ipa.read(plists[0]))


def verify(path, injected=False):
    if not injected:
        with open(path, 'rb') as file:
            if hashlib.file_digest(file, 'sha256').hexdigest() != SOURCE['sha256']:
                raise ValueError('Base IPA checksum mismatch')
    with zipfile.ZipFile(path) as ipa:
        if ipa.testzip() is not None:
            raise ValueError('Corrupt IPA')
        app, info = metadata(ipa)
        assert info['CFBundleIdentifier'] == SOURCE['bundleIdentifier']
        assert info['CFBundleShortVersionString'] == SOURCE['version']
        assert info['CFBundleVersion'] == SOURCE['build']
        main = ipa.read(app + info['CFBundleExecutable'])
        deps = list(libraries(main))
        assert bytecode_version(ipa.read(app + 'main.jsbundle')) == SOURCE['hermesVersion']
        for selector in (b'instance:didInitializeRuntime:', b'_loadScriptFromSource:', b'callFunctionOnBufferedRuntimeExecutor:', b'RCTSource'):
            assert selector in main, f'Missing React Native hook: {selector!r}'
        if injected:
            assert '@rpath/ValencedTweak.dylib' in deps, 'Discord does not load Valenced'
            embedded = sections(ipa.read(app + 'Frameworks/ValencedTweak.dylib'))
            assert bytecode_version(embedded['__vbundle']) == SOURCE['hermesVersion'], 'Hermes bytecode mismatch'
            manifest = json.loads(embedded['__vmanifest'])
            ids = {p['id'] for p in manifest['plugins']}
            assert {'valenced.api', 'valenced.settings', 'valenced.settings.plugins'} <= ids
            names = set(ipa.namelist())
            for name in names:
                if name.endswith('/') or not name.startswith(app):
                    continue
                with ipa.open(name) as file:
                    magic = file.read(4)
                if magic != b'\xcf\xfa\xed\xfe':
                    continue
                for dep in libraries(ipa.read(name)):
                    assert not any(s in dep for s in ('/var/jb/', '.jbroot', 'libroothide', 'ValencedCore.framework')) , dep
                    if dep.startswith(('/System/Library/', '/usr/lib/')):
                        continue
                    if dep.startswith('@rpath/'):
                        target = app + 'Frameworks/' + dep[7:]
                    elif dep.startswith('@loader_path/'):
                        target = posixpath.normpath(posixpath.dirname(name) + '/' + dep[13:])
                    elif dep.startswith('@executable_path/'):
                        target = posixpath.normpath(app + dep[17:])
                    else:
                        raise ValueError(f'Non-portable dependency: {dep}')
                    assert target in names, f'Missing {dep} required by {name}'
    print(f'PASS: {"injected" if injected else "base"} IPA validated')


def feed(path, version, sha):
    with zipfile.ZipFile(path) as ipa:
        _, info = metadata(ipa)
    repo = os.environ['GITHUB_REPOSITORY']
    base = f'https://github.com/{repo}/releases/download/latest'
    date = datetime.now(timezone.utc).isoformat()
    description = f'Valenced iOS · Discord {info["CFBundleShortVersionString"]} · build {version}\nSource: {sha}\nAI-assisted fork. Device and third-party plugin compatibility require testing.'
    record = dict(version=version, date=date, downloadURL=base + '/Discord_Valenced.ipa', size=Path(path).stat().st_size, localizedDescription=description)
    app = dict(name='Discord (Valenced)', bundleIdentifier=info['CFBundleIdentifier'], developerName='Valenced & Sersium', iconURL=f'https://raw.githubusercontent.com/{repo}/main/assets/icon.png', tintColor='5865F2', versionDate=date, versionDescription=description, versions=[record], **{k: v for k, v in record.items() if k != 'date'})
    data = dict(name='Valenced iOS', identifier='com.sersium.valenceios.source', website=f'https://github.com/{repo}', sourceURL=base + '/feather.json', apps=[app])
    Path('feather.json').write_text(json.dumps(data, indent=2) + '\n')
    Path('release-notes.md').write_text(description + '\n\nUnsigned IPA: sign and install with Feather. This rolling release replaces the previous successful build.\n')


if __name__ == '__main__':
    if sys.argv[1] == 'feed':
        feed(*sys.argv[2:])
    else:
        verify(sys.argv[2], injected=sys.argv[1] == 'verify')
