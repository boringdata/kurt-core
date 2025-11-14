"""
Shared test fixtures for Kurt tests.

Provides isolated temporary project setup for running tests.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def reset_dbos_state():
    """
    Reset DBOS state between tests to prevent state pollution.

    This fixture:
    - Resets the _dbos_initialized flag
    - Destroys DBOS instance to clean up threads and connections
    - Should be used by tests that use DBOS/workflows

    Usage:
        def test_something(tmp_project, reset_dbos_state):
            # Test runs with clean DBOS state
    """
    # Import here to avoid circular dependencies
    import kurt.workflows

    # Reset global state before test
    kurt.workflows._dbos_initialized = False

    # Try to cleanup any existing DBOS instance
    try:
        import dbos._dbos as dbos_module

        # DBOS stores the global instance in _dbos_global_instance
        if (
            hasattr(dbos_module, "_dbos_global_instance")
            and dbos_module._dbos_global_instance is not None
        ):
            instance = dbos_module._dbos_global_instance
            if (
                hasattr(instance, "_destroy")
                and hasattr(instance, "_initialized")
                and instance._initialized
            ):
                # Destroy with short timeout to clean up threads
                instance._destroy(workflow_completion_timeout_sec=0)
            dbos_module._dbos_global_instance = None
    except (ImportError, AttributeError, Exception):
        # Ignore errors during cleanup
        pass

    yield

    # Reset global state after test
    kurt.workflows._dbos_initialized = False

    # Cleanup DBOS instance after test
    try:
        import dbos._dbos as dbos_module

        if (
            hasattr(dbos_module, "_dbos_global_instance")
            and dbos_module._dbos_global_instance is not None
        ):
            instance = dbos_module._dbos_global_instance
            if (
                hasattr(instance, "_destroy")
                and hasattr(instance, "_initialized")
                and instance._initialized
            ):
                # Destroy with short timeout to clean up threads
                instance._destroy(workflow_completion_timeout_sec=0)
            dbos_module._dbos_global_instance = None
    except (ImportError, AttributeError, Exception):
        # Ignore errors during cleanup
        pass


@pytest.fixture
def tmp_project(monkeypatch, tmp_path, reset_dbos_state):
    """
    Create isolated temporary Kurt project for testing.

    This fixture:
    - Creates a temp directory for the project
    - Changes working directory to temp project
    - Creates kurt.config file
    - Creates sources/ directory
    - Resets DBOS state for clean test isolation
    - Cleans up after test

    Usage:
        def test_something(tmp_project):
            # Test runs in isolated temp project
            # kurt.config exists
            # sources/ directory exists
            # Can run CLI commands without affecting real project
    """
    # Create temp project structure
    project_dir = tmp_path / "test-kurt-project"
    project_dir.mkdir()

    # Create standard directories
    (project_dir / "sources").mkdir()
    (project_dir / "projects").mkdir()
    (project_dir / "rules").mkdir()

    # Change to temp project directory first (so create_config writes to correct location)
    monkeypatch.chdir(project_dir)

    # Create kurt.config using new format
    from kurt.config.base import create_config

    create_config()

    # Create .kurt directory for database
    kurt_dir = project_dir / ".kurt"
    kurt_dir.mkdir()

    # Set environment variable so Kurt finds this config
    monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))

    # Clear any cached config in the config module
    try:
        import kurt.config.base as config_module

        if hasattr(config_module, "_cached_config"):
            config_module._cached_config = None
    except (ImportError, AttributeError):
        pass

    # Run migrations to initialize database
    from kurt.db.migrations.utils import apply_migrations

    apply_migrations(auto_confirm=True)

    yield project_dir

    # Cleanup happens automatically with tmp_path


@pytest.fixture
def tmp_project_without_migrations(monkeypatch, tmp_path):
    """
    Create isolated temporary Kurt project WITHOUT running migrations.

    Use this fixture for testing the init command or migrations themselves.
    For most tests, use isolated_cli_runner instead.
    """
    # Create temp project structure
    project_dir = tmp_path / "test-kurt-project"
    project_dir.mkdir()

    # Create standard directories
    (project_dir / "sources").mkdir()
    (project_dir / "projects").mkdir()
    (project_dir / "rules").mkdir()

    # Change to temp project directory first
    monkeypatch.chdir(project_dir)

    # Create kurt.config using new format
    from kurt.config.base import create_config

    create_config()

    # Create .kurt directory for database
    kurt_dir = project_dir / ".kurt"
    kurt_dir.mkdir()

    # Set environment variable so Kurt finds this config
    monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))

    # NOTE: Do NOT run migrations - leave database empty

    yield project_dir

    # Cleanup happens automatically with tmp_path


@pytest.fixture
def isolated_cli_runner(tmp_project):
    """
    Click CLI runner with isolated temp project.

    This fixture combines tmp_project with Click's CliRunner
    for testing CLI commands in isolation.

    Usage:
        def test_init_command(isolated_cli_runner):
            runner, project_dir = isolated_cli_runner
            result = runner.invoke(main, ['init'])
            assert result.exit_code == 0
    """
    from click.testing import CliRunner

    runner = CliRunner(
        env={"KURT_PROJECT_ROOT": str(tmp_project)}  # Ensure Kurt uses temp project
    )

    return runner, tmp_project


@pytest.fixture
def mock_http_responses():
    """
    Mock all HTTP responses for map command tests.

    This fixture prevents actual network calls and makes tests fast.
    It mocks:
    - httpx.get() for sitemap and webpage fetching
    - trafilatura functions for content extraction

    Returns:
        Dict with mock objects for customization in tests
    """
    # Mock httpx.get for HTTP requests
    with patch("httpx.get") as mock_get, patch("httpx.Client") as mock_client:
        # Default successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://example.com/page1</loc></url>
    <url><loc>https://example.com/page2</loc></url>
    <url><loc>https://example.com/page3</loc></url>
</urlset>"""
        mock_response.content = mock_response.text.encode("utf-8")

        mock_get.return_value = mock_response

        # Mock httpx.Client context manager
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        yield {"mock_get": mock_get, "mock_client": mock_client, "mock_response": mock_response}


