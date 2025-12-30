# Metadata File Structure - Detailed Specification

## Directory Layout

```
kurt-data/
├── metadata/
│   ├── corpus/                          # Corpus metadata files
│   │   ├── v0000001-1735470600000.corpus-metadata.json
│   │   ├── v0000002-1735557000000.corpus-metadata.json
│   │   └── v0000003-1735643400000.corpus-metadata.json
│   │
│   ├── snapshots/                       # Snapshot manifest lists
│   │   ├── snap-3827461234567-manifest-list.json
│   │   ├── snap-3827462938472-manifest-list.json
│   │   └── snap-3827464821093-manifest-list.json
│   │
│   └── manifests/                       # Partition manifests
│       ├── documents/                   # Document manifests
│       │   ├── domain=example.com/
│       │   │   ├── content_type=blog/
│       │   │   │   ├── date=2024-12/
│       │   │   │   │   └── snap-3827462938472.manifest.json
│       │   │   │   └── date=2025-01/
│       │   │   │       └── snap-3827462938472.manifest.json
│       │   │   └── content_type=reference/
│       │   │       └── date=2024-12/
│       │   │           └── snap-3827462938472.manifest.json
│       │   └── domain=docs.example.com/
│       │       └── content_type=reference/
│       │           └── date=2024-12/
│       │               └── snap-3827462938472.manifest.json
│       │
│       └── entities/                    # Entity manifests (optional)
│           └── snap-3827462938472-entities.manifest.json
│
├── sources/                             # Actual content files (existing)
│   ├── example.com/
│   │   ├── blog/
│   │   │   └── fastapi-intro.md
│   │   └── docs/
│   │       └── getting-started.md
│   └── docs.example.com/
│       └── integrations/
│           └── postgresql.md
│
└── kurt.db                              # SQLite database (existing)
```

---

## File Naming Conventions

### Corpus Metadata Files
**Pattern**: `v{sequence}-{timestamp}.corpus-metadata.json`
- `sequence`: 7-digit zero-padded sequence number (0000001, 0000002, ...)
- `timestamp`: Unix timestamp in milliseconds

**Examples**:
- `v0000001-1735470600000.corpus-metadata.json` - First snapshot
- `v0000042-1735557000000.corpus-metadata.json` - 42nd update

### Snapshot Manifest Lists
**Pattern**: `snap-{snapshot-id}-manifest-list.json`
- `snapshot-id`: Unique 13-digit snapshot identifier (Unix timestamp + random)

**Examples**:
- `snap-3827461234567-manifest-list.json`
- `snap-3827462938472-manifest-list.json`

### Document Partition Manifests
**Pattern**: `domain={domain}/content_type={type}/date={YYYY-MM}/snap-{snapshot-id}.manifest.json`

**Examples**:
- `domain=example.com/content_type=blog/date=2024-12/snap-3827462938472.manifest.json`
- `domain=docs.example.com/content_type=reference/date=2024-12/snap-3827462938472.manifest.json`

### Entity Manifests
**Pattern**: `snap-{snapshot-id}-entities.manifest.json`

**Example**:
- `snap-3827462938472-entities.manifest.json`

---

## 1. Corpus Metadata File (corpus-metadata.json)

**Location**: `metadata/corpus/v{sequence}-{timestamp}.corpus-metadata.json`

### Full Example

```json
{
  "format-version": 1,
  "corpus-uuid": "a4c9e7f2-8d3b-4a1e-9c5f-7b8a6d4e2c1a",
  "corpus-name": "default",
  "location": "/home/user/kurt-data",

  "last-sequence-number": 42,
  "last-updated-ms": 1735557000000,

  "schema": {
    "schema-id": 3,
    "identifier-field-ids": [1],
    "fields": [
      {
        "id": 1,
        "name": "document_id",
        "type": "uuid",
        "required": true,
        "doc": "Unique document identifier"
      },
      {
        "id": 2,
        "name": "title",
        "type": "string",
        "required": false
      },
      {
        "id": 3,
        "name": "source_url",
        "type": "string",
        "required": false,
        "doc": "Original URL where content was fetched"
      },
      {
        "id": 4,
        "name": "content_type",
        "type": "string",
        "required": false,
        "doc": "Content classification: reference, tutorial, blog, etc."
      },
      {
        "id": 5,
        "name": "published_date",
        "type": "timestamp",
        "required": false
      },
      {
        "id": 6,
        "name": "entity_count",
        "type": "int",
        "required": false
      },
      {
        "id": 7,
        "name": "claim_count",
        "type": "int",
        "required": false
      },
      {
        "id": 8,
        "name": "indexed_at",
        "type": "timestamp",
        "required": true
      },
      {
        "id": 9,
        "name": "content_hash",
        "type": "string",
        "required": true,
        "doc": "SHA-256 hash of content for change detection"
      },
      {
        "id": 10,
        "name": "embedding_vector",
        "type": "binary",
        "required": false,
        "doc": "512-dim float32 embedding vector"
      }
    ]
  },

  "partition-spec": [
    {
      "spec-id": 1,
      "fields": [
        {
          "field-id": 1001,
          "source-id": 3,
          "name": "domain_partition",
          "transform": "extract_domain"
        },
        {
          "field-id": 1002,
          "source-id": 4,
          "name": "content_type_partition",
          "transform": "identity"
        },
        {
          "field-id": 1003,
          "source-id": 5,
          "name": "date_partition",
          "transform": "month"
        }
      ]
    }
  ],

  "default-spec-id": 1,
  "last-partition-id": 1003,

  "properties": {
    "owner": "kurt-system",
    "created-at": "2025-12-20T10:00:00Z",
    "indexing-pipeline-version": "v2.1.0",
    "embedding-model": "all-MiniLM-L6-v2",
    "embedding-dimensions": "512",
    "llm-extraction-model": "gpt-4o-mini"
  },

  "current-snapshot-id": 3827462938472,

  "snapshots": [
    {
      "snapshot-id": 3827461234567,
      "parent-snapshot-id": null,
      "timestamp-ms": 1735470600000,
      "sequence-number": 41,
      "manifest-list": "metadata/snapshots/snap-3827461234567-manifest-list.json",
      "summary": {
        "operation": "bootstrap",
        "added-documents": 1250,
        "removed-documents": 0,
        "total-documents": 1250,
        "added-entities": 8500,
        "total-entities": 8500,
        "added-claims": 24000,
        "total-claims": 24000,
        "indexing-pipeline-version": "v2.0.0",
        "git-commit": "3e4613f"
      }
    },
    {
      "snapshot-id": 3827462938472,
      "parent-snapshot-id": 3827461234567,
      "timestamp-ms": 1735557000000,
      "sequence-number": 42,
      "manifest-list": "metadata/snapshots/snap-3827462938472-manifest-list.json",
      "summary": {
        "operation": "incremental-index",
        "added-documents": 25,
        "removed-documents": 0,
        "total-documents": 1275,
        "added-entities": 142,
        "total-entities": 8642,
        "added-claims": 356,
        "total-claims": 24356,
        "indexing-pipeline-version": "v2.1.0",
        "git-commit": "ae44662"
      }
    }
  ],

  "snapshot-log": [
    {
      "snapshot-id": 3827461234567,
      "timestamp-ms": 1735470600000
    },
    {
      "snapshot-id": 3827462938472,
      "timestamp-ms": 1735557000000
    }
  ],

  "metadata-log": [
    {
      "metadata-file": "metadata/corpus/v0000041-1735470600000.corpus-metadata.json",
      "timestamp-ms": 1735470600000
    }
  ],

  "sort-orders": [],
  "default-sort-order-id": 0
}
```

### Field Explanations

| Field | Type | Description |
|-------|------|-------------|
| `format-version` | int | Metadata format version (currently 1) |
| `corpus-uuid` | string | Unique identifier for this corpus |
| `location` | string | Base path for all corpus files |
| `last-sequence-number` | int | Monotonically increasing sequence counter |
| `schema` | object | Table schema with field IDs (never reused) |
| `partition-spec` | array | How documents are partitioned |
| `current-snapshot-id` | long | Points to the latest snapshot |
| `snapshots` | array | Full history of all snapshots |
| `snapshot-log` | array | Chronological log of snapshot IDs |
| `metadata-log` | array | History of metadata file locations |

---

## 2. Snapshot Manifest List

**Location**: `metadata/snapshots/snap-{snapshot-id}-manifest-list.json`

### Full Example

