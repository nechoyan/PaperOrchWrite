# PaperOrchWrite Framework Hardening Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Make the fork safer to install and more dependable for daily multi-agent paper-writing workflows.

**Architecture:** Focus on the highest-leverage improvements from the repo review: harden installation/setup, add deterministic regression tests plus CI, and remove misleading documentation drift. Keep the host-agent-first architecture intact; improve reliability around it.

**Tech Stack:** Bash, Python 3 standard library (`unittest`, `subprocess`, `tempfile`), GitHub Actions.

---

### Task 1: Repair setup assets and generated config

**Objective:** Make setup reproducible and remove the broken config output path.

**Files:**
- Create: `.env.example`
- Modify: `setup.sh`

**Implementation:**
1. Add a real `.env.example` with commented optional integrations.
2. Fix `setup.sh` so it writes usable values to `~/.paperorchestra/config`.
3. Remove claims about bootstrap files that are not shipped.
4. Make the summary explicitly describe optional integrations and real next steps.

**Verification:**
- `bash -n setup.sh`
- Run setup non-interactively in a temporary HOME and assert the config file is created with expected keys.

### Task 2: Add regression tests for deterministic scripts and setup flow

**Objective:** Provide fast checks for the parts users will rely on most during repeated paper-writing runs.

**Files:**
- Create: `tests/test_setup.py`
- Create: `tests/test_workspace_scripts.py`

**Implementation:**
1. Add a setup test that runs `setup.sh` with blank stdin inside a temp HOME.
2. Add workspace smoke tests covering `init_workspace.py`, `validate_inputs.py`, and `extract_metrics.py` using `examples/minimal/inputs`.
3. Keep the tests self-contained and runnable with `python -m unittest discover -s tests -v`.

**Verification:**
- `python -m unittest discover -s tests -v`

### Task 3: Add CI and align docs with reality

**Objective:** Prevent future drift and make the repo clearer for real-world use.

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/coding-agent-integration.md`
- Modify: `skills/paper-orchestra/references/host-integration.md`

**Implementation:**
1. Add a small CI workflow that installs requirements and runs the unittest suite.
2. Fix the README/doc wording around skill counts and optional integrations.
3. Update integration docs to point to the automated helpers instead of stale manual snippets.
4. Clarify that the repo ships no required LLM SDKs, while optional API-backed helpers remain available.

**Verification:**
- `python -m unittest discover -s tests -v`
- Inspect updated docs for consistency with repository contents.

### Task 4: Final validation

**Objective:** Verify the fork is in a cleaner state for user adoption.

**Files:**
- Modify: none

**Verification:**
- `python -m compileall -q skills`
- `bash -n setup.sh`
- `python -m unittest discover -s tests -v`
- `git diff --stat`
