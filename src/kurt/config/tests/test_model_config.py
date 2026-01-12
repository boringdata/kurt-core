"""Tests for StepConfig and ConfigParam classes."""

from typing import Optional

import pytest

from kurt.config import ConfigParam, ModelConfig, StepConfig
from kurt.config.base import get_config_file_path


class TestConfigParam:
    """Test ConfigParam metadata class."""

    def test_configparam_defaults(self):
        """Test ConfigParam with default values."""
        param = ConfigParam(default=50)
        assert param.default == 50
        assert param.fallback is None
        assert param.description == ""
        assert param.ge is None
        assert param.le is None

    def test_configparam_with_fallback(self):
        """Test ConfigParam with fallback key."""
        param = ConfigParam(fallback="INDEXING_LLM_MODEL")
        assert param.default is None
        assert param.fallback == "INDEXING_LLM_MODEL"

    def test_configparam_with_constraints(self):
        """Test ConfigParam with validation constraints."""
        param = ConfigParam(default=0.25, ge=0.0, le=1.0, description="DBSCAN epsilon")
        assert param.default == 0.25
        assert param.ge == 0.0
        assert param.le == 1.0
        assert param.description == "DBSCAN epsilon"

    def test_configparam_repr(self):
        """Test ConfigParam string representation."""
        param = ConfigParam(default=50, fallback="MAX_CONCURRENT", ge=1, le=100)
        repr_str = repr(param)
        assert "default=50" in repr_str
        assert "fallback='MAX_CONCURRENT'" in repr_str
        assert "ge=1" in repr_str
        assert "le=100" in repr_str


class TestStepConfigBasic:
    """Test StepConfig base class."""

    def test_step_config_direct_instantiation(self, tmp_project):
        """Test direct instantiation without config file."""

        class TestConfig(StepConfig):
            value: int = ConfigParam(default=42)
            name: str = ConfigParam(default="test")

        config = TestConfig()
        assert config.value == 42
        assert config.name == "test"

    def test_step_config_with_overrides(self, tmp_project):
        """Test direct instantiation with overrides."""

        class TestConfig(StepConfig):
            value: int = ConfigParam(default=42)
            name: str = ConfigParam(default="test")

        config = TestConfig(value=100, name="custom")
        assert config.value == 100
        assert config.name == "custom"

    def test_step_config_from_config_module_only(self, tmp_project):
        """Test from_config with module-only name (workflow config)."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write("TEST.VALUE=100\n")
            f.write('TEST.NAME="custom"\n')

        class TestConfig(StepConfig):
            value: int = ConfigParam(default=42)
            name: str = ConfigParam(default="test")

        config = TestConfig.from_config("test")
        assert config.value == 100
        assert config.name == "custom"

    def test_step_config_from_config_module_step(self, tmp_project):
        """Test from_config with module.step name (step config)."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write("TEST.MODEL.VALUE=100\n")
            f.write('TEST.MODEL.NAME="custom"\n')

        class TestConfig(StepConfig):
            value: int = ConfigParam(default=42)
            name: str = ConfigParam(default="test")

        config = TestConfig.from_config("test.model")
        assert config.value == 100
        assert config.name == "custom"

    def test_step_config_from_config_with_overrides(self, tmp_project):
        """Test from_config with overrides."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write("TEST.VALUE=100\n")
            f.write('TEST.NAME="from_config"\n')

        class TestConfig(StepConfig):
            value: int = ConfigParam(default=42)
            name: str = ConfigParam(default="test")

        # Override name but keep value from config
        config = TestConfig.from_config("test", name="override")
        assert config.value == 100
        assert config.name == "override"

    def test_step_config_fallback_to_global(self, tmp_project):
        """Test StepConfig falls back to global config."""

        class TestConfig(StepConfig):
            llm_model: str = ConfigParam(fallback="INDEXING_LLM_MODEL")

        config = TestConfig.from_config("test")
        assert config.llm_model == "openai/gpt-4o-mini"

    def test_step_config_step_specific_overrides_fallback(self, tmp_project):
        """Test step-specific config overrides fallback."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write('TEST.MODEL.LLM_MODEL="anthropic/claude-3-haiku"\n')

        class TestConfig(StepConfig):
            llm_model: str = ConfigParam(fallback="INDEXING_LLM_MODEL")

        config = TestConfig.from_config("test.model")
        assert config.llm_model == "anthropic/claude-3-haiku"


