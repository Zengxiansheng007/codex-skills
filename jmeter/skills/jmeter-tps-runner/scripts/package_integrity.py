"""Read-only package verification. Host metadata is not executable configuration."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

ROOT = Path(__file__).resolve().parents[1]
HOST_METADATA = '_user_meta.json'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reject_link(path):
    info = Path(path).lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise ValueError('Links/reparse points are not supported: ' + str(path))


def package_files(root):
    """Do not follow symlinks or Windows junctions, including ignored metadata."""
    found = set()
    def walk(folder):
        for entry in os.scandir(folder):
            p = Path(entry.path)
            reject_link(p)
            rel = p.relative_to(root).as_posix()
            if entry.is_dir(follow_symlinks=False):
                if rel == HOST_METADATA:
                    raise ValueError('Host metadata must be an ordinary file')
                walk(p)
            elif entry.is_file(follow_symlinks=False):
                found.add(rel)
            else:
                raise ValueError('Non-regular package entry: ' + rel)
    reject_link(root)
    walk(root)
    return found


def verify_package(root=ROOT):
    root = Path(root).absolute()
    reject_link(root)
    root = root.resolve()
    actual = package_files(root)
    manifest_path = root / 'MANIFEST.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    files = manifest.get('files')
    if not isinstance(files, dict) or not files or 'SKILL.md' not in files:
        raise ValueError('Invalid package manifest')
    normalized = set()
    for name, expected in files.items():
        if not isinstance(name, str) or not isinstance(expected, str):
            raise ValueError('Invalid manifest entry')
        p = PurePosixPath(name)
        if (p.is_absolute() or p.as_posix() != name or not p.parts
                or any(part in ('.', '..') or part.endswith((' ', '.')) for part in p.parts)
                or any(c in name for c in '\\:\x00')
                or name in ('MANIFEST.json', HOST_METADATA)
                or not re.fullmatch('[a-f0-9]{64}', expected)
                or name.casefold() in normalized):
            raise ValueError('Unsafe/duplicate manifest path or digest: ' + name)
        normalized.add(name.casefold())
        target = root.joinpath(*p.parts)
        if name not in actual or root not in target.resolve().parents or digest(target) != expected:
            raise ValueError('Package integrity mismatch: ' + name)
    allowed = set(files) | {'MANIFEST.json', HOST_METADATA}
    extra = actual - allowed
    if extra:
        raise ValueError('Unexpected package files: ' + ', '.join(sorted(extra)))
    return {'status': 'integrity-verified', 'files': len(files),
            'manifest_sha256': digest(manifest_path),
            'host_metadata_present': HOST_METADATA in actual,
            'runtime_qualified': False,
            'limit': 'Local manifest consistency, not a digital signature or host qualification'}
