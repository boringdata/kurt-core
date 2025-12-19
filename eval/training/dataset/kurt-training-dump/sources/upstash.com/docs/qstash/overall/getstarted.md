---
title: Getting Started - Upstash Documentation
url: https://upstash.com/docs/qstash/overall/getstarted
hostname: upstash.com
sitename: Upstash Documentation
date: 2025-10-09
---
**serverless messaging and scheduling solution**. It fits easily into your existing workflow and allows you to build reliable systems without managing infrastructure. Instead of calling an endpoint directly, QStash acts as a middleman between you and an API to guarantee delivery, perform automatic retries on failure, and more.

## Quick Start

Check out these Quick Start guides to get started with QStash in your application.

## Next.js

Build a Next application that uses QStash to start a long-running job on your platform


## Python

Build a Python application that uses QStash to schedule a daily job that clean up a database

## Send your first message

**Prerequisite**You need an Upstash account before publishing messages, create one

[here](https://console.upstash.com).

### Public API

Make sure you have a publicly available HTTP API that you want to send your messages to. If you don’t, you can use something like[requestcatcher.com](https://requestcatcher.com/),

[webhook.site](https://webhook.site/)or

[webhook-test.com](https://webhook-test.com/)to try it out. For example, you can use this URL to test your messages:

[https://firstqstashmessage.requestcatcher.com](https://firstqstashmessage.requestcatcher.com)

### Get your token

Go to the[Upstash Console](https://console.upstash.com/qstash)and copy the

`QSTASH_TOKEN`

.
### Publish a message

A message can be any shape or form: json, xml, binary, anything, that can be transmitted in the http request body. We do not impose any restrictions other than a size limit of 1 MB (which can be customized at your request). In addition to the request body itself, you can also send HTTP headers. Learn more about this in the[message publishing section](https://upstash.com/docs/qstash/howto/publishing).

### Check Response

You should receive a response with a unique message ID.### Check Message Status

Head over to[Upstash Console](https://console.upstash.com/qstash)and go to the

`Logs`

tab where you can see your message activities.
[here](https://upstash.com/docs/qstash/howto/debug-logs).

## Features and Use Cases


## Background Jobs

Run long-running tasks in the background, without blocking your application


## Schedules

Schedule messages to be delivered at a time in the future


## Fan out

Publish messages to multiple endpoints, in parallel, using URL Groups


## FIFO

Enqueue messages to be delivered one by one in the order they have enqueued.


## Flow Control

Custom rate per second and parallelism limits to avoid overflowing your endpoint.


## Callbacks

Get a response delivered to your API when a message is delivered


## Retry Failed Jobs

Use a Dead Letter Queue to have full control over failed messages


## Deduplication

Prevent duplicate messages from being delivered


## LLM Integrations

Publish, enqueue, or batch chat completion requests using large language models with QStash
features.