```json
{
  "format-version": 1,
  "snapshot-id": 3827462938472,
  "parent-snapshot-id": 3827461234567,
  "timestamp-ms": 1735557000000,
  "sequence-number": 42,

  "summary": {
    "operation": "incremental-index",
    "total-documents": 1275,
    "total-entities": 8642,
    "total-claims": 24356,
    "total-relationships": 12845,
    "total-partitions": 12,
    "total-data-files": 1275,
    "total-delete-files": 0,
    "added-documents": 25,
    "removed-documents": 0
  },

  "manifests": [
    {
      "manifest-path": "metadata/manifests/documents/domain=example.com/content_type=blog/date=2024-12/snap-3827462938472.manifest.json",
      "manifest-length": 125430,
      "partition-spec-id": 1,
      "content": "data",
      "sequence-number": 42,
      "min-sequence-number": 41,
      "added-snapshot-id": 3827462938472,
      "added-files-count": 5,
      "existing-files-count": 43,
      "deleted-files-count": 0,

      "partitions": [
        {
          "contains-null": false,
          "contains-nan": false,
          "lower-bound": {
            "domain_partition": "example.com",
            "content_type_partition": "blog",
            "date_partition": "2024-12-01"
          },
          "upper-bound": {
            "domain_partition": "example.com",
            "content_type_partition": "blog",
            "date_partition": "2024-12-31"
          }
        }
      ],

      "statistics": {
        "document-count": 48,
        "entity-count": 324,
        "claim-count": 892,
        "relationship-count": 456,

        "entity-types": {
          "Technology": 156,
          "Product": 89,
          "Feature": 79
        },

        "content-type-breakdown": {
          "blog": 48
        },

        "published-date-range": {
          "min": "2024-12-01T00:00:00Z",
          "max": "2024-12-31T23:59:59Z"
        },

        "has-code-examples": true,
        "avg-confidence": 0.87,
        "avg-word-count": 1250,

        "top-entities": [
          {"name": "FastAPI", "count": 28},
          {"name": "Python", "count": 42},
          {"name": "PostgreSQL", "count": 15}
        ]
      }
    },

    {
      "manifest-path": "metadata/manifests/documents/domain=docs.example.com/content_type=reference/date=2024-12/snap-3827462938472.manifest.json",
      "manifest-length": 342890,
      "partition-spec-id": 1,
      "content": "data",
      "sequence-number": 42,
      "min-sequence-number": 41,
      "added-snapshot-id": 3827461234567,
      "added-files-count": 0,
      "existing-files-count": 122,
      "deleted-files-count": 0,

      "partitions": [
        {
          "contains-null": false,
          "contains-nan": false,
          "lower-bound": {
            "domain_partition": "docs.example.com",
            "content_type_partition": "reference",
            "date_partition": "2024-12-01"
          },
          "upper-bound": {
            "domain_partition": "docs.example.com",
            "content_type_partition": "reference",
            "date_partition": "2024-12-31"
          }
        }
      ],

      "statistics": {
        "document-count": 122,
        "entity-count": 1893,
        "claim-count": 5421,
        "relationship-count": 2834,

        "entity-types": {
          "Feature": 892,
          "Product": 445,
          "Technology": 334,
          "Integration": 222
        },

        "content-type-breakdown": {
          "reference": 122
        },

        "published-date-range": {
          "min": "2024-12-01T00:00:00Z",
          "max": "2024-12-31T23:59:59Z"
        },

        "has-code-examples": true,
        "avg-confidence": 0.92,
        "avg-word-count": 2850,

        "top-entities": [
          {"name": "FastAPI", "count": 98},
          {"name": "SQLAlchemy", "count": 76},
          {"name": "Pydantic", "count": 64},
          {"name": "PostgreSQL", "count": 52}
        ]
      }
    },

    {
      "manifest-path": "metadata/manifests/documents/domain=example.com/content_type=tutorial/date=2025-01/snap-3827462938472.manifest.json",
      "manifest-length": 89234,
      "partition-spec-id": 1,
      "content": "data",
      "sequence-number": 42,
      "min-sequence-number": 42,
      "added-snapshot-id": 3827462938472,
      "added-files-count": 20,
      "existing-files-count": 0,
      "deleted-files-count": 0,

      "partitions": [
        {
          "contains-null": false,
          "contains-nan": false,
          "lower-bound": {
            "domain_partition": "example.com",
            "content_type_partition": "tutorial",
            "date_partition": "2025-01-01"
          },
          "upper-bound": {
            "domain_partition": "example.com",
            "content_type_partition": "tutorial",
            "date_partition": "2025-01-15"
          }
        }
      ],

      "statistics": {
        "document-count": 20,
        "entity-count": 142,
        "claim-count": 356,
        "relationship-count": 189,

        "entity-types": {
          "Technology": 68,
          "Feature": 45,
          "Product": 29
        },

        "content-type-breakdown": {
          "tutorial": 20
        },

        "published-date-range": {
          "min": "2025-01-01T00:00:00Z",
          "max": "2025-01-15T12:00:00Z"
        },

        "has-code-examples": true,
        "avg-confidence": 0.89,
        "avg-word-count": 1820,

        "top-entities": [
          {"name": "Docker", "count": 18},
          {"name": "Kubernetes", "count": 12},
          {"name": "FastAPI", "count": 15}
        ]
      }
    }
  ]
}
```

