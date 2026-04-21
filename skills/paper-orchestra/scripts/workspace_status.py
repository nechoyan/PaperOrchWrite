#!/usr/bin/env python3
"""
workspace_status.py — Inspect a PaperOrchestra workspace and report progress.

This script is meant to speed up multi-agent execution and resume flows. It
summarizes which pipeline artifacts already exist, what is missing, and the next
recommended deterministic or agent-driven action.

Usage:
    python workspace_status.py --workspace /path/to/workspace/
    python workspace_status.py --workspace /path/to/workspace/ --format json
"""
import argparse
import json
import os
import pathlib
from typing import Any

REQUIRED_INPUTS = [
    "idea.md",
    "experimental_log.md",
    "template.tex",
    "conference_guidelines.md",
]


def _safe_read_text(path: pathlib.Path) -> str:
    try:
        return path.read_text()
    except OSError:
        return ""


def _json_load(path: pathlib.Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _count_matching(directory: pathlib.Path, suffixes: tuple[str, ...]) -> int:
    if not directory.is_dir():
        return 0
    count = 0
    for entry in directory.iterdir():
        if entry.is_file() and entry.suffix.lower() in suffixes:
            count += 1
    return count


def _gather_inputs(inputs_dir: pathlib.Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for name in REQUIRED_INPUTS:
        path = inputs_dir / name
        result[name] = {
            "path": str(path),
            "exists": path.is_file(),
            "non_empty": path.is_file() and path.stat().st_size > 0,
        }
    figures_dir = inputs_dir / "figures"
    result["figures_dir"] = {
        "path": str(figures_dir),
        "exists": figures_dir.is_dir(),
        "count": _count_matching(figures_dir, (".png", ".pdf", ".jpg", ".jpeg", ".webp")),
    }
    return result


def _gather_artifacts(workspace: pathlib.Path) -> dict[str, Any]:
    outline_path = workspace / "outline.json"
    citation_pool_path = workspace / "citation_pool.json"
    captions_path = workspace / "figures" / "captions.json"
    drafts_dir = workspace / "drafts"
    refinement_dir = workspace / "refinement"
    final_dir = workspace / "final"
    briefs_dir = workspace / "briefs"

    citation_pool = _json_load(citation_pool_path) or {}
    captions = _json_load(captions_path) or {}

    refinement_iters = []
    if refinement_dir.is_dir():
        refinement_iters = sorted(
            [entry.name for entry in refinement_dir.iterdir() if entry.is_dir() and entry.name.startswith("iter")]
        )

    return {
        "outline": {
            "path": str(outline_path),
            "exists": outline_path.is_file(),
        },
        "generated_figures": {
            "dir": str(workspace / "figures"),
            "count": _count_matching(workspace / "figures", (".png", ".pdf", ".jpg", ".jpeg", ".webp")),
            "captions_path": str(captions_path),
            "captions_exists": captions_path.is_file(),
            "caption_count": len(captions) if isinstance(captions, dict) else 0,
        },
        "refs_bib": {
            "path": str(workspace / "refs.bib"),
            "exists": (workspace / "refs.bib").is_file(),
        },
        "citation_pool": {
            "path": str(citation_pool_path),
            "exists": citation_pool_path.is_file(),
            "paper_count": len(citation_pool.get("papers", [])) if isinstance(citation_pool, dict) else 0,
            "cutoff_date": citation_pool.get("cutoff_date") if isinstance(citation_pool, dict) else None,
        },
        "drafts": {
            "dir": str(drafts_dir),
            "intro_relwork_exists": (drafts_dir / "intro_relwork.tex").is_file(),
            "paper_exists": (drafts_dir / "paper.tex").is_file(),
        },
        "refinement": {
            "dir": str(refinement_dir),
            "worklog_exists": (refinement_dir / "worklog.json").is_file(),
            "iterations": refinement_iters,
        },
        "final": {
            "dir": str(final_dir),
            "paper_tex_exists": (final_dir / "paper.tex").is_file(),
            "paper_pdf_exists": (final_dir / "paper.pdf").is_file(),
        },
        "tex_profile": {
            "path": str(workspace / "tex_profile.json"),
            "exists": (workspace / "tex_profile.json").is_file(),
        },
        "provenance": {
            "path": str(workspace / "provenance.json"),
            "exists": (workspace / "provenance.json").is_file(),
        },
        "briefs": {
            "dir": str(briefs_dir),
            "count": _count_matching(briefs_dir, (".md", ".json")),
        },
    }


def _compute_readiness(workspace: pathlib.Path, inputs: dict[str, Any], artifacts: dict[str, Any]) -> dict[str, Any]:
    required_ready = all(inputs[name]["exists"] and inputs[name]["non_empty"] for name in REQUIRED_INPUTS)
    plotting_done = artifacts["generated_figures"]["count"] > 0 and artifacts["generated_figures"]["captions_exists"]
    lit_review_done = (
        artifacts["refs_bib"]["exists"]
        and artifacts["drafts"]["intro_relwork_exists"]
        and artifacts["citation_pool"]["exists"]
    )
    section_ready = (
        artifacts["outline"]["exists"]
        and artifacts["refs_bib"]["exists"]
        and artifacts["citation_pool"]["exists"]
        and artifacts["drafts"]["intro_relwork_exists"]
        and artifacts["generated_figures"]["captions_exists"]
        and artifacts["generated_figures"]["count"] > 0
        and artifacts["tex_profile"]["exists"]
    )
    refinement_started = artifacts["drafts"]["paper_exists"] or artifacts["refinement"]["worklog_exists"]

    return {
        "step0_inputs_ready": required_ready,
        "step0_tex_profile_ready": artifacts["tex_profile"]["exists"],
        "step1_outline_ready": required_ready,
        "step1_outline_done": artifacts["outline"]["exists"],
        "step2_plotting_ready": artifacts["outline"]["exists"],
        "step2_plotting_done": plotting_done,
        "step3_lit_review_ready": artifacts["outline"]["exists"],
        "step3_lit_review_done": lit_review_done,
        "step4_section_writing_ready": section_ready,
        "step4_section_writing_done": artifacts["drafts"]["paper_exists"],
        "step5_refinement_ready": (
            artifacts["drafts"]["paper_exists"]
            and artifacts["citation_pool"]["exists"]
            and artifacts["refs_bib"]["exists"]
        ),
        "step5_refinement_started": refinement_started,
        "step5_refinement_done": artifacts["final"]["paper_tex_exists"],
        "final_compile_ready": artifacts["final"]["paper_tex_exists"],
        "final_compile_done": artifacts["final"]["paper_pdf_exists"],
    }


def _recommended_actions(workspace: pathlib.Path, inputs: dict[str, Any], artifacts: dict[str, Any], readiness: dict[str, Any]) -> list[dict[str, str]]:
    ws = str(workspace)
    actions: list[dict[str, str]] = []

    missing_inputs = [name for name in REQUIRED_INPUTS if not inputs[name]["exists"] or not inputs[name]["non_empty"]]
    if missing_inputs:
        actions.append({
            "label": "Provide required inputs",
            "command": f"python skills/paper-orchestra/scripts/validate_inputs.py --workspace {ws}",
            "reason": "Workspace is missing one or more required input files: " + ", ".join(missing_inputs),
        })
        return actions

    if not artifacts["tex_profile"]["exists"]:
        actions.append({
            "label": "Probe local TeX packages",
            "command": f"python skills/paper-orchestra/scripts/check_tex_packages.py --out {ws}/tex_profile.json",
            "reason": "Section writing is more reliable once tex_profile.json exists.",
        })

    if not artifacts["outline"]["exists"]:
        actions.append({
            "label": "Run Step 1 (Outline)",
            "command": "Load skills/outline-agent/SKILL.md and write workspace/outline.json",
            "reason": "All downstream steps depend on outline.json.",
        })
        return actions

    if not artifacts["briefs"]["count"]:
        actions.append({
            "label": "Generate agent handoffs",
            "command": f"python skills/paper-orchestra/scripts/build_agent_handoffs.py --workspace {ws}",
            "reason": "Per-step briefs reduce repeated scanning by parallel agents.",
        })

    if not artifacts["generated_figures"]["captions_exists"] or artifacts["generated_figures"]["count"] == 0:
        actions.append({
            "label": "Run Step 2 (Plotting)",
            "command": "Load skills/plotting-agent/SKILL.md and execute the plotting plan from workspace/outline.json",
            "reason": "Generated figures/captions are not complete yet.",
        })

    if not artifacts["refs_bib"]["exists"] or not artifacts["drafts"]["intro_relwork_exists"]:
        actions.append({
            "label": "Run Step 3 (Literature Review)",
            "command": "Load skills/literature-review-agent/SKILL.md and produce workspace/refs.bib + workspace/drafts/intro_relwork.tex",
            "reason": "Citation artifacts are incomplete.",
        })

    if not artifacts["drafts"]["paper_exists"] and readiness["step4_section_writing_ready"]:
        actions.append({
            "label": "Run Step 4 (Section Writing)",
            "command": "Load skills/section-writing-agent/SKILL.md and write workspace/drafts/paper.tex",
            "reason": "Outline + literature review are ready for the single-call writing step.",
        })

    if artifacts["drafts"]["paper_exists"] and not readiness["step5_refinement_ready"]:
        missing = []
        if not artifacts["citation_pool"]["exists"]:
            missing.append("citation_pool.json")
        if not artifacts["refs_bib"]["exists"]:
            missing.append("refs.bib")
        actions.append({
            "label": "Finish Step 3 artifacts before refinement",
            "command": "Load skills/literature-review-agent/SKILL.md and produce the missing citation artifacts",
            "reason": "Refinement expects the allowed bibliography set: " + ", ".join(missing),
        })

    if readiness["step5_refinement_ready"] and not artifacts["final"]["paper_tex_exists"]:
        actions.append({
            "label": "Run Step 5 (Content Refinement)",
            "command": "Load skills/content-refinement-agent/SKILL.md and promote the accepted snapshot into workspace/final/",
            "reason": "A draft exists and the refinement prerequisites are ready.",
        })

    if artifacts["final"]["paper_tex_exists"] and not artifacts["final"]["paper_pdf_exists"]:
        actions.append({
            "label": "Compile final PDF",
            "command": f"cd {ws}/final && latexmk -pdf paper.tex",
            "reason": "final/paper.tex exists but final/paper.pdf is missing.",
        })

    if artifacts["final"]["paper_pdf_exists"] and not artifacts["provenance"]["exists"]:
        actions.append({
            "label": "Record provenance",
            "command": "Write workspace/provenance.json with hashes of inputs and outputs",
            "reason": "Final artifacts exist; provenance is still missing.",
        })

    if not actions:
        actions.append({
            "label": "Workspace looks complete",
            "command": f"python skills/paper-orchestra/scripts/build_agent_handoffs.py --workspace {ws}",
            "reason": "Refresh the handoffs if you want a concise summary for reviewers or follow-up agents.",
        })
    return actions


def inspect_workspace(workspace: pathlib.Path) -> dict[str, Any]:
    workspace = workspace.resolve()
    inputs_dir = workspace / "inputs"
    inputs = _gather_inputs(inputs_dir)
    artifacts = _gather_artifacts(workspace)
    readiness = _compute_readiness(workspace, inputs, artifacts)
    actions = _recommended_actions(workspace, inputs, artifacts, readiness)

    return {
        "workspace": str(workspace),
        "inputs": inputs,
        "artifacts": artifacts,
        "readiness": readiness,
        "recommended_actions": actions,
    }


def render_text_report(status: dict[str, Any]) -> str:
    lines = [
        f"Workspace: {status['workspace']}",
        "",
        "Required inputs:",
    ]
    for name in REQUIRED_INPUTS:
        info = status["inputs"][name]
        state = "ready" if info["exists"] and info["non_empty"] else "missing"
        lines.append(f"- {name}: {state} ({info['path']})")

    figs = status["inputs"]["figures_dir"]
    lines.extend([
        f"- inputs/figures: {figs['count']} file(s)",
        "",
        "Artifacts:",
        f"- outline.json: {'yes' if status['artifacts']['outline']['exists'] else 'no'}",
        f"- generated figures: {status['artifacts']['generated_figures']['count']} image(s)",
        f"- captions.json: {'yes' if status['artifacts']['generated_figures']['captions_exists'] else 'no'}",
        f"- refs.bib: {'yes' if status['artifacts']['refs_bib']['exists'] else 'no'}",
        f"- citation_pool.json papers: {status['artifacts']['citation_pool']['paper_count']}",
        f"- drafts/intro_relwork.tex: {'yes' if status['artifacts']['drafts']['intro_relwork_exists'] else 'no'}",
        f"- drafts/paper.tex: {'yes' if status['artifacts']['drafts']['paper_exists'] else 'no'}",
        f"- refinement iterations: {', '.join(status['artifacts']['refinement']['iterations']) or 'none'}",
        f"- final/paper.tex: {'yes' if status['artifacts']['final']['paper_tex_exists'] else 'no'}",
        f"- final/paper.pdf: {'yes' if status['artifacts']['final']['paper_pdf_exists'] else 'no'}",
        f"- tex_profile.json: {'yes' if status['artifacts']['tex_profile']['exists'] else 'no'}",
        f"- briefs/: {status['artifacts']['briefs']['count']} file(s)",
        "",
        "Recommended next actions:",
    ])
    for action in status["recommended_actions"]:
        lines.append(f"- {action['label']}: {action['reason']}")
        lines.append(f"  {action['command']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, help="Path to the workspace directory")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format")
    args = parser.parse_args()

    workspace = pathlib.Path(os.path.abspath(args.workspace))
    if not workspace.exists():
        print(f"ERROR: workspace does not exist: {workspace}")
        return 1

    status = inspect_workspace(workspace)
    if args.format == "json":
        print(json.dumps(status, indent=2))
    else:
        print(render_text_report(status))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
