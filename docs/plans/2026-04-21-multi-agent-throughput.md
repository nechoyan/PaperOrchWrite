# Multi-Agent Throughput Improvements Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Reduce repeated host-agent scanning and make PaperOrchWrite faster to resume by adding deterministic workspace-status and agent-handoff generation tools.

**Architecture:** Add one inspector script that understands the workspace state and one handoff generator that produces concise per-step brief files for parallel agents. Wire both into docs and workspace scaffolding so users can run them immediately after validation and after each major step.

**Tech Stack:** Python 3 standard library (`argparse`, `json`, `pathlib`, `textwrap`), unittest, markdown docs.

---

### Task 1: Add workspace inspection/status script

**Objective:** Give users and host agents a fast deterministic summary of what exists, what is missing, and which pipeline step is ready next.

**Files:**
- Create: `skills/paper-orchestra/scripts/workspace_status.py`
- Modify: `skills/paper-orchestra/scripts/init_workspace.py`
- Test: `tests/test_workspace_productivity.py`

**Implementation:**
1. Create `workspace_status.py` with a reusable `inspect_workspace()` function.
2. Detect presence/counts for inputs, outline, figures, refs, citation pool, drafts, refinement snapshots, final outputs, tex profile, provenance.
3. Emit either human-readable text or JSON via `--format text|json`.
4. Include recommended next actions such as `run outline`, `run plotting and lit review`, `run section writing`, `run refinement`, `compile final paper`.
5. Add `briefs/` to the scaffolded workspace tree in `init_workspace.py` so the new throughput tooling has a canonical output directory.

**Verification:**
- `python skills/paper-orchestra/scripts/workspace_status.py --workspace /tmp/ws --format json`
- `python -m unittest discover -s tests -v`

### Task 2: Add agent-handoff generator

**Objective:** Precompute compact step-specific briefs so parallel agents read only what they need instead of rescanning the entire workspace.

**Files:**
- Create: `skills/paper-orchestra/scripts/build_agent_handoffs.py`
- Test: `tests/test_workspace_productivity.py`

**Implementation:**
1. Reuse the workspace inspector from Task 1.
2. Generate `workspace/briefs/` outputs for:
   - `00-workspace-summary.md`
   - `01-outline-agent.md`
   - `02-plotting-agent.md`
   - `03-literature-review-agent.md`
   - `04-section-writing-agent.md`
   - `05-content-refinement-agent.md`
   - `handoff_manifest.json`
3. Each brief should list exact paths, available prerequisites, missing prerequisites, and a deterministic checklist for the next agent.
4. Keep content concise and path-oriented so host agents can load the brief plus the relevant skill file.

**Verification:**
- `python skills/paper-orchestra/scripts/build_agent_handoffs.py --workspace /tmp/ws`
- Assert the briefs exist and mention the expected files.

### Task 3: Update docs and orchestrator guidance

**Objective:** Teach users to use the new status + handoff tooling for faster multi-agent runs.

**Files:**
- Modify: `README.md`
- Modify: `skills/paper-orchestra/SKILL.md`
- Modify: `skills/paper-orchestra/references/io-contract.md`
- Modify: `examples/minimal/README.md`

**Implementation:**
1. Document the new `workspace_status.py` and `build_agent_handoffs.py` scripts.
2. In the orchestrator skill, recommend generating status + handoffs after validation and refreshing them after each major step.
3. In the I/O contract, add `briefs/` to the workspace layout.
4. In the example docs, add a quick command sequence showing the new throughput workflow.

**Verification:**
- Read the updated docs and confirm the commands and paths are consistent.

### Task 4: Final validation and ship

**Objective:** Verify the second batch is ready to commit and push.

**Verification:**
- `bash -n setup.sh`
- `python -m unittest discover -s tests -v`
- `python -m compileall -q skills tests`
- `git diff --check`