---

## 3. Document Partition Manifest

**Location**: `metadata/manifests/documents/domain={domain}/content_type={type}/date={YYYY-MM}/snap-{snapshot-id}.manifest.json`

### Full Example

```json
{
  "format-version": 1,
  "manifest-version": 1,
  "snapshot-id": 3827462938472,
  "sequence-number": 42,
  "min-sequence-number": 42,

  "partition-spec-id": 1,
  "partition": {
    "domain_partition": "example.com",
    "content_type_partition": "tutorial",
    "date_partition": "2025-01"
  },

  "schema-id": 3,

  "documents": [
    {
      "status": "ADDED",
      "sequence-number": 42,
      "file-sequence-number": 42,

      "document-id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "source-url": "https://example.com/tutorials/docker-fastapi",
      "content-path": "sources/example.com/tutorials/docker-fastapi.md",
      "content-hash": "sha256:7f8a9b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a",

      "metadata": {
        "title": "Deploying FastAPI with Docker: Complete Guide",
        "content-type": "tutorial",
        "published-date": "2025-01-10T14:30:00Z",
        "indexed-at": "2025-01-10T16:45:00Z",
        "author": {
          "name": "Jane Developer",
          "url": "https://example.com/authors/jane"
        },
        "description": "Learn how to containerize and deploy FastAPI applications using Docker and Docker Compose",

        "word-count": 2340,
        "has-code-examples": true,
        "has-step-by-step-procedures": true,
        "has-narrative-structure": true,
        "is-chronological": false
      },

      "statistics": {
        "entity-count": 8,
        "claim-count": 18,
        "relationship-count": 12,

        "entities": [
          {
            "entity-id": "ent-docker-001",
            "canonical-name": "Docker",
            "entity-type": "Technology",
            "mention-count": 24,
            "confidence": 0.98,
            "sections": [
              "Introduction",
              "Dockerfile Setup",
              "Building Images",
              "Running Containers"
            ],
            "first-mention-offset": 245
          },
          {
            "entity-id": "ent-fastapi-001",
            "canonical-name": "FastAPI",
            "entity-type": "Technology",
            "mention-count": 18,
            "confidence": 0.95,
            "sections": [
              "Introduction",
              "Application Setup",
              "Dockerfile Setup"
            ],
            "first-mention-offset": 123
          },
          {
            "entity-id": "ent-docker-compose-001",
            "canonical-name": "Docker Compose",
            "entity-type": "Technology",
            "mention-count": 8,
            "confidence": 0.92,
            "sections": [
              "Multi-Container Setup",
              "Deployment"
            ],
            "first-mention-offset": 1456
          },
          {
            "entity-id": "ent-uvicorn-001",
            "canonical-name": "Uvicorn",
            "entity-type": "Technology",
            "mention-count": 6,
            "confidence": 0.89,
            "sections": [
              "Application Setup",
              "Running Containers"
            ],
            "first-mention-offset": 789
          }
        ],

        "relationships": [
          {
            "source-entity": "FastAPI",
            "target-entity": "Docker",
            "relationship-type": "uses",
            "confidence": 0.95,
            "evidence-count": 12,
            "context": "containerization and deployment"
          },
          {
            "source-entity": "FastAPI",
            "target-entity": "Uvicorn",
            "relationship-type": "requires",
            "confidence": 0.92,
            "evidence-count": 6,
            "context": "ASGI server for running application"
          },
          {
            "source-entity": "Docker Compose",
            "target-entity": "Docker",
            "relationship-type": "extends",
            "confidence": 0.88,
            "evidence-count": 4,
            "context": "orchestration tool"
          }
        ],

        "claims": [
          {
            "claim-id": "claim-docker-fastapi-001",
            "claim-text": "Docker enables consistent FastAPI deployment across environments",
            "claim-type": "ValueProp",
            "confidence": 0.91,
            "entities": ["Docker", "FastAPI"],
            "section": "Introduction",
            "character-offset-start": 245,
            "character-offset-end": 310,
            "source-quote": "Using Docker ensures your FastAPI application runs consistently across development, testing, and production environments"
          },
          {
            "claim-id": "claim-docker-fastapi-002",
            "claim-text": "Multi-stage Docker builds reduce FastAPI image size",
            "claim-type": "Performance",
            "confidence": 0.88,
            "entities": ["Docker", "FastAPI"],
            "section": "Dockerfile Setup",
            "character-offset-start": 892,
            "character-offset-end": 945,
            "source-quote": "Multi-stage builds can reduce your final image size by up to 70%"
          }
        ],

        "embedding": {
          "model": "all-MiniLM-L6-v2",
          "dimensions": 512,
          "norm": 1.0,
          "checksum": "md5:a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3"
        },

        "avg-claim-confidence": 0.89,
        "avg-entity-confidence": 0.94
      },

      "size-bytes": 15680,
      "record-count": 1,
      "key-metadata": null
    },

    {
      "status": "ADDED",
      "sequence-number": 42,
      "file-sequence-number": 42,

      "document-id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "source-url": "https://example.com/tutorials/kubernetes-deployment",
      "content-path": "sources/example.com/tutorials/kubernetes-deployment.md",
      "content-hash": "sha256:8a9b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b",

      "metadata": {
        "title": "Deploying FastAPI to Kubernetes",
        "content-type": "tutorial",
        "published-date": "2025-01-12T09:15:00Z",
        "indexed-at": "2025-01-12T11:30:00Z",
        "author": {
          "name": "John DevOps",
          "url": "https://example.com/authors/john"
        },
        "description": "Step-by-step guide to deploying FastAPI applications on Kubernetes with best practices",

        "word-count": 3240,
        "has-code-examples": true,
        "has-step-by-step-procedures": true,
        "has-narrative-structure": true,
        "is-chronological": true
      },

      "statistics": {
        "entity-count": 12,
        "claim-count": 24,
        "relationship-count": 18,

        "entities": [
          {
            "entity-id": "ent-kubernetes-001",
            "canonical-name": "Kubernetes",
            "entity-type": "Technology",
            "mention-count": 42,
            "confidence": 0.97,
            "sections": [
              "Introduction",
              "Cluster Setup",
              "Deployment Configuration",
              "Service Configuration",
              "Scaling"
            ],
            "first-mention-offset": 89
          },
          {
            "entity-id": "ent-fastapi-001",
            "canonical-name": "FastAPI",
            "entity-type": "Technology",
            "mention-count": 28,
            "confidence": 0.96,
            "sections": [
              "Introduction",
              "Application Preparation",
              "Deployment Configuration"
            ],
            "first-mention-offset": 156
          },
          {
            "entity-id": "ent-docker-001",
            "canonical-name": "Docker",
            "entity-type": "Technology",
            "mention-count": 15,
            "confidence": 0.94,
            "sections": [
              "Application Preparation",
              "Container Registry"
            ],
            "first-mention-offset": 567
          }
        ],

        "relationships": [
          {
            "source-entity": "Kubernetes",
            "target-entity": "Docker",
            "relationship-type": "uses",
            "confidence": 0.96,
            "evidence-count": 8,
            "context": "container orchestration"
          },
          {
            "source-entity": "FastAPI",
            "target-entity": "Kubernetes",
            "relationship-type": "uses",
            "confidence": 0.93,
            "evidence-count": 12,
            "context": "deployment platform"
          }
        ],

        "claims": [
          {
            "claim-id": "claim-k8s-fastapi-001",
            "claim-text": "Kubernetes enables automatic scaling of FastAPI applications",
            "claim-type": "Feature",
            "confidence": 0.94,
            "entities": ["Kubernetes", "FastAPI"],
            "section": "Scaling",
            "character-offset-start": 2456,
            "character-offset-end": 2517
          }
        ],

        "embedding": {
          "model": "all-MiniLM-L6-v2",
          "dimensions": 512,
          "norm": 1.0,
          "checksum": "md5:b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4"
        },

        "avg-claim-confidence": 0.91,
        "avg-entity-confidence": 0.95
      },

      "size-bytes": 22340,
      "record-count": 1,
      "key-metadata": null
    }
  ],

  "statistics": {
    "total-documents": 20,
    "total-entities": 142,
    "total-claims": 356,
    "total-relationships": 189,
    "total-size-bytes": 378920
  }
}
```

