---
title: announcing-duckdb-snippet-sets-with-motherduck-sharing-databases
content_type: blog
source_url: https://motherduck.com/blog/announcing-duckdb-snippet-sets-with-motherduck-sharing-databases
indexed_at: '2025-11-25T19:57:31.492927'
content_hash: 91d0e93ee1158937
has_code_examples: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Announcing: DuckDB code snippet sets with MotherDuck Sharing

2023/11/28 - 3 min read

BY

[Ryan Boyd](https://motherduck.com/authors/ryan-boyd/)

The [DuckDB Snippets site](https://duckdbsnippets.com/?orderBy=snippet.createdAt%3DDESC) has been a source of inspiration for me as I’ve explored all the powerful analytic capabilities and SQL simplification in DuckDB. The site brings together code snippets from the community for DuckDB in SQL, Python, Bash and R to do things like [Quickly Convert a CSV to Parquet](https://duckdbsnippets.com/snippets/6/quickly-convert-a-csv-to-parquet-bash-function), [Query the Output of Another Process](https://duckdbsnippets.com/snippets/10/query-the-output-of-another-process), [Filter Column Names Using a Pattern](https://duckdbsnippets.com/snippets/20/filter-column-names-using-a-pattern) and [more](https://duckdbsnippets.com/),

Today, we’ve released a couple features that will make the site even more powerful: the ability to bundle multiple themed snippets together, and the ability to include a [MotherDuck Share](https://motherduck.com/docs/key-tasks/managing-shared-motherduck-database/) of public data with your snippet(s).

## Sharing DuckDB Data with MotherDuck

[MotherDuck Shares](https://motherduck.com/docs/key-tasks/managing-shared-motherduck-database/) give you the power to share an updatable snapshot of an entire DuckDB database with other users by providing them with a secret URL. We’ve seen them be used inside companies to give colleagues access to data and publicly like the authors of the [DuckDB in Action book](https://motherduck.com/duckdb-book-brief/) have chosen to do \[see page 26 in the free book\].

Here’s a snippet showing [how to use DuckDB-specific SQL extensions](https://duckdbsnippets.com/snippets/145/duckdb-in-action-some-neat-duckdb-specific-sql-extension) from [Michael Simons](https://twitter.com/rotnroll666), one of the authors of the DuckDB book:

[![screenshot of duckdbsnippets.com code snippet of using DuckDB-specific SQL extensions](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage2_310f0661ee.png&w=3840&q=75)](https://duckdbsnippets.com/snippets/145/duckdb-in-action-some-neat-duckdb-specific-sql-extension)

To see this code snippet quack into action \[ha!\], you can visit [app.motherduck.com](https://app.motherduck.com/) and sign up for a free MotherDuck account. Then you can copy the `ATTACH`, `USE`, and desired `SELECT` statements into your MotherDuck notebook to see the SQL in action. Note that you can also do this all in the DuckDB CLI if you prefer.

We encourage you to check these out, vote on the snippets you find most helpful and submit your own snippets with public data.

## Bundle Multiple Snippets Together

If you’re a current DuckDB Snippets user, you probably already caught that the snippet I shared above bundled multiple code snippets together into a single set. You can now do that whether or not you have a MotherDuck Share link referenced.

Here’s an example from [Simon Aubury](https://twitter.com/SimonAubury), who is also writing an upcoming [DuckDB book](https://www.barnesandnoble.com/w/getting-started-with-duckdb-simon-aubury/1143504699), on how to [load remote parquet files into DuckDB](https://duckdbsnippets.com/snippets/167/loading-remote-parquet-files):

[![screenshot of duckdbsnippets.com code snippets on loading remote parquet files into DuckDB](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage1_fda11804a7.png&w=3840&q=75)](https://duckdbsnippets.com/snippets/167/loading-remote-parquet-files)

You can try out this snippet in [MotherDuck](https://app.motherduck.com/) or in the DuckDB CLI running on your laptop.

Simon also has other great snippets on [Working with public REST APIs using DuckDB](https://duckdbsnippets.com/snippets/169/working-with-public-rest-apis) and [Working with spatial data in DuckDB](https://duckdbsnippets.com/snippets/162/working-with-spatial-data).

## Thanks to the DuckDB Community

Thanks to the community for writing such great code snippets for the [DuckDB Snippets site](https://duckdbsnippets.com/?orderBy=snippet.createdAt%3DDESC) and voting on the snippets you like the most. Special thanks to [Michael Simons](https://duckdbsnippets.com/users/121), [Michael Hunger](https://duckdbsnippets.com/users/129), [Simon Aubury](https://duckdbsnippets.com/users/53) and the MotherDuck DevRel team ( [Mehdi Ouazza](https://duckdbsnippets.com/users/11), [David Neal](https://duckdbsnippets.com/users/181)) for seeding these new-style snippets on the site. Looking forward to seeing what **_you_** submit!

### TABLE OF CONTENTS

[Sharing DuckDB Data with MotherDuck](https://motherduck.com/blog/announcing-duckdb-snippet-sets-with-motherduck-sharing-databases/#sharing-duckdb-data-with-motherduck)

[Bundle Multiple Snippets Together](https://motherduck.com/blog/announcing-duckdb-snippet-sets-with-motherduck-sharing-databases/#bundle-multiple-snippets-together)

[Thanks to the DuckDB Community](https://motherduck.com/blog/announcing-duckdb-snippet-sets-with-motherduck-sharing-databases/#thanks-to-the-duckdb-community)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![This Month in the DuckDB Ecosystem: November 2023](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fthumbnail_duckdb_newsletter_november_40fdfbd23c.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2023/)

[2023/11/22 - Marcos Ortiz](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2023/)

### [This Month in the DuckDB Ecosystem: November 2023](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2023)

DuckDB Monthly November: Featuring David Gasquez, top content, and upcoming events!

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response