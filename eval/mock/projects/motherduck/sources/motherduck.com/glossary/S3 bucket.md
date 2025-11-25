---
title: S3 bucket
content_type: tutorial
source_url: https://motherduck.com/glossary/S3 bucket
indexed_at: '2025-11-25T20:02:55.683911'
content_hash: 245482b768c285f5
has_code_examples: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# S3 bucket

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

An [S3 bucket](https://aws.amazon.com/s3/) is a fundamental storage container in Amazon Web Services' Simple Storage Service (S3). It functions as a cloud-based folder for storing and organizing data objects, such as files, images, and documents. S3 buckets are globally unique, scalable, and designed to provide high durability and availability for data storage. They support various access control mechanisms and can be configured for different storage classes based on data access patterns and cost considerations. Data engineers often use S3 buckets as a central repository for raw data, processed datasets, or as part of data lakes. When working with DuckDB, you can directly query data stored in S3 buckets using syntax like:

```sql
Copy code

SELECT * FROM read_parquet('s3://your-bucket-name/path/to/file.parquet');
```

This seamless integration allows for efficient data processing without the need to download files locally.

Authorization Response