@pytest.fixture
def mock_map_functions():
    """
    Mock the core map.py functions to avoid network calls.

    This is a higher-level mock that patches the discovery functions
    directly in the map module.

    Returns:
        Dict with mock functions for customization
    """
    with (
        patch("kurt.content.map._discover_sitemap_urls") as mock_sitemap,
        patch("kurt.content.map.identify_blogroll_candidates") as mock_blogroll,
        patch("kurt.content.map.extract_chronological_content") as mock_extract,
        patch("kurt.content.map.crawl_website") as mock_crawler,
    ):
        # Default return values
        mock_sitemap.return_value = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
        ]

        mock_blogroll.return_value = []  # No blogrolls by default

        mock_extract.return_value = []  # No extracted content by default

        mock_crawler.return_value = []  # No crawled URLs by default

        yield {
            "mock_sitemap": mock_sitemap,
            "mock_blogroll": mock_blogroll,
            "mock_extract": mock_extract,
            "mock_crawler": mock_crawler,
        }


@pytest.fixture
def isolated_cli_runner_with_mocks(isolated_cli_runner, mock_map_functions):
    """
    Combined fixture: isolated CLI runner + mocked map functions.

    Use this for fast map command tests that don't need real network calls.

    Usage:
        def test_map_url(isolated_cli_runner_with_mocks):
            runner, project_dir, mocks = isolated_cli_runner_with_mocks

            # Customize mock return values
            mocks['mock_sitemap'].return_value = ["https://example.com/custom"]

            # Run command
            result = runner.invoke(main, ["map", "url", "https://example.com"])
            assert result.exit_code == 0
    """
    runner, project_dir = isolated_cli_runner
    return runner, project_dir, mock_map_functions


