"""
Kurt Models - dbt-style pipeline models.

Models are organized by layer:
- landing/: Raw data ingestion (discovery, fetch)
- staging/: Transformed/processed data (sections, entities, claims)

Usage:
    # Run a specific model
    kurt run landing.discovery --source-url https://example.com
    kurt run landing.fetch --ids doc-1,doc-2
    kurt run staging.sections

    # Run all models in a layer
    kurt run landing
    kurt run staging

Table naming convention:
    Model name: landing.fetch -> Table name: landing_fetch
"""

# Import models to register them with the framework
from . import landing, staging

__all__ = ["landing", "staging"]
