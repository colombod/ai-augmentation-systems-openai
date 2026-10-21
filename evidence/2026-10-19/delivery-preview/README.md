# Delivery preview checks

`results.json` records the local planning preview checks. `package-sha256.json`
identifies the tested package files; caches are excluded. These checks used the
working tree, not a published commit.

The isolated installation probe creates a temporary marketplace, project and
Codex home, installs the copied package, requests `skills/list` over app-server
stdio and invokes the installed Python helper. It makes no model request and
uses no hook-trust bypass. Temporary personal configuration and credentials are
not copied. The output records only this package's skills.

Reproduce from the repository root:

```sh
python3 scripts/validate_marketplace.py
python3 -m unittest discover -s tests/delivery -v
python3 scripts/probe_delivery_install.py
```

All 15 skills also passed the installed Codex `skill-creator` skill's
`scripts/quick_validate.py`, using PyYAML in a temporary environment. Imported
source hashes were compared against checkout
`df0c0a5b0dba1449b6cdfef421bfe1ebc4d658c0`; its tracked working tree remained clean.

During development, the first install probe used a substring path filter. Its
temporary directory also contained the word `delivery`, so it incorrectly counted
five built-in skills as package skills and failed the expected-set assertion.
The probe now checks the installed package's actual manifest identity and cache
location. This was a probe defect, not a successful workflow test. The first
skill-validator invocation also failed because system Python lacked PyYAML;
running it in the temporary dependency environment passed all skills.

No real-model workflow, desktop UI, ChatGPT, autonomous role, hook enforcement or
judge-provider acceptance is established here. The source review was performed
in one session, not by independent reviewers.
