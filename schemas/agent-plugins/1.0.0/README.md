# Vendored manifest schema

`plugin.schema.json` was retrieved on 20 October 2026 from
https://agent-plugins.org/schemas/1.0.0/plugin.schema.json without modification.
Its declared schema dialect is JSON Schema 2020-12. Validation uses `jsonschema`
and does not fetch a different schema during CI or local tests. Package helpers
do not depend on this development dependency.
