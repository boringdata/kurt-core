"""Tests for Kurt skill installer."""

from __future__ import annotations

from pathlib import Path

import pytest

from kurt.skills.installer import install_skill, is_installed, uninstall_skill


@pytest.fixture
def skill_dir(tmp_path):
    """Temporary directory for skill installation."""
    return tmp_path / "skills" / "kurt"


class TestInstallSkill:
    def test_installs_all_files(self, skill_dir):
        """Install copies SKILL.md, skill.py, and README.md."""
        result = install_skill(skill_dir)

        assert result == skill_dir
        assert (skill_dir / "SKILL.md").exists()
        assert (skill_dir / "skill.py").exists()
        assert (skill_dir / "README.md").exists()

    def test_skill_py_is_executable(self, skill_dir):
        """skill.py should be executable after install."""
        install_skill(skill_dir)

        skill_py = skill_dir / "skill.py"
        assert skill_py.stat().st_mode & 0o111

    def test_skill_md_has_frontmatter(self, skill_dir):
        """SKILL.md should have YAML frontmatter with required fields."""
        install_skill(skill_dir)

        content = (skill_dir / "SKILL.md").read_text()
        assert content.startswith("---")
        assert "name: kurt" in content
        assert "version:" in content
        assert "actions:" in content
        assert "url_patterns:" in content

    def test_skill_md_documents_actions(self, skill_dir):
        """SKILL.md should document all main actions."""
        install_skill(skill_dir)

        content = (skill_dir / "SKILL.md").read_text()
        for action in ["fetch", "map", "workflow", "tool"]:
            assert f"name: {action}" in content

    def test_raises_if_exists_without_force(self, skill_dir):
        """Should raise FileExistsError if already installed."""
        install_skill(skill_dir)

        with pytest.raises(FileExistsError, match="already installed"):
            install_skill(skill_dir)

    def test_force_overwrites(self, skill_dir):
        """--force should overwrite existing installation."""
        install_skill(skill_dir)

        # Modify a file
        (skill_dir / "SKILL.md").write_text("modified")

        # Force reinstall
        install_skill(skill_dir, force=True)

        content = (skill_dir / "SKILL.md").read_text()
        assert content.startswith("---")
        assert "modified" not in content

    def test_creates_parent_dirs(self, tmp_path):
        """Should create parent directories if they don't exist."""
        deep_path = tmp_path / "a" / "b" / "c" / "kurt"
        install_skill(deep_path)

        assert (deep_path / "SKILL.md").exists()


class TestUninstallSkill:
    def test_removes_skill_dir(self, skill_dir):
        """Uninstall removes the skill directory."""
        install_skill(skill_dir)
        assert skill_dir.exists()

        result = uninstall_skill(skill_dir)

        assert result is True
        assert not skill_dir.exists()

    def test_returns_false_if_not_installed(self, skill_dir):
        """Uninstall returns False if skill not installed."""
        result = uninstall_skill(skill_dir)
        assert result is False


class TestIsInstalled:
    def test_true_when_installed(self, skill_dir):
        """is_installed returns True after installation."""
        install_skill(skill_dir)
        assert is_installed(skill_dir) is True

    def test_false_when_not_installed(self, skill_dir):
        """is_installed returns False when not installed."""
        assert is_installed(skill_dir) is False

    def test_false_when_dir_exists_but_no_skill_md(self, skill_dir):
        """is_installed returns False if dir exists but SKILL.md is missing."""
        skill_dir.mkdir(parents=True)
        assert is_installed(skill_dir) is False


class TestSkillPyContent:
    def test_skill_py_has_main(self, skill_dir):
        """skill.py should have a main() function."""
        install_skill(skill_dir)

        content = (skill_dir / "skill.py").read_text()
        assert "def main()" in content

    def test_skill_py_has_json_output(self, skill_dir):
        """skill.py should output JSON for machine parsing."""
        install_skill(skill_dir)

        content = (skill_dir / "skill.py").read_text()
        assert "json.dumps" in content

    def test_skill_py_has_error_handling(self, skill_dir):
        """skill.py should handle missing kurt binary."""
        install_skill(skill_dir)

        content = (skill_dir / "skill.py").read_text()
        assert "FileNotFoundError" in content
        assert "TimeoutExpired" in content

    def test_skill_py_has_all_actions(self, skill_dir):
        """skill.py should support all main actions."""
        install_skill(skill_dir)

        content = (skill_dir / "skill.py").read_text()
        for action in ["fetch", "map", "workflow", "tool"]:
            assert f'"{action}"' in content
