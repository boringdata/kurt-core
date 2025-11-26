---
title: flight-sql-vs-rest-vs-jdbc
content_type: blog
source_url: https://motherduck.com/blog/flight-sql-vs-rest-vs-jdbc
indexed_at: '2025-11-25T19:58:02.740998'
content_hash: b1b7f5e38abb7ca3
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Why REST and JDBC Are Killing Your Data Stack — Flight SQL to the Rescue

2025/06/13 - 8 min read

BY

[Thomas (TFMV) McGeehan](https://motherduck.com/authors/thomas-tfmv-mcgeehan/)

Data pipelines today feel like an underground fight: you build them fast, but the real battle starts when you try to serve the results. Welcome to Flight Club.

The first rule of Flight Club? You do not talk to REST.

The second rule? You definitely do not talk to REST.

The third rule? If your pipeline goes limp, chokes on JSON, or taps out on throughput, the session is over.

[DuckDB](https://duckdb.org/) changed how we do local analytics — the lovechild of [SQLite](https://www.sqlite.org/) and a supercomputer, delivering screaming-fast OLAP without the servers, clusters, or life-ruining setup scripts.

But modern data teams don't just analyze. They integrate, connect, and serve. From [BI dashboards](https://superset.apache.org/) to [ML pipelines](https://www.tensorflow.org/) to that one stakeholder who still loves their pivot tables, the need to expose DuckDB cleanly over a network keeps surfacing.

Picture this: Your team has built a lightning-fast DuckDB analytics pipeline that crunches billions of records in seconds. But when it's time to serve those insights to your dashboards or ML models? You're forced to squeeze that beautiful columnar data through the rusty pipes of REST or JDBC. It's like putting a Ferrari engine in a horse-drawn carriage.

## The Problem with REST and JDBC

The problem? REST is duct tape. JDBC is legacy glue. Both are leaky, brittle, and built for another era.

- **REST**: Forces your columnar data into bloated JSON, then makes you parse it back. Up to 90% of your time? Spent on serialization, not computation.
- **JDBC**: Still thinks in rows when the world has moved to columns. Like trying to stream Netflix through a dial-up modem.

That's where [Apache Arrow Flight SQL](https://arrow.apache.org/docs/dev/format/FlightSql.html) comes in.

Not another framework to learn. Not a platform to buy into. A protocol — lean, typed, binary-native. Fire SQL queries and stream columnar data with zero-copy swagger.

It doesn't just work. It flies.

No more encoding rows into JSON just to decode them faster than you can say "technical debt." No more pretending analytics engines are web servers. Flight SQL treats data like it's 2025: fast, typed, and unapologetically direct.

Two open-source servers — [Hatch](https://github.com/TFMV/hatch) and [GizmoSQL](https://github.com/gizmodata/gizmosql) — are already strapping rockets to DuckDB with Arrow Flight SQL. Different vibes, same mission: Give DuckDB wings. Let it serve, stream, and scale like the compute beast it is.

In this post, we'll break it down: Why [Arrow](https://arrow.apache.org/) \+ Flight SQL is stupidly fast (we're talking 20+ Gb/s per core), how Flight SQL powers real-time pipelines without breaking a sweat, what Hatch and GizmoSQL bring to the DuckDB party, and how local-first analytics just became a distributed superpower.

No REST. No bloat. Just protocol-native performance. Welcome to Flight Club.

## Understanding Arrow Flight SQL

### Arrow: A Data Format That Doesn't Suck

[Apache Arrow](https://arrow.apache.org/) is the Usain Bolt of data formats—columnar, in-memory, and built for speed. It's designed to shuttle structured data across tools and languages without breaking a sweat.

- **Column-first layout** → [SIMD](https://en.wikipedia.org/wiki/Single_instruction,_multiple_data)-friendly (Single Instruction, Multiple Data), enabling parallel processing at the CPU level
- **Language-neutral** → [C++](https://arrow.apache.org/docs/cpp/), [Go](https://arrow.apache.org/docs/go/), [Python](https://arrow.apache.org/docs/python/), [Rust](https://arrow.apache.org/docs/rust/), [Java](https://arrow.apache.org/docs/java/), and probably Klingon soon
- **Shared format** → Zero-copy data sharing between processes—point at data instead of copying it
- **Vector-ready** → Perfect for batching, scanning, and [ML inference](https://www.tensorflow.org/)

Arrow isn't just a format. It's a shared memory model that says, "Why copy data when you can just point at it?"

### Flight: gRPC for Tables, No Bloat

[Arrow Flight](https://arrow.apache.org/docs/dev/format/Flight.html) is the network protocol that makes Arrow feel like it's teleporting. Forget JSON blobs or binary spaghetti—Flight streams Arrow batches over [gRPC](https://grpc.io/) like a data wizard slinging spells.

It's [gRPC](https://grpc.io/) for tables, with:

- **Zero-copy Arrow [IPC](https://arrow.apache.org/docs/dev/format/Columnar.html) streaming** → Data moves at ludicrous speed, no serialization tax
- **Schema-first descriptors** → No guesswork, just precision
- **Built-in parallelism** → Because waiting is for suckers
- **Cross-language clients** → Pick your poison, it just works

Here's a real-world example:

```bash
Copy code

# Traditional REST/JDBC way:
# 1. Query database (1-2s)
# 2. Serialize to JSON/rows (0.5-1s)
# 3. Transfer over network (0.2-0.5s)
# 4. Deserialize back to usable format (0.5-1s)
# Total: 2.2-4.5s

# Flight SQL way:
# 1. Query database (1-2s)
# 2. Stream Arrow batches directly (0.1-0.2s)
# Total: 1.1-2.2s
```

![Flight SQL Performance Comparison](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimg1_flight_8a7512c978.png&w=3840&q=75)

No ORMs, JDBC or REST nonsense. Just fast, typed, structured streams that respect your time.

### Flight SQL: SQL with Wings

[Flight SQL](https://arrow.apache.org/docs/dev/format/FlightSql.html) takes Arrow Flight and slaps SQL semantics on it. Send a query, get an Arrow table back. No middleman, no drama.

- **SQL queries** → Arrow tables, no detours
- **Standardized [protobuf](https://developers.google.com/protocol-buffers) interfaces** → Predictable, not a puzzle
- **Typed parameters, prepared statements, metadata reflection** → It's like SQL grew up and got a job

This isn't your grandma's database driver. It's SQL for pipelines, built for machines, not GUIs.

| Protocol | Median Round Trip | Payload Format | Peak Throughput |
| --- | --- | --- | --- |
| REST | 75 ms | JSON (yawn) | 1-2 Gb/s |
| JDBC | 52 ms | Binary (meh) | 5-10 Gb/s |
| Flight SQL | 18 ms | Arrow IPC (wow) | 20+ Gb/s |

Flight SQL doesn't just win; it laps the competition while sipping coffee.

## Meet the Flight Club Members

Two open-source projects are bringing Flight SQL to DuckDB, and they're as different as a duck and a goose. Both get the job done.

### Hatch: The Purist's Choice

[Hatch](https://github.com/TFMV/hatch) is Go-based, Arrow-native, and built for people who think "composable" is a personality trait. It's experimentable, open to the wild, and always looking for new recruits.

- **Single static binary** → Deploy it anywhere, no fuss
- **[OpenTelemetry](https://opentelemetry.io/) tracing, config hot-reloading** → Because observability is sexy
- **Fast Arrow record pooling and schema caching** → Efficiency is the name of the game
- **Multiple auth modes** → Secure without the headache

Run it locally, at the edge, or sneak it into a bigger system.

![Hatch Architecture](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimg2_flight_b1846edea2.png&w=3840&q=75)

### GizmoSQL: The Backend Whisperer

[GizmoSQL](https://github.com/gizmodata/gizmosql) is a full Arrow Flight SQL server with support for both DuckDB and SQLite as pluggable backends. Built in C++ and extended from Voltron Data's sqlflite, it's been battle-tested, hardened, and upgraded for real-world flexibility.

- **[TLS](https://en.wikipedia.org/wiki/Transport_Layer_Security), [JWT](https://jwt.io/), and init scripts** → Secure and customizable by default
- **[Docker](https://www.docker.com/)-first deployment** → Instant setup with production-grade defaults
- **[JDBC](https://en.wikipedia.org/wiki/Java_Database_Connectivity), [ADBC](https://arrow.apache.org/adbc/), [CLI](https://en.wikipedia.org/wiki/Command-line_interface), [Ibis](https://ibis-project.org/), [SQLAlchemy](https://www.sqlalchemy.org/)** → Clients for nearly every stack

Whether you want to mount a local DB, run interactive pipelines, or integrate cleanly with BI tools, GizmoSQL is a solid, well-documented launchpad.

DuckDB deserves a clean, stable interface to the world.

## Flight Club in Action

Ready to lift off? Here's how to get started with GizmoSQL:

```bash
Copy code

docker run -d \
  --name gizmosql \
  -p 31337:31337 \
  -e GIZMOSQL_USERNAME=gizmosql_username \
  -e GIZMOSQL_PASSWORD=gizmosql_password \
  gizmodata/gizmosql:latest
```

Give the server a few seconds to start.

### Querying with Python

Here's how you talk to it:

```python
Copy code

import os
from adbc_driver_flightsql import dbapi as gizmosql, DatabaseOptions

with gizmosql.connect(
    uri="grpc+tls://localhost:31337",
    db_kwargs={
        "username": os.getenv("GIZMOSQL_USERNAME", "gizmosql_username"),
        "password": os.getenv("GIZMOSQL_PASSWORD", "gizmosql_password"),
        DatabaseOptions.TLS_SKIP_VERIFY.value: "true",
    },
) as conn:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT n_nationkey, n_name FROM nation WHERE n_nationkey = ?",
            parameters=[24],
        )
        x = cur.fetch_arrow_table()
        print(x)
```

That's it. No REST endpoints to design. No JDBC drivers to wrestle. Just SQL in, Arrow out, running at memory speed.

Want to serve this to a dashboard? Point [Superset](https://superset.apache.org/) or [Metabase](https://www.metabase.com/) at your GizmoSQL server. Need real-time ML features? Stream them through Flight SQL. The protocol handles the heavy lifting while you focus on the analytics.

Remember: This is your data. And it's ending one transformation at a time.

## Why This Changes Everything

Once you unshackle DuckDB with Flight SQL, the possibilities explode like a data piñata:

- **Dashboards** → [Superset](https://superset.apache.org/), [Metabase](https://www.metabase.com/), [Tableau](https://www.tableau.com/) now get data at memory speed, not HTTP speed
- **Streaming pipelines** → Arrow in, Arrow out, no conversion tax. Perfect for real-time ML feature stores
- **ML workloads** → Feed models at 20+ Gb/s per core. Because your GPU is hungry
- **Federated meshes** → DuckDB as a compute shard in your data galaxy, speaking Arrow end-to-end

Flight SQL makes these real, not just PowerPoint dreams. Here's what it means in practice:

- **10x faster dashboard refreshes** → From coffee-break wait times to blink-and-you-miss-it speed
- **95% less CPU overhead** → Your machines can focus on compute, not conversion
- **Zero data format tax** → Arrow all the way down means no more format ping-pong

### The Future of Flight SQL

Flight SQL is the start, not the finish line. It's the foundation for wilder ideas:

- **[UDFs](https://en.wikipedia.org/wiki/User-defined_function) over Flight** → Stream [WASM](https://webassembly.org/) or native extensions like a boss
- **Column-level security** → Only stream what's allowed, no leaks
- **Inline analytics plugins** → Embed computation right in the protocol
- **Self-hosted analytic nodes** → Distribute DuckDB like confetti, not containers

This isn't a platform pitch. It's a protocol revolution. Each innovation builds on Flight's core promise: moving data at the speed of memory, not the speed of serialization.

## Stop Torturing Analytics

Flight SQL isn't here to replace everything. It's just the fastest, cleanest, most developer-friendly way to serve columnar data over the wire in 2025.

DuckDB changed how we crunch data locally. Flight SQL lets it spread its wings and scale horizontally—not just in size, but in impact. It's about unlocking the full potential of your analytics:

- **Local development** → Lightning-fast iteration on your laptop
- **Edge deployment** → DuckDB at every [CDN](https://en.wikipedia.org/wiki/Content_delivery_network) point of presence
- **Cloud scale** → Distributed queries that feel local

No more REST duct tape. No more JDBC relics. Let's build data services that treat DuckDB like the rockstar it is.

Give DuckDB wings. Let it soar.

**The last rule of Flight Club? Build fast. Serve smart. Never serialize again.**

### TABLE OF CONTENTS

[The Problem with REST and JDBC](https://motherduck.com/blog/flight-sql-vs-rest-vs-jdbc/#the-problem-with-rest-and-jdbc)

[Understanding Arrow Flight SQL](https://motherduck.com/blog/flight-sql-vs-rest-vs-jdbc/#understanding-arrow-flight-sql)

[Meet the Flight Club Members](https://motherduck.com/blog/flight-sql-vs-rest-vs-jdbc/#meet-the-flight-club-members)

[Flight Club in Action](https://motherduck.com/blog/flight-sql-vs-rest-vs-jdbc/#flight-club-in-action)

[Why This Changes Everything](https://motherduck.com/blog/flight-sql-vs-rest-vs-jdbc/#why-this-changes-everything)

[Stop Torturing Analytics](https://motherduck.com/blog/flight-sql-vs-rest-vs-jdbc/#stop-torturing-analytics)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![DuckDB Ecosystem: June 2025](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FThree_items_Duck_DB_Ecosystem_1_c24205c719.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-june-2025/)

[2025/06/06 - Simon Späti](https://motherduck.com/blog/duckdb-ecosystem-newsletter-june-2025/)

### [DuckDB Ecosystem: June 2025](https://motherduck.com/blog/duckdb-ecosystem-newsletter-june-2025)

DuckDB Monthly #30: DuckDB's new table format, Radio extension and more!

[![Getting Started with DuckLake: A New Table Format for Your Lakehouse](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fducklake_5c914ac5f3.png&w=3840&q=75)](https://motherduck.com/blog/getting-started-ducklake-table-format/)

[2025/06/09 - Mehdi Ouazza](https://motherduck.com/blog/getting-started-ducklake-table-format/)

### [Getting Started with DuckLake: A New Table Format for Your Lakehouse](https://motherduck.com/blog/getting-started-ducklake-table-format)

Learn how DuckLake simplifies metadata and brings fast, database-like features to your data lakehouse — with a hands-on example using DuckDB and PostgreSQL

[View all](https://motherduck.com/blog/)

Authorization Response