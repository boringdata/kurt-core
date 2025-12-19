---
title: Getting Started - Upstash Documentation
url: https://upstash.com/docs/vector/overall/getstarted
hostname: upstash.com
sitename: Upstash Documentation
date: 2025-10-09
---
**Prerequisite**You need an Upstash account before creating a vector, create one

[here](https://console.upstash.com).

## Create an Index

Once you logged in, you can create a Vector Index by clicking on the`Create Index`

button in the Vector tab.
**Name:**Type a name for your index.

**Region:**Choose the region for your index. For optimal performance, select the region closest to your applications. We plan to support additional regions and cloud providers. Feel free to send your requests to

[[email protected]](https://upstash.com/cdn-cgi/l/email-protection#d4a7a1a4a4bba6a094a1a4a7a0b5a7bcfab7bbb9)

**Type:**The type of index: Dense,

[Sparse](https://upstash.com/docs/vector/features/sparseindexes)or

[Hybrid](https://upstash.com/docs/vector/features/hybridindexes). For semantic search, you can prefer dense. For full text (or keyword) search, you can prefer sparse. If you need a combination, you can choose hybrid. If you choose Dense or Hybrid as index type, you will also be presented with options to select the dimensions and distance metric of your index. Once you pick these options, you will choose a plan:

**Free:**The free plan is suitable for small projects. It has a limit of 10,000 queries and 10,000 updates daily.

**Pay as You Go:**Pay as you go plan is a flexible plan with per-request-pricing. It is suitable for projects with unpredictable traffic.

**Fixed:**Fixed plan is suitable for projects with predictable traffic. It has a fixed monthly price with 1M query and 1M updates daily.

**Pro:**Pro plan is suitable for projects with high traffic and storage needs. It has a fixed monthly price with extra security and isolation features.

**Enterprise:**If you plan to have over a billion vectors then Enterprise plan is for you. It has a fixed monthly price with extra security and isolation features. Contact us at

[[email protected]](https://upstash.com/cdn-cgi/l/email-protection#0774666b6274477277747366746f2964686a)for more information.

## Insert Index

You can access data in your index using REST API or our SDKs. You can copy the sample code from the`Connect`

section in the console.
- Python
- JavaScript
- Go
- PHP
- curl

## Query Index

You can perform a similarity search by providing a query vector as a parameter. The dimension of the query vector must match the dimension of your index. Also, you can query by metadata filtering.Upstash is eventually consistent, so there may be a delay before the newly inserted or updated vectors are ready for querying.

- Python
- JavaScript
- Go
- PHP
- curl

## Usage and Data Browser

In Upstash console, you can see the charts of your index:**Daily Requests:**The number of queries and updates to your index in the last 5 days.**Throughput:**The number of queries and updates to your index in the selected time period.**Latency:**The mean and P99 latency of queries and updates to your index in the selected time period.**Vector Count:**The number of vectors in your index in the selected time period.**Data Size:**The size of your index in the selected time period.