---

## 4. Entity Manifest (Optional)

**Location**: `metadata/manifests/entities/snap-{snapshot-id}-entities.manifest.json`

### Full Example

```json
{
  "format-version": 1,
  "manifest-version": 1,
  "snapshot-id": 3827462938472,
  "sequence-number": 42,

  "schema-id": 3,

  "entities": [
    {
      "entity-id": "ent-fastapi-001",
      "canonical-name": "FastAPI",
      "entity-type": "Technology",
      "description": "Modern, fast web framework for building APIs with Python based on standard Python type hints",

      "aliases": [
        "Fast API",
        "fast-api",
        "FastApi"
      ],

      "created-at": "2025-01-05T10:00:00Z",
      "updated-at": "2025-01-10T16:45:00Z",

      "statistics": {
        "total-mentions": 342,
        "document-count": 28,
        "avg-confidence": 0.94,
        "min-confidence": 0.82,
        "max-confidence": 0.98,

        "document-distribution": {
          "reference": 12,
          "tutorial": 8,
          "blog": 6,
          "guide": 2
        },

        "documents": [
          {
            "document-id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "source-url": "https://example.com/tutorials/docker-fastapi",
            "mention-count": 18,
            "confidence": 0.95,
            "sections": [
              "Introduction",
              "Application Setup",
              "Dockerfile Setup"
            ]
          },
          {
            "document-id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
            "source-url": "https://example.com/tutorials/kubernetes-deployment",
            "mention-count": 28,
            "confidence": 0.96,
            "sections": [
              "Introduction",
              "Application Preparation",
              "Deployment Configuration"
            ]
          }
        ],

        "relationships": [
          {
            "relationship-type": "integrates_with",
            "target-entities": [
              {
                "entity-id": "ent-postgresql-001",
                "canonical-name": "PostgreSQL",
                "document-count": 8,
                "avg-confidence": 0.91
              },
              {
                "entity-id": "ent-mongodb-001",
                "canonical-name": "MongoDB",
                "document-count": 5,
                "avg-confidence": 0.88
              }
            ]
          },
          {
            "relationship-type": "uses",
            "target-entities": [
              {
                "entity-id": "ent-docker-001",
                "canonical-name": "Docker",
                "document-count": 12,
                "avg-confidence": 0.93
              },
              {
                "entity-id": "ent-pydantic-001",
                "canonical-name": "Pydantic",
                "document-count": 15,
                "avg-confidence": 0.95
              }
            ]
          }
        ],

        "related-claims": 124,
        "avg-claim-confidence": 0.89
      },

      "embedding": {
        "model": "all-MiniLM-L6-v2",
        "dimensions": 512,
        "norm": 1.0,
        "checksum": "md5:c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5"
      }
    },

    {
      "entity-id": "ent-postgresql-001",
      "canonical-name": "PostgreSQL",
      "entity-type": "Technology",
      "description": "Open-source relational database management system emphasizing extensibility and SQL compliance",

      "aliases": [
        "Postgres",
        "postgres",
        "PostgreSQL Database"
      ],

      "created-at": "2025-01-05T10:00:00Z",
      "updated-at": "2025-01-09T14:20:00Z",

      "statistics": {
        "total-mentions": 218,
        "document-count": 18,
        "avg-confidence": 0.96,
        "min-confidence": 0.87,
        "max-confidence": 0.99,

        "document-distribution": {
          "reference": 8,
          "tutorial": 6,
          "guide": 3,
          "blog": 1
        },

        "documents": [
          {
            "document-id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
            "source-url": "https://docs.example.com/integrations/postgresql",
            "mention-count": 28,
            "confidence": 0.98,
            "sections": [
              "Introduction",
              "Setup",
              "Connection Pooling",
              "Migrations"
            ]
          }
        ],

        "relationships": [
          {
            "relationship-type": "integrates_with",
            "target-entities": [
              {
                "entity-id": "ent-fastapi-001",
                "canonical-name": "FastAPI",
                "document-count": 8,
                "avg-confidence": 0.91
              },
              {
                "entity-id": "ent-sqlalchemy-001",
                "canonical-name": "SQLAlchemy",
                "document-count": 12,
                "avg-confidence": 0.94
              }
            ]
          }
        ],

        "related-claims": 86,
        "avg-claim-confidence": 0.92
      },

      "embedding": {
        "model": "all-MiniLM-L6-v2",
        "dimensions": 512,
        "norm": 1.0,
        "checksum": "md5:d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6"
      }
    }
  ],

  "statistics": {
    "total-entities": 8642,
    "entity-type-breakdown": {
      "Technology": 3456,
      "Product": 2134,
      "Feature": 1892,
      "Topic": 845,
      "Integration": 234,
      "Company": 81
    }
  }
}
```

