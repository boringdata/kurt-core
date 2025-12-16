"""Constants for content fetching module."""

# Firecrawl configuration
FIRECRAWL_DEFAULT_BATCH_SIZE = 100  # Maximum URLs per batch request
FIRECRAWL_MAX_CONCURRENCY = 10  # Default concurrent requests for batch

# HTTP configuration
HTTP_TIMEOUT = 30.0  # Timeout for HTTP requests in seconds

# Batch processing
LARGE_BATCH_WARNING_THRESHOLD = 100  # Warn when fetching this many documents
DEFAULT_MAX_CONCURRENT = 5  # Default parallel fetch operations

# Content processing
MAX_ANCHOR_TEXT_LENGTH = 500  # Maximum anchor text length for links
EMBEDDING_BYTES_TO_DIMS = 4  # Conversion factor for embedding dimensions

# Cost estimation
COST_PER_DOCUMENT = 0.005  # Estimated cost per document fetch

# Logging
LOG_BATCH_PROGRESS_INTERVAL = 10  # Log progress every N documents in batch
