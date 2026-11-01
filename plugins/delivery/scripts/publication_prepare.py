#!/usr/bin/env python3
"""Prepare an unapproved local bundle from an explicit committed Git subtree."""
import argparse
import os
from pathlib import PurePosixPath
import re
import selectors
import subprocess
import sys
import time

from project import checked_path
from publication_service import MAX_ENVELOPE, MAX_FILES, MAX_FRAME, Refused, canonical, decode, envelope, exact

OID = re.compile(r'(?:[a-f0-9]{40}|[a-f0-9]{64})')
MODES = {'100644': '0644', '100755': '0755'}
EXTRA_MODES = {'0600', '0644', '0700', '0755'}


def relative(value):
    if type(value) is not str or not value or len(value) > 256 or '\\' in value or '\0' in value:
        raise Refused()
    path = PurePosixPath(value)
    if not path.parts or path.is_absolute() or str(path) != value or any(x in ('.', '..') for x in path.parts):
        raise Refused()
    return value


def git_read(repo, args, limit, deadline):
    """Bound output before allocation; never fetch missing objects or run filters."""
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='', GIT_TERMINAL_PROMPT='0',
               GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
    command = ['git', '--no-replace-objects', '--no-optional-locks', '-c', 'core.fsmonitor=false',
               '-c', 'core.untrackedCache=false', '-c', 'core.hooksPath='+os.devnull,
               '-C', str(repo), *args]
    with subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, env=env) as process:
        try:
            output = bytearray()
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not selector.select(remaining):
                        raise Refused()
                    chunk = os.read(process.stdout.fileno(), min(65536, limit + 1 - len(output)))
                    if not chunk:
                        break
                    output.extend(chunk)
                    if len(output) > limit:
                        raise Refused()
            if process.wait(timeout=max(.001, deadline-time.monotonic())) != 0:
                raise Refused()
            return bytes(output)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()


def prepare(repo, request):
    exact(request, {'commit', 'source', 'prefix', 'destination', 'body', 'metadata', 'extras'})
    commit = request['commit']
    if type(commit) is not str or OID.fullmatch(commit) is None:
        raise Refused()
    source, prefix = relative(request['source']), relative(request['prefix'])
    metadata = request['metadata']
    if type(metadata) is not dict or 'modes' in metadata or type(request['extras']) is not list:
        raise Refused()
    if len(request['extras']) > MAX_FILES:
        raise Refused()
    value = {'operation': 'local-release', 'destination': request['destination'],
             'body': request['body'], 'metadata': {**metadata, 'modes': '{}'}, 'files': []}
    envelope(value)  # Validate supplied text/metadata before Git inspection.
    root = checked_path(repo)
    deadline = time.monotonic() + 30
    def read(*args, limit=1024):
        return git_read(root, args, limit, deadline)
    if not root.is_dir() or read('rev-parse', '--show-toplevel', limit=4096).decode() != str(root)+'\n':
        raise Refused()
    if read('rev-parse', '--verify', commit).decode('ascii').strip() != commit:
        raise Refused()
    if read('cat-file', '-t', commit) != b'commit\n':
        raise Refused()
    tree = read('rev-parse', '--verify', commit+':'+source).decode().strip()
    if OID.fullmatch(tree) is None or read('cat-file', '-t', tree) != b'tree\n':
        raise Refused()
    # Each permitted path character may occupy four UTF-8 bytes; reserve
    # the Git mode/type/OID header and delimiter, including SHA-256 OIDs.
    listing = read('ls-tree', '-rz', tree, limit=(MAX_FILES+1)*(256*4+80))
    entries = listing.rstrip(b'\0').split(b'\0') if listing else []
    if not entries or len(entries) + len(request['extras']) > MAX_FILES:
        raise Refused()
    names, modes, blobs = set(), {}, []
    total = 0
    def name_mode(name, mode):
        name = relative(name)
        if name in names or any(name.startswith(n+'/') or n.startswith(name+'/') for n in names):
            raise Refused()
        names.add(name)
        modes[name] = mode
        return name
    for entry in entries:
        header, path = entry.split(b'\t', 1)
        mode, kind, oid = header.decode('ascii').split(' ')
        if mode not in MODES or kind != 'blob' or OID.fullmatch(oid) is None:
            raise Refused()
        name = name_mode(prefix+'/'+relative(path.decode('utf-8')), MODES[mode])
        size = int(read('cat-file', '-s', oid))
        if size < 0 or size > MAX_ENVELOPE:
            raise Refused()
        total += size
        if total > MAX_ENVELOPE:
            raise Refused()
        blobs.append((name, oid, size))
    for extra in request['extras']:
        exact(extra, {'name', 'content', 'mode'})
        if type(extra['mode']) is not str or extra['mode'] not in EXTRA_MODES or type(extra['content']) is not str:
            raise Refused()
        name = name_mode(extra['name'], extra['mode'])
        total += len(extra['content'].encode('utf-8'))
        if total > MAX_ENVELOPE:
            raise Refused()
        value['files'].append({'name': name, 'content': extra['content']})
    for name, oid, size in blobs:
        raw = read('cat-file', 'blob', oid, limit=size)
        if len(raw) != size:
            raise Refused()
        content = raw.decode('utf-8')
        if content.encode('utf-8') != raw:
            raise Refused()
        value['files'].append({'name': name, 'content': content})
    value['files'].sort(key=lambda item: item['name'])
    value['metadata']['modes'] = canonical(modes)
    return envelope(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(MAX_FRAME+1)
        if len(raw) > MAX_FRAME:
            raise Refused()
        output = prepare(args.repo, decode(raw))
        print(output)
        return 0
    except Exception:
        print('{"status":"unavailable"}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
