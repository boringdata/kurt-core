---
title: motherduck-duckdb-dbt
content_type: tutorial
source_url: https://motherduck.com/blog/motherduck-duckdb-dbt
indexed_at: '2025-11-25T19:58:31.660396'
content_hash: 4233f76fbdf40552
has_code_examples: true
has_step_by_step: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# MotherDuck + dbt: Better Together

2023/09/07 - 5 min read

BY

[Sung Won Chung](https://motherduck.com/authors/sung-won-chung--/)

## My Personal DuckDB Story

DuckDB has been charming to me ever since I wrote [about it a year ago](https://roundup.getdbt.com/p/dbt-learning-to-love-software-engineers).

It gave me the glimmers of something I’ve been begging for a long time: fast should be measured in seconds, not minutes.

[I kicked the tires a lot when working at dbt Labs](https://github.com/dbt-labs/jaffle_shop_duckdb).

- [And here](https://www.loom.com/share/ed4a6f59957e43158837eb4ba0c5ed67)

- [And most recently here](https://www.loom.com/share/e213768457094a3187663a6cff76a61d?sid=29d6d696-0581-4b50-af45-7132dfb65f80)


And in all the tire kicking, it has remained true to the glimmers it gave me and so much more. It’s fast, easy, and cheap. And if it’s running on your local computer, it’s free.

I’ve had incredibly asymmetric expectations of how much money, time, and work it takes to make data fast and easy that I think to myself, “Oh, of course you’re supposed to pay lots of dollars to run queries on millions/billions of rows per month.” This has pleasantly disrupted that inner anchoring point. I see something more charming at play. Data teams can be productive with data bigger and work faster and save more money than they could have dreamed of 5 years ago. Heck! Even a year ago. So let’s get into it.

## Why use MotherDuck + dbt?

Well, DuckDB and Motherduck’s primary use case is solving analytical problems fast. Because of its columnar design, it’s able to do just that. Even more so, the creators were smart about making integrations with adjacent data tools a first class experience. We see this with reading S3 files without copying them over and querying postgres directly without needing to extract and load it into DuckDB. And you don’t need to define schemas or tedious configurations to make it work! Motherduck enables the multiplayer experience that having a single file on your machine is too tedious to pass around and synchronize with your teammates. Motherduck runs DuckDB on your behalf AND uses your local computer if the query you’re running makes more sense to run there. You get dynamic execution out of the box. And that’s pretty sweet.

But more than platitudes, let’s get hands-on with working code so you can taste and see for yourself!

## Get Started

You can follow along with [this repo](https://github.com/sungchun12/jaffle_shop_duckdb/tree/blog-guide):

1. Signup for a [MotherDuck account!](https://motherduck.com/)![signup](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fmotherduck_signup_33d4e9cf54.png%3Fupdated_at%3D2023-09-06T12%3A58%3A42.172Z&w=3840&q=75)
Note : MotherDuck is still under private beta, but I heard you could get an invite if you join their [community slack](https://slack.motherduck.com/) with a good duck pun.

2. Sign in and your screen should look like this minus some of the stuff you’ll be building in the rest of this guide.
![signin](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fsignin_14a92fa2b0.png%3Fupdated_at%3D2023-09-06T12%3A58%3A41.340Z&w=3840&q=75)

3. Click on the settings in the upper right hand corner and copy your Service Token to the clipboard.
![signin](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fservice_token_8fec7f0642.png%3Fupdated_at%3D2023-09-06T12%3A58%3A39.304Z&w=3840&q=75)

4. Clone the repo and change directories into it.


```bash
Copy code

git clone -b blog-guide https://github.com/sungchun12/jaffle_shop_duckdb.git
cd jaffle_shop_duckdb
```

5. Follow the detailed instructions to setup your [free AWS account and use S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/GetStartedWithS3.html):

_Note: Feel free to skip this step if you already have an AWS account with S3 setup! Plus, MotherDuck has these data under their public S3 bucket at s3://us-prd-motherduck-open-datasets/jaffle\_shop/csv/_

6. Take the csv files stored in the git repo [here](https://github.com/sungchun12/jaffle_shop_duckdb/tree/blog-guide/seeds) and upload them into S3:
![signin](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fseeds_9b3753fd5d.png%3Fupdated_at%3D2023-09-06T12%3A58%3A41.504Z&w=3840&q=75)![signin](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fs3_seeds_adf0454153.png%3Fupdated_at%3D2023-09-06T12%3A58%3A41.673Z&w=3840&q=75)

7. [Copy the AWS S3 access keys to authenticate](https://docs.aws.amazon.com/powershell/latest/userguide/pstools-appendix-sign-up.html) your dbt project for later.


## Configure Your dbt project

_Note: Huge thanks to Josh Wills for creating the dbt-duckdb adapter and it works great with both DuckDB and MotherDuck: [https://github.com/jwills/dbt-duckdb](https://github.com/jwills/dbt-duckdb). This demo only works with DuckDB version 0.8.1: [https://motherduck.com/docs/intro](https://motherduck.com/docs/intro)_

1. Adjust your `profiles.yml` for the naming conventions that make sense to you. Specifically, focus on schema.

```yaml
Copy code

jaffle_shop:

  target: dev
  outputs:
    dev:
      type: duckdb
      schema: dev_sung
      path: 'md:jaffle_shop'
      threads: 16
      extensions:
        - httpfs
      settings:
        s3_region: "{{ env_var('S3_REGION', 'us-west-1') }}"
        s3_access_key_id: "{{ env_var('S3_ACCESS_KEY_ID') }}"
        s3_secret_access_key: "{{ env_var('S3_SECRET_ACCESS_KEY') }}"

    dev_public_s3:
      type: duckdb
      schema: dev_sung
      path: 'md:jaffle_shop'
      threads: 16
      extensions:
        - httpfs
      settings:
        s3_region: "{{ env_var('S3_REGION', 'us-east-1') }}" # default region to make hello_public_s3.sql work correctly!
        s3_access_key_id: "{{ env_var('S3_ACCESS_KEY_ID') }}"
        s3_secret_access_key: "{{ env_var('S3_SECRET_ACCESS_KEY') }}"

    prod:
      type: duckdb
      schema: prod_sung
      path: 'md:jaffle_shop'
      threads: 16
      extensions:
        - httpfs
      settings:
        s3_region: us-west-1
        s3_access_key_id: "{{ env_var('S3_ACCESS_KEY_ID') }}"
        s3_secret_access_key: "{{ env_var('S3_SECRET_ACCESS_KEY') }}"
```

2. Export your motherduck and S3 credentials to the terminal session, so your dbt project can authenticate to both

```shell
Copy code

# all examples are fake
export motherduck_token=<your motherduck token> # aouiweh98229g193g1rb9u1
export S3_REGION=<your region> # us-west-1
export S3_ACCESS_KEY_ID=<your access key id> # haoiwehfpoiahpwohf
export S3_SECRET_ACCESS_KEY=<your secret access key> # jiaowhefa998333
```

3. Create a python virtual environment and install the packages to run this dbt project

```shell
Copy code

python3 -m venv venv
source venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

4. Run `dbt debug` to verify dbt can connect to motherduck and S3

```shell
Copy code

dbt debug
```

5. Run `dbt build` to run and test the project!

```shell
Copy code

dbt build
```

6. If you're feeling adventurous, run the below to reference a public s3 bucket provided by MotherDuck!

Impacted dbt model

```sql
Copy code

--filename: hello_public_s3.sql
{% if target.name == 'dev_public_s3' %}

SELECT * FROM 's3://us-prd-motherduck-open-datasets/jaffle_shop/csv/raw_customers.csv'

{% else %}

select 1 as id

{% endif %}
```

```shell
Copy code

dbt build --target dev_public_s3
```

7. Now, you should see everything ran with green font everywhere and you should see this in the UI! Including the S3 data you built a dbt model on top of!

![signin](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgreen_logs_ad3ec33dd1.png%3Fupdated_at%3D2023-09-06T12%3A58%3A39.718Z&w=3840&q=75)![signin](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fmotherduck_success_5f718670be.png%3Fupdated_at%3D2023-09-06T12%3A58%3A42.460Z&w=3840&q=75)

That’s it! Ruffle up those feathers and start quacking and slapping those juicy SQL queries together to solve your analytics problems faster and cheaper than ever before!

## Conclusion

We’re at a really cool place where all I had to give you was a couple instructions to get you up and running with MotherDuck. I really hope the data industry gets to a place where we brag about the things we do NOT have to do vs. pride ourselves on complexity for its own sake. What matters is that we solve problems and spend time, money, and energy doing it where it’s actually worth it to solve those problems. I’m excited to see you all build MotherDuck guides far superior to mine. That’s why this is so fun. We get to sharpen each other!

_Want to know more about MotherDuck and dbt ? Checkout [MotherDuck & dbt documentation](https://motherduck.com/docs/integrations/transformation/dbt/) and have a look at their YouTube tutorial about DuckDB & dbt 👇_

Unleashing DuckDB & dbt for local analytics triumphs - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[Unleashing DuckDB & dbt for local analytics triumphs](https://www.youtube.com/watch?v=asxGh2TrNyI)

MotherDuck

Search

Watch later

Share

Copy link

Info

Shopping

Tap to unmute

If playback doesn't begin shortly, try restarting your device.

Full screen is unavailable. [Learn More](https://support.google.com/youtube/answer/6276924)

You're signed out

Videos you watch may be added to the TV's watch history and influence TV recommendations. To avoid this, cancel and sign in to YouTube on your computer.

CancelConfirm

More videos

## More videos

Share

Include playlist

An error occurred while retrieving sharing information. Please try again later.

[Watch on](https://www.youtube.com/watch?v=asxGh2TrNyI&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 8:54

•Live

•

### TABLE OF CONTENTS

[My Personal DuckDB Story](https://motherduck.com/blog/motherduck-duckdb-dbt/#my-personal-duckdb-story)

[Why use MotherDuck + dbt?](https://motherduck.com/blog/motherduck-duckdb-dbt/#why-use-motherduck-dbt)

[Get Started](https://motherduck.com/blog/motherduck-duckdb-dbt/#get-started)

[Configure Your dbt project](https://motherduck.com/blog/motherduck-duckdb-dbt/#configure-your-dbt-project)

[Conclusion](https://motherduck.com/blog/motherduck-duckdb-dbt/#conclusion)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![This Month in the DuckDB Ecosystem: August 2023](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fthumbnail_duckdb_newsletter_1_feb51165aa.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-nine/)

[2023/08/21 - Marcos Ortiz](https://motherduck.com/blog/duckdb-ecosystem-newsletter-nine/)

### [This Month in the DuckDB Ecosystem: August 2023](https://motherduck.com/blog/duckdb-ecosystem-newsletter-nine)

This Month in the DuckDB Ecosystem: August 2023

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response