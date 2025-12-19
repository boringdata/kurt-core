---
title: APM
url: https://docs.datadoghq.com/tracing/
hostname: datadoghq.com
sitename: docs.datadoghq.com
date: 2025-01-01
---
Join an introductory or intermediate enablement session to learn more about how Datadog Application Performance Monitoring (APM) provides AI-powered, code-level distributed tracing from browser and mobile applications to backend services and databases.

Datadog Application Performance Monitoring (APM) provides deep visibility into your applications, enabling you to identify performance bottlenecks, troubleshoot issues, and optimize your services. With distributed tracing, out-of-the-box dashboards, and seamless correlation with other telemetry data, Datadog APM helps ensure the best possible performance and user experience for your applications.

The simplest way to start with Datadog APM is with Single Step Instrumentation. This approach installs the Datadog Agent and instruments your application in one step, with no additional configuration steps required. To learn more, read Single Step Instrumentation.

For setups that require more customization, Datadog supports custom instrumentation with Datadog tracing libraries and Dynamic Instrumentation in the Datadog UI. To learn more, read Application Instrumentation.

If you're new to Datadog APM, read Getting Started with APM to learn how to send your first trace to Datadog.

Use cases

Discover some ways Datadog APM can help support your use cases:

You want to…

How Datadog APM can help

Understand how requests flow through your system.

Use the Trace Explorer to query and visualize end-to-end traces across distributed services.

Monitor service health and performance of individual services.

Use the service and resource pages to assess service health by analyzing performance metrics, tracking deployments, and identifying problematic resources.

Correlate traces with DBM, RUM, logs, synthetics, and profiles.

Use Ingestion Controls to adjust ingestion configuration and sampling rates by service and resource. Use Retention filters to choose which spans to retain for 15 days.

Trace Explorer

The Trace Explorer allows you search and analyze your traces in real-time. Identify performance bottlenecks, troubleshoot errors, and pivot to related logs and metrics to understand the full context around any issue.

Traces start in your instrumented applications and flow into Datadog.

Datadog APM provides tools to manage the volume and retention of your trace data. Use Ingestion Controls to adjust sampling rates and retention filters to control which spans are stored.