#!/usr/bin/env python3
"""
build_agent_handoffs.py — Generate compact per-step briefs for a workspace.

The goal is to help multi-agent hosts avoid rescanning the full workspace on
resume. Each generated markdown file points an agent at the exact files it needs
for one pipeline step.

Usage:
    python build_agent_handoffs.py --workspace /path/to/workspace/
"""
import argparse
import json
import os
import pathlib
import textwrap

from workspace_status import inspect_workspace


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _write(path: pathlib.Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n")


def _render_summary(status: dict) -> str:
    actions = []
    for item in status["recommended_actions"]:
        actions.append(f"- **{item['label']}** — {item['reason']}\n  - `{item['command']}`")
    actions_block = "\n".join(actions)
    artifacts = status["artifacts"]
    return textwrap.dedent(
        f"""
        # Workspace Summary

        **Workspace:** `{status['workspace']}`

        ## Snapshot

        - outline.json: {_yes_no(artifacts['outline']['exists'])}
        - generated figures: {artifacts['generated_figures']['count']}
        - captions.json: {_yes_no(artifacts['generated_figures']['captions_exists'])}
        - refs.bib: {_yes_no(artifacts['refs_bib']['exists'])}
        - citation_pool papers: {artifacts['citation_pool']['paper_count']}
        - drafts/intro_relwork.tex: {_yes_no(artifacts['drafts']['intro_relwork_exists'])}
        - drafts/paper.tex: {_yes_no(artifacts['drafts']['paper_exists'])}
        - refinement iterations: {', '.join(artifacts['refinement']['iterations']) or 'none'}
        - final/paper.tex: {_yes_no(artifacts['final']['paper_tex_exists'])}
        - final/paper.pdf: {_yes_no(artifacts['final']['paper_pdf_exists'])}
        - tex_profile.json: {_yes_no(artifacts['tex_profile']['exists'])}

        ## Recommended next actions

        {actions_block}
        """
    ).strip()


def _render_step_brief(title: str, status: dict, needed: list[str], optional: list[str], checklist: list[str], missing: list[str]) -> str:
    needed_lines = "\n".join(f"- `{line}`" for line in needed) or "- none"
    optional_lines = "\n".join(f"- `{line}`" for line in optional) or "- none"
    checklist_lines = "\n".join(f"- {line}" for line in checklist) or "- none"
    missing_lines = "\n".join(f"- {line}" for line in missing) or "- none"
    return textwrap.dedent(
        f"""
        # {title}

        **Workspace:** `{status['workspace']}`

        ## Required paths
        {needed_lines}

        ## Optional/supporting paths
        {optional_lines}

        ## Missing prerequisites
        {missing_lines}

        ## Deterministic checklist
        {checklist_lines}
        """
    ).strip()


def build_handoffs(workspace: pathlib.Path) -> dict:
    briefs_dir = workspace / "briefs"
    briefs_dir.mkdir(parents=True, exist_ok=True)

    summary_path = briefs_dir / "00-workspace-summary.md"
    outline_path = briefs_dir / "01-outline-agent.md"
    plotting_path = briefs_dir / "02-plotting-agent.md"
    litreview_path = briefs_dir / "03-literature-review-agent.md"
    writing_path = briefs_dir / "04-section-writing-agent.md"
    refinement_path = briefs_dir / "05-content-refinement-agent.md"
    manifest_path = briefs_dir / "handoff_manifest.json"

    for path in (summary_path, outline_path, plotting_path, litreview_path, writing_path, refinement_path, manifest_path):
        path.touch()

    status = inspect_workspace(workspace)
    inputs = status["inputs"]
    artifacts = status["artifacts"]

    _write(summary_path, _render_summary(status))

    _write(
        outline_path,
        _render_step_brief(
            "Outline Agent Brief",
            status,
            needed=[
                f"{status['workspace']}/inputs/idea.md",
                f"{status['workspace']}/inputs/experimental_log.md",
                f"{status['workspace']}/inputs/template.tex",
                f"{status['workspace']}/inputs/conference_guidelines.md",
            ],
            optional=[f"{status['workspace']}/briefs/00-workspace-summary.md"],
            checklist=[
                "Read the required inputs and produce workspace/outline.json.",
                "Validate workspace/outline.json with validate_outline.py before handing off downstream.",
                "Refresh handoffs afterward so parallel agents see the new outline.",
            ],
            missing=[name for name in ("idea.md", "experimental_log.md", "template.tex", "conference_guidelines.md") if not inputs[name]["exists"] or not inputs[name]["non_empty"]],
        ),
    )

    _write(
        plotting_path,
        _render_step_brief(
            "Plotting Agent Brief",
            status,
            needed=[
                f"{status['workspace']}/outline.json",
                f"{status['workspace']}/figures/",
            ],
            optional=[
                f"{status['workspace']}/inputs/figures/",
                f"{status['workspace']}/briefs/00-workspace-summary.md",
            ],
            checklist=[
                "Read outline.json and execute outline.plotting_plan.",
                "Write each generated figure into workspace/figures/.",
                "Write workspace/figures/captions.json with one caption per figure_id.",
                "Refresh handoffs after plotting completes.",
            ],
            missing=[] if artifacts["outline"]["exists"] else ["outline.json"],
        ),
    )

    _write(
        litreview_path,
        _render_step_brief(
            "Literature Review Agent Brief",
            status,
            needed=[
                f"{status['workspace']}/outline.json",
                f"{status['workspace']}/inputs/conference_guidelines.md",
                f"{status['workspace']}/inputs/idea.md",
                f"{status['workspace']}/inputs/experimental_log.md",
            ],
            optional=[
                f"{status['workspace']}/cache/s2_cache.json",
                f"{status['workspace']}/briefs/00-workspace-summary.md",
            ],
            checklist=[
                "Read outline.json and execute outline.intro_related_work_plan.",
                "Produce workspace/citation_pool.json, workspace/refs.bib, and workspace/drafts/intro_relwork.tex.",
                "Run validate_pool.py --fix and sync_keys.py after BibTeX generation.",
                "Refresh handoffs after literature review completes.",
            ],
            missing=[] if artifacts["outline"]["exists"] else ["outline.json"],
        ),
    )

    section_missing = []
    if not artifacts["outline"]["exists"]:
        section_missing.append("outline.json")
    if not artifacts["citation_pool"]["exists"]:
        section_missing.append("citation_pool.json")
    if not artifacts["refs_bib"]["exists"]:
        section_missing.append("refs.bib")
    if not artifacts["drafts"]["intro_relwork_exists"]:
        section_missing.append("drafts/intro_relwork.tex")
    if not artifacts["generated_figures"]["captions_exists"]:
        section_missing.append("figures/captions.json")
    if artifacts["generated_figures"]["count"] == 0:
        section_missing.append("generated figure PNGs in workspace/figures/")
    if not artifacts["tex_profile"]["exists"]:
        section_missing.append("tex_profile.json")

    _write(
        writing_path,
        _render_step_brief(
            "Section Writing Agent Brief",
            status,
            needed=[
                f"{status['workspace']}/outline.json",
                f"{status['workspace']}/inputs/idea.md",
                f"{status['workspace']}/inputs/experimental_log.md",
                f"{status['workspace']}/drafts/intro_relwork.tex",
                f"{status['workspace']}/citation_pool.json",
                f"{status['workspace']}/refs.bib",
                f"{status['workspace']}/inputs/conference_guidelines.md",
                f"{status['workspace']}/figures/",
                f"{status['workspace']}/figures/captions.json",
                f"{status['workspace']}/tex_profile.json",
            ],
            optional=[f"{status['workspace']}/briefs/00-workspace-summary.md"],
            checklist=[
                "Use a single multimodal call to draft workspace/drafts/paper.tex.",
                "Preserve intro_relwork.tex verbatim and integrate figures + captions.",
                "Run orphan_cite_gate.py, latex_sanity.py, and anti_leakage_check.py before handing off.",
                "Refresh handoffs after section writing completes.",
            ],
            missing=section_missing,
        ),
    )

    refinement_missing = []
    if not artifacts["drafts"]["paper_exists"]:
        refinement_missing.append("drafts/paper.tex")
    if not artifacts["citation_pool"]["exists"]:
        refinement_missing.append("citation_pool.json")
    if not artifacts["refs_bib"]["exists"]:
        refinement_missing.append("refs.bib")

    _write(
        refinement_path,
        _render_step_brief(
            "Content Refinement Agent Brief",
            status,
            needed=[
                f"{status['workspace']}/drafts/paper.tex",
                f"{status['workspace']}/inputs/conference_guidelines.md",
                f"{status['workspace']}/inputs/experimental_log.md",
                f"{status['workspace']}/citation_pool.json",
                f"{status['workspace']}/refs.bib",
                f"{status['workspace']}/refinement/",
                f"{status['workspace']}/final/",
            ],
            optional=[f"{status['workspace']}/briefs/00-workspace-summary.md"],
            checklist=[
                "Iterate with the simulated reviewer and maintain refinement/worklog.json.",
                "Snapshot each iteration under refinement/iterN/.",
                "Promote the accepted snapshot into final/paper.tex and compile final/paper.pdf.",
                "Refresh handoffs after refinement completes.",
            ],
            missing=refinement_missing,
        ),
    )

    manifest = {
        "workspace": status["workspace"],
        "generated_at": os.path.getmtime(summary_path),
        "status": status,
        "briefs": {
            "summary": str(summary_path),
            "outline": str(outline_path),
            "plotting": str(plotting_path),
            "literature_review": str(litreview_path),
            "section_writing": str(writing_path),
            "content_refinement": str(refinement_path),
        },
    }
    _write(manifest_path, json.dumps(manifest, indent=2))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, help="Path to the workspace directory")
    args = parser.parse_args()

    workspace = pathlib.Path(os.path.abspath(args.workspace))
    if not workspace.exists():
        print(f"ERROR: workspace does not exist: {workspace}")
        return 1

    manifest = build_handoffs(workspace)
    print(json.dumps({
        "workspace": manifest["workspace"],
        "brief_count": len(manifest["briefs"]),
        "manifest": str(workspace / "briefs" / "handoff_manifest.json"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