---

## 5. SQLite Catalog Table

The corpus catalog lives in the existing Kurt SQLite database (`kurt.db`).

### Schema

```sql
CREATE TABLE corpus_catalog (
    corpus_name TEXT PRIMARY KEY,
    current_metadata_file TEXT NOT NULL,
    corpus_uuid TEXT NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_corpus_catalog_updated ON corpus_catalog(updated_at);
```

### Example Data

```sql
INSERT INTO corpus_catalog VALUES
  ('default', 'metadata/corpus/v0000042-1735557000000.corpus-metadata.json', 'a4c9e7f2-8d3b-4a1e-9c5f-7b8a6d4e2c1a', '2025-01-05 10:00:00', '2025-01-10 16:45:00'),
  ('blog-only', 'metadata/corpus/v0000015-1735550000000.corpus-metadata.json', 'b5d8f3e9-9d4c-5b2f-ad6g-8c9b7e5d3f2b', '2025-01-07 14:30:00', '2025-01-10 12:00:00');
```

---

## File Size Estimates

Based on 1,275 documents with ~8,600 entities:

| File Type | Count | Size per File | Total Size |
|-----------|-------|---------------|------------|
| Corpus metadata | 1 (current) | 15 KB | 15 KB |
| Snapshot manifest list | 1 (current) | 80 KB | 80 KB |
| Document manifests | ~12 partitions | 100-350 KB | ~2 MB |
| Entity manifest | 1 (optional) | 1.2 MB | 1.2 MB |
| **Total per snapshot** | | | **~3.3 MB** |