class TestStepConfigTypeCoercion:
    """Test type coercion in StepConfig."""

    def test_type_coercion_int(self, tmp_project):
        """Test StepConfig coerces string to int."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write("TEST.COUNT=42\n")

        class TestConfig(StepConfig):
            count: int = ConfigParam(default=0)

        config = TestConfig.from_config("test")
        assert config.count == 42
        assert isinstance(config.count, int)

    def test_type_coercion_float(self, tmp_project):
        """Test StepConfig coerces string to float."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write("TEST.EPS=0.25\n")

        class TestConfig(StepConfig):
            eps: float = ConfigParam(default=0.5)

        config = TestConfig.from_config("test")
        assert config.eps == 0.25
        assert isinstance(config.eps, float)

    def test_type_coercion_bool(self, tmp_project):
        """Test StepConfig coerces string to bool."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write("TEST.ENABLED=true\n")
            f.write("TEST.DISABLED=false\n")

        class TestConfig(StepConfig):
            enabled: bool = ConfigParam(default=False)
            disabled: bool = ConfigParam(default=True)

        config = TestConfig.from_config("test")
        assert config.enabled is True
        assert config.disabled is False

    def test_type_coercion_optional(self, tmp_project):
        """Test StepConfig with optional field."""

        class TestConfig(StepConfig):
            optional_value: Optional[str] = ConfigParam(default=None)

        config = TestConfig.from_config("test")
        assert config.optional_value is None


class TestStepConfigValidation:
    """Test validation constraints in StepConfig."""

    def test_validation_ge(self, tmp_project):
        """Test StepConfig validates ge constraint."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write("TEST.VALUE=-1\n")

        class TestConfig(StepConfig):
            value: int = ConfigParam(default=0, ge=0)

        with pytest.raises(ValueError, match="must be >= 0"):
            TestConfig.from_config("test")

    def test_validation_le(self, tmp_project):
        """Test StepConfig validates le constraint."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write("TEST.VALUE=200\n")

        class TestConfig(StepConfig):
            value: int = ConfigParam(default=50, le=100)

        with pytest.raises(ValueError, match="must be <= 100"):
            TestConfig.from_config("test")


class TestStepConfigHelpers:
    """Test StepConfig helper methods."""

    def test_get_config_keys_module_only(self, tmp_project):
        """Test get_config_keys for module-only config."""

        class TestConfig(StepConfig):
            max_pages: int = ConfigParam(default=1000)
            dry_run: bool = ConfigParam(default=False)

        keys = TestConfig.get_config_keys("map")
        assert keys == {
            "max_pages": "MAP.MAX_PAGES",
            "dry_run": "MAP.DRY_RUN",
        }

    def test_get_config_keys_module_step(self, tmp_project):
        """Test get_config_keys for module.step config."""

        class TestConfig(StepConfig):
            eps: float = ConfigParam(default=0.25)
            min_samples: int = ConfigParam(default=2)

        keys = TestConfig.get_config_keys("indexing.entity_clustering")
        assert keys == {
            "eps": "INDEXING.ENTITY_CLUSTERING.EPS",
            "min_samples": "INDEXING.ENTITY_CLUSTERING.MIN_SAMPLES",
        }

    def test_get_param_info(self, tmp_project):
        """Test get_param_info returns correct metadata."""

        class TestConfig(StepConfig):
            eps: float = ConfigParam(default=0.25, ge=0.0, le=1.0, description="DBSCAN epsilon")
            llm_model: str = ConfigParam(fallback="INDEXING_LLM_MODEL")

        info = TestConfig.get_param_info()
        assert "eps" in info
        assert info["eps"]["default"] == 0.25
        assert info["eps"]["ge"] == 0.0
        assert info["eps"]["le"] == 1.0
        assert info["eps"]["description"] == "DBSCAN epsilon"
        assert info["llm_model"]["fallback"] == "INDEXING_LLM_MODEL"


class TestWorkflowConfigs:
    """Test realistic workflow config scenarios."""

    def test_map_config_workflow_level(self, tmp_project):
        """Test MapConfig-style workflow config."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write("MAP.MAX_PAGES=500\n")
            f.write("MAP.DRY_RUN=true\n")

        class MapConfig(StepConfig):
            max_pages: int = ConfigParam(default=1000, ge=1, le=10000)
            max_depth: Optional[int] = ConfigParam(default=None, ge=1, le=5)
            dry_run: bool = ConfigParam(default=False)

        config = MapConfig.from_config("map")
        assert config.max_pages == 500
        assert config.max_depth is None  # Not set, uses default
        assert config.dry_run is True

    def test_map_discovery_step_level(self, tmp_project):
        """Test step-level config within a workflow."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write("MAP.DISCOVERY.MAX_DEPTH=3\n")
            f.write("MAP.DISCOVERY.TIMEOUT=60\n")

        class MapDiscoveryConfig(StepConfig):
            max_depth: int = ConfigParam(default=5, ge=1, le=10)
            timeout: int = ConfigParam(default=30, ge=1, le=300)

        config = MapDiscoveryConfig.from_config("map.discovery")
        assert config.max_depth == 3
        assert config.timeout == 60

    def test_fetch_config_with_fallback(self, tmp_project):
        """Test FetchConfig-style with fallback to global config."""

        class FetchConfig(StepConfig):
            fetch_engine: str = ConfigParam(
                default="trafilatura", fallback="INGESTION_FETCH_ENGINE"
            )
            embedding_max_chars: int = ConfigParam(default=1000, ge=100, le=5000)

        config = FetchConfig.from_config("fetch")
        # Falls back to INGESTION_FETCH_ENGINE from global config
        assert config.fetch_engine == "trafilatura"
        assert config.embedding_max_chars == 1000

    def test_fetch_extract_step_with_fallback(self, tmp_project):
        """Test step config with fallback to global."""

        class FetchExtractConfig(StepConfig):
            llm_model: str = ConfigParam(fallback="INDEXING_LLM_MODEL")
            max_concurrent: int = ConfigParam(default=10, fallback="MAX_CONCURRENT_INDEXING")

        config = FetchExtractConfig.from_config("fetch.extract")
        assert config.llm_model == "openai/gpt-4o-mini"
        assert config.max_concurrent == 50  # Falls back to MAX_CONCURRENT_INDEXING


class TestWorkflowFallback:
    """Test workflow_fallback feature for step configs."""

    def test_step_inherits_from_workflow(self, tmp_project):
        """Test step config inherits value from workflow config."""
        config_file = get_config_file_path()

        # Set workflow-level config only
        with open(config_file, "a") as f:
            f.write("MAP.MAX_DEPTH=5\n")

        class DiscoveryStepConfig(StepConfig):
            max_depth: int = ConfigParam(default=3, workflow_fallback=True)
            timeout: int = ConfigParam(default=30)

        config = DiscoveryStepConfig.from_config("map.discovery")
        assert config.max_depth == 5  # Inherited from MAP.MAX_DEPTH
        assert config.timeout == 30  # Default (not in config)

    def test_step_overrides_workflow(self, tmp_project):
        """Test step-specific config overrides workflow config."""
        config_file = get_config_file_path()

        # Set both workflow and step level
        with open(config_file, "a") as f:
            f.write("MAP.MAX_DEPTH=5\n")
            f.write("MAP.DISCOVERY.MAX_DEPTH=3\n")

        class DiscoveryStepConfig(StepConfig):
            max_depth: int = ConfigParam(default=10, workflow_fallback=True)

        config = DiscoveryStepConfig.from_config("map.discovery")
        assert config.max_depth == 3  # Step-specific overrides workflow

    def test_workflow_fallback_with_global_fallback(self, tmp_project):
        """Test workflow_fallback combined with global fallback."""

        # Only global config set (no workflow or step level)
        class ExtractStepConfig(StepConfig):
            llm_model: str = ConfigParam(workflow_fallback=True, fallback="INDEXING_LLM_MODEL")

        config = ExtractStepConfig.from_config("fetch.extract")
        assert config.llm_model == "openai/gpt-4o-mini"  # Falls back to global

    def test_workflow_fallback_priority(self, tmp_project):
        """Test fallback priority: step > workflow > global > default."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write("FETCH.FETCH_ENGINE=httpx\n")  # Workflow level

        class ExtractStepConfig(StepConfig):
            fetch_engine: str = ConfigParam(
                default="trafilatura",
                workflow_fallback=True,
                fallback="INGESTION_FETCH_ENGINE",
            )

        config = ExtractStepConfig.from_config("fetch.extract")
        assert config.fetch_engine == "httpx"  # Workflow level wins over global

    def test_no_workflow_fallback_ignores_workflow(self, tmp_project):
        """Test that without workflow_fallback, workflow config is ignored."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write("MAP.MAX_DEPTH=5\n")

        class DiscoveryStepConfig(StepConfig):
            max_depth: int = ConfigParam(default=3)  # No workflow_fallback

        config = DiscoveryStepConfig.from_config("map.discovery")
        assert config.max_depth == 3  # Uses default, ignores MAP.MAX_DEPTH

    def test_get_config_keys_shows_fallback_chain(self, tmp_project):
        """Test get_config_keys shows workflow fallback in output."""

        class DiscoveryStepConfig(StepConfig):
            max_depth: int = ConfigParam(default=3, workflow_fallback=True)
            llm_model: str = ConfigParam(fallback="INDEXING_LLM_MODEL")
            timeout: int = ConfigParam(default=30)

        keys = DiscoveryStepConfig.get_config_keys("map.discovery")
        assert "-> MAP.MAX_DEPTH" in keys["max_depth"]
        assert "-> INDEXING_LLM_MODEL" in keys["llm_model"]
        assert "->" not in keys["timeout"]


class TestModelConfigAlias:
    """Test that ModelConfig is an alias for StepConfig."""

    def test_model_config_is_step_config(self):
        """Test ModelConfig is alias for StepConfig."""
        assert ModelConfig is StepConfig

    def test_model_config_works_same(self, tmp_project):
        """Test ModelConfig works the same as StepConfig."""

        class TestConfig(ModelConfig):
            value: int = ConfigParam(default=42)

        config = TestConfig.from_config("test")
        assert config.value == 42
