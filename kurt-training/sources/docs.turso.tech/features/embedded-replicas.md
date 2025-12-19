---
title: Embedded Replicas - Turso
url: https://docs.turso.tech/features/embedded-replicas/introduction
hostname: turso.tech
sitename: Turso
date: 2025-10-18
---
[edge network](https://docs.turso.tech/features/data-edge). For mobile applications, where stable connectivity is a challenge, embedded replicas are invaluable as they allow uninterrupted access to the local database. Embedded replicas provide a smooth switch between local and remote database operations, allowing the same database to adapt to various scenarios effortlessly. They also ensure speedy data access by syncing local copies with the remote database, enabling microsecond-level read operations — a significant advantage for scenarios demanding quick data retrieval.

## How it works

-
You configure a local file to be your main database.
- The
`url`

parameter in the client configuration.

- The
-
You configure a remote database to sync with.
- The
`syncUrl`

parameter in the client configuration.

- The
-
You read from a database:
- Reads are always served from the local replica configured at
`url`

.

- Reads are always served from the local replica configured at
-
You write to a database:
- Writes are sent to the remote primary database configured at
`syncUrl`

by default. - You can write locally if you set the
`offline`

config option to`true`

. - Any write transactions with reads are also sent to the remote primary database.
- Once the write is successful, the local database is updated with the changes automatically (read your own writes — can be disabled).

- Writes are sent to the remote primary database configured at

### Periodic sync

You can automatically sync data to your embedded replica using the periodic sync interval property. Simply pass the`syncInterval`

parameter when instantiating the client:
### Read your writes

Embedded Replicas also will guarantee read-your-writes semantics. What that means in practice is that after a write returns successfully, the replica that initiated the write will always be able to see the new data right away, even if it never calls`sync()`

.
Other replicas will see the new data when they call `sync()`

, or at the next sync period, if [Periodic Sync](https://docs.turso.tech#periodic-sync)is used.

### Encryption at rest

Embedded Replicas support encryption at rest with one of the libSQL client SDKs. Simply pass the`encryptionKey`

parameter when instantiating the client:
The encryption key used should be generated and managed by you.

## Usage

To use embedded replicas, you need to create a client with a`syncUrl`

parameter. This parameter specifies the URL of the remote Turso database that the client will sync with:
You should call

`.sync()`

in the background whenever your application wants to sync the remote and local embedded replica. For example, you can call it every 5 minutes or every time the application starts.## Things to know

- Do not open the local database while the embedded replica is syncing. This can lead to data corruption.
- In certain contexts, such as serverless environments without a filesystem, you can’t use embedded replicas.
- There are a couple scenarios where you may sync more frames than you might
expect.
- A write that causes the internal btree to split at any node would cause many new frames to be written to the replication log.
- A server restart that left the on-disk wal in dirty state would regenerate the replication log and sync additional frames.
- Removing/invalidating the local files on disk could cause the embedded replica to re-sync from scratch.

- One frame equals 4kB of data (one on disk page frame), so if you write a 1 byte row, it will always show up as a 4kB write since that is the unit in which libsql writes with.

## Deployment Guides


## Turso + Fly

Deploy a JavaScript project with Embedded Replicas to Fly.io


## Turso + Koyeb

Deploy a JavaScript/Rust project with Embedded Replicas to Koyeb


## Turso + Railway

Deploy a JavaScript/Rust project with Embedded Replicas to Railway


## Turso + Render

Deploy a JavaScript project with Embedded Replicas to Render


## Turso + Linode by Akamai

Deploy a JavaScript/Rust project with Embedded Replicas to Akamai