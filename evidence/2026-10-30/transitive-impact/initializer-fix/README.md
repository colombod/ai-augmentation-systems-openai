# Possible package initializer reach from curated anchors

Source SHA: `30159c0ac4c2617c9672bc8ad84b9185ea66be6f`.
Previous source: `d1d9176d99c67a0de84234d00ebe02122a90b2ea`.
Branch `delivery/transitive-impact`; still unreleased candidate preview.10.
No other branch, PR, merge, host permission or runtime setup is changed.

Independent source review found a real gap: a Python package module anchor with
no explicit imports did not reach its enclosing initializer. An initializer-only
dependency could consequently appear exclusive to another feature in a retirement
proposal, despite being shared in a possible package-import context.

The focused reproduction initially failed with `KeyError: 'shared.py'`: the
expected shared dependency was absent. Its raw failure is preserved in
`checks/initial-failing-reproduction.txt`. That initial equivalent fixture used a
no-import package module and another explicit importer. The final regression uses
the reviewer's precise package layout:

```
pkg/__init__.py: import shared
pkg/a.py:        import shared
pkg/b.py:        pass
shared.py:       pass
```

With feature A anchored at `pkg/a.py` and B at `pkg/b.py`, B now reaches:

```
pkg/b.py --possible package-import context, line:null--> pkg/__init__.py
pkg/__init__.py:1 --python-import--> shared.py
```

Retiring A preserves shared.py for B; shared.py is excluded from derived exclusive
candidates. The canonical record remains byte-identical. Same-size/mtime-preserved
working edits hidden with assume-unchanged on both initializer and shared dependency
are detected as stale through raw bytes, with the original snapshot commit retained
and public CLI exit 1. Missing/unsupported initializer contexts stay explicitly
unknown; no namespace traversal or symlink execution is invented.

The change seeds possible enclosing initializer reach **per feature**, without
changing the global explicit-import resolver or default direct-impact results.
Implicit edges use `kind: python-package-initializer`, `line: null`: they have no
explicit source import location. They describe a possible package import, not
certain execution; standalone script invocation may not run those initializers.
Coverage includes this qualification and `anchor_package_context_unknown`.
Retirement still only proposes candidates; unknown consumers require review and
an explicit owner decision. No source/deletion or readiness authority is granted.

Actual verification:

- **14 graph regressions passed**; all **154 Python tests passed**, including the
  existing direct behavior, record/history, authority and greenfield cases.
- **22 Node tests**, marketplace validation and final `git diff --check` passed.
- Independent read-only reviewer inspected this bounded correction, found no
  concrete blocker, independently ran **32 product tests** and all **154 Python
  tests**, catalogue validation and diff checks successfully.
- Isolated CLI 0.163.0 installation discovers all **16 skills** and installed
  greenfield record/handoff/optional-unavailability checks pass; zero model calls.
- At exact source SHA above, the existing **eight public-command actual-repository
  proof** still passes: operator_capture.py has zero direct matches and two
  dependency matches, with runtime.py:657 and delivery_gates.py:22 evidence; shared
  retirement preservation and the code-free illustrative greenfield case pass.
  Raw outputs/exits/records are retained under `real-repository/`.

These are source, process and static dependency checks. They do not establish
model-driven quality, actual token/time benefit, deployed features, native host,
desktop/ChatGPT, authenticated dot access or outside-user adoption. The separate
model evaluation gate remains pending. No PR publication retry or merge attempted.
