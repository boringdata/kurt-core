---
title: layers-multi-tenant-data-warehouse
content_type: case_study
source_url: https://motherduck.com/case-studies/layers-multi-tenant-data-warehouse
indexed_at: '2025-11-25T20:02:35.326690'
content_hash: d7024a903143c927
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO CASE STUDIES](https://motherduck.com/case-studies/)

# How Layers Slashed Analytics Costs and Gave Every Customer a Private Data Warehouse

MotherDuck has let us just focus on the analytics and the roll up, the actual querying portion of it, and has kind of kicked out all of the concerns and time and research on where are we storing this data long term? What about the costs? What about the latency? What about the scale? All of those are sort of afterthoughts now.

![Jake Casto's photo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fjakecasto_dce7fec5f8.jpeg&w=3840&q=75)

Jake Casto

Founder

[![Jake Casto company logo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Flayers_logo_d023d0e735.svg&w=3840&q=75)](https://www.uselayers.com/)

We were somehow spending more money to show a very basic analytics dashboard with no more than a dozen data points than the billions of requests that we serve.

## **TL;DR Snapshot**

| Metric | Before MotherDuck | After MotherDuck |
| :-- | :-- | :-- |
| **Cost per small tenant** | Projected 100x increase in cost for each tenant after a vendor's pricing change. | "Fractions of a penny" incremental cost for small brands. |
| **Retention flexibility** | Inflexible, platform-wide retention that couldn't easily extend beyond 90 days. | Per-tenant retention windows (5, 90, 180+ days) configured on demand. |
| **Performance isolation** | The risk of "noisy neighbors" in a shared architecture was a major concern. | Per-tenant engines and storage namespaces provide performance isolation. |

## **About Layers**

Layers powers on-site product search, recommendations, and usage analytics for retail brands. Traffic is spiky and large: 100M requests on a typical day, with peaks pushing toward the billion mark during promotions. Layers must surface fresh usage metrics in customer-facing dashboards and feed ML models that drive recommendations. End-user UX matters; queries need to land in well under 110 ms so they do not drag down storefront performance.

Every customer (tenant) behaves differently. Boutique brands trickle data and may only want a short lookback window, while big-box retailers send firehose volumes and expect long retention for seasonal trend analysis. These differences created economic challenges for Layers, which needed a way to tune data cost, compute, and retention per tenant.

## **The Roadblock**

Layers initially tried stitching together commodity infrastructure: Postgres for transactional bits, a streaming pipeline, and a serverless data API to serve dashboards. Reality hit hard.

- **Shared-Architecture Concerns** A multi-tenant analytical service raised concerns about performance isolation. The team worried that a large retail tenant running heavy analytics could slow down performance for smaller tenants, and there was no clean way to attribute costs to the customers responsible for them.
- **Network Latency harming CX** Serving dashboards over a stateless serverless API added "close to 100 milliseconds" on its own. That blew the company's 110 ms latency budget before application logic could even run.
- **Failing Analytics Solutions** After running analytics on PostgreSQL hit a bottleneck, Layers moved to TinyBird, a serverless ClickHouse solution. Following initial struggles with integration, a pricing model change was the final straw. The change would have led to a 100x increase in cost for the same workload for each tenant. Multiplying that across dozens of customers made the business model unworkable. Layers paused roadmap work to find a new pattern.

> We were somehow spending more money to show a very basic analytics dashboard with no more than a dozen data points than the billions of requests that we serve.

## **Why MotherDuck**

MotherDuck combines DuckDB's in-process speed with cloud elasticity and object storage economics. Two things mattered most to Layers:

**per-tenant architecture** and the **object storage + MotherDuck paradigm**.

1\. Per-tenant architecture (private warehouse per customer)

In MotherDuck, the lightweight DuckDB execution engine can be instantiated on demand, letting Layers treat each SaaS customer as if they have their own mini data warehouse without paying for idle clusters28.

- **Performance isolation**: The team's concern about performance was addressed, as long scans for a large retailer do not have to contend with a boutique shop's lightweight queries. Work happens in separate DuckDB processes.
- **Metering and showback**: Because compute spins up per tenant, Layers can attribute CPU-seconds and query counts to the correct customer. Small tenants cost pennies, while heavy tenants are visible and billable.
- **Retention by contract**: Need to store 5 days for a free tier but 180+ days for an enterprise account? Simply adjust the lifecycle rules on that tenant's object storage prefix. It's a configuration edit, not a data migration.

2\. Object storage + MotherDuck paradigm (batch, not stream)

Layers shifted from an always-on streaming ingestion mindset to a batched object-store pattern. They realized that for their customers, real-time could mean updates every 5 to 15 minutes, not every few milliseconds.

- **Ingest events to object storage**: Cloudflare Pipelines write compressed columnar files (like Parquet) to R2 every few minutes.
- **Zero-copy analytics**: MotherDuck can read these files in place. No need to pump rows through a long ETL chain or load them into proprietary storage.
- **Cheap historical depth**: Object storage costs pennies per GB-month. Instead of purging globally, Layers can leave data in storage indefinitely for a very small cost and "let everything flow in" if a customer needs to extend their retention window.
- **Flexible batch cadence**: For near-real-time dashboards, Layers lands micro-batches every 5 to 15 minutes. For cost-sensitive tenants, hourly or daily is fine.

![Layers_architecture](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2025_08_18_at_1_55_24_PM_dffdebbda8.png&w=3840&q=75)

Beyond customer-facing analytics, this architecture also powers Layers' ML and recommendation workloads. The same analytical queries that feed dashboards can be leveraged for training models and generating personalized product recommendations, all within the same isolated tenant infrastructure.

> "MotherDuck has let us just focus on the analytics and the roll up, the actual querying portion of it, and has kind of kicked out all of the concerns and time and research on where are we storing this data long term? You know, what about the costs? What about the latency? What about the scale? All of those are sort of afterthoughts now."

## **Results**

- **Economic Impact**: Avoided a projected 1,000x cost increase from a previous vendor's pricing change. The marginal cost for smaller tenants is now "fractions of a penny," which unlocked a freemium tier.
- **Performance and User Experience**: Dashboards load within the 110 ms SLA target because there is no extra network hop through an external query API. Heavy enterprise queries don't contend with smaller tenants' workloads thanks to per-tenant DuckDB execution.
- **Data Agility**: Retention windows are now a lever in sales conversations. Engineers can prototype locally against the same data that powers production, using the same SQL.

Authorization Response