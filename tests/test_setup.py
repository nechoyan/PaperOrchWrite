import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


class SetupScriptTests(unittest.TestCase):
    def _make_minimal_repo(self, temp_dir: str) -> pathlib.Path:
        repo_dir = pathlib.Path(temp_dir) / "repo"
        repo_dir.mkdir()
        shutil.copy2(REPO_ROOT / "setup.sh", repo_dir / "setup.sh")
        shutil.copy2(REPO_ROOT / ".env.example", repo_dir / ".env.example")

        skills_dir = repo_dir / "skills"
        for skill_name in ("paper-orchestra", "outline-agent"):
            (skills_dir / skill_name).mkdir(parents=True)
            (skills_dir / skill_name / "SKILL.md").write_text(f"# {skill_name}\n")

        return repo_dir

    def test_setup_script_creates_expected_config_and_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_dir = self._make_minimal_repo(temp_dir)
            home_dir = pathlib.Path(temp_dir) / "home"
            home_dir.mkdir()

            env = os.environ.copy()
            env["HOME"] = str(home_dir)

            result = subprocess.run(
                ["bash", str(repo_dir / "setup.sh")],
                cwd=repo_dir,
                input="\n\n\n",
                text=True,
                capture_output=True,
                env=env,
                check=True,
            )

            config_path = home_dir / ".paperorchestra" / "config"
            self.assertTrue(config_path.exists(), result.stdout + result.stderr)
            config_text = config_path.read_text()
            self.assertIn("SEMANTIC_SCHOLAR_API_KEY=", config_text)
            self.assertIn("EXA_API_KEY=", config_text)
            self.assertIn("PAPERBANANA_PATH=", config_text)
            self.assertIn(f"PAPERORCHESTRA_REPO={repo_dir}", config_text)
            self.assertNotIn("*** SEMANTIC_SCHOLAR_API_KEY)", config_text)

            env_text = (repo_dir / ".env").read_text()
            self.assertIn("SEMANTIC_SCHOLAR_API_KEY=", env_text)
            self.assertIn("EXA_API_KEY=", env_text)
            self.assertIn("PAPERBANANA_PATH=", env_text)

            claude_skill = home_dir / ".claude" / "skills" / "paper-orchestra"
            self.assertTrue(claude_skill.is_symlink())
            self.assertEqual(claude_skill.resolve(), (repo_dir / "skills" / "paper-orchestra").resolve())

            self.assertIn("docs/coding-agent-integration.md", result.stdout)


if __name__ == "__main__":
    unittest.main()
