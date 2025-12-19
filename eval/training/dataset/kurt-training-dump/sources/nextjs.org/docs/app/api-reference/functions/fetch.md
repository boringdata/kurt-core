---
title: Functions: fetch | Next.js
url: https://nextjs.org/docs/app/api-reference/functions/fetch
hostname: nextjs.org
description: API reference for the extended fetch function.
sitename: Next.js
date: 2025-10-22
---
# fetch

Next.js extends the [Web fetch() API](https://developer.mozilla.org/docs/Web/API/Fetch_API) to allow each request on the server to set its own persistent caching and revalidation semantics.

In the browser, the `cache`

option indicates how a fetch request will interact with the *browser's* HTTP cache. With this extension, `cache`

indicates how a *server-side* fetch request will interact with the framework's persistent [Data Cache](https://nextjs.org/docs/app/guides/caching#data-cache).

You can call `fetch`

with `async`

and `await`

directly within Server Components.

```
export default async function Page() {
let data = await fetch('https://api.vercel.app/blog')
let posts = await data.json()
return (
<ul>
{posts.map((post) => (
<li key={post.id}>{post.title}</li>
))}
</ul>
)
}
```


`fetch(url, options)`


Since Next.js extends the [Web fetch() API](https://developer.mozilla.org/docs/Web/API/Fetch_API), you can use any of the

[native options available](https://developer.mozilla.org/docs/Web/API/fetch#parameters).

`options.cache`


Configure how the request should interact with Next.js [Data Cache](https://nextjs.org/docs/app/guides/caching#data-cache).

`fetch(`https://...`, { cache: 'force-cache' | 'no-store' })`


(default): Next.js fetches the resource from the remote server on every request in development, but will fetch once during`auto no cache`

`next build`

because the route will be statically prerendered. If[Dynamic APIs](https://nextjs.org/docs/app/guides/caching#dynamic-rendering)are detected on the route, Next.js will fetch the resource on every request.: Next.js fetches the resource from the remote server on every request, even if Dynamic APIs are not detected on the route.`no-store`

: Next.js looks for a matching request in its Data Cache.`force-cache`

- If there is a match and it is fresh, it will be returned from the cache.
- If there is no match or a stale match, Next.js will fetch the resource from the remote server and update the cache with the downloaded resource.


`options.next.revalidate`


`fetch(`https://...`, { next: { revalidate: false | 0 | number } })`


Set the cache lifetime of a resource (in seconds). [Data Cache](https://nextjs.org/docs/app/guides/caching#data-cache).

- Cache the resource indefinitely. Semantically equivalent to`false`

`revalidate: Infinity`

. The HTTP cache may evict older resources over time.- Prevent the resource from being cached.`0`

- (in seconds) Specify the resource should have a cache lifetime of at most`number`

`n`

seconds.


Good to know:

- If an individual
`fetch()`

request sets a`revalidate`

number lower than the[default]of a route, the whole route revalidation interval will be decreased.`revalidate`

- If two fetch requests with the same URL in the same route have different
`revalidate`

values, the lower value will be used.- Conflicting options such as
`{ revalidate: 3600, cache: 'no-store' }`

are not allowed, both will be ignored, and in development mode a warning will be printed to the terminal.

`options.next.tags`


`fetch(`https://...`, { next: { tags: ['collection'] } })`


Set the cache tags of a resource. Data can then be revalidated on-demand using [ revalidateTag](https://nextjs.org/docs/app/api-reference/functions/revalidateTag). The max length for a custom tag is 256 characters and the max tag items is 128.

## Troubleshooting

### Fetch default `auto no store`

and `cache: 'no-store'`

not showing fresh data in development

Next.js caches `fetch`

responses in Server Components across Hot Module Replacement (HMR) in local development for faster responses and to reduce costs for billed API calls.

By default, the [HMR cache](https://nextjs.org/docs/app/api-reference/config/next-config-js/serverComponentsHmrCache) applies to all fetch requests, including those with the default `auto no cache`

and `cache: 'no-store'`

option. This means uncached requests will not show fresh data between HMR refreshes. However, the cache will be cleared on navigation or full-page reloads.

See the [ serverComponentsHmrCache](https://nextjs.org/docs/app/api-reference/config/next-config-js/serverComponentsHmrCache) docs for more information.

### Hard refresh and caching in development

In development mode, if the request includes the `cache-control: no-cache`

header, `options.cache`

, `options.next.revalidate`

, and `options.next.tags`

are ignored, and the `fetch`

request is served from the source.

Browsers typically include `cache-control: no-cache`

when the cache is disabled in developer tools or during a hard refresh.

## Version History

| Version | Changes |
|---|---|
`v13.0.0` | `fetch` introduced. |

Was this helpful?