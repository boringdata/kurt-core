"""Domain analytics workflow for syncing metrics from analytics platforms."""

from kurt_new.workflows.domain_analytics.adapters import (
    AnalyticsAdapter,
    AnalyticsMetrics,
    get_adapter,
)
from kurt_new.workflows.domain_analytics.config import (
    DomainAnalyticsConfig,
    add_platform_config,
    analytics_config_exists,
    create_template_config,
    get_platform_config,
    platform_configured,
)
from kurt_new.workflows.domain_analytics.models import (
    AnalyticsDomain,
    AnalyticsStatus,
    PageAnalytics,
)
from kurt_new.workflows.domain_analytics.utils import normalize_url_for_analytics
from kurt_new.workflows.domain_analytics.workflow import (
    domain_analytics_workflow,
    run_domain_analytics,
)

__all__ = [
    # Config
    "DomainAnalyticsConfig",
    "get_platform_config",
    "add_platform_config",
    "platform_configured",
    "analytics_config_exists",
    "create_template_config",
    # Workflow
    "domain_analytics_workflow",
    "run_domain_analytics",
    # Adapters
    "get_adapter",
    "AnalyticsAdapter",
    "AnalyticsMetrics",
    # Models
    "AnalyticsDomain",
    "AnalyticsStatus",
    "PageAnalytics",
    # Utils
    "normalize_url_for_analytics",
]
