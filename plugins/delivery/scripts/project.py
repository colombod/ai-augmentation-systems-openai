#!/usr/bin/env python3
"""Non-destructive planning workspace initialization and read-only inventory."""
import argparse
import json
import os
from pathlib import Path
import re
import sys


class ProjectError(ValueError):
    pass


def checked_path(path):
    """Reject symlink components rather than reading/writing through them."""
    path = Path(os.path.abspath(os.path.expanduser(str(path))))
    for component in (*reversed(path.parents), path):
        if component.is_symlink():
            raise ProjectError(f'Symlink paths are not supported: {component}')
    return path


def delivery_root(project):
    project = checked_path(project)
    if not project.is_dir():
        raise ProjectError(f'Project directory does not exist: {project}')
    # A child component must reuse the nearest existing ancestor workspace.
    for ancestor in (project, *project.parents):
        candidate = checked_path(ancestor / '.delivery')
        if candidate.exists():
            if not candidate.is_dir():
                raise ProjectError(f'Not a directory: {candidate}')
            return candidate
    # Avoid creating a shadow workspace beside one in a nested component.
    for base, dirs, _ in os.walk(project, followlinks=False):
        dirs[:] = [d for d in dirs if d not in {'.git', '.beads', 'node_modules', '.venv'}]
        if '.delivery' in dirs:
            raise ProjectError(f'Nested .delivery found at {Path(base) / ".delivery"}; select that component explicitly')
    return project / '.delivery'


def validate_tree(root):
    if not root.exists():
        return
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            checked_path(Path(base) / name)


def initialize(project, initiative):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', initiative):
        raise ProjectError('Initiative must be lowercase kebab-case')
    root = delivery_root(project)
    validate_tree(root)
    target = checked_path(root / 'initiatives' / initiative)
    # Preflight all known paths before creating anything. Existing content wins.
    paths = [root, root / 'initiatives', target] + [root / d for d in
             ('personas', 'interviews', 'simulations', 'decisions', 'stories', 'reviews', 'sprints')]
    for path in paths:
        checked_path(path)
        if path.exists() and not path.is_dir():
            raise ProjectError(f'Not a directory: {path}')
    created = []
    for path in paths:
        if not path.exists():
            try:
                path.mkdir()
            except FileExistsError:
                if not path.is_dir() or path.is_symlink():
                    raise ProjectError(f'Path changed during initialization: {path}')
            else:
                created.append(str(path))
    return {'delivery_root': str(root), 'initiative': initiative, 'created': created,
            'capability': 'planning-preview', 'artifacts_overwritten': 0}


def inventory(project):
    root = delivery_root(project)
    validate_tree(root)
    files = sorted(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()) if root.exists() else []
    initiatives = sorted(p.name for p in (root / 'initiatives').iterdir() if p.is_dir()) if (root / 'initiatives').is_dir() else []
    return {'delivery_root': str(root), 'exists': root.exists(), 'initiatives': initiatives,
            'files': files, 'capability': 'planning-preview',
            'verification': 'inventory-only; read artifacts and evidence before assessing readiness',
            'team_runtime': 'not-inspected; use runtime.py status',
            'judge_provider': 'not-inspected; explicitly selected in runtime configuration'}


def prose_words(path):
    """Count Markdown prose excluding frontmatter, fenced code and pipe tables."""
    lines = Path(path).read_text().splitlines()
    # Upstream templates may put a budget comment before frontmatter.
    text = re.sub(r'<!--.*?-->', '', '\n'.join(lines), flags=re.S).lstrip()
    text = re.sub(r'^---\n.*?\n---(?:\n|$)', '', text, count=1, flags=re.S)
    words = []
    fence = None
    for line in text.splitlines():
        match = re.match(r'^\s{0,3}(`{3,}|~{3,})', line)
        if match:
            marker = match[1]
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence) and not line.strip().strip(marker[0]).strip():
                fence = None
            continue
        if fence or line.lstrip().startswith('|'):
            continue
        words.extend(re.findall(r"\b[\w]+(?:['’\-][\w]+)*\b", line))
    return len(words)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('init', 'status'):
        command = sub.add_parser(name)
        command.add_argument('--project', required=True, help='Explicit local project/component directory')
        if name == 'init':
            command.add_argument('--initiative', required=True)
    sub.add_parser('words').add_argument('file')
    args = parser.parse_args()
    try:
        if args.command == 'init':
            result = initialize(args.project, args.initiative)
        elif args.command == 'status':
            result = inventory(args.project)
        else:
            result = {'file': args.file, 'prose_words': prose_words(args.file)}
        print(json.dumps(result, indent=2))
        return 0
    except (ProjectError, OSError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
