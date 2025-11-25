---
title: analyze-x-data-nodejs-duckdb
content_type: tutorial
source_url: https://motherduck.com/blog/analyze-x-data-nodejs-duckdb
indexed_at: '2025-11-25T19:58:40.178288'
content_hash: debafc7110f7970f
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Analyze Your X (Twitter) Data with Node.js and DuckDB

2023/11/08 - 7 min read

BY
David Neal

Would you like to know which of your X (the artist formerly known as Twitter) posts received the most favorites or reposts? How many times have you replied? In which months were you the most active? What were the first ten posts you wrote? In this tutorial, we will answer all these questions and give you the tools to discover even more!

Not very long ago, X started offering a way for its users to [download an archive](https://help.twitter.com/en/managing-your-account/accessing-your-x-data) of their data. When you request and receive your X data archive, you get a static web app. It lets you browse and search your tweets and gives you some basic stats. Your archive not only has tweets and associated media but also includes followers, direct messages, likes, ad impressions and engagements, personalization data, and much more.

Unfortunately, the static web app only gives you a few options to view and discover your data. You're on your own to dive deeper. And, while the archive includes a "readme" document that describes the data, the data itself is not in a format you can easily query and analyze. Node.js and DuckDB to the rescue!

## Node.js and DuckDB analytics project overview

Before you dive into the steps, it’s helpful to understand how and why these technologies work well together. Node.js is a minimal software development framework based on the JavaScript language. Since the X archive data is in the form of JavaScript code, Node.js is a good choice for converting the JavaScript code into a data format that is easier to consume and query. You will use the Node.js application to convert your X posts into a comma-separated values (CSV) data file. You will also learn how Node.js can be used to automate DuckDB to execute queries from JavaScript code.

DuckDB is a lightweight data analysis application that supports the structured query language (SQL) and can natively query common data formats such as CSV. You will learn to use the DuckDB command-line interface (CLI) to further analyze your X posts with SQL without writing any JavaScript code.

**I heard DuckDB can read JSON files. Why do I need Node.js?**

Yes, DuckDB can read JSON files! The problem is the X archive data files are not in JSON format. They are JavaScript code files with JSON inside designed to run in the front-end app. Code is needed to convert the JavaScript files to JSON. The script in this project _could_ have stopped with creating a JSON file. However, it was helpful to transform the data from the original JSON to CSV to create a structure that was more comfortable to query.

## Requirements and setup

- [Download your X data archive](https://help.twitter.com/en/managing-your-account/accessing-your-x-data). Your request may take 24 hours or more to process.
- Install [Node.js version 18 or higher](https://nodejs.org/).
- Install [DuckDB](https://duckdb.org/).

> Note: You can use DuckDB in a Node.js application with the [duckdb-async](https://www.npmjs.com/package/duckdb-async) library without having to install the DuckDB app. However, you may want the standalone app to run your queries against the converted data.

- [Clone](https://github.com/reverentgeek/analyze-x-nodejs-duckdb) the `analyze-x-nodejs-duckdb` project. If you're not familiar with using `git`, you can also [download](https://github.com/reverentgeek/analyze-x-nodejs-duckdb/archive/refs/heads/main.zip) and unzip the project.
- Open the project in your terminal or command prompt and run `npm install` to install dependencies.
- Extract (unzip) your X archive and copy or move the files into your project folder named `x-archive`. The `x-archive` folder should now look like the following.

```sh
Copy code

|__ x-archive
    |__ assets
    |__ data
    |__ readme.md
    |__ Your archive.html
```

## Launch the conversion application

From your terminal or command window, make sure your current directory is the project folder. Run the following command:

```sh
Copy code

node .
```

If everything is set up correctly, your tweets archive will be converted to a CSV file, and you'll see the output of several queries. Scroll up to see the see the results!

## Further analysis using DuckDB

Now that all of your posts have been converted to a CSV file, you can use DuckDB to query that data directly. With the power of SQL, you can answer all kinds of questions!

From the same terminal or command prompt, start the DuckDB application with the following command.

```sh
Copy code

duckdb
```

Your cursor should be before a `D` prompt, waiting for a command or SQL statement. To see the first ten posts you created, enter the following query.

```sql
Copy code

SELECT created_at_date, link, full_text
FROM "./src/data/tweets.csv"
ORDER BY created_at_date, created_at_time
LIMIT 10;
```

> Note: When typing in a SQL query, press the _return_ or _enter_ key to move to a new line. The query will not execute until you type the ending semicolon \`;\` and press _return_ or _enter_.

The sky is the limit! Here are all the columns in the CSV file you can use as part of your queries.

| Column Name | Description |
| --- | --- |
| id | The post ID assigned by X |
| favorite\_count | The number of favorites on the post |
| retweet\_count | The number of times the post was reposted |
| created\_at\_date | The post creation date, formatted as \`yyyy-mm-dd\` |
| created\_at\_time | The post creation time, formatted as \`HH:mm:ss\` (0-23 hour format) |
| is\_reply | Is this post a reply, \`0\` for false, \`1\` for true |
| in\_reply\_to\_user\_id | If the post is a reply, this is the user ID of the account being replied to |
| is\_self\_reply | If the post is a reply to self (part of a thread), \`0\` or \`1\` |
| retweet | If the post is a retweet, \`0\` for false, \`1\` for true |
| has\_media | If the post contains media, such as an image, \`0\` for false, \`1\` for true |
| hashtags | The number of hashtags in the post |
| user\_mentions | The number of user mentions in the post |
| urls | The number of URLs in the post |
| source | The name of the app used to create the post |
| link | The post URL |
| full\_text | The text of the post |

> Note: When you want to exit from DuckDB back to the console, type `.exit` and press _return_, or press CTRL+C twice.

## An overview of the Node.js code

Node.js is a powerful software development environment that uses JavaScript for building all kinds of applications, from scripts like what you see in this project to full-blown web applications, mobile apps, desktop apps, and much more. This project uses the `duckdb-async` library to execute DuckDB queries directly. Here is an example of the source code found in the `duckdb.js` file in this project.

```js
Copy code

import duckdb from "duckdb-async";

export async function analyzePosts( csvFilePath ) {
  try {
    // Create an instance of DuckDB using in-memory storage
    const db = await duckdb.Database.create( ":memory:" );

    await topRetweets( db, csvFilePath );
    await topFavorites( db, csvFilePath );
    await postStats( db, csvFilePath );

  } catch ( err ) {
    console.log( "Uh oh! There's an error!" );
    console.log( err );
  }
}

async function topRetweets( db, csvFilePath ) {
  const topRetweets = await db.all( `
  SELECT full_text,
    created_at_date + created_at_time AS created_at,
    retweet_count,
    link
  FROM read_csv_auto( '${ csvFilePath }' )
  ORDER BY retweet_count DESC
  LIMIT 3;` );

  console.log( "\nTop Retweets!\n" );
  console.log( topRetweets );
}
```

The first line imports the `duckdb-async` library. The `analyzePosts` takes a single argument, the path to the CSV file to query. The function creates an instance of DuckDB, which it uses to call functions to perform various queries. The `topRetweets` function is shown next as an example of how to execute a DuckDB query from Node.js.

> TIP: If you don't have a good code editor, download and install [Visual Studio Code](https://code.visualstudio.com/Download). Use it to explore the source code and the data in your X archive!

## Next steps with Node.js and DuckDB

Now that you've tasted what's possible with Node.js and DuckDB, there's more data to analyze! As mentioned, the archive includes direct messages, followers, and interesting data like personalization and ads. Modify the code to build something that answers whatever questions you have!

Happy coding and querying with Node.js and DuckDB!

### TABLE OF CONTENTS

[Node.js and DuckDB analytics project overview](https://motherduck.com/blog/analyze-x-data-nodejs-duckdb/#nodejs-and-duckdb-analytics-project-overview)

[Requirements and setup](https://motherduck.com/blog/analyze-x-data-nodejs-duckdb/#requirements-and-setup)

[Launch the conversion application](https://motherduck.com/blog/analyze-x-data-nodejs-duckdb/#launch-the-conversion-application)

[Further analysis using DuckDB](https://motherduck.com/blog/analyze-x-data-nodejs-duckdb/#further-analysis-using-duckdb)

[An overview of the Node.js code](https://motherduck.com/blog/analyze-x-data-nodejs-duckdb/#an-overview-of-the-nodejs-code)

[Next steps with Node.js and DuckDB](https://motherduck.com/blog/analyze-x-data-nodejs-duckdb/#next-steps-with-nodejs-and-duckdb)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Making PySpark Code Faster with DuckDB](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fthumbnail_2_pyspark_67e53443d8.png&w=3840&q=75)](https://motherduck.com/blog/making-pyspark-code-faster-with-duckdb/)

[2023/11/02 - Mehdi Ouazza](https://motherduck.com/blog/making-pyspark-code-faster-with-duckdb/)

### [Making PySpark Code Faster with DuckDB](https://motherduck.com/blog/making-pyspark-code-faster-with-duckdb)

Making PySpark Code Faster with DuckDB

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response