#!/usr/bin/env python3
"""Explicit local command evidence, not task acceptance or a security sandbox.

Run only already-authorized product commands in the caller's existing lane.
Review uses a new independent local clone; reality verification runs against an
explicit surface directory and observes its revision before and after the check.
No network fetching, deployment, provider selection or permission changes.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time

from project import checked_path
from delivery_gates import GateService

SHA = re.compile(r'(?:[0-9a-f]{40}|[0-9a-f]{64})\Z')
CAPTURE_LIMIT = 256 * 1024


def clean_environment():
    return {k:v for k,v in os.environ.items() if not k.startswith(('GIT_', 'DELIVERY_', 'BEADS_')) and k != 'BD_ACTOR'}


def capture(command, cwd, timeout):
    if not isinstance(command, list) or not command or any(not isinstance(x, str) or '\0' in x for x in command) or not command[0]:
        raise ValueError('Explicit nonempty command argument array required')
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 3600:
        raise ValueError('Timeout must be greater than zero and at most 3600 seconds')
    started = time.monotonic()
    context = {'cwd':str(cwd), 'started_at':datetime.now(timezone.utc).isoformat()}
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            process = subprocess.Popen(command, cwd=cwd, env=clean_environment(), stdin=subprocess.DEVNULL,
                stdout=stdout, stderr=stderr, start_new_session=True)
        except OSError as error:
            return {**context,'command':command, 'stdout':'', 'stderr':str(error), 'exit_code':None,
                    'timed_out':False, 'truncated':False, 'launch_failed':True,
                    'duration_seconds':round(time.monotonic()-started, 6)}
        timed_out = False
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            # Include descendants in the bound; a child retaining output handles
            # must not keep running after the requested check has ended.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        def read(stream):
            stream.seek(0)
            data = stream.read(CAPTURE_LIMIT + 1)
            return data[:CAPTURE_LIMIT].decode('utf-8', errors='replace'), len(data) > CAPTURE_LIMIT
        out, out_clip = read(stdout)
        err, err_clip = read(stderr)
    return {**context,'command':command, 'stdout':out, 'stderr':err, 'exit_code':process.returncode,
            'timed_out':timed_out, 'truncated':out_clip or err_clip,
            'duration_seconds':round(time.monotonic()-started, 6)}


def successful(run):
    return run['exit_code'] == 0 and not run['timed_out'] and not run['truncated']


def require_sha(head):
    if not isinstance(head, str) or not SHA.fullmatch(head):
        raise ValueError('Exact full lowercase commit SHA required')


def raw_check(root, head):
    git = ['git','--no-optional-locks','-c','core.fsmonitor=false','-c','core.untrackedCache=false','-C',str(root)]
    try:
        GateService.verify_tracked_bytes(git, root, head, env=clean_environment())
        staged = capture(git+['diff-index','--cached','--quiet','--no-ext-diff','--no-textconv',head,'--'],root,10)
        return {'passed':successful(staged), 'staged_check':staged}
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        return {'passed':False,'error':str(error)}


def review(repository, head, command, timeout=300):
    require_sha(head)
    source = checked_path(repository)
    if not source.is_dir():
        raise ValueError('Existing authorized local product repository required')
    record = {'kind':'scratch-review', 'head':head, 'repository':str(source), 'passed':False,
              'human_authority':False, 'accepted':False, 'setup':[]}
    with tempfile.TemporaryDirectory(prefix='delivery-review-') as directory:
        clone = Path(directory)/'product'
        for argv in (['git','clone','--quiet','--no-checkout','--no-local','--no-hardlinks','--',str(source),str(clone)],
                     ['git','-C',str(clone),'checkout','--quiet','--detach',head+'^{commit}']):
            step = capture(argv, directory, timeout)
            record['setup'].append(step)
            if not successful(step):
                return record
        before = capture(['git','rev-parse','HEAD'], clone, timeout)
        record['revision_before'] = before
        if not successful(before) or before['stdout'].strip() != head:
            return record
        record['raw_bytes_before'] = raw_check(clone, head)
        if not record['raw_bytes_before']['passed']:
            return record
        record['run'] = capture(command, clone, timeout)
        after = capture(['git','rev-parse','HEAD'], clone, timeout)
        clean = raw_check(clone, head)
        record.update(revision_after=after, tracked_changes=clean)
        record['passed'] = (successful(record['run']) and successful(after) and after['stdout'].strip() == head
                            and clean['passed'])
    return record


def verify(directory, head, criterion, revision_command, command, timeout=300, contains=None):
    require_sha(head)
    if not isinstance(criterion, str) or not criterion.strip():
        raise ValueError('Explicit criterion required')
    cwd = checked_path(directory)
    record = {'kind':'surface-command', 'expected_deployed_head':head, 'criterion':criterion,
              'surface_directory':str(cwd), 'contains':contains, 'passed':False,
              'human_authority':False, 'accepted':False}
    before = capture(revision_command, cwd, timeout)
    record['revision_before'] = before
    if not successful(before) or before['stdout'].strip() != head:
        return record
    record['run'] = capture(command, cwd, timeout)
    after = capture(revision_command, cwd, timeout)
    record['revision_after'] = after
    record['passed'] = (successful(record['run']) and successful(after) and after['stdout'].strip() == head
                        and (contains is None or contains in record['run']['stdout']))
    return record


def save_record(path, record):
    destination = checked_path(path)
    data = (json.dumps(record, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()
    with destination.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path':str(destination), 'sha256':hashlib.sha256(data).hexdigest(), 'passed':record['passed']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('review','verify'))
    parser.add_argument('--directory', required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--command-json', required=True, help='JSON argument array; no implicit shell')
    parser.add_argument('--revision-command-json', help='Surface version query returning exactly the deployed full SHA')
    parser.add_argument('--criterion')
    parser.add_argument('--contains')
    parser.add_argument('--timeout', type=float, default=300)
    parser.add_argument('--output', required=True, help='New evidence file, normally under .delivery-evidence/')
    args = parser.parse_args()
    if checked_path(args.output).exists():
        raise ValueError('Evidence file already exists; preserve previous observations')
    command = json.loads(args.command_json)
    if args.mode == 'review':
        if args.revision_command_json or args.criterion or args.contains:
            raise ValueError('Surface options apply only to verify mode')
        record = review(args.directory, args.head, command, args.timeout)
    else:
        if not args.revision_command_json or not args.criterion:
            raise ValueError('Surface verification needs an explicit revision query and criterion')
        record = verify(args.directory,args.head,args.criterion,json.loads(args.revision_command_json),command,args.timeout,args.contains)
    print(json.dumps(save_record(args.output, record)))
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        print(json.dumps({'error':str(error)}))
        raise SystemExit(2)
