---
title: git-for-data-part-1
content_type: blog
source_url: https://motherduck.com/blog/git-for-data-part-1
indexed_at: '2025-11-25T19:56:38.973255'
content_hash: 71e8006c3e1677f3
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Branch, Test, Deploy: A Git-Inspired Approach for Data

2025/11/24 - 17 min read

BY

[Simon Späti](https://motherduck.com/authors/simon-sp%C3%A4ti/)

Remember the 2 AM on-call duty when a recent data pipeline broke the production environment? A data pipeline you've never touched just corrupted customer records. You need to roll back, fast. Or you want to test a new transformation on real production data before deployment, but recreating a production-like state in dev would take all day. Sounds familiar?

This is what a Git strategy for your data deployment promises to solve. This article explores using Git-like workflows for data, compares them to traditional Git, examines how data changes the workflow, assesses the current state of Git for data, and looks at key architectural concepts related to Git workflows in data.

The core challenge is universal across data teams: managing local, test, and production environments. Running large ETL jobs on prod data is expensive and time-consuming (anonymization, data prep, environment setup). But what if you could branch your data like you branch code? Test on real data, discard changes instantly, and deploy with confidence. That's the promise of Git for data, and let's find out if it can become a reality.

NOTE: Examine Tools in Part 2
There will be a part 2, where we look into the tools and implementations available such as LakeFS, Dolt, Nessie, MotherDuck's zero-copy clones, and more. But more importantly, we'll explore why you'd want this workflow in the first place and how it actually works in practice.

## Why Git for Data?

Besides the above two use cases—running prod data in dev or reverting production data if a pipeline accidentally deleted or changed something incorrectly—the main goal of Git for data is giving the data engineer peace of mind during production runs.

### The Problem We Have

When you have multiple stages in your data engineering architecture, from `stage -> core -> data marts`, potentially a cube on top, and multiple data pipelines running in parallel, the problem is rolling back an error consistently across the data stack.

How do we do that? We can't just revert one table, the sales table for example, because it will not work with all related customers, as they might have changed in the meantime, or the products, or their location, or gone out of business.

Data might be stored on a data lake, maybe on a database, or a key-value store like Redis. The data might be huge, containing the full CRM or all sales transactions over the last years. So the question is, how do we **revert or test things** consistently based on production-like data in terms of **both quality and size**?

That's where Git for data came from, and where tools such as LakeFS, Nessie, Bauplan and approaches like branching found a way to do it for a dedicated spot or across the stack.

### The Goal: What to Expect from a Git-like Workflow for Data?

We want to explore how Git can be integrated with data storage solutions like data lakes and databases to enable branching, cloning, and other Git-based functionality, which is what we already use for code in the realm of data engineering.

For this, we need to investigate how the full data stack, such as orchestration or transformation tools in the data workflow, can leverage Git-based versioning and branching. We need a strategy for scaling the Git-based data workflow to handle large production datasets without the extra work of copying or backup processes of existing databases + code + environment variables manually as we do today.

We want **Git for data management, similar to how it is used for code**, to facilitate deployment and testing. As we have the code packaged, we can package it into a Docker file and run it on that set of data.

Imagine if we could have Git management end-to-end on data analytics, a fully integrated Git workflow. If we only have the data, that already helps because then we can run a set of code. The end-to-end integration would be nice, but not the most important. Data is the hard part here. So if we are able to achieve that, we already win big by avoiding all the test cycles and CI/CDs we need to wait for or gain stability by quickly testing before deploying to production.

The hard part is scaling Git for data, especially in large-scale production environments where production data is really large. Copying this data and even adding some additional jobs with tests or setting up environments and integrations on top might take hours, or even the full night, if no errors occur.

Let's find out what existing tools in the market figured out and what efficient ways there are to scale Git for data without the downsides.

### Why not Plain "Git"?

Literally using Git doesn't work well for data. We get line-level conflict resolution (not cell-level). Git has no concept of schema. The files need to be sorted the same way to get useful diffs, and it has a 100MB GitHub file limit.

Git isn't made for data itself, but for small, text-based code changes. On top of that, in data work we differentiate between these two categories:

- Data pipeline versioning -> transformations or code
- Versioned databases -> the actual data

## Current State of Git for Data Work

Git for code is very well known, not so much Git for data. Let's explore the current state of Git for data.

### How Does Git Work?

To understand Git for data, we need to understand how branching with Git works, so we can apply it to data.

For example, Git branching holds all metadata and changes of the code from each state. This is handled through hashes. But Git is not made for data because it was designed with code versioning in mind, not large binary files or datasets. As Linus Torvalds himself [noted](https://www.youtube.com/watch?v=sCr_gb8rdEI), as the creator of Git, large files in Git were never part of the intended use case. The system's architecture of storing complete snapshots and computing hashes for everything works well for text-based code but becomes unwieldy with large data files. But as data practitioners, we actively want to work with data, with state, which is always harder than just code.

Git and Git-like solutions (alternatives are [Tangled](https://tangled.org/) and [Gitea](https://about.gitea.com/)) work. But which of these features do we want for data? And which specific ones do we need more compared to versioning code?

Git has concepts like versioning, rollback, diffs, lineage, branch/merge, and sharing. On the data side, which we get into more later, we have concepts such as files vs tables, structured vs unstructured, schema vs data, branching, and time travel.

For data, we need a storage layer or a way optimized for large data, schemas, and column types without necessarily duplicating the data. We also need to be able to revert the code and state easily. For example, revert the data pipelines that put production in an incorrect state.

If we look at [The Struggle of Enterprise Data Integration](https://airbyte.com/blog/modern-data-stack-struggle-of-enterprise-adoption), we can see that lots of what enterprises struggle with in data is change management and managing complexity. So hopefully, Git for data will help us with this?

### How Does It Work with Data?

Data works differently. We need an open way of sharing and moving data that we can then version, _branch_ off to different versions easily, and roll back to older versions.

![image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Fgit_image_1_ed936b4007.png&w=3840&q=75)
Source: [Git for Data - What, How and Why Now?](https://lakefs.io/blog/git-for-data/)

Branching is the right word, also what Git is doing:

```css
Copy code

                 E---F---G  experiment-spark-3
                /
           C---D  dev-testing
          /
main  A---B---H---I  production
                 \
                  J---K  hotfix-corrupted-sales
```

We start with a version, and then diverge into different versions, and potentially merge back. **Merging** different branches is one option we **won't need for data compared to code**. With code, different features can be developed independently and then merged into the _main branch_ at the end. With data, it's more about testing prod data on dev and then rolling out the code changes to prod, but not merging the "test" branch with the prod branch; otherwise we change, duplicate, or corrupt data.

The LakeFS solution (more on how it works later down) and its implemented Git-like features:
![image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Fgit_image_2_ae841f5f84.png&w=3840&q=75)
Source: [Git for Data - What, How and Why Now?](https://lakefs.io/blog/git-for-data/)

[Tigris's new Fork](https://www.tigrisdata.com/blog/fork-buckets-like-code/) capabilities solve some of these challenges with _fractal snapshots_:

> You can instantly create an **isolated copy of your data** for development, testing, or experimentation. Have a **massive production dataset** you want to play with? You **don't need to wait for a full copy**. Just fork your source bucket, experiment freely, throw it away, and spin up a new one — instantly.
>
> Their timelines diverge from the source bucket at the moment of the fork. It's the many-worlds version of object storage.

The key is that **every object is immutable**. Each write creates a new version, timestamped and preserved.

> That immutability allows Tigris to **version the entire bucket, and capture it as a single snapshot**.

![git-image-3.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Fgit_image_3_ea87a15566.png&w=3840&q=75)

This is interesting. Rather than single Delta or Iceberg tables, it versions the full bucket with the help of the versioning capabilities of these open table formats. Tigris says further, "Each object maintains its own version chain, and a **snapshot is an atomic cut across all those chains** at a specific moment in time."

A more comprehensive example with two different tables and different isolations that helps understand these processes in a data lake example with open table format tables stored on object storage:

![git-image-5.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Fgit_image_5_f0310a64b5.png&w=3840&q=75)

Important to know: a snapshot is an atomically consistent version across all those chains at a specific moment in time, and when retrieving a snapshot, Tigris, for example, returns the newest `version ≤ snapshot timestamp` of each table. For example, Snapshot `T3-dev` would contain Customer Table v4-dev and _only_ Sales Table v5-dev (not v4-dev).

One technology used behind this is called [Prolly Tree](https://docs.dolthub.com/architecture/storage-engine/prolly-tree), also known as [Merkle Trees](https://en.wikipedia.org/wiki/Merkle_tree):
![image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Fgit_image_6_5f150caf6f.png&w=3840&q=75)
Image from [Prolly Trees on Dolt Documentation](https://docs.dolthub.com/architecture/storage-engine/prolly-tree)

NOTE: In a way this is also how Software Engineers vs. Data Engineers work
Software engineers need little to no data (data can also be replaced with having unpredictable, upstream events as a dependency), they can \*\*mock it easily (e.g. website)\*\* in dev, and in prod, they usually need big resources.
For data people, we have **hard dependencies on prod data**, usually **heavy compute in development**, lower compute in prod. SW engineers focus on the [SDLC (Software Development Lifecycle)](https://www.geeksforgeeks.org/software-engineering/software-development-life-cycle-sdlc/) and DE engineers need to focus on the data engineering lifecycle. There are many more differences. I wrote a little more on [Data Engineer vs. Software Engineer](https://www.ssp.sh/brain/data-engineer-vs-software-engineer).

### Data Movement Efficiency Spectrum

Before we get into the architectural decisions and the tools, let's _observe the data movements_ when we implement Git for data, and let's categorize them by the amount of data movement required, ordered from most to least efficient:

**The most efficient approach uses metadata/catalog-based versioning**. Catalog pointers that just point to the same files multiple times (lakeFS and Iceberg are using this) create multiple logical versions of datasets without any physical duplication. No data movement involved.

**The next best approach is zero-copy or data virtualization technologies**. Tools like Apache Arrow enable data sharing between processes and systems without serialization overhead. You avoid the costly conversion between formats—no deserializing from source format to an intermediate representation and back again.

**When changes occur, delta-based approaches are the best way**. Rather than copying the entire dataset, you only store what has changed in new files. If you need to roll back, you simply revert the pointer to the previous file and state while keeping the changed files. This requires data management to manage changes.

**The least efficient but simplest approach is full 1:1 data copying.** Traditional methods like ODBC transfers, CSV exports, or database dumps require serializing data from the source format, moving it entirely, and deserializing it at the destination (e.g., from MS SQL to Pandas). But also, just creating a copy on S3 while keeping the same format is an expensive transaction, even more so with bigger datasets.

This works best for **small datasets** where the overhead doesn't matter, and offers the convenience of true isolation and easy rollback without complex change tracking.

We can say we work from `metadata → zero-copy → delta → full copy`. Let's investigate how lakeFS and other tools solved that problem and which approach they have chosen.

## Architecture: Key Technical Concepts

Now that we understand how data moves and its efficiency spectrum, let's look at how these approaches are **implemented in practice**. The architectural approaches can be categorized by implementation pattern:

1. **Environment-based versioning (traditional approach):** Typically uses **full copy** or **delta** from our efficiency spectrum.

   - Infrastructure-level: Kubernetes-based `dev/test/prod` environments with isolated data copies.
   - Application-level: Custom metadata tables, audit logs, or SCD (Slowly Changing Dimensions) patterns managing versions in the data warehouse.
2. **Zero-copy and virtualization approaches:** Leverage the **metadata/catalog** and **zero-copy** tiers, enabling logical versioning without physical data duplication.

   - Data virtualization (Dremio, Denodo, Starburst) queries sources on-demand without moving data.
   - Zero-copy cloning (MotherDuck, Snowflake, Azure Synapse) creates instant clones using metadata pointers.
   - In-memory sharing (Apache Arrow) enables process-to-process data sharing without serialization.
3. **Git-like data versioning tools:** Purpose-built tools operating at the **metadata/catalog tier** with **delta** capabilities for changes and connecting datasets in a connected way (with branching and Git-like functions).

   - **Data lake tools:** LakeFS, Project Nessie, Tigris work on object storage with open table formats (Iceberg, Delta Lake, Hudi) that have versioning built-in with time travel via `TIMESTAMP AS OF "2019-01-01"` or `VERSION AS OF 5238`.
   - **Database-native solutions:** Vary by efficiency—Supabase (branching), BigQuery (snapshots with 7-day time travel), MotherDuck (cloning, sharing), Databricks (Delta Lake integration), Dremio (Arctic catalog with Nessie). Note: Not all "cloning" is zero-copy—some create actual copies, others use copy-on-write, and the most efficient use pure metadata.
   - **Hybrid approaches:** Combine techniques like open table formats + lakeFS, or database cloning + scheduled snapshots for comprehensive version history.

Let's look at them in more detail and especially focus on the key techniques that **enable Git-like versioning**.

### Zero-Copy and Cloning

Zero-copying is important as we want fast creation of a new state. Zero-copying and cloning are the solution to that initial fast copy of an existing dataset. You can think of cloning a "production" database or lake.

Both zero-copy and cloning are related but not quite the same. For example, something can support cloning but it's NOT zero-copy (e.g., Dolt). It uses copy-on-write with structural sharing. We can say that the difference is:

- **Cloning** = _Can you create a copy?_ (the capability)
- **Zero-copy** = _Does it duplicate data or just use metadata pointers?_ (the implementation technique)

In the best case, we have both cloning and zero-copy: cloning production or a set of data without the need to duplicate the data, therefore zero-copy.

We can also borrow an analogy from Linux with a **Symlink**. You can have multiple pointers at different places pointing to the same file. You can read, open, and change, but the data is only stored once. Instead of moving data, we just create one new or many new pointers.

The result is creating new datasets instantly, as it's just a metadata process, and not an actual data transfer. We change the pointer **without moving data**.

### Branching with Metadata Catalogs

Branching is implemented through **metadata catalogs**, systems that use pointers to track different versions of data without duplicating it, just like Git does. This is the most efficient way of versioning, as it's just a metadata process.

As mentioned above, this is the best way of versioning, as it's just a metadata process. Most modern tools implement this approach, though not all mean the same thing. Let's conceptually explore what we mean by branching data.

Branching is when you freeze the current state in an atomic and consistent way across multiple tables. Instead of focusing on one singular table, we do it for a full data warehouse layer or bucket.

[Snapshotting](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/periodic-snapshot-fact-table/) is one of the approaches we use as part of our [Data Engineering Toolkit](https://motherduck.com/blog/data-engineering-toolkit-essential-tools/). Here we snapshot each table based on recurring date-time, e.g., every end of month. Because we do that for all tables in our data warehouse, it's also what I'd call the same approach we are doing with newer branching capabilities.

But generally, branching allows a snapshot or fork across tables and data assets. It can also be used to integrate a [Write-Audit-Publish (WAP)](https://lakefs.io/blog/data-engineering-patterns-write-audit-publish/) workflow, where you _write_ into a temporary state, _audit_ the quality and integrity of data, and only then _publish_ (merge) it into production. This shows that branching solves the problem of **having consistency to test a certain feature in isolation** before merging all changes coherently, or none at all.

With additional features of merging (with some tools) or having a detailed commit log for what's happening, especially in combination with AI agents, this provides strong support to [steward](https://www.rilldata.com/blog/data-modeling-for-the-agentic-era-semantics-speed-and-stewardship) these autonomous agents and gatekeep and verify through humans.

#### Prolly Trees: A Data Structure for Efficient Branching

A great technical implementation of such an approach is Prolly Tree or Merkle Trees.

Prolly Trees are the technical foundation that makes Git-like versioning work for databases. Think of it as smart data chunking where data gets split into blocks using hash functions, and each block gets a unique fingerprint.

The key insight is that no matter how you modify data, **identical content always produces identical fingerprints**. This means when you change a row, only that specific chunk and its path to the root need updating, and everything else stays untouched and shared between versions.

This is exactly like how Git tracks changes in code, but optimized for tabular data. The result: diffing scales with what changed (a few rows), not dataset size (millions of rows), enabling instant branching and efficient storage across versions. This is what I found during research about Dolt.

### Hybrid Approaches

In reality, we often combine multiple techniques to get the best of all worlds. For example, you might use open table formats (Iceberg/Delta Lake) for their built-in time travel capabilities, layered with lakeFS for branch-based isolation across your entire data lake.

Or pair MotherDuck's zero-copy cloning with scheduled snapshots to create comprehensive version history beyond the default 7-day window. The key is matching your data versioning strategy (metadata, zero-copy, or delta) with your orchestration and transformation tools, supporting branch deployments that clone both code and data together for true isolated testing environments.

## Conclusion

We learned that Git for data is harder than version control for code because we're not just tracking changes but managing state, often at a massive scale. While Git revolutionized software development by making branching and merging trivial, the same would be helpful for data. Data, however, has the requirements that tables must remain consistent across relationships, that production datasets can span gigabytes and terabytes, and that copying data for testing is slow and often expensive.

The promise of Git-like workflows for data is to borrow Git-like concepts of branching, rollback, and isolated environments while addressing data's unique constraints. The key is leveraging metadata for zero-copy cloning and structural sharing through technologies like Prolly Trees, so we can create instant branches of production data without duplicating the actual data. The evolution we go through is from pure metadata pointers (most efficient) through delta-based changes to complete copies, which are simplest to work with but also the slowest. It's also the difference in provisioning speed: one can be ready in seconds, while the other takes hours, depending on the size of the data.

It's exciting how these capabilities can change the way we do data engineering. In Part 2, we'll explore tools like LakeFS, Nessie, Dolt, and others that are embracing these workflow changes and providing architectural implementations to this problem, each with different trade-offs around scale, integration, and operational complexity. We'll also check out how MotherDuck offers a handy solution for snapshotting that works really well with DuckDB and DuckLake.

I hope you gained good insight into the state of the art for Git workflows with data and how future data pipelines can benefit from such thinking and implementations, especially for testing and building more confidence in change management and, therefore, velocity in data engineering development cycles.

### TABLE OF CONTENTS

[Why Git for Data?](https://motherduck.com/blog/git-for-data-part-1/#why-git-for-data)

[Current State of Git for Data Work](https://motherduck.com/blog/git-for-data-part-1/#current-state-of-git-for-data-work)

[Architecture: Key Technical Concepts](https://motherduck.com/blog/git-for-data-part-1/#architecture-key-technical-concepts)

[Conclusion](https://motherduck.com/blog/git-for-data-part-1/#conclusion)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Small Data SF 2025: the Recap!](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Fsmall_data_sf_2025_f373154984.png&w=3840&q=75)](https://motherduck.com/blog/small-data-sf-recap-2025/)

[2025/11/14 - Garrett O'Brien](https://motherduck.com/blog/small-data-sf-recap-2025/)

### [Small Data SF 2025: the Recap!](https://motherduck.com/blog/small-data-sf-recap-2025)

Dive into a recap of the world's hottest efficiency-themed data conference, Small Data SF!

[![Unstructured Document Analysis with Tensorlake and MotherDuck](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Ftensorlake_15913398e1.png&w=3840&q=75)](https://motherduck.com/blog/unstructured-analysis-tensorlake-motherduck/)

[2025/11/19 - Diptanu Gon Choudhury](https://motherduck.com/blog/unstructured-analysis-tensorlake-motherduck/)

### [Unstructured Document Analysis with Tensorlake and MotherDuck](https://motherduck.com/blog/unstructured-analysis-tensorlake-motherduck)

Learn how to query unstructured documents with friendly SQL!

[View all](https://motherduck.com/blog/)

Authorization Response