---
title: atm-com-analytics-costs-sql-expressibility
content_type: case_study
source_url: https://motherduck.com/case-studies/atm-com-analytics-costs-sql-expressibility
indexed_at: '2025-11-25T20:02:36.725272'
content_hash: 72660cae8172320d
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO CASE STUDIES](https://motherduck.com/case-studies/)

# ATM.com cuts analytics costs by 65% while gaining SQL expressibility

Even with a few big backfills, we're still looking at costs that are 35 to 40% of what we're paying with SingleStore.

![Nico Ritschel's photo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fnico_ritschel_photo_41ba132b33.jpg&w=3840&q=75)

Nico Ritschel

Director of Engineering

[![Nico Ritschel company logo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Fatm_1_0fe4ee9409.svg&w=3840&q=75)](https://atm.com/)

ATM.com empowers users on their financial journey, offering cash advances and tools to help users mature financially. Founded in 2019, the Irvine-based fintech has evolved from its initial focus on data monetization to become a comprehensive financial platform serving millions of users with microtransactions daily.

[ATM.com](http://atm.com/), a fintech platform serving millions of users, migrates from SingleStore to MotherDuck, transforming their analytics workflow and ML model development.

As director of engineering, **Nico Ritschel** leads a lean analytics team that punches above its weight. With just two people handling all analytics—Ritschel and their lead backend engineer—the team manages everything from experimentation platforms to ML models that power core business decisions.

## **The SingleStore trap: doubling costs with no escape**

ATM.com had built their analytics infrastructure on SingleStore, initially attracted by its promise of serving as both a warehouse and operational database. The company envisioned it as the core of their system, especially as they explored becoming more advertising-focused.

But reality hit hard. SingleStore's pricing model meant costs could only go in one direction: up.

"I saw costs balloon with SingleStore with no sign of remediation in sight," Ritschel explains. "It seemed like customers with SingleStore just continue to double their usage yearly. There's no real option besides doubling. You can't size something up more incrementally."

The technical limitations proved equally frustrating. SingleStore's ingest functionality, which watches S3 buckets for new data, created an unexpected problem. "It clutters the internal memory store with metadata for the files that have been loaded," Ritschel notes. "The ironic part is that the amount of maintenance required to keep that operating smoothly is more than just loading the files yourself."

The situation became untenable when Ritschel needed to size up cluster sizes solely to handle accumulated metadata—not actual data processing needs.

## **Finding DuckDB: from local transformations to production analytics**

Ritschel's path to MotherDuck began with a new M2 MacBook Pro and a desire to leverage its power. After seeing MotherDuck CEO Jordan Tigani's posts about dual execution and watching talks about leveraging Apple silicon, something clicked.

"DuckDB seemed like a bit of a silver bullet when I first saw it," Ritschel recalls. "I can just query Parquet on S3 directly, and it makes range requests and does all this fancy stuff without having to spin up a Spark cluster. It kind of blew my mind."

The expressibility of DuckDB's SQL syntax became a major draw. Ritschel had been using DuckDB for local transformations and found switching back to SingleStore's syntax increasingly painful. The seamless integration with tools like pandas through zero-copy operations demonstrated what modern analytics could look like.

## **Migration in motion: from Rails to ML models**

ATM.com's architecture reflects the complexity of a modern fintech platform. Their Rails applications backed by Postgres handle millions of daily transactions, while Kinesis streams pump clickstream events from mobile apps into S3 as JSON or Parquet files. Marketing data, partner integrations, and Braze customer engagement data all flow into the analytics platform.

The migration to MotherDuck is happening incrementally, using Sling for data movement from RDS Postgres. Despite still being in transition, the results are already dramatic.

"Even with a few big backfills, we're still looking at costs that are 35 to 40% of what we're paying with SingleStore," Ritschel reports.

The performance improvements extend beyond cost savings. The team runs extensive experimentation across their platform, with granular details around engagement, cost, and revenue informing spending decisions. Ad offer optimization, financial reporting, and reconciliation of millions of microtransactions all run more smoothly on MotherDuck.

## **Powering machine learning with modern infrastructure**

One of the most compelling use cases emerged in machine learning. ATM.com builds ML models for various business functions, from user behavior prediction to financial risk assessment. The workflow has become remarkably streamlined.

"We're mostly working with XGBoost models," Ritschel explains. "The workflow thus far has been building the models out in Hex, and we can actually export the weights and infer directly in Ruby."

This tight integration between analytics and production systems — feeding analytical insights back into backend systems for real-time decision making — is powerful for their business. It's a pattern that was painful with SingleStore but flows naturally with MotherDuck.

The team uses SQLMesh for transformations, managing everything from nightly de-duplication processes on tables approaching 10 billion rows to complex financial modeling for strategic planning.

## **Breaking free from vendor lock-in**

The contrast with traditional vendor relationships couldn't be starker. Where SingleStore support meant filing tickets and waiting days for responses from lower-tier employees, MotherDuck's team provides what Ritschel describes as "white glove service."

"Everyone always bends over backwards to help.”

This support proved crucial during migration, helping the team navigate differences in JSON handling and optimize their analytics patterns for MotherDuck's architecture. While some adjustments were needed—particularly around JSON storage and querying approaches—nothing proved insurmountable.

## **Looking ahead: the promise of modern data infrastructure**

As ATM.com completes their migration, they're exploring advanced features like DuckLake and Iceberg integration. With costs already down 65% and performance dramatically improved, the team can focus on what matters: building better financial products for their users.

"Keep on quacking," Ritschel says.

For a fintech platform processing millions of daily transactions with just two people handling analytics, finding the right data infrastructure isn't just about technology—it's about empowerment. MotherDuck has given ATM.com's lean team the tools to compete with companies ten times their size, all while cutting costs and improving performance.

With MotherDuck, the destination is clear: a modern data stack that scales with the business, not the vendor's revenue targets.

Authorization Response