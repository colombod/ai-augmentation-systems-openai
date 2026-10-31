#!/usr/bin/env python3
"""Disposable test observer; raw capture stays local and is never printed."""
import importlib.util
import json
from pathlib import Path
import sys


def main():
    service, capture, *arguments = sys.argv[1:]
    spec = importlib.util.spec_from_file_location('observed_publication', service)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = module.mcp
    # Inventory and thread runtimes may start separate processes. The caller
    # supplies a fresh private run directory; append preserves both observations.
    with Path(capture).open('a', encoding='utf-8') as output:
        def observed(store, request):
            if isinstance(request, dict) and request.get('method') == 'tools/call':
                params = request.get('params', {})
                output.write(json.dumps({'name':params.get('name'),
                    'arguments':params.get('arguments')}, sort_keys=True) + '\n')
                output.flush()
            return original(store, request)
        module.mcp = observed
        sys.argv = [service, *arguments]
        return module.main()


if __name__ == '__main__':
    raise SystemExit(main())
