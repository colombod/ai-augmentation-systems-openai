"""Validate catalogue boundaries and portable manifests against a vendored schema."""
import json
import re
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / 'schemas/agent-plugins/1.0.0/plugin.schema.json'
SCHEMA = json.loads(SCHEMA_PATH.read_text())
Draft202012Validator.check_schema(SCHEMA)
MANIFEST_VALIDATOR = Draft202012Validator(SCHEMA)


def validate_manifest(data):
    """Use the complete published schema, including nested metadata constraints."""
    MANIFEST_VALIDATOR.validate(data)


def validate(root=ROOT):
    root = root.resolve()
    catalog = json.loads((root / '.agents/plugins/marketplace.json').read_text())
    assert catalog.get('name'), 'Marketplace needs a name'
    assert catalog.get('interface', {}).get('displayName'), 'Marketplace needs a display name'
    assert isinstance(catalog.get('plugins'), list), 'plugins must be an array'
    names = set()
    for entry in catalog['plugins']:
        name = entry['name']
        assert name not in names, f'Duplicate plugin: {name}'
        names.add(name)
        source = entry['source']
        assert source['source'] == 'local', 'This repository publishes self-contained local packages'
        relative = source['path']
        assert relative.startswith('./plugins/'), 'Published plugins must live under ./plugins/'
        package = (root / relative).resolve()
        assert package.is_relative_to(root / 'plugins'), 'Plugin path escapes plugins/'
        assert package.is_dir(), f'Missing package: {relative}'
        manifest = package / 'plugin.json'
        if not manifest.exists():
            manifest = package / '.codex-plugin/plugin.json'
        data = json.loads(manifest.read_text())
        if manifest.parent == package:
            validate_manifest(data)
        assert data['name'] == name, 'Catalogue and package names differ'
        assert re.fullmatch(r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?', data['version']), 'Use semver'
        assert data.get('description'), 'Package needs a description'
        assert entry.get('category'), 'Catalogue entry needs category'
        assert entry['policy']['installation'] in {'AVAILABLE', 'INSTALLED_BY_DEFAULT', 'NOT_AVAILABLE'}
        assert entry['policy']['authentication'] in {'ON_INSTALL', 'ON_USE'}
    return len(names)


if __name__ == '__main__':
    count = validate()
    print(f'Marketplace valid: {count} published plugin(s)')
