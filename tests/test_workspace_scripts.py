import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PYTHON = sys.executable


class WorkspaceScriptTests(unittest.TestCase):
    def test_workspace_smoke_flow_on_minimal_example(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = pathlib.Path(temp_dir) / "workspace"
            example_inputs = REPO_ROOT / "examples" / "minimal" / "inputs"

            init_script = REPO_ROOT / "skills" / "paper-orchestra" / "scripts" / "init_workspace.py"
            validate_script = REPO_ROOT / "skills" / "paper-orchestra" / "scripts" / "validate_inputs.py"
            extract_script = REPO_ROOT / "skills" / "section-writing-agent" / "scripts" / "extract_metrics.py"

            subprocess.run([PYTHON, str(init_script), "--out", str(workspace)], check=True)
            for input_file in example_inputs.iterdir():
                target = workspace / "inputs" / input_file.name
                if input_file.is_dir():
                    shutil.copytree(input_file, target, dirs_exist_ok=True)
                else:
                    shutil.copy2(input_file, target)

            validate = subprocess.run(
                [PYTHON, str(validate_script), "--workspace", str(workspace)],
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertIn("OK: all 4 required inputs present and well-formed.", validate.stdout)

            metrics_path = workspace / "metrics.json"
            extract = subprocess.run(
                [PYTHON, str(extract_script), "--log", str(workspace / 'inputs' / 'experimental_log.md'), "--out", str(metrics_path)],
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertIn("OK: extracted 4 table(s)", extract.stdout)
            self.assertTrue(metrics_path.exists())

        
    def test_validate_inputs_fails_when_required_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = pathlib.Path(temp_dir) / "workspace"
            init_script = REPO_ROOT / "skills" / "paper-orchestra" / "scripts" / "init_workspace.py"
            validate_script = REPO_ROOT / "skills" / "paper-orchestra" / "scripts" / "validate_inputs.py"

            subprocess.run([PYTHON, str(init_script), "--out", str(workspace)], check=True)
            inputs_dir = workspace / "inputs"
            (inputs_dir / "idea.md").write_text("# Problem Statement\n\n## Core Hypothesis\n")
            (inputs_dir / "experimental_log.md").write_text("## 1. Experimental Setup\n\n## 2. Raw Numeric Data\n")
            (inputs_dir / "template.tex").write_text("\\documentclass{article}\n\\section{Intro}\n")

            validate = subprocess.run(
                [PYTHON, str(validate_script), "--workspace", str(workspace)],
                text=True,
                capture_output=True,
            )
            self.assertEqual(validate.returncode, 1)
            self.assertIn("MISSING:", validate.stderr)
            self.assertIn("conference_guidelines.md", validate.stderr)


if __name__ == "__main__":
    unittest.main()
