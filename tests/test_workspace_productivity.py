import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PYTHON = sys.executable


class WorkspaceProductivityTests(unittest.TestCase):
    def _create_workspace_with_inputs(self, temp_dir: str) -> pathlib.Path:
        workspace = pathlib.Path(temp_dir) / "workspace"
        init_script = REPO_ROOT / "skills" / "paper-orchestra" / "scripts" / "init_workspace.py"
        subprocess.run([PYTHON, str(init_script), "--out", str(workspace)], check=True)

        example_inputs = REPO_ROOT / "examples" / "minimal" / "inputs"
        for input_file in example_inputs.iterdir():
            target = workspace / "inputs" / input_file.name
            if input_file.is_dir():
                shutil.copytree(input_file, target, dirs_exist_ok=True)
            else:
                shutil.copy2(input_file, target)
        return workspace

    def test_workspace_status_reports_outline_as_next_step_for_fresh_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self._create_workspace_with_inputs(temp_dir)
            status_script = REPO_ROOT / "skills" / "paper-orchestra" / "scripts" / "workspace_status.py"

            result = subprocess.run(
                [PYTHON, str(status_script), "--workspace", str(workspace), "--format", "json"],
                text=True,
                capture_output=True,
                check=True,
            )
            payload = json.loads(result.stdout)
            self.assertTrue(payload["readiness"]["step0_inputs_ready"])
            self.assertFalse(payload["readiness"]["step1_outline_done"])
            labels = [item["label"] for item in payload["recommended_actions"]]
            self.assertIn("Run Step 1 (Outline)", labels)

    def test_build_agent_handoffs_creates_step_specific_briefs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self._create_workspace_with_inputs(temp_dir)
            (workspace / "outline.json").write_text(json.dumps({
                "plotting_plan": [{"figure_id": "fig_demo"}],
                "intro_related_work_plan": {"search_directions": ["adaptive attention"]},
                "section_plan": []
            }))
            (workspace / "figures" / "fig_demo.png").write_bytes(b"png")
            (workspace / "figures" / "captions.json").write_text(json.dumps({"fig_demo": "Demo caption"}))
            (workspace / "refs.bib").write_text("@article{demo2024paper, title={Demo}}\n")
            (workspace / "citation_pool.json").write_text(json.dumps({
                "papers": [{"paperId": "p1", "bibtex_key": "demo2024paper"}],
                "cutoff_date": "2024-10-01",
                "min_cite_paper_count": 1,
            }))
            (workspace / "drafts" / "intro_relwork.tex").write_text("\\section{Introduction}\n")
            (workspace / "drafts" / "paper.tex").write_text("\\documentclass{article}\n\\begin{document}demo\\end{document}\n")
            (workspace / "tex_profile.json").write_text(json.dumps({"available": ["booktabs"]}))

            handoff_script = REPO_ROOT / "skills" / "paper-orchestra" / "scripts" / "build_agent_handoffs.py"
            result = subprocess.run(
                [PYTHON, str(handoff_script), "--workspace", str(workspace)],
                text=True,
                capture_output=True,
                check=True,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["brief_count"], 6)

            briefs_dir = workspace / "briefs"
            expected_files = [
                briefs_dir / "00-workspace-summary.md",
                briefs_dir / "01-outline-agent.md",
                briefs_dir / "02-plotting-agent.md",
                briefs_dir / "03-literature-review-agent.md",
                briefs_dir / "04-section-writing-agent.md",
                briefs_dir / "05-content-refinement-agent.md",
                briefs_dir / "handoff_manifest.json",
            ]
            for path in expected_files:
                self.assertTrue(path.exists(), path)

            section_brief = (briefs_dir / "04-section-writing-agent.md").read_text()
            self.assertIn("drafts/intro_relwork.tex", section_brief)
            self.assertIn("refs.bib", section_brief)
            self.assertIn("tex_profile.json", section_brief)

            manifest = json.loads((briefs_dir / "handoff_manifest.json").read_text())
            self.assertEqual(manifest["status"]["artifacts"]["citation_pool"]["paper_count"], 1)
            self.assertTrue(manifest["status"]["readiness"]["step4_section_writing_ready"])


if __name__ == "__main__":
    unittest.main()
