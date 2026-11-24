# Python Git Hooks Blueprint: pre-commit & Lefthook

> **Snapshot: November 2026.** Versions referenced: `pre-commit` 4.6.x, `lefthook` 2.x (published on PyPI), `ruff` 0.16.x, `pre-commit-hooks` v6.0.0.
> After copying any config, run `uv lock --upgrade` and `pre-commit autoupdate` so nothing starts out stale.

## Contents

1. [Executive summary](#1-executive-summary)
2. [The dependency model](#2-the-dependency-model)
3. [Shared foundation (both options)](#3-shared-foundation-both-options)
4. [Option A: pre-commit](#4-option-a-pre-commit)
5. [Option B: Lefthook](#5-option-b-lefthook)
6. [Choosing between them](#6-choosing-between-them)
7. [Switching from one to the other](#7-switching-from-one-to-the-other)
8. [CI parity](#8-ci-parity)
9. [Maintenance & governance](#9-maintenance--governance)
10. [Anti-patterns & troubleshooting](#10-anti-patterns--troubleshooting)
11. [Rollout checklist](#11-rollout-checklist)

---

## 1. Executive summary

| | **pre-commit** | **Lefthook** |
|---|---|---|
| Written in | Python | Go (single binary) |
| Config file | `.pre-commit-config.yaml` | `lefthook.yml` |
| Philosophy | Package manager for hooks: clones hook repos and builds isolated envs | Task runner for git events: runs commands you already have |
| Hook tools come from | `repo` + `rev` in the config | Your project environment (`uv run`, `uv.lock`) |
| Parallel execution | Limited (per-hook `require_serial`) | First-class (`parallel`, `group`) |
| Shared hook ecosystem | Huge (pre-commit.com/hooks) | None; you write commands |
| Best for | Python-centric repos, big community hook library | Polyglot monorepos, speed, single source of truth for versions |

**Rules of thumb**

- Pick **one** runner per repo. Both write to `.git/hooks/*`, so running both causes duplicate or conflicting hooks.
- Hooks are a **fast-feedback layer**. CI is the **authority**. Never rely on hooks alone.
- Tool versions should have **one source of truth**. In a uv project that is `uv.lock`.

---

## 2. The dependency model

A professional setup has three layers. Most confusion comes from mixing them up.

```
Layer 0  Toolchain      Python, uv, git                      (installed on the machine / CI image)
Layer 1  Hook runner    pre-commit  OR  lefthook             (dev dependency, in uv.lock)
Layer 2  Hook tools     ruff, mypy, pytest, commitizen ...   (dev dependencies, in uv.lock)
```

How a commit flows:

```
git commit
   │
   ▼
.git/hooks/pre-commit        <- shim written by `pre-commit install` / `lefthook install`
   │
   ├── pre-commit (Python) ──▶ reads .pre-commit-config.yaml
   │                           ├── remote repos: cloned + built into ~/.cache/pre-commit (isolated envs)
   │                           └── local hooks:  run in YOUR env via `uv run`
   │
   └── lefthook (Go) ────────▶ reads lefthook.yml
                               └── every job runs in YOUR env via `uv run`
```

### Where does each dependency live?

| Concern | pre-commit | Lefthook |
|---|---|---|
| Install the runner | `pre-commit` in a dev dependency group | `lefthook` in a dev dependency group (PyPI package), or `brew` / `npm` / `go install` |
| Source of hook tools | Remote repos pinned by `rev:`, or `repo: local` | Always your project env |
| Version pin location | `.pre-commit-config.yaml` (`rev:`) **and** `uv.lock` if the tool is also a dev dependency | `uv.lock` only |
| Version drift risk | **Real**: `ruff` in the config can differ from `ruff` in `pyproject.toml` | None |
| Type checkers that need project deps (mypy, pyright) | Use a `repo: local` + `language: system` hook; avoid `additional_dependencies` | Native, no extra setup |
| Disk footprint | Isolated env per hook repo + rev in `~/.cache/pre-commit` | Just the binary |
| Works offline | After first run (cache) | Yes |

**Takeaway:** pre-commit gives you a rich ecosystem but a *second* dependency graph to maintain. Lefthook has no second graph, but you wire each tool yourself.

---

## 3. Shared foundation (both options)

### 3.1 Repository layout

```
my-service/
├── .editorconfig
├── .gitignore                  # include lefthook-local.yml
├── .pre-commit-config.yaml     # Option A only
├── lefthook.yml                # Option B only
├── Makefile                    # bootstrap / check targets (shared by hooks and CI)
├── pyproject.toml
├── uv.lock
├── src/
│   └── my_service/
└── tests/
```

### 3.2 `pyproject.toml`: dependency groups (PEP 735)

Split tools into small groups so CI jobs can install only what they need, while `dev` stays a one-command install for humans.

```toml
[project]
name = "my-service"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[dependency-groups]
# Humans run `uv sync` and get everything in `dev`.
dev = [
  { include-group = "hooks" },
  { include-group = "lint" },
  { include-group = "typecheck" },
  { include-group = "test" },
  { include-group = "commit" },
]
hooks = [
  "pre-commit>=4.5",     # Option A
  # "lefthook>=2.0",     # Option B (use this INSTEAD of pre-commit)
]
lint = ["ruff>=0.15"]
typecheck = ["mypy>=1.13"]
test = ["pytest>=8.3", "pytest-cov>=6.0", "pytest-xdist>=3.6"]
commit = ["commitizen>=4.0"]
```

> Add tools with `uv add --group lint ruff`, `uv add --group test pytest`, etc. `uv sync` installs the `dev` group by default.

### 3.3 `pyproject.toml`: tool configuration

Keep rules in `pyproject.toml` so hooks, CI, and editors all read the same thing.

```toml
[tool.ruff]
line-length = 100
target-version = "py312"
src = ["src", "tests"]

[tool.ruff.lint]
select = [
  "E", "W",   # pycodestyle
  "F",        # pyflakes
  "I",        # isort
  "B",        # bugbear
  "UP",       # pyupgrade
  "SIM",      # simplify
  "C4",       # comprehensions
  "PT",       # pytest style
  "S",        # bandit (security)
  "RUF",      # ruff-specific
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]   # allow assert in tests

[tool.ruff.format]
docstring-code-format = true

[tool.mypy]
python_version = "3.12"
strict = true
files = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers"
markers = ["slow: long-running tests, excluded from pre-push"]

[tool.commitizen]
name = "cz_conventional_commits"
```

### 3.4 Hook policy: what runs when

| Stage | Time budget | Checks | May modify files? |
|---|---|---|---|
| `pre-commit` | < 5 s | whitespace/EOF, merge-conflict markers, large files, private keys, `ruff check --fix`, `ruff format`, `uv.lock` in sync | Yes (auto-fix) |
| `commit-msg` | < 1 s | Conventional Commits format | No |
| `pre-push` | < 60 s | `mypy`, unit tests (`-m "not slow"`) | No |
| **CI** | full | everything on `--all-files`, full test suite, coverage, security scans | No |

> If a check takes more than a few seconds, it does **not** belong in `pre-commit`. Move it to `pre-push` or CI. Slow hooks are the #1 reason developers start using `--no-verify`.

### 3.5 `Makefile`: one entry point for hooks and CI

```makefile
.PHONY: bootstrap lint format typecheck test check

bootstrap:                 ## First-time setup for a fresh clone
	uv sync --locked
	uv run pre-commit install        # Option A
	# uv run lefthook install        # Option B

lint:
	uv run ruff check .

format:
	uv run ruff format --check .

typecheck:
	uv run mypy

test:
	uv run pytest --cov

check: lint format typecheck test    ## What CI runs
```

### 3.6 `.editorconfig`

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.py]
indent_style = space
indent_size = 4

[*.{yml,yaml,toml,json}]
indent_style = space
indent_size = 2

[Makefile]
indent_style = tab
```

---

## 4. Option A: pre-commit

### 4.1 Install

```bash
uv sync --locked
uv run pre-commit install        # installs all types in default_install_hook_types
```

### 4.2 `.pre-commit-config.yaml`

```yaml
minimum_pre_commit_version: "4.0.0"

# Install shims for all three stages with a single `pre-commit install`.
default_install_hook_types: [pre-commit, commit-msg, pre-push]

default_language_version:
  python: python3.12

fail_fast: false

repos:
  # ── Generic hygiene (remote repo, pinned by tag) ──────────────────────────
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-merge-conflict
      - id: check-added-large-files
        args: [--maxkb=500]
      - id: check-yaml
      - id: check-toml
      - id: detect-private-key
      - id: debug-statements

  # ── Lint + format (Ruff) ──────────────────────────────────────────────────
  # NOTE: keep this rev in sync with the ruff version in uv.lock,
  # or use the "local" variant in section 4.4 to avoid drift entirely.
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.16.4
    hooks:
      - id: ruff-check
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  # ── Project-aware hooks (run in YOUR env via uv) ──────────────────────────
  - repo: local
    hooks:
      - id: uv-lock-check
        name: uv.lock is in sync with pyproject.toml
        entry: uv lock --check
        language: system
        files: ^(pyproject\.toml|uv\.lock)$
        pass_filenames: false

      - id: mypy
        name: mypy
        entry: uv run --frozen mypy
        language: system
        types: [python]
        pass_filenames: false     # type checking needs whole-project context
        require_serial: true
        stages: [pre-push]

      - id: pytest-unit
        name: pytest (unit, fast)
        entry: uv run --frozen pytest -m "not slow" -x -q
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-push]

      - id: conventional-commit
        name: conventional commit message
        entry: uv run --frozen cz check --commit-msg-file
        language: system
        stages: [commit-msg]

# Optional: only if you use the pre-commit.ci service.
# It cannot run `language: system` hooks that need uv, so skip them there.
# ci:
#   autofix_commit_msg: "style: auto-fix by pre-commit.ci"
#   autoupdate_schedule: monthly
#   skip: [uv-lock-check, mypy, pytest-unit, conventional-commit]
```

### 4.3 Daily commands

```bash
uv run pre-commit run --all-files                          # run everything on the whole repo
uv run pre-commit run ruff-check --files src/app/main.py   # one hook, specific files
uv run pre-commit run --hook-stage pre-push --all-files    # simulate the pre-push stage
uv run pre-commit autoupdate --freeze                      # bump revs and pin to commit SHAs

SKIP=mypy git commit -m "wip: ..."                         # skip one hook, one commit
git commit --no-verify                                     # emergency only; CI will still catch it
```

### 4.4 Removing version drift: Ruff as a local hook

If you want `uv.lock` to be the single source of truth, replace the `ruff-pre-commit` block with:

```yaml
  - repo: local
    hooks:
      - id: ruff-check
        name: ruff check
        entry: uv run --frozen ruff check --fix --exit-non-zero-on-fix
        language: system
        types_or: [python, pyi]
      - id: ruff-format
        name: ruff format
        entry: uv run --frozen ruff format
        language: system
        types_or: [python, pyi]
```

Trade-off: you lose pre-commit's isolated, cached tool envs, and the hook now requires `uv` and a synced environment on every machine (which your `bootstrap` target already guarantees).

### 4.5 pre-commit-specific dependency notes

- Hook envs for remote repos live in `~/.cache/pre-commit`. Cache that directory in CI, keyed on `hashFiles('.pre-commit-config.yaml')`.
- Avoid `additional_dependencies` for mypy/pyright. Mirroring your project's dependency graph there inevitably drifts. Use a local hook instead (as above).
- Use the current stage names (`pre-commit`, `pre-push`, `pre-merge-commit`). The old names (`commit`, `push`, `merge-commit`) are deprecated since pre-commit 4.0; `pre-commit migrate-config` fixes them.
- `pre-commit autoupdate --freeze` pins to SHAs, which is better supply-chain hygiene than mutable tags.

---

## 5. Option B: Lefthook

### 5.1 Install

```bash
# Put lefthook in uv.lock so every dev and CI run uses the same version
uv add --group hooks lefthook
uv sync --locked
uv run lefthook install
```

Alternatives: `brew install lefthook`, `npm i -D lefthook`, or `go install`. The PyPI route is the best fit for a Python repo because the version is locked like every other dev tool.

> Lefthook 2.x notes: `exclude` accepts **globs only** (regexp support was dropped), the deprecated `skip_output` option is gone (use `output`), and Windows hooks run through `sh`.

### 5.2 `lefthook.yml`

Jobs run **in the order listed** unless you opt into parallelism. Fixers must stay sequential because they mutate files.

```yaml
# yaml-language-server: $schema=https://json.schemastore.org/lefthook.json
min_version: 2.0.0

output:
  - failure
  - summary

pre-commit:
  jobs:
    # Fixers: sequential, auto-restage what they changed
    - name: ruff-fix
      glob: "*.{py,pyi}"
      run: uv run --frozen ruff check --fix {staged_files}
      stage_fixed: true

    - name: ruff-format
      glob: "*.{py,pyi}"
      run: uv run --frozen ruff format {staged_files}
      stage_fixed: true

    # Checkers: read-only, safe to run in parallel
    - name: checks
      group:
        parallel: true
        jobs:
          - name: uv-lock-check
            glob: "{pyproject.toml,uv.lock}"
            run: uv lock --check

commit-msg:
  jobs:
    - name: conventional-commit
      run: uv run --frozen cz check --commit-msg-file {1}

pre-push:
  parallel: true
  jobs:
    - name: type-check
      glob: "*.{py,pyi}"
      run: uv run --frozen mypy        # whole project, not {staged_files}

    - name: unit-tests
      run: uv run --frozen pytest -m "not slow" -x -q
```

Why `--exit-non-zero-on-fix` is **not** used here: with `stage_fixed: true`, Lefthook re-stages the fixed files and the commit proceeds. Remaining unfixable lint errors still return a non-zero exit code and block the commit.

Lefthook ships no hook library, so basic hygiene (trailing whitespace, final newline) is handled by `.editorconfig` plus `ruff format`. Add explicit jobs for anything else you need (large-file checks, secret scanning, etc.).

### 5.3 Personal overrides: `lefthook-local.yml` (git-ignored)

```yaml
# lefthook-local.yml: never commit this file
pre-push:
  jobs:
    - name: unit-tests
      skip: true          # I run tests from my IDE
```

```gitignore
# .gitignore
lefthook-local.yml
```

### 5.4 Daily commands

```bash
uv run lefthook run pre-commit --all-files     # run a hook group on the whole repo
uv run lefthook run pre-push                   # simulate pre-push

LEFTHOOK_EXCLUDE=type-check git push           # skip one job
LEFTHOOK=0 git commit -m "wip: ..."            # disable Lefthook entirely (emergency only)
```

---

## 6. Choosing between them

| Situation | Recommendation |
|---|---|
| Python-only repo, want the largest ready-made hook library | **pre-commit** |
| Python + JS/Go/Rust monorepo, one hook runner for all | **Lefthook** |
| You want `uv.lock` to be the only version source | **Lefthook**, or pre-commit with all-local hooks |
| Contributors without a working Python env (docs/frontend people) | **Lefthook** (static binary) |
| You use pre-commit.ci for auto-fix PRs | **pre-commit** |
| Hooks are slow and you want parallel execution | **Lefthook** |
| Existing org-wide pre-commit conventions and shared hook repos | **pre-commit** |

Default recommendation for a new Python service with a uv lockfile: **Lefthook + `uv run`**, because it removes the second dependency graph. Choose pre-commit when ecosystem breadth or pre-commit.ci matters more.

---

## 7. Switching from one to the other

```bash
# pre-commit  ->  Lefthook
uv run pre-commit uninstall -t pre-commit -t commit-msg -t pre-push
uv remove --group hooks pre-commit
uv add --group hooks lefthook
uv run lefthook install
git rm .pre-commit-config.yaml

# Lefthook  ->  pre-commit
uv run lefthook uninstall
uv remove --group hooks lefthook
uv add --group hooks pre-commit
uv run pre-commit install
git rm lefthook.yml
```

If `git config core.hooksPath` is set, both tools may refuse to install or install somewhere unexpected. Unset it (`git config --unset core.hooksPath`) or point everything at the same directory deliberately.

---

## 8. CI parity

CI must not depend on developers having installed hooks. Run the checks explicitly.

```yaml
# .github/workflows/quality.yml
name: quality
on:
  push:
    branches: [main]
  pull_request:

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      # Bump these actions to their current majors (or pin by SHA) when you adopt this file.
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true

      - run: uv sync --locked

      # ── Option A: pre-commit ──────────────────────────────────────────────
      - uses: actions/cache@v4
        with:
          path: ~/.cache/pre-commit
          key: pre-commit-${{ hashFiles('.pre-commit-config.yaml') }}
      - run: uv run pre-commit run --all-files --show-diff-on-failure

      # ── Option B: Lefthook ────────────────────────────────────────────────
      # - run: uv run lefthook run pre-commit --all-files
      # - run: git diff --exit-code HEAD   # fail if a fixer changed anything
      #   (compare against HEAD because stage_fixed stages the changes)

      # ── Heavy checks run here, not in hooks ───────────────────────────────
      - run: uv run mypy
      - run: uv run pytest --cov
```

**Parity rule:** the commands in CI and in hooks must come from the same place (`pyproject.toml` config + `make check`). If a check only exists in one of them, it will eventually disagree with the other.

---

## 9. Maintenance & governance

- **Updating tools**
  - `uv lock --upgrade-package ruff` for the locked tools.
  - `pre-commit autoupdate --freeze` for remote hook repos (Option A).
  - Automate both with Renovate or Dependabot (both support `uv`; Renovate also has a `pre-commit` manager).
- **Bypass policy:** `--no-verify` is for emergencies. CI still blocks the merge, so a bypassed hook only delays the failure.
- **Onboarding:** a new clone should need exactly one command: `make bootstrap`. Hooks are never installed automatically by git, so document this in `README.md`.
- **Hook budget:** review hook runtime quarterly. If `pre-commit` takes more than ~5 seconds on a typical change, move something to `pre-push` or CI.
- **Ownership:** treat the hook config like production code: code review, changelog entries for rule changes, and no silent rule loosening.

---

## 10. Anti-patterns & troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| Hooks run twice | Both pre-commit and Lefthook installed | Uninstall one (section 7) |
| Hook is "not running" on a fresh clone | Shim was never installed | `make bootstrap` |
| Developers always use `--no-verify` | Hooks too slow or flaky | Move slow checks to `pre-push`/CI; fix flaky hooks first |
| mypy gives different results locally vs CI | mypy runs in an isolated pre-commit env without project deps | Use a local `uv run mypy` hook |
| Ruff output differs between hook and CI | `rev:` in config differs from `uv.lock` | Sync versions, or use local Ruff hooks (section 4.4) |
| Lefthook fixers corrupt files | `parallel: true` on jobs that edit the same files | Keep fixers sequential; parallelize read-only checks only |
| mypy checks only the staged files and misses errors | `pass_filenames` left on / `{staged_files}` used | Run mypy on the whole project |
| `core.hooksPath` errors on install | A global/local hooks path is set | Unset it or manage hooks from that path deliberately |
| Hook fails on Windows only (Lefthook 2.x) | Commands now run via `sh` | Use `sh`-compatible syntax or Git Bash |
| CI is green but the hook auto-fixed files locally | Fixer ran locally, change never committed | Run `git add -u` and re-commit, or let `stage_fixed` handle it (Lefthook) |

---

## 11. Rollout checklist

- [ ] Decide on **one** runner (pre-commit or Lefthook) and document why
- [ ] Tools in `[dependency-groups]` and locked in `uv.lock`
- [ ] Ruff / mypy / pytest configured in `pyproject.toml`
- [ ] Hook config committed (`.pre-commit-config.yaml` **or** `lefthook.yml`)
- [ ] `pre-commit` stage under ~5 s; heavy checks on `pre-push`
- [ ] `commit-msg` hook enforces Conventional Commits (if used)
- [ ] `make bootstrap` documented in `README.md`
- [ ] CI runs the same checks on `--all-files` plus mypy and the full test suite
- [ ] `lefthook-local.yml` in `.gitignore` (Option B)
- [ ] Automated updates configured (Renovate/Dependabot or scheduled `autoupdate`)
- [ ] Bypass policy written down (`--no-verify` only for emergencies)
