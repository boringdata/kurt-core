"""Domain analytics workflow for syncing metrics from analytics platforms."""

# Re-export from integration for convenience
from kurt.integrations.domains_analytics import (
    AnalyticsAdapter,
    AnalyticsMetrics,
    get_adapter,
)
from kurt.integrations.domains_analytics.config import (
    add_platform_config,
    analytics_config_exists,
    create_template_config,
    get_platform_config,
    platform_configured,
)
from kurt.integrations.domains_analytics.utils import normalize_url_for_analytics

# Workflow-specific exports
from kurt.workflows.domain_analytics.config import DomainAnalyticsConfig
from kurt.workflows.domain_analytics.models import (
    AnalyticsDomain,
    AnalyticsStatus,
    PageAnalytics,
)
from kurt.workflows.domain_analytics.workflow import (
    domain_analytics_workflow,
    run_domain_analytics,
)

__all__ = [
    # Workflow Config
    "DomainAnalyticsConfig",
    # Workflow
    "domain_analytics_workflow",
    "run_domain_analytics",
    # Models
    "AnalyticsDomain",
    "AnalyticsStatus",
    "PageAnalytics",
    # Re-exported from integration
    "get_adapter",
    "AnalyticsAdapter",
    "AnalyticsMetrics",
    "get_platform_config",
    "add_platform_config",
    "platform_configured",
    "analytics_config_exists",
    "create_template_config",
    "normalize_url_for_analytics",
]
