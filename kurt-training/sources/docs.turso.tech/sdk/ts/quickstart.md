---
title: Turso Quickstart (TypeScript / JS) - Turso
url: https://docs.turso.tech/sdk/ts/quickstart
hostname: turso.tech
description: Get started with Turso and TypeScript using the libSQL client in a few simple steps
sitename: Turso
date: 2025-10-12
---
- Retrieve database credentials
- Install the JavaScript libSQL client
- Connect to a remote Turso database
- Execute a query using SQL

1

Retrieve database credentials

You will need an existing database to continue. If you don’t have one, Get the database authentication token:Assign credentials to the environment variables inside

[create one](https://docs.turso.tech/quickstart).Get the database URL:`.env`

.You will want to store these as environment variables.

2

Install @libsql/client

Begin by installing the

`@libsql/client`

dependency in your project:3

Initialize a new client

Next add your database URL and auth token:

4

Execute a query using SQL

You can execute a SQL query against your existing database by calling If you need to use placeholders for values, you can do that:

`execute()`

: