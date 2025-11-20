"""Tests for the update system."""

import json
from pathlib import Path
from unittest.mock import patch

from kurt.update.detector import FileUpdate
from kurt.update.hasher import (
    compute_file_hash,
    load_installed_files,
    record_installed_file,
    save_installed_files,
    was_file_modified,
)
from kurt.update.merger import merge_settings_json


class TestHasher:
    """Test file hash tracking."""

    def test_compute_file_hash(self, tmp_path):
        """Test computing file hash."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, world!")

        hash1 = compute_file_hash(test_file)
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA256 hex digest

        # Same content should produce same hash
        hash2 = compute_file_hash(test_file)
        assert hash1 == hash2

        # Different content should produce different hash
        test_file.write_text("Different content")
        hash3 = compute_file_hash(test_file)
        assert hash1 != hash3

    def test_save_and_load_installed_files(self, tmp_path, monkeypatch):
        """Test saving and loading installed files tracking data."""
        monkeypatch.chdir(tmp_path)
        kurt_dir = tmp_path / ".kurt"
        kurt_dir.mkdir()

        data = {
            ".claude/CLAUDE.md": {
                "hash": "abc123",
                "version": "0.2.7",
                "installed_at": "2024-01-15T10:30:00Z",
            }
        }

        save_installed_files(data)
        loaded = load_installed_files()

        assert loaded == data

    def test_record_installed_file(self, tmp_path, monkeypatch):
        """Test recording file installation."""
        monkeypatch.chdir(tmp_path)
        kurt_dir = tmp_path / ".kurt"
        kurt_dir.mkdir()

        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        record_installed_file("test.txt", test_file, "0.2.7")

        data = load_installed_files()
        assert "test.txt" in data
        assert data["test.txt"]["version"] == "0.2.7"
        assert "hash" in data["test.txt"]
        assert "installed_at" in data["test.txt"]

    def test_was_file_modified(self, tmp_path, monkeypatch):
        """Test detecting file modifications."""
        monkeypatch.chdir(tmp_path)
        kurt_dir = tmp_path / ".kurt"
        kurt_dir.mkdir()

        test_file = tmp_path / "test.txt"
        test_file.write_text("Original content")

        # Record initial installation
        record_installed_file("test.txt", test_file, "0.2.7")

        # File should not be modified
        assert not was_file_modified("test.txt", test_file)

        # Modify file
        test_file.write_text("Modified content")

        # File should be detected as modified
        assert was_file_modified("test.txt", test_file)

    def test_was_file_modified_untracked(self, tmp_path, monkeypatch):
        """Test that untracked files are considered modified."""
        monkeypatch.chdir(tmp_path)
        kurt_dir = tmp_path / ".kurt"
        kurt_dir.mkdir()

        test_file = tmp_path / "test.txt"
        test_file.write_text("Content")

        # Untracked file should be considered modified (user-created)
        assert was_file_modified("test.txt", test_file)


class TestMerger:
    """Test settings.json merging."""

    def test_merge_settings_json_new_file(self, tmp_path):
        """Test merging when local file doesn't exist."""
        package_settings = tmp_path / "package_settings.json"
        package_settings.write_text(json.dumps({"hooks": {"user-prompt-submit": "kurt --version"}}))

        local_settings = tmp_path / "local_settings.json"

        result = merge_settings_json(local_settings, package_settings)

        assert "hooks" in result
        assert result["hooks"]["user-prompt-submit"] == "kurt --version"

    def test_merge_settings_json_preserve_user_settings(self, tmp_path):
        """Test that user settings are preserved."""
        package_settings = tmp_path / "package_settings.json"
        package_settings.write_text(json.dumps({"hooks": {"user-prompt-submit": "kurt --version"}}))

        local_settings = tmp_path / "local_settings.json"
        local_settings.write_text(
            json.dumps(
                {
                    "hooks": {"my-custom-hook": "echo test"},
                    "custom_setting": "value",
                }
            )
        )

        result = merge_settings_json(local_settings, package_settings)

        # User's custom settings preserved
        assert result["custom_setting"] == "value"
        assert result["hooks"]["my-custom-hook"] == "echo test"

        # Kurt's hooks updated
        assert result["hooks"]["user-prompt-submit"] == "kurt --version"

    def test_merge_settings_json_update_kurt_hooks(self, tmp_path):
        """Test that Kurt's hooks get updated."""
        package_settings = tmp_path / "package_settings.json"
        package_settings.write_text(
            json.dumps({"hooks": {"user-prompt-submit": "kurt --version-new"}})
        )

        local_settings = tmp_path / "local_settings.json"
        local_settings.write_text(
            json.dumps({"hooks": {"user-prompt-submit": "kurt --version-old"}})
        )

        result = merge_settings_json(local_settings, package_settings)

        # Kurt's hook should be updated to new version
        assert result["hooks"]["user-prompt-submit"] == "kurt --version-new"


