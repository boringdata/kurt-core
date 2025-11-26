---
title: introducing-motherduck-for-business-analytics
content_type: blog
source_url: https://motherduck.com/blog/introducing-motherduck-for-business-analytics
indexed_at: '2025-11-25T19:58:23.713858'
content_hash: 170d89a1ee194613
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# MotherDuck for Business Analytics: GDPR, SOC 2 Type II, Tiered Support, and New Plan Offerings

2025/02/11 - 5 min read

BY

[Sheila Sitaram](https://motherduck.com/authors/sheila-sitaram/)

MotherDuck became [Generally Available](https://motherduck.com/blog/announcing-motherduck-general-availability-data-warehousing-with-duckdb/) in June 2024. Since then, we have worked with hundreds of customers to help them move away from overengineered solutions for an ergonomic, easy to use data warehouse.

To better serve future-minded businesses building production-grade analytics, we are introducing new data warehousing features, including read scaling and tiered support offerings. We have also achieved SOC 2 Type II and GDPR compliance.

## Introducing the Business Plan

We are introducing a new [Business Plan](https://motherduck.com/product/pricing/) with unlimited Organization members to align the production-grade analytics and data warehousing features we’re building with the needs of our customers.

**Highlights of the Business Plan include:**

- Performance optimization and tuning with three new, configurable instance types
- Access to read scaling replicas for high-volume BI dashboards and customer-facing analytics applications
- Priority support with faster response times and an in-app interface for raising support requests

Users and potential customers who are interested in an annual contract also have the option to pre-commit to a level of MotherDuck usage. To learn more, please connect with our [Sales team](https://motherduck.com/contact-us/sales/).

## 3 Configurable Instance Types

Starting today, we are introducing three configurable, serverless instance types, Pulse, Standard, and Jumbo, to provide more flexibility and control over performance for different analytics workloads.

MotherDuck does things a bit differently than other databases by providing each Organization (Org) member with an isolated read-write instance to enable individual, user-level configuration.

With the introduction of instance types, users in an Organization can now decide between Pulse, an **on-demand, auto-scaling instance**, or Standard and Jumbo, **dedicated instances** metered on compute time.

**Pulse:** For lightweight, on-demand analytics

- Common uses include small, frequent operations like micro-batching data loads, multi-tenant applications, and smaller ad-hoc query workloads

**Standard:** Designed for common data warehouse workloads, including loads and transforms

- Our workhorse instance that provides great performance on a variety of workloads, from ad-hoc analytics to data pipelines and transformations

**Jumbo:** Built for production-scale analytics with heavy concurrent queries

- Common uses include more complex queries, larger data pipelines, BI dashboards, and complex joins and aggregations for growing datasets for faster performance than the Standard instance

These instance types give customers the ability to tailor their data warehouse performance to match their workload needs while ensuring cost efficiency. For more information about the instances, refer to our [documentation](https://motherduck.com/docs/about-motherduck/billing/instances/).

## Read Scaling

We introduced [Read Scaling](https://motherduck.com/blog/read-scaling-preview/) in December 2024 and have received overwhelmingly positive customer feedback about its utility for scaling BI workloads and building data applications that take advantage of our unique [per-user tenancy model](https://motherduck.com/product/data-teams/).

In partnership with DuckDB Labs, we have also continued to make write concurrency improvements to enhance data ingestion and pipeline performance. These updates further streamline data workflows for teams building interactive analytics applications.

With today’s launch of the Business Plan, users can also configure read scaling replicas in a self-serve fashion directly in the MotherDuck UI to handle extra load from concurrent read-only users.

![Read Scaling UI](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FInstance_Sizes_373fde68f8.gif&w=3840&q=75)

## Human-First Support

A thoughtful, human-first approach to delivering great support is as important as building great products. Starting today, customers on paid plans can submit support requests directly within the MotherDuck UI.
Our Customer team genuinely cares about your success and strives to act as an extension of your own team. Each support request submitted in the UI is carefully reviewed by real humans to make sure you can move quickly from question to insight without any blockers.

To coincide with embedding the support experience in the UI, we are also introducing [tiered support options](https://motherduck.com/product/pricing/) with faster access to MotherDuck experts and an expedited response SLA for Business Plan customers.

For more details on our support policy, please visit [motherduck.com/customer-support](https://motherduck.com/customer-support/).

![Support in the UI](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FUI_643427e647.gif&w=3840&q=75)

## SOC 2 Type II and GDPR Compliance

Earning and maintaining our customers’ trust is of the utmost importance to us at MotherDuck. Earlier this year we announced that we obtained [our first SOC 2 Type I report](https://motherduck.com/blog/announcing-motherduck-general-availability-data-warehousing-with-duckdb/). We have continued to invest in our security program and have now obtained our first SOC 2 Type II report. Additionally, we are GDPR compliant, as certified by GDPR local, in accordance with EU data protection regulations.

Looking ahead, we’ll continue to reinforce our commitment to building and maintaining a secure cloud data warehouse for globally minded businesses looking for a new, simpler way to deliver production-grade analytics without the overhead. We are committed to continuously enhancing our security framework to adopt additional compliance measures to protect your most valuable business assets. Our security and privacy program uses a defense in-depth strategy to protect your most valuable business assets and fortify trust. Achieving SOC 2 Type II and GDPR compliance validates our adherence to rigorous industry standards, ensuring customers can trust us with their most critical analytics workloads.

Our security program was once again audited by an external third party against the AICPA Trust Service Principles, including Security, Availability, and Confidentiality. This achievement validates our commitment as we continue to take steps to earn and maintain our customers’ trust while maturing our security posture. For more information about our trust and security program, please visit [motherduck.com/trust-and-security](https://motherduck.com/trust-and-security/#Compliance).

Security and Compliance reports are available on request for Business Plan customers by contacting [security@motherduck.com](https://motherduck.com/blog/introducing-motherduck-for-business-analytics/security@motherduck.com). We are constantly evolving to stay ahead of emerging threats and regulatory changes, and we will continue to work towards additional certifications and security enhancements to best support our customers. For healthcare customers, HIPAA BAAs can also be signed on request.

## What’s Next

These updates are the foundation for continued innovation and simplicity as we iterate and improve MotherDuck’s ducking simple cloud data warehouse in 2025 and beyond.

As always, we appreciate the feedback you’ve shared as we continue to lay the groundwork for the future. We could not be more excited about what’s to come.

### TABLE OF CONTENTS

[Introducing the Business Plan](https://motherduck.com/blog/introducing-motherduck-for-business-analytics/#introducing-the-business-plan)

[3 Configurable Instance Types](https://motherduck.com/blog/introducing-motherduck-for-business-analytics/#3-configurable-instance-types)

[Read Scaling](https://motherduck.com/blog/introducing-motherduck-for-business-analytics/#read-scaling)

[Human-First Support](https://motherduck.com/blog/introducing-motherduck-for-business-analytics/#human-first-support)

[SOC 2 Type II and GDPR Compliance](https://motherduck.com/blog/introducing-motherduck-for-business-analytics/#soc-2-type-ii-and-gdpr-compliance)

[What’s Next](https://motherduck.com/blog/introducing-motherduck-for-business-analytics/#whats-next)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![MotherDuck Now Supports DuckDB 1.2: Faster, Friendlier, Better Performance](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FDuck_DB_1_2_ea12029200.png&w=3840&q=75)](https://motherduck.com/blog/announcing-duckdb-12-on-motherduck-cdw/)

[2025/02/05 - Sheila Sitaram](https://motherduck.com/blog/announcing-duckdb-12-on-motherduck-cdw/)

### [MotherDuck Now Supports DuckDB 1.2: Faster, Friendlier, Better Performance](https://motherduck.com/blog/announcing-duckdb-12-on-motherduck-cdw)

DuckDB 1.2 has launched, with improvements in performance, the SQL experience, CSV handling, and scalability - all fully supported in MotherDuck!

[![How to build an interactive, shareable sentiment analysis dashboard with MotherDuck & Fabi.ai](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FFabi_blog_023f05dd0e.png&w=3840&q=75)](https://motherduck.com/blog/fabi-ai-llm-prompt-analysis/)

[2025/02/12 - Marc Dupuis](https://motherduck.com/blog/fabi-ai-llm-prompt-analysis/)

### [How to build an interactive, shareable sentiment analysis dashboard with MotherDuck & Fabi.ai](https://motherduck.com/blog/fabi-ai-llm-prompt-analysis)

Interactive, shareable sentiment analysis dashboard with MotherDuck & Fabi.ai

[View all](https://motherduck.com/blog/)

Authorization Response