@pytest.fixture
def mock_dspy_signature():
    """
    Generic fixture for mocking DSPy signature calls.

    This fixture allows you to mock any DSPy signature by providing the signature
    name and the return value. It patches dspy.ChainOfThought to return your mock values.

    Usage:
        def test_with_mock_signature(mock_dspy_signature):
            # Define what the LLM should return
            mock_output = MySignatureOutput(
                field1="value1",
                field2="value2"
            )

            # Set up the mock
            with mock_dspy_signature("MySignature", mock_output):
                # Call your function that uses dspy.ChainOfThought(MySignature)
                result = my_function()
                assert result.field1 == "value1"

    Advanced usage with dynamic responses:
        def test_with_dynamic_responses(mock_dspy_signature):
            # Define a function that returns different values based on input
            def dynamic_response(**kwargs):
                input_text = kwargs.get('input_field')
                if "python" in input_text.lower():
                    return OutputModel(language="Python")
                else:
                    return OutputModel(language="Unknown")

            with mock_dspy_signature("MySignature", dynamic_response):
                result = my_function()

    Multiple signatures:
        def test_multiple_signatures(mock_dspy_signature):
            # You can nest multiple mocks
            with mock_dspy_signature("Signature1", output1):
                with mock_dspy_signature("Signature2", output2):
                    result = my_function()
    """
    from contextlib import contextmanager

    @contextmanager
    def _mock_signature(signature_name: str, return_value):
        """
        Context manager for mocking a DSPy signature.

        Args:
            signature_name: Name of the signature class (for reference/debugging)
            return_value: Either:
                - A concrete return value (Pydantic model instance)
                - A callable that takes **kwargs and returns the output
        """
        with patch("dspy.ChainOfThought") as mock_cot:
            # Create a mock that can be called
            mock_module = MagicMock()

            def create_mock_result(output):
                """
                Create a mock result that properly mimics DSPy ChainOfThought output.

                DSPy ChainOfThought returns an object where OutputFields are attributes.
                For signatures with multiple OutputFields, each field becomes an attribute.
                For signatures with a single OutputField, we default to 'resolutions'.
                """
                mock_result = MagicMock()

                # Check if output has fields
                # Check Pydantic v2 first (model_fields on class), then v1 (__fields__)
                if hasattr(output.__class__, "model_fields"):
                    # Pydantic v2 - check fields from class, not instance
                    model_fields = output.__class__.model_fields
                    # For GroupResolution (single field 'resolutions'), we want result.resolutions = GroupResolution object
                    # Not result.resolutions = list
                    if len(model_fields) == 1 and "resolutions" in model_fields:
                        # Single-field case: ResolveEntityGroup signature
                        # result.resolutions should be the GroupResolution object itself
                        mock_result.resolutions = output
                    else:
                        # Multi-field case: copy each field
                        for field_name in model_fields.keys():
                            setattr(mock_result, field_name, getattr(output, field_name))
                elif hasattr(output, "__fields__") and len(output.__fields__) > 0:
                    # Pydantic v1 or custom class with __fields__
                    # Copy all fields as attributes (for multi-field outputs like ClusteringResult)
                    for field_name in output.__fields__.keys():
                        setattr(mock_result, field_name, getattr(output, field_name))
                else:
                    # No fields detected - assume single output value for 'resolutions' field
                    mock_result.resolutions = output

                return mock_result

            if callable(return_value) and not isinstance(return_value, MagicMock):
                # If return_value is a function, use it to generate responses
                def side_effect(*args, **kwargs):
                    output = return_value(**kwargs)
                    return create_mock_result(output)

                mock_module.side_effect = side_effect
            else:
                # Static return value
                mock_module.return_value = create_mock_result(return_value)

            mock_cot.return_value = mock_module
            yield mock_module

    return _mock_signature


@pytest.fixture
def mock_all_llm_calls():
    """
    Mock all DSPy/LLM calls to avoid API calls during tests.

    This fixture patches embeddings, LM initialization, and DSPy configuration
    to prevent tests from making real API calls to OpenAI.

    Usage:
        def test_something(mock_all_llm_calls):
            # Test code that uses DSPy - no API calls will be made
            pass

    Note: This is NOT autouse to avoid interfering with tests that have their
    own specific mocking strategies. Tests that need this should request it explicitly.
    """
    with (
        patch("kurt.content.indexing_helpers._generate_embeddings") as mock_gen_embeddings,
        patch("dspy.Embedder") as mock_embedder_class,
        patch("dspy.LM") as mock_lm_class,
        patch("dspy.configure") as mock_configure,
    ):
        # Return fake embeddings - match the number of texts input
        def fake_embeddings(texts):
            return [[0.1] * 384 for _ in texts]

        mock_gen_embeddings.side_effect = fake_embeddings

        # Mock Embedder
        mock_embedder_instance = MagicMock()
        mock_embedder_instance.return_value = [[0.1] * 384]
        mock_embedder_class.return_value = mock_embedder_instance

        # Mock LM to return a fake LM instance
        mock_lm_instance = MagicMock()
        mock_lm_class.return_value = mock_lm_instance

        # Mock dspy.settings.lm to return the mock LM
        with patch("dspy.settings") as mock_settings:
            mock_settings.lm = mock_lm_instance
            yield {
                "gen_embeddings": mock_gen_embeddings,
                "embedder": mock_embedder_instance,
                "lm": mock_lm_instance,
                "configure": mock_configure,
            }
