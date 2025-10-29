"""Integration tests for file add command handler."""

from unittest.mock import patch

import pytest

from kurt.commands.add_files import handle_file_add


class TestHandleFileAdd:
    """Test file add command handler."""

    @patch("kurt.commands.add_files.add_single_file")
    def test_adds_single_file_successfully(self, mock_add_single, tmp_path):
        # Setup
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test Article")

        mock_add_single.return_value = {
            "doc_id": "test-doc-id",
            "created": True,
            "indexed": True,
            "title": "Test Article",
            "content_length": 100,
            "index_result": {"content_type": "article", "topics": ["test", "python"]},
        }

        # Execute
        handle_file_add(str(test_file), fetch_only=False, dry_run=False, limit=None, force=False)

        # Verify
        mock_add_single.assert_called_once_with(test_file, index=True)

    @patch("kurt.commands.add_files.add_single_file")
    def test_single_file_index_only_mode(self, mock_add_single, tmp_path):
        # Setup
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        mock_add_single.return_value = {
            "doc_id": "test-doc-id",
            "created": True,
            "indexed": False,
            "title": "Test",
            "content_length": 50,
        }

        # Execute with fetch_only (actually means no-index in file context)
        handle_file_add(str(test_file), fetch_only=True, dry_run=False, limit=None, force=False)

        # Should call with index=False
        mock_add_single.assert_called_once_with(test_file, index=False)

    @patch("kurt.commands.add_files.console")
    def test_dry_run_single_file(self, mock_console, tmp_path):
        # Setup
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        # Execute dry run
        handle_file_add(str(test_file), fetch_only=False, dry_run=True, limit=None, force=False)

        # Should only print preview, not actually add
        # Check that console.print was called with preview message
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Would add" in str(call) for call in print_calls)

    @patch("kurt.commands.add_files.add_directory")
    def test_adds_directory_successfully(self, mock_add_dir, tmp_path):
        # Setup
        test_dir = tmp_path / "docs"
        test_dir.mkdir()
        (test_dir / "file1.md").write_text("# File 1")
        (test_dir / "file2.md").write_text("# File 2")

        mock_add_dir.return_value = {
            "total": 2,
            "created": 2,
            "skipped": 0,
            "indexed": 2,
            "errors": 0,
            "files": [
                {
                    "path": str(test_dir / "file1.md"),
                    "doc_id": "id1",
                    "created": True,
                    "title": "File 1",
                },
                {
                    "path": str(test_dir / "file2.md"),
                    "doc_id": "id2",
                    "created": True,
                    "title": "File 2",
                },
            ],
        }

        # Execute
        handle_file_add(str(test_dir), fetch_only=False, dry_run=False, limit=None, force=False)

        # Verify
        mock_add_dir.assert_called_once()
        call_args = mock_add_dir.call_args
        assert call_args[0][0] == test_dir  # First positional arg
        assert call_args[1]["recursive"] is True
        assert call_args[1]["index"] is True

    @patch("kurt.commands.add_files.add_directory")
    def test_directory_with_limit(self, mock_add_dir, tmp_path):
        # Setup
        test_dir = tmp_path / "docs"
        test_dir.mkdir()

        # Create more files than limit
        for i in range(10):
            (test_dir / f"file{i}.md").write_text(f"# File {i}")

        mock_add_dir.return_value = {
            "total": 5,  # Limited to 5
            "created": 5,
            "skipped": 0,
            "indexed": 5,
            "errors": 0,
            "files": [],
        }

        # Execute with limit
        handle_file_add(str(test_dir), fetch_only=False, dry_run=False, limit=5, force=False)

        # Verify limit was applied (this would be done in handle_file_add)
        mock_add_dir.assert_called_once()

    @patch("kurt.commands.add_files.discover_markdown_files")
    @patch("kurt.commands.add_files.console")
    def test_dry_run_directory(self, mock_console, mock_discover, tmp_path):
        # Setup
        test_dir = tmp_path / "docs"
        test_dir.mkdir()

        file1 = test_dir / "file1.md"
        file2 = test_dir / "file2.md"
        file1.write_text("# File 1")
        file2.write_text("# File 2")

        mock_discover.return_value = [file1, file2]

        # Execute dry run
        handle_file_add(str(test_dir), fetch_only=False, dry_run=True, limit=None, force=False)

        # Should discover but not add
        mock_discover.assert_called_once_with(test_dir, recursive=True)

        # Should print preview
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Would add" in str(call) for call in print_calls)

    @patch("kurt.commands.add_files.add_directory")
    @patch("kurt.commands.add_files.should_confirm_file_batch")
    @patch("kurt.commands.add_files.click.confirm")
    def test_prompts_for_confirmation_on_large_batch(
        self, mock_confirm, mock_should_confirm, mock_add_dir, tmp_path
    ):
        # Setup
        test_dir = tmp_path / "docs"
        test_dir.mkdir()

        # Create many files
        for i in range(30):
            (test_dir / f"file{i}.md").write_text(f"# File {i}")

        mock_should_confirm.return_value = True
        mock_confirm.return_value = True  # User confirms

        # Mock discover to return file list
        with patch("kurt.commands.add_files.discover_markdown_files") as mock_discover:
            mock_discover.return_value = list(test_dir.glob("*.md"))

            mock_add_dir.return_value = {
                "total": 30,
                "created": 30,
                "skipped": 0,
                "indexed": 30,
                "errors": 0,
                "files": [],
            }

            # Execute
            handle_file_add(str(test_dir), fetch_only=False, dry_run=False, limit=None, force=False)

            # Should prompt for confirmation
            mock_should_confirm.assert_called_once()
            mock_confirm.assert_called_once()

    @patch("kurt.commands.add_files.add_directory")
    @patch("kurt.commands.add_files.should_confirm_file_batch")
    @patch("kurt.commands.add_files.click.confirm")
    def test_aborts_when_user_declines_confirmation(
        self, mock_confirm, mock_should_confirm, mock_add_dir, tmp_path
    ):
        # Setup
        test_dir = tmp_path / "docs"
        test_dir.mkdir()

        for i in range(30):
            (test_dir / f"file{i}.md").write_text(f"# File {i}")

        mock_should_confirm.return_value = True
        mock_confirm.return_value = False  # User declines

        # Mock discover
        with patch("kurt.commands.add_files.discover_markdown_files") as mock_discover:
            mock_discover.return_value = list(test_dir.glob("*.md"))

            # Execute
            handle_file_add(str(test_dir), fetch_only=False, dry_run=False, limit=None, force=False)

            # Should not call add_directory
            mock_add_dir.assert_not_called()

    @patch("kurt.commands.add_files.add_directory")
    @patch("kurt.commands.add_files.should_confirm_file_batch")
    def test_force_flag_skips_confirmation(self, mock_should_confirm, mock_add_dir, tmp_path):
        # Setup
        test_dir = tmp_path / "docs"
        test_dir.mkdir()

        for i in range(30):
            (test_dir / f"file{i}.md").write_text(f"# File {i}")

        mock_should_confirm.return_value = False  # Force flag prevents confirmation

        mock_add_dir.return_value = {
            "total": 30,
            "created": 30,
            "skipped": 0,
            "indexed": 30,
            "errors": 0,
            "files": [],
        }

        # Execute with force
        handle_file_add(str(test_dir), fetch_only=False, dry_run=False, limit=None, force=True)

        # Should not prompt, just proceed
        mock_should_confirm.assert_called_once_with(30, force=True)
        mock_add_dir.assert_called_once()

    @patch("kurt.commands.add_files.console")
    def test_handles_invalid_file_path(self, mock_console):
        # Execute with non-existent path
        with pytest.raises(SystemExit):  # click.Abort causes SystemExit in tests
            handle_file_add(
                "/non/existent/path.md", fetch_only=False, dry_run=False, limit=None, force=False
            )

    @patch("kurt.commands.add_files.add_directory")
    @patch("kurt.commands.add_files.console")
    def test_displays_error_details(self, mock_console, mock_add_dir, tmp_path):
        # Setup
        test_dir = tmp_path / "docs"
        test_dir.mkdir()

        # Mock errors in result
        mock_add_dir.return_value = {
            "total": 3,
            "created": 1,
            "skipped": 1,
            "indexed": 1,
            "errors": 1,
            "files": [
                {"path": "file1.md", "created": True},
                {"path": "file2.md", "skipped": True},
                {"path": "file3.md", "error": "Invalid format"},
            ],
        }

        # Execute
        handle_file_add(str(test_dir), fetch_only=False, dry_run=False, limit=None, force=False)

        # Should display error information
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("error" in str(call).lower() for call in print_calls)

    @patch("kurt.commands.add_files.add_single_file")
    @patch("kurt.commands.add_files.console")
    def test_displays_skip_reason_for_duplicate(self, mock_console, mock_add_single, tmp_path):
        # Setup
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        mock_add_single.return_value = {
            "doc_id": "existing-id",
            "created": False,
            "indexed": False,
            "skipped": True,
            "reason": "Content already exists",
        }

        # Execute
        handle_file_add(str(test_file), fetch_only=False, dry_run=False, limit=None, force=False)

        # Should display skip reason
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("already exists" in str(call).lower() for call in print_calls)
