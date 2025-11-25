---
title: trunkrs-same-day-delivery-motherduck-from-redshift
content_type: case_study
source_url: https://motherduck.com/case-studies/trunkrs-same-day-delivery-motherduck-from-redshift
indexed_at: '2025-11-25T20:02:59.033379'
content_hash: 1fcd0ba39f56f15c
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO CASE STUDIES](https://motherduck.com/case-studies/)

# Trunkrs accelerates same-day delivery decisions with MotherDuck

With MotherDuck, we're seeing that response is just a lot snappier. We can see that we're just going deeper because we have more time to spend on the data.

![Hidde Stokvis's photo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FT2_HGPGLGJ_U2_HG_6_HF_54_5f7437812113_512_3f1c807aa2.png&w=3840&q=75)

Hidde Stokvis

COO and Data Leader

[![Hidde Stokvis company logo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Ftrunkrs_logo_3c611c30c7.svg&w=3840&q=75)](https://trunkrs.nl/)

Trunkrs orchestrates a network of existing assets—vehicles that would otherwise sit idle in the evenings—to create an efficient same-day delivery network specializing in perishable goods.

Trunkrs isn't your typical parcel delivery company. While they compete with major carriers in the Netherlands, their approach is fundamentally different. The company orchestrates a network of existing assets—vehicles that would otherwise sit idle in the evenings—to create an efficient same-day delivery network specializing in perishable goods.

"Internally, we are kind of a software company tying all of this together and hopefully owning as little assets as possible," explains Hidde Stokvis, who leads data initiatives at Trunkrs. The company has become the market leader in frozen meat delivery by leveraging their quick network to eliminate the need for expensive cold chain logistics.

This software-first approach extends to how Trunkrs uses data. With operations changing rapidly throughout each day—sorting processes, delivery routes, partner performance—the team needs real-time insights to maintain their edge in efficiency.

## **The morning meeting that changed everything**

Every morning, Trunkrs runs a day-start meeting where teams dive into the previous day's performance. They keep a live Looker dashboard open during these calls, drilling into specific issues as they arise. Was sorting quality low? Which warehouse had problems? Was it a specific customer's packaging or labeling causing delays?

"Even if it just takes 10 seconds longer, that's annoying if you're in a call and you're trying to get to the bottom of a problem," Stokvis notes. With their previous Redshift setup, queries could be sluggish and unpredictable, limiting how deeply the team could investigate issues.

The slow queries had a cascading effect. Users would stop drilling down after waiting too long for results. Problems that could have been solved went unaddressed. The very efficiency Trunkrs brought to logistics was being undermined by their data infrastructure.

## **From Redshift frustration to serverless simplicity**

Trunkrs had built a comprehensive data stack, ingesting data from Postgres application databases, HubSpot, their accounting software, and numerous other sources using Meltano and Dagster. Everything flowed into Redshift, where dbt transformed the data for analysis in Looker.

But Redshift required constant optimization. Despite most queries focusing on recent data—what happened yesterday, last week, or this month—the system struggled with the parallel requests from users monitoring fast-changing operations.

"It takes a lot of work to optimize Redshift," Stokvis observes. "And basically, we had to scale for that. And it wasn't cost efficient."

The team evaluated multiple alternatives including ClickHouse before discovering DuckDB through online communities. What attracted them to MotherDuck was how it aligned with their engineering philosophy.

"We are heavily using serverless in our backend, in our applications," Stokvis explains. "We develop a lot and try to spend less time on our infrastructure." MotherDuck's abstraction of the underlying architecture meant their data engineers could focus on delivering insights rather than database tuning.

## **Simple migration, powerful results**

The migration proved surprisingly straightforward. Trunkrs created a carbon copy of their Redshift setup in MotherDuck, running both systems in parallel as they moved sources over. They used pg\_duckdb as a proxy for Looker, making the integration seamless.

Along the way, they discovered opportunities for optimization. While Redshift had required more normalized data structures, MotherDuck performed well with denormalized tables that Looker preferred, simplifying their overall architecture.

The support from MotherDuck's team proved crucial during implementation. "We could just work together with you guys on Slack in the beginning and basically run through all the issues we had," Stokvis recalls. "If it blocks even for a couple of days, your speed of implementation goes down. But you guys were on top of that."

## **Drilling deeper into operational excellence**

The impact was immediate and transformative. Those morning meetings that had been constrained by query performance became dynamic problem-solving sessions.

"With MotherDuck, we're seeing that response is just a lot snappier," Stokvis reports. "We can see that we're just going deeper because we have more time to spend on the data. And it becomes less of an annoyance, so everybody's okay with us diving in a little bit deeper."

This speed unlocked a virtuous cycle. Faster queries meant deeper analysis. Deeper analysis meant better problem identification. Better problem identification meant fewer repeated mistakes. The efficiency Trunkrs brought to logistics was finally matched by the efficiency of their data stack.

"The quicker you can go through this and drill down in that data, the more insights you will get and easier it becomes to make sure that we're not making the same mistake today that we made yesterday," Stokvis explains.

## **Expanding the data-driven culture**

With approximately 700GB already migrated (about 30-40% of their total data), Trunkrs is expanding how they use analytics. They're moving beyond sending static Excel and PDF reports to customers, planning to embed analytics directly in their shipping portal.

The team has also split their MotherDuck usage between transformation workloads (dbt and ELT processes) and query workloads (Looker and direct SQL access), though they haven't yet optimized instance types for these different use cases. As they complete the migration, they expect to realize additional cost savings compared to their Redshift setup.

"It really makes your data feel like an application," Stokvis reflects. "And that's something you want, but it's difficult with data. It depends a lot on your architecture, your setup, your transformations. With MotherDuck, that's a little bit less. The speed is just a lot higher. So a lot of that bother is already taken away."

For a company built on optimizing existing assets and maximizing efficiency, finding a data platform that embodies those same principles has proven to be the perfect match. As Trunkrs continues to revolutionize same-day delivery in the Netherlands, they now have the analytical horsepower to match their operational ambitions.

## Trunkrs' Data Stack

- **Cloud Data Warehouse:** MotherDuck after migrating from Amazon Redshift
- **Data sources:** Postgres, Hubspot, accounting software, etc.
- **Data extraction and orchestration:** [Meltano](https://motherduck.com/ecosystem/meltano/) and [Dagster](https://motherduck.com/ecosystem/dagster/)
- **Data transformation:** [dbt](https://motherduck.com/ecosystem/dbt/)
- **Dashboards and business intelligence:** [Looker](https://cloud.google.com/looker) (via [pg\_duckdb](https://github.com/duckdb/pg_duckdb))

Authorization Response