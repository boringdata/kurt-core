"""Tests for ModelConfig and ConfigParam classes."""

from typing import Optional

import pytest

from kurt.config import ConfigParam, ModelConfig
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


class TestModelConfig:
    """Test ModelConfig base class."""

    def test_model_config_basic(self, tmp_project):
        """Test basic ModelConfig subclass."""

        class TestConfig(ModelConfig):
            value: int = ConfigParam(default=42)
            name: str = ConfigParam(default="test")

        config = TestConfig.load("test.model")
        assert config.value == 42
        assert config.name == "test"

    def test_model_config_with_step_specific_values(self, tmp_project):
        """Test ModelConfig loads step-specific values from config."""
        config_file = get_config_file_path()

        # Add step-specific config
        with open(config_file, "a") as f:
            f.write("TEST.MODEL.VALUE=100\n")
            f.write('TEST.MODEL.NAME="custom"\n')

        class TestConfig(ModelConfig):
            value: int = ConfigParam(default=42)
            name: str = ConfigParam(default="test")

        config = TestConfig.load("test.model")
        assert config.value == 100
        assert config.name == "custom"

    def test_model_config_fallback_to_global(self, tmp_project):
        """Test ModelConfig falls back to global config."""

        class TestConfig(ModelConfig):
            llm_model: str = ConfigParam(fallback="INDEXING_LLM_MODEL")

        config = TestConfig.load("test.model")
        # Should fall back to INDEXING_LLM_MODEL from default config
        assert config.llm_model == "openai/gpt-4o-mini"

    def test_model_config_step_specific_overrides_fallback(self, tmp_project):
        """Test step-specific config overrides fallback."""
        config_file = get_config_file_path()

        # Add step-specific config
        with open(config_file, "a") as f:
            f.write('TEST.MODEL.LLM_MODEL="anthropic/claude-3-haiku"\n')

        class TestConfig(ModelConfig):
            llm_model: str = ConfigParam(fallback="INDEXING_LLM_MODEL")

        config = TestConfig.load("test.model")
        # Step-specific should override fallback
        assert config.llm_model == "anthropic/claude-3-haiku"

    def test_model_config_type_coercion_int(self, tmp_project):
        """Test ModelConfig coerces string to int."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write("TEST.MODEL.COUNT=42\n")

        class TestConfig(ModelConfig):
            count: int = ConfigParam(default=0)

        config = TestConfig.load("test.model")
        assert config.count == 42
        assert isinstance(config.count, int)

    def test_model_config_type_coercion_float(self, tmp_project):
        """Test ModelConfig coerces string to float."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write("TEST.MODEL.EPS=0.25\n")

        class TestConfig(ModelConfig):
            eps: float = ConfigParam(default=0.5)

        config = TestConfig.load("test.model")
        assert config.eps == 0.25
        assert isinstance(config.eps, float)

    def test_model_config_type_coercion_bool(self, tmp_project):
        """Test ModelConfig coerces string to bool."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write("TEST.MODEL.ENABLED=true\n")
            f.write("TEST.MODEL.DISABLED=false\n")

        class TestConfig(ModelConfig):
            enabled: bool = ConfigParam(default=False)
            disabled: bool = ConfigParam(default=True)

        config = TestConfig.load("test.model")
        assert config.enabled is True
        assert config.disabled is False

    def test_model_config_validation_ge(self, tmp_project):
        """Test ModelConfig validates ge constraint."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write("TEST.MODEL.VALUE=-1\n")

        class TestConfig(ModelConfig):
            value: int = ConfigParam(default=0, ge=0)

        with pytest.raises(ValueError, match="must be >= 0"):
            TestConfig.load("test.model")

    def test_model_config_validation_le(self, tmp_project):
        """Test ModelConfig validates le constraint."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write("TEST.MODEL.VALUE=200\n")

        class TestConfig(ModelConfig):
            value: int = ConfigParam(default=50, le=100)

        with pytest.raises(ValueError, match="must be <= 100"):
            TestConfig.load("test.model")

    def test_model_config_invalid_model_name(self, tmp_project):
        """Test ModelConfig raises error for invalid model name."""

        class TestConfig(ModelConfig):
            value: int = ConfigParam(default=0)

        with pytest.raises(ValueError, match="must be in format"):
            TestConfig.load("invalid")

    def test_model_config_get_config_keys(self, tmp_project):
        """Test get_config_keys returns correct keys."""

        class TestConfig(ModelConfig):
            eps: float = ConfigParam(default=0.25)
            min_samples: int = ConfigParam(default=2)
            llm_model: str = ConfigParam(fallback="INDEXING_LLM_MODEL")

        keys = TestConfig.get_config_keys("indexing.entity_clustering")
        assert keys == {
            "eps": "INDEXING.ENTITY_CLUSTERING.EPS",
            "min_samples": "INDEXING.ENTITY_CLUSTERING.MIN_SAMPLES",
            "llm_model": "INDEXING.ENTITY_CLUSTERING.LLM_MODEL",
        }

    def test_model_config_get_param_info(self, tmp_project):
        """Test get_param_info returns correct metadata."""

        class TestConfig(ModelConfig):
            eps: float = ConfigParam(default=0.25, ge=0.0, le=1.0, description="DBSCAN epsilon")
            llm_model: str = ConfigParam(fallback="INDEXING_LLM_MODEL")

        info = TestConfig.get_param_info()
        assert "eps" in info
        assert info["eps"]["default"] == 0.25
        assert info["eps"]["ge"] == 0.0
        assert info["eps"]["le"] == 1.0
        assert info["eps"]["description"] == "DBSCAN epsilon"
        assert info["llm_model"]["fallback"] == "INDEXING_LLM_MODEL"

    def test_model_config_optional_field(self, tmp_project):
        """Test ModelConfig with optional field."""

        class TestConfig(ModelConfig):
            optional_value: Optional[str] = ConfigParam(default=None)

        config = TestConfig.load("test.model")
        assert config.optional_value is None

    def test_model_config_multi_part_step_name(self, tmp_project):
        """Test ModelConfig with multi-part step name."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write("INDEXING.SECTION_EXTRACTIONS.BATCH_SIZE=100\n")

        class TestConfig(ModelConfig):
            batch_size: int = ConfigParam(default=50)

        config = TestConfig.load("indexing.section_extractions")
        assert config.batch_size == 100