**Historical snapshots**: With 30-day retention at daily snapshots, ~100 MB total metadata.

---

## File Versioning and Immutability

### Key Principles

1. **Never modify existing files**: Each snapshot creates NEW files
2. **Copy-on-write**: Unchanged partitions reference old manifest files
3. **Atomic updates**: Update catalog pointer only after all files written
4. **Garbage collection**: Delete old snapshots only when past retention period

### Example: Incremental Update

**Before** (Snapshot 41):
```
metadata/snapshots/snap-3827461234567-manifest-list.json
metadata/manifests/documents/domain=example.com/content_type=blog/date=2024-12/snap-3827461234567.manifest.json
metadata/manifests/documents/domain=docs.example.com/content_type=reference/date=2024-12/snap-3827461234567.manifest.json
```

**After** (Snapshot 42 - added 20 tutorials):
```
metadata/snapshots/snap-3827462938472-manifest-list.json  (NEW)
metadata/manifests/documents/domain=example.com/content_type=blog/date=2024-12/snap-3827461234567.manifest.json  (REUSED)
metadata/manifests/documents/domain=docs.example.com/content_type=reference/date=2024-12/snap-3827461234567.manifest.json  (REUSED)
metadata/manifests/documents/domain=example.com/content_type=tutorial/date=2025-01/snap-3827462938472.manifest.json  (NEW)
```

The new manifest list references 2 old manifests + 1 new manifest.

---

## Summary

The metadata file structure provides:

1. **Hierarchical organization**: Catalog → Metadata → Snapshots → Manifests → Documents
2. **Partition-based pruning**: Statistics at every level enable efficient filtering
3. **Immutable snapshots**: Complete version history with time travel
4. **Self-describing**: JSON format (or Avro) readable by any tool
5. **Incremental efficiency**: Reuse unchanged manifests across snapshots
6. **Dual views**: Document-centric AND entity-centric access patterns

This structure balances query performance (via statistics and pruning) with storage efficiency (via manifest reuse) while maintaining complete corpus version history.
