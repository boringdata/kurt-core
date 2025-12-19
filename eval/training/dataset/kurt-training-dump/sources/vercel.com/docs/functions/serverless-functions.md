---
title: Vercel Functions
url: https://vercel.com/docs/functions
hostname: vercel.com
description: Vercel Functions allow you to run server-side code without managing a server.
sitename: vercel.com
date: 2025-12-01
---
# Vercel Functions

Vercel Functions lets you run server-side code without managing servers. They adapt automatically to user demand, handle connections to APIs and databases, and offer enhanced concurrency through [fluid compute](https://vercel.com/docs/fluid-compute), which is useful for AI workloads or any I/O-bound tasks that require efficient scaling

When you deploy your application, Vercel automatically sets up the tools and optimizations for your chosen [framework](https://vercel.com/docs/frameworks). It ensures low latency by routing traffic through Vercel's [CDN](https://vercel.com/docs/cdn), and placing your functions in a specific region when you need more control over [data locality](https://vercel.com/docs/functions#functions-and-your-data-source).

To get started with creating your first function, copy the code below:

While using is the recommended way to create a Vercel Function, you can still use HTTP methods like and .

To learn more, see the [quickstart](https://vercel.com/docs/functions/quickstart) or [deploy a template](https://vercel.com/templates).

Vercel Functions run in a single [region](https://vercel.com/docs/functions/configuring-functions/region) by default, although you can configure them to run in multiple regions if you have globally replicated data. These functions let you add extra capabilities to your application, such as handling authentication, streaming data, or querying databases.

When a user sends a request to your site, Vercel can automatically run a function based on your application code. You do not need to manage servers, or handle scaling.

Vercel creates a new function invocation for each incoming request. If another request arrives soon after the previous one, Vercel [reuses the same function](https://vercel.com/docs/fluid-compute#optimized-concurrency) instance to optimize performance and cost efficiency. Over time, Vercel only keeps as many active functions as needed to handle your traffic. Vercel scales your functions down to zero when there are no incoming requests.

By allowing concurrent execution within the same instance (and so using idle time for compute), fluid compute reduces cold starts, lowers latency, and saves on compute costs. It also prevents the need to spin up multiple isolated instances when tasks spend most of their time waiting for external operations.

Functions should always execute close to where your data source is to reduce latency. By default, functions using the Node.js runtime execute in Washington, D.C., USA (), a common location for external data sources. You can set a new region through your [project's settings on Vercel](https://vercel.com/docs/functions/configuring-functions/region#setting-your-default-region).

You can view various performance and cost efficiency metrics using Vercel Observability:

- Choose your project from the
[dashboard](https://vercel.com/d?to=%2F%5Bteam%5D%2F%5Bproject%5D&title=Go+to+dashboard). - Click on the Observability tab and select the Vercel Functions section.
- Click on the chevron icon to expand and see all charts.

From here, you'll be able to see total consumed and saved GB-Hours, and the ratio of the saved usage. When you have [fluid](https://vercel.com/docs/fluid-compute) enabled, you will also see the amount of cost savings from the [optimized concurrency model](https://vercel.com/docs/fluid-compute#optimized-concurrency).

Vercel Functions are priced based on active CPU, provisioned memory, and invocations. See the [fluid compute pricing](https://vercel.com/docs/functions/usage-and-pricing) documentation for more information.

If your project is not using fluid compute, see the [legacy pricing documentation](https://vercel.com/docs/functions/usage-and-pricing/legacy-pricing) for Vercel Functions.

Was this helpful?