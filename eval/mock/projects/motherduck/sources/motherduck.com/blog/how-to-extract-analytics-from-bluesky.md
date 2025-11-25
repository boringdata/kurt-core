---
title: how-to-extract-analytics-from-bluesky
content_type: blog
source_url: https://motherduck.com/blog/how-to-extract-analytics-from-bluesky
indexed_at: '2025-11-25T19:58:32.854883'
content_hash: 617921736b8837fd
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# How to Extract Analytics from Bluesky, the New Open Social Network

2024/11/20 - 10 min read

BY

[Simon Späti](https://motherduck.com/authors/simon-sp%C3%A4ti/)
,
[Mehdi Ouazza](https://motherduck.com/authors/mehdi-ouazza/)

Do you remember the good old times of Twitter? When you could fetch data through the API in real-time, allowing people to build tools on top of it. These times are back. Now, with Bluesky, you can do the same.

What is Bluesky? Bluesky is a social network like Twitter and Threads, but unlike them, it is fully open-source. It is [growing](https://bsky.app/profile/bsky.app/post/3lb3qyu64bs2z) by 1 million new users daily, and we can all follow along with the numbers and create new tools.

In this article, we do exactly that. We'll get analytics from Bluesky leveraging DuckDB and MotherDuck, and we'll explore the open APIs and streams so that you can build your own dashboards, tools, and visualizations. No one should stop you from getting your own insights from the data, and Bluesky is the perfect place to start.

Your browser does not support the video tag.

Live post visualized in 3D, made with [Bluesky Firehose](https://firehose3d.theo.io/)

## What is Bluesky

[Bluesky](https://github.com/bluesky-social/social-app) is a social app for web, Android, and iOS, and leverages an innovative decentralized social networking protocol called [ATProto](https://github.com/bluesky-social/atproto). If Bluesky goes down, the protocol and your posts/data stay, and the new UI can be rebuilt. Two alternative UIs are already built on top of ATProto: [Frontpage](https://frontpage.fyi/), an alternative Hackernews, and [Smoke Signal](https://smokesignal.events/), an RSVP management app.

These don't use all the features ATProto provides, but specific information about the user and information that helps the app serve its particular purpose. You can also start cross-using or displaying information from the protocol. For example, you could show posts with a specific hashtag or people from a particular area for each meetup. The use cases are endless.

### How does it work?

Another feature that Bluesky and ATProto have is decentralization. Bluesky revolutionized this with the ATProto. Although, by default, the content is hosted on the Bluesky [Personal Data Server (PDS)](https://github.com/bluesky-social/pds) server, **everyone can host their content on their server**, and the interface is your handle, the same as it was with the web.

Interestingly, this approach is a return to the old web, giving more power to the people and moving away from prominent social media companies that control everything. Dan illustrates this best in his video about [Web Without Walls](https://www.youtube.com/watch?v=F1sJW6nTP6E), showcasing it with blogs you own, interlinked to other blogs and websites from your server to the other. Today, centralized social media platforms host and own all your content on their servers; without them, your content is lost, too.

![image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fhackmd.io%2F_uploads%2FB1DGtxYfJx.png&w=3840&q=75)
Illustration going from websites to centralized social media platforms to a decentralized AT Protocol.

Decentralization and hosting of your server are achieved through the so-called Personal Data Server (PDS), which is also open-source. Interestingly, each user's data is implemented and stored with a single SQLite database. This means there are around 19 million as of now, but when you run your own, you could implement it with any backend, e.g., DuckDB. 😉

Tip

Check out ATProto Browser to see all artifacts attached to the protocol.


Check all your artifacts, such as posts, likes, etc., on the [ATProto Browser](https://atproto-browser.vercel.app/), such as the events mentioned above or Frontpage interactions. E.g., for my handle, this looks like this:


![ATProto Browser Example](https://motherduck.com/_next/image/?url=https%3A%2F%2Fhackmd.io%2F_uploads%2FB13VYeFMke.png&w=3840&q=75)

### Philosophy and Working Without a Massive Algorithm

Before we get into some code examples, here is a quick note on the philosophy behind Bluesky and how it differs from Twitter, Instagram, and LinkedIn. Instead of one colossal algorithm deciding what we see and what not, Bluesky works based on people and feeds. The feeds are either created by Bluesky (e.g., [popular with friends](https://bsky.app/profile/did:plc:z72i7hdynmk6r22z27h6tvur/feed/with-friends), [quiet posters](https://bsky.app/profile/did:plc:vpkhqolt662uhesyj6nxm7ys/feed/infreq), [likes of likes](https://bsky.app/profile/did:plc:pxwzal3aspfg2xnbbt2fjami/feed/likes-of-likes), etc.) or can be created by users themselves.

This way, you are in control of what you see. The ["Discover" feed](https://bsky.app/profile/did:plc:z72i7hdynmk6r22z27h6tvur/feed/whats-hot) is closest to other social media algorithms.

## Coding Time: Discover the Open APIs and Streams

Let's have some fun.

Not only is everything open-source but the APIs and [Jetstreams](https://docs.bsky.app/blog/jetstream) (streams of posts, likes, etc.) can also be queried for free. Let's explore some hands-on examples.

### Reading Posts with DuckDB Directly

To illustrate, you can simply read the post with DuckDB - e.g. reading my last 5 posts

```sql
Copy code

SELECT * FROM read_json_auto('https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor=did:plc:edglm4muiyzty2snc55ysuqx&limit=10')
```

The `read_json_auto` works on any JSON file and API endpoint if there aren't any http headers or other things that need to be set.
To find the unique Bluesky-ID, aka the Decentralized Identifier (DID) that you need for the above query we need to do another `GET` request to `https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle?handle=my_handle`

```sql
Copy code

D SELECT * FROM read_json_auto('https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle?handle=ssp.sh');
┌──────────────────────────────────┐
│               did                │
│             varchar              │
├──────────────────────────────────┤
│ did:plc:edglm4muiyzty2snc55ysuqx │
└──────────────────────────────────┘
D
```

It's worth noting that there's also a community DuckDB extension for HTTP requests, which is more powerful and allows you to set headers, etc. You can install it with `INSTALL http_client FROM community;` and then use it with `http_get` or `http_post`.

```sql
Copy code

INSTALL http_client FROM community;
LOAD http_client;
 WITH __input AS (
    SELECT
      http_get('https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle?handle=ssp.sh') AS res
  )
  SELECT
    res::json->>'body' as identity_json
  FROM __input;

identity_json
------------------------------------------
{"did":"did:plc:edglm4muiyzty2snc55ysuqx"}
```

Getting your feed then will be just another request to this endpoint,`https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor=<my_did>&limit=100` with your DID.

### Most Engagement with the Latest 100 Posts

To read the most engaging posts with this endpoint and plot a little bar chart that comes with DuckDB included, we can create a `MACRO` as follows.

```sql
Copy code

-- setting the did value as variable
SET variable did_value = 'did:plc:edglm4muiyzty2snc55ysuqx';
```

```sql
Copy code

CREATE MACRO get_engagement_data(did_value) AS TABLE (
    WITH raw_data AS (
        -- Use the DID parameter to construct the URL
        SELECT * FROM read_json_auto(
            'https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor=' || did_value || '&limit=100'
        )
    ),
    unnested_feed AS (
        SELECT unnest(feed) AS post_data FROM raw_data
    ),
    engagement_data AS (
        SELECT
            RIGHT(post_data.post.uri, 13) AS post_uri,
            post_data.post.author.handle,
            LEFT(post_data.post.record.text, 50) AS post_text,
            post_data.post.record.createdAt AS created_at,
            (post_data.post.replyCount +
             post_data.post.repostCount +
             post_data.post.likeCount +
             post_data.post.quoteCount) AS total_engagement,
            post_data.post.replyCount AS replies,
            post_data.post.repostCount AS reposts,
            post_data.post.likeCount AS likes,
            post_data.post.quoteCount AS quotes
        FROM unnested_feed
    )
    SELECT
        post_uri,
        created_at,
        total_engagement,
        bar(total_engagement, 0,
            (SELECT MAX(total_engagement) FROM engagement_data),
            30) AS engagement_chart,
        replies, reposts, likes, quotes,
        post_text
    FROM engagement_data
    ORDER BY total_engagement DESC
    LIMIT 30
);
```

```sql
Copy code

SELECT * FROM get_engagement_data(getvariable('did_value'));
```

That looks something like this:
![image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fhackmd.io%2F_uploads%2FrkpUYxYzJe.png&w=3840&q=75)

Note: The API limit is around `100`, so if you want more than `100`, you'll need to paginate or write code.

## Using Python for interacting with the AT Protocol

If you want all the posts, you can use the [Python SDK](https://atproto.blue/en/latest/) to interact with the AT Protocol.

### A Firehose or Live Stream of Posts

You can subscribe to the stream with this snippet: [firehose.py](https://github.com/sspaeti/bsky-atproto/blob/main/python/firehose.py).
It will stream everything and looks like this:
![demo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fdemo_68db34b900.gif&w=3840&q=75)
If you want a stream dedicated to hashtags, for instance, #datasky and #databs, check the code snippet [hashtag\_databs.py](https://github.com/sspaeti/bsky-atproto/blob/main/python/streaming_hashtag_databs.py), which captures all posts sent with these hashtags.

### Streaming and Uploading to \#databs to MotherDuck

I also created [streaming\_into\_motherduckdb.py](https://github.com/sspaeti/bsky-atproto/blob/main/python/streaming_into_motherduckdb.py) that lists both hashtags, writes them to parquet files and uploads them to a public DuckDB database hosted on MotherDuck. If you create an [account for free](https://app.motherduck.com/), you can query my shared DuckDB database with `ATTACH 'md:_share/bsky/c07e1ca0-6b51-4906-96cd-b310ec35e562' as md_bsky` and query a couple of posts I uploaded for test.

```bash
Copy code

❯ duckdb
D ATTACH 'md:_share/bsky/c07e1ca0-6b51-4906-96cd-b310ec35e562' as md_bsky;
D from md_bsky.posts limit 5;
┌──────────────────────┬──────────────────────┬──────────────────────┬──────────────────────┬──────────────────────┬──────────────────────┬─────────┬─────────┐
│         uri          │         cid          │        author        │         text         │      created_at      │      indexed_at      │ hashtag │  langs  │
│       varchar        │       varchar        │       varchar        │       varchar        │       varchar        │       varchar        │ varchar │ varchar │
├──────────────────────┼──────────────────────┼──────────────────────┼──────────────────────┼──────────────────────┼──────────────────────┼─────────┼─────────┤
│ at://did:plc:6czr5…  │ bafyreiddu2muv2yo5…  │ bramz.bsky.social    │ #databs, what Pyth…  │ 2024-11-18T08:52:4…  │ 2024-11-18T08:52:4…  │ databs  │ en      │
│ at://did:plc:edglm…  │ bafyreiebsxxsgtzba…  │ ssp.sh               │ #databs test :)      │ 2024-11-18T08:31:5…  │ 2024-11-18T08:31:5…  │ databs  │ en      │
│ at://did:plc:jfda6…  │ bafyreifizd4lxahgq…  │ victorsothervector…  │ (last thing before…  │ 2024-11-18T07:48:1…  │ 2024-11-18T07:48:1…  │ databs  │ en      │
│ at://did:plc:iyv5h…  │ bafyreifieocd3grqb…  │ rkv2401.bsky.social  │ Does anyone know o…  │ 2024-11-18T06:59:0…  │ 2024-11-18T06:59:0…  │ databs  │ en      │
│ at://did:plc:je4jm…  │ bafyreics4cctwgzw6…  │ maninekkalapudi.io   │ Entering the dark …  │ 2024-11-18T03:51:5…  │ 2024-11-18T03:51:5…  │ databs  │ en      │
└──────────────────────┴──────────────────────┴──────────────────────┴──────────────────────┴──────────────────────┴──────────────────────┴─────────┴─────────┘
```

You could do the same within MotherDuck's platform and make use of the visualization features and the benefits of the collaborative notebook approach.

You can also use [Jake](https://bsky.app/profile/jakthom.bsky.social/post/3lb4y65z24k2q)'s great collection, where he shares the Jetstream as Cloudflare R2 to query openly with DuckDB:

```bash
Copy code

❯ duckdb
D attach 'https://hive.buz.dev/bluesky/catalog' as bsky;
select count(*) from bsky.jetstream;

100% ▕████████████████████████████████████████████████████████████▏
D select count(*) from bsky.jetstream;

┌──────────────┐
│ count_star() │
│    int64     │
├──────────────┤
│       500000 │
└──────────────┘
```

It also works in the browser - check it here [DuckDB Wasm – DuckDB](https://duckdb.org/docs/api/wasm/overview.html):
![image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimg_5_ca30b061aa.png&w=3840&q=75)
Image by [Jake](https://bsky.app/profile/jakthom.bsky.social)

## What are people building?

There are currently many collaboration efforts going on, and hourly, new things are shared among the new, friendly Bluesky community. Many people try to help each other and build the best data tooling around Bluesky and ATProto. Here is the one I came across lately (I'm sorry if I forgot anyone):

- David is building on [atproto-data-tools](https://github.com/davidgasquez/atproto-data-tools): 🦋 Small scripts and tools to do data stuff with the AT Protocol.
- JavaScript implementation: [Consuming the firehose for less than $2.50/mo](https://bsky.bad-example.com/consuming-the-firehose-cheaply/)
- Jake Thomas providing the first R2 catalog, see [his post](https://bsky.app/profile/jakthom.bsky.social/post/3lb4y65z24k2q)
- [Victoriano](https://github.com/victoriano) is visualizing the post in a network graph with [Graphext](https://github.com/victoriano/bluesky-social-graph). David did a subset for `#databs` and `datasky` [here](https://davidgasquez.com/exploring-atproto-python/)
- Bluesky examples with Python: [atproto/examples](https://github.com/MarshalX/atproto/tree/main/examples)
- [Tobias Muller](https://bsky.app/profile/tobilg.com) built [skyfirehose](https://skyfirehose.com/) to also offers to query the Bluesky Jetstream with DuckDB.

I hope we can work together collaboratively and build the best Bluesky tools for data people. If not us, then who? 😀

### TABLE OF CONTENTS

[What is Bluesky](https://motherduck.com/blog/how-to-extract-analytics-from-bluesky/#what-is-bluesky)

[Coding Time: Discover the Open APIs and Streams](https://motherduck.com/blog/how-to-extract-analytics-from-bluesky/#coding-time-discover-the-open-apis-and-streams)

[Using Python for interacting with the AT Protocol](https://motherduck.com/blog/how-to-extract-analytics-from-bluesky/#using-python-for-interacting-with-the-at-protocol)

[What are people building?](https://motherduck.com/blog/how-to-extract-analytics-from-bluesky/#what-are-people-building)

!['DuckDB In Action' book cover](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fduckdb-book-full-cover.68e4f598.png&w=3840&q=75)

Get your free book!

E-mail

Subscribe to other MotherDuck news

Submit

Free Book!

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![15+ Companies Using DuckDB in Production: A Comprehensive Guide](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fthumbnail_15duckdb_prod_53e4fe2664.png&w=3840&q=75)](https://motherduck.com/blog/15-companies-duckdb-in-prod/)

[2024/11/12 - Simon Späti](https://motherduck.com/blog/15-companies-duckdb-in-prod/)

### [15+ Companies Using DuckDB in Production: A Comprehensive Guide](https://motherduck.com/blog/15-companies-duckdb-in-prod)

Discover how companies are running DuckDB in production

[![From Data Lake to Lakehouse: Can DuckDB be the best portable data catalog?](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FDuck_DB_catalog_51d1dc1d0c.png&w=3840&q=75)](https://motherduck.com/blog/from-data-lake-to-lakehouse-duckdb-portable-catalog/)

[2024/11/14 - Mehdi Ouazza](https://motherduck.com/blog/from-data-lake-to-lakehouse-duckdb-portable-catalog/)

### [From Data Lake to Lakehouse: Can DuckDB be the best portable data catalog?](https://motherduck.com/blog/from-data-lake-to-lakehouse-duckdb-portable-catalog)

Discover how catalog became crucial for Lakehouse and how DuckDB can help as a catalog

[View all](https://motherduck.com/blog/)

Authorization Response