class TestDetector:
    """Test update detection."""

    def test_file_update_dataclass(self):
        """Test FileUpdate dataclass."""
        update = FileUpdate(
            rel_path=".claude/CLAUDE.md",
            local_path=Path("/tmp/.claude/CLAUDE.md"),
            package_path=Path("/pkg/claude_plugin/CLAUDE.md"),
            status="needs_update",
            category="claude_main",
        )

        assert update.rel_path == ".claude/CLAUDE.md"
        assert update.status == "needs_update"
        assert update.category == "claude_main"

    @patch("kurt.update.detector.Path.cwd")
    def test_detect_ide_installations(self, mock_cwd, tmp_path):
        """Test detecting installed IDEs."""
        from kurt.update.detector import detect_ide_installations

        mock_cwd.return_value = tmp_path

        # No IDEs installed
        assert detect_ide_installations() == []

        # Claude installed
        (tmp_path / ".claude").mkdir()
        assert "claude" in detect_ide_installations()

        # Both installed
        (tmp_path / ".cursor").mkdir()
        ides = detect_ide_installations()
        assert "claude" in ides
        assert "cursor" in ides


class TestUpdateIntegration:
    """Integration tests for update system."""

    @patch("kurt.update.orchestrator.detect_updates")
    @patch("kurt.config.base.config_file_exists")
    def test_update_files_not_initialized(self, mock_config_exists, mock_detect):
        """Test that update fails if project not initialized."""
        from kurt.update import update_files

        mock_config_exists.return_value = False

        result = update_files()

        assert result.get("error") == 1

    @patch("kurt.update.orchestrator.detect_updates")
    @patch("kurt.update.orchestrator.console")
    @patch("kurt.config.base.config_file_exists")
    def test_update_files_nothing_to_update(self, mock_config_exists, mock_console, mock_detect):
        """Test update when everything is up to date."""
        from kurt.update import update_files
        from kurt.update.detector import UpdateSummary

        mock_config_exists.return_value = True
        mock_detect.return_value = UpdateSummary(
            needs_update=[],
            modified_locally=[],
            user_created=[],
            up_to_date=[],
        )

        result = update_files()

        assert result["updated"] == 0
        assert result["skipped"] == 0

    @patch("kurt.update.orchestrator.detect_updates")
    @patch("kurt.update.orchestrator.apply_file_update")
    @patch("kurt.update.orchestrator.console")
    @patch("kurt.config.base.config_file_exists")
    def test_update_files_with_auto_confirm(
        self, mock_config_exists, mock_console, mock_apply, mock_detect, tmp_path
    ):
        """Test auto-confirm mode updates all files."""
        from kurt.update import update_files
        from kurt.update.detector import FileUpdate, UpdateSummary

        mock_config_exists.return_value = True

        # Mock one file needing update
        file_update = FileUpdate(
            rel_path=".claude/instructions/test.md",
            local_path=tmp_path / ".claude" / "instructions" / "test.md",
            package_path=tmp_path / "pkg" / "test.md",
            status="needs_update",
            category="claude_instructions",
        )

        mock_detect.return_value = UpdateSummary(
            needs_update=[file_update],
            modified_locally=[],
            user_created=[],
            up_to_date=[],
        )

        result = update_files(auto_confirm=True)

        # File should be updated
        assert result["updated"] >= 1
        mock_apply.assert_called()