class TestModelConfigIntegration:
    """Integration tests for ModelConfig."""

    def test_realistic_entity_clustering_config(self, tmp_project):
        """Test realistic EntityClusteringConfig."""
        config_file = get_config_file_path()

        # Add some overrides
        with open(config_file, "a") as f:
            f.write("INDEXING.ENTITY_CLUSTERING.EPS=0.3\n")

        class EntityClusteringConfig(ModelConfig):
            eps: float = ConfigParam(
                default=0.25, ge=0.0, le=1.0, description="DBSCAN epsilon parameter"
            )
            min_samples: int = ConfigParam(
                default=2, ge=1, description="DBSCAN min_samples parameter"
            )
            llm_model: str = ConfigParam(
                fallback="INDEXING_LLM_MODEL", description="LLM for resolution"
            )

        config = EntityClusteringConfig.load("indexing.entity_clustering")

        # eps is overridden
        assert config.eps == 0.3
        # min_samples uses default
        assert config.min_samples == 2
        # llm_model falls back to global
        assert config.llm_model == "openai/gpt-4o-mini"

    def test_realistic_section_extractions_config(self, tmp_project):
        """Test realistic SectionExtractionsConfig."""

        class SectionExtractionsConfig(ModelConfig):
            llm_model: str = ConfigParam(
                fallback="INDEXING_LLM_MODEL", description="LLM model for extraction"
            )
            batch_size: int = ConfigParam(
                default=50, ge=1, le=200, description="Batch size for DSPy calls"
            )
            max_concurrent: int = ConfigParam(
                fallback="MAX_CONCURRENT_INDEXING", description="Max concurrent LLM calls"
            )

        config = SectionExtractionsConfig.load("indexing.section_extractions")

        # All use defaults/fallbacks
        assert config.llm_model == "openai/gpt-4o-mini"
        assert config.batch_size == 50
        assert config.max_concurrent == 50  # Falls back to MAX_CONCURRENT_INDEXING
