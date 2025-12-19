---
title: Vercel CDN overview
url: https://vercel.com/docs/cdn
hostname: vercel.com
description: Vercel's CDN enables you to store content close to your customers and run compute in regions close to your data, reducing latency and improving end-user performance.
sitename: vercel.com
date: 2025-11-25
---
# Vercel CDN overview

Vercel's CDN is a globally distributed platform that stores content near your customers and runs compute in [regions](https://vercel.com/docs/regions) close to your data, reducing latency and improving end-user performance.

If you're deploying an app on Vercel, you already use our CDN. These docs will teach you how to optimize your apps and deployment configuration to get the best performance for your use case.

Vercel's CDN is built on a robust global infrastructure designed for optimal performance and reliability:

- Points of Presence (PoPs): Our network includes 126 PoPs distributed worldwide. These PoPs act as the first point of contact for incoming requests and route requests to the nearest region.
- Vercel Regions: Behind these PoPs, we maintain
[19 compute-capable regions](https://vercel.com/docs/regions)where your code runs close to your data. - Private Network: Traffic flows through private, low-latency connections from PoPs to the nearest region, ensuring fast and efficient data transfer.

This architecture balances the widespread geographical distribution benefits with the efficiency of concentrated caching and computing resources. By maintaining fewer, dense regions, we increase cache hit probabilities while ensuring low-latency access through our extensive PoP network.

[Redirects](https://vercel.com/docs/redirects): Redirects tell the client to make a new request to a different URL. They are useful for enforcing HTTPS, redirecting users, and directing traffic.[Rewrites](https://vercel.com/docs/rewrites): Rewrites change the URL the server uses to fetch the requested resource internally, allowing for dynamic content and improved routing.[Headers](https://vercel.com/docs/headers): Headers can modify the request and response headers, improving security, performance, and functionality.[Caching](https://vercel.com/docs/cdn-cache): Caching stores responses in the CDN, reducing latency and improving performance[Streaming](https://vercel.com/docs/functions/streaming-functions): Streaming enhances your user's perception of your app's speed and performance.[HTTPS / SSL](https://vercel.com/docs/encryption): Vercel serves every deployment over an HTTPS connection by automatically provisioning SSL certificates.[Compression](https://vercel.com/docs/compression): Compression reduces data transfer and improves performance, supporting both gzip and brotli compression.

Vercel's CDN pricing is divided into three resources:

- Fast Data Transfer: Data transfer between the Vercel CDN and the user's device.
- Fast Origin Transfer: Data transfer between the CDN and Vercel Functions.
- Edge Requests: Requests made to the CDN.

All resources are billed based on usage with each plan having an [included allotment](https://vercel.com/docs/pricing). Those on the Pro plan are billed according to additional allotments.

The pricing for each resource is based on the region from which requests to your site come. Use the dropdown to select your preferred region and see the pricing for each resource.

Resource | Hobby Included | On-demand Rates |
|---|---|---|
| First 100 GB | $0.15 per 1 GB | |
| First 10 GB | $0.06 per 1 GB | |
| First 1,000,000 | $2.00 per 1,000,000 Requests |

The table below shows the metrics for the [Networking](https://vercel.com/docs/pricing/networking) section of the Usage dashboard.

To view information on managing each resource, select the resource link in the Metric column. To jump straight to guidance on optimization, select the corresponding resource link in the Optimize column.

Metric | Description | Priced | Optimize |
|---|---|---|---|
|

[Fast Data Transfer](https://vercel.com/docs/manage-cdn-usage#fast-data-transfer)[Yes](https://vercel.com/docs/pricing/regional-pricing)[Learn More](https://vercel.com/docs/manage-cdn-usage#optimizing-fast-data-transfer)[Fast Origin Transfer](https://vercel.com/docs/manage-cdn-usage#fast-origin-transfer)[Yes](https://vercel.com/docs/pricing/regional-pricing)[Learn More](https://vercel.com/docs/manage-cdn-usage#optimizing-fast-origin-transfer)[Edge Requests](https://vercel.com/docs/manage-cdn-usage#edge-requests)[Yes](https://vercel.com/docs/pricing/regional-pricing)[Learn More](https://vercel.com/docs/manage-cdn-usage#optimizing-edge-requests)See the [manage and optimize networking usage](https://vercel.com/docs/pricing/networking) section for more information on how to optimize your usage.

The CDN supports the following protocols (negotiated with [ALPN](https://tools.ietf.org/html/rfc7301)):

Vercel supports 35 [frontend frameworks](https://vercel.com/docs/frameworks). These frameworks provide a local development environment used to test your app before deploying to Vercel.

Through [framework-defined infrastructure](https://vercel.com/blog/framework-defined-infrastructure), Vercel then transforms your framework build outputs into globally [managed infrastructure](https://vercel.com/products/managed-infrastructure) for production.

If you are using [Vercel Functions](https://vercel.com/docs/functions) or other compute on Vercel *without* a framework, you can use the [Vercel CLI](https://vercel.com/docs/cli) to test your code locally with [.](https://vercel.com/docs/cli/dev)

While sometimes necessary, proceed with caution when you place another CDN in front of Vercel:

- Vercel's CDN is designed to deploy new releases of your site without downtime by purging the
[CDN Cache](https://vercel.com/docs/cdn-cache)globally and replacing the current deployment. - If you use an additional CDN in front of Vercel, it can cause issues because Vercel has no control over the other provider, leading to the serving of stale content or returning 404 errors.
- To avoid these problems while still using another CDN, we recommend you either configure a short cache time or disable the cache entirely. Visit the documentation for your preferred CDN to learn how to do either option or learn more about
[using a proxy](https://vercel.com/kb/guide/can-i-use-a-proxy-on-top-of-my-vercel-deployment)in front of Vercel.

Was this helpful?