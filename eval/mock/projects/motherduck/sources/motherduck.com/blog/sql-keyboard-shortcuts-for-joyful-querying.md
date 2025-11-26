---
title: sql-keyboard-shortcuts-for-joyful-querying
content_type: tutorial
source_url: https://motherduck.com/blog/sql-keyboard-shortcuts-for-joyful-querying
indexed_at: '2025-11-25T19:58:35.578829'
content_hash: 8fefd221dbee92b6
has_code_examples: true
has_step_by_step: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Nine Keyboard Shortcuts for SQL Flow State

2025/08/22 - 7 min read

BY

[Jacob Matson](https://motherduck.com/authors/jacob-matson/)

I'm a reformed Excel power user - and as such, my career started with jokes with my CFO boss about “mousers” followed by diligently learned keyboard shortcuts. This admittedly perverse cultural notion also unlocked something I am still chasing to this day: getting into a flow state, where my fingers flew across the keyboard, shaping numbers with keyboard shortcuts. I wasn't thinking about the software; I was just solving the problem. Pure joy.

When I moved to SQL, I had to start over. As my stack changes so did my IDE. I never spent the time to learn those same shortcuts and the concentration was gone, and so was the joy. The UI felt like a barrier to me, not a help. And that has held true through the years, until now. This core design principle is why I love the MotherDuck UI. It feels like its designed with me in mind. With a powerful set of keyboard shortcuts, I can forget about the software and just focus on the analysis.

![rainman.gif](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Frainman_54405f8dc4.gif&w=3840&q=75)

This post will show you how to get that 'in the zone' feeling back, creating a faster, more fluid, and genuinely more _joyful_ analytics experience. We'll walk through a practical exploratory data analysis (EDA) of the NYC taxi dataset, using only keyboard shortcuts at each stage.

## **Prerequisites**

First, you'll need a MotherDuck account.

Second, let's get the NYC taxi dataset loaded. We'll use the yellow taxi trip data in the `sample_data` database that comes attached by default. You can preview the dataset easily with the query below:

```sql
Copy code

FROM sample_data.nyc.taxi
```

## **The Workflow**

Now, let's dive in and see how we can explore this data without our hands ever leaving the keyboard.

### **Step 1: Find Your Focus**

A clean workspace is key to concentration. Before I even write a line of code, I like to clear away the clutter and create a distraction-free "zen mode" for my analysis. You can instantly hide the side panels to focus on what matters: your query.

- **Shortcut:** Hide the left-hand database browser with `Ctrl + B`.
- **Shortcut:** Hide the right-hand results inspector with `Ctrl + I`.
- **Shortcut**: Lock into worksheet mode with `Ctrl + E`.

With three quick keystrokes, the interface melts away, leaving you with a clean canvas for your analysis.

### **Step 2: Running Your Initial Query**

Let's start by getting a feel for the data. A simple `DESCRIBE` is perfect for understanding the schema and seeing what kinds of values are in each column. Type this into your cell:

```sql
Copy code

DESCRIBE sample_data.nyc.taxi
```

Now for the good stuff: Instead of reaching for the mouse to click "Run," just press `Ctrl + Enter`.

- **Shortcut:** Run the entire query in the cell with `Ctrl + Enter`.

Instantly, your results appear. No clicking, no waiting, just a seamless flow from thought to result.

### **Step 3: Targeted Analysis**

Often, a query has multiple parts, like a Common Table Expression (CTE). During development, you might not want to run the whole thing, but just check the output of one piece.

Let's say you have this query to find the most common trip distances:

```sql
Copy code

WITH trips AS (
  SELECT
    trip_distance
  FROM nyc_taxi
  WHERE trip_distance > 0
)

SELECT
  trip_distance,
  COUNT(*) AS num_trips
FROM trips
GROUP BY ALL
ORDER BY num_trips DESC
```

If you only want to see the output of the trips CTE, just highlight that part of the query with your keyboard and hit `Ctrl + Shift + Enter`.

- **Shortcut:** Run only the selected text with `Ctrl + Shift + Enter`.

This lets you debug and build complex queries piece by piece, giving you an incredible level of control, all from the keyboard. However…

### **Step 4: Explore your CTEs with Instant SQL**

This is my favorite part. Instant SQL is a true game-changer that brings back that "in the zone" feeling. It updates your results _as you type_. No more run-wait-debug cycle.

- **Shortcut:** Toggle Instant SQL mode on with `Ctrl + Shift + .`

Now, as you type and modify your query, you see the results change in real-time. It feels less like writing code and more like sculpting data. It’s a delightful experience that you have to try to believe.

Going back to the CTE from previous step - you can seamless toggle between the CTE node and the final select node, seeing both results render in the pane!

![instant sql.gif](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Finstant_sql_7ee71d5c97.gif&w=3840&q=75)

### **Step 5: Iterate and Experiment with Comments**

Great analysis is iterative. You constantly tweak your query, adding and removing columns or filters. Instead of deleting lines, it's often better to comment them out. Let's start with a query to look at fares and tips.

```sql
Copy code

SELECT
  passenger_count,
  total_amount,
  tip_amount, -- Let's look at this for now
FROM nyc_taxi
ORDER BY total_amount DESC;
```

What if you want to temporarily remove tip\_amount? Just move your cursor to that line and press `Ctrl + /`. DuckDB's tolerance for trailing commas makes this especially great feeling.

- **Shortcut:** Toggle line comments with `Ctrl + /`.

Your query now looks like this, and you can run it to see the change. Hit `Ctrl + /` again to bring the line back. It's a fast, non-destructive way to experiment.

```sql
Copy code

SELECT
  passenger_count,
  total_amount,
  -- tip_amount, -- Let's look at this for now
FROM nyc_taxi
ORDER BY total_amount DESC;
```

### **Step 6: Leverage AI assistance**

Sometimes you know _what_ you want to ask, but not exactly _how_ to write the SQL. Let's say you want to find the average trip distance and fare per passenger count, but only for trips paid by credit card (payment\_type = 1).

Instead of breaking your flow to search documentation, you can summon a helpful assistant directly in the editor. Just press `Ctrl + Shift + E`.

- **Shortcut:** Open the AI query assistant with `Ctrl + Shift + E`.

A small window will pop up. Type your question in plain English: "calculate the average trip distance and fare per passenger count for credit card trips". The assistant will generate the SQL for you, keeping you right in the editor and focused on the problem.

![cmdk.gif](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fcmdk_f6c7670e8d.gif&w=3840&q=75)

### **Step 7: Automated SQL Formatting**

After all that exploration, your query might be a little messy. For sharing, saving, or just for your own sanity, clean SQL is crucial. There's a deep satisfaction in tidying up your work with a single command.

- **Shortcut:** Automatically format the entire cell with `Ctrl + Alt + O`.

One keystroke, and your query is instantly transformed into a perfectly formatted, readable piece of code. It's the perfect finishing touch.

## **Your Keyboard Shortcut Cheat Sheet**

Here’s a quick reference of all the shortcuts we used to keep you in the flow. You can also check out the [docs for a complete list](https://motherduck.com/docs/getting-started/interfaces/motherduck-quick-tour/#keyboard-shortcuts)!

| Shortcut | Description |
| :-- | :-- |
| `Ctrl` \+ `B` | Toggle the left-hand browser panel. |
| `Ctrl` \+ `I` | Toggle the right-hand inspector panel. |
| `Ctrl` \+ `Enter` | Run the current cell. |
| `Ctrl` \+ `Shift` \+ `Enter` | Run the selected text. |
| `Ctrl` \+ `/` | Toggle line comments. |
| `Ctrl` \+ `K` | Open the Command View. |
| `Ctrl` \+ `Shift` \+ `E` | Open the AI Edit mode. |
| `Ctrl` \+ `Shift` \+ `.` | Toggle Instant SQL mode. |
| `Ctrl` \+ `E` | Toggle Worksheet View. |
| `Ctrl` \+ `Alt` \+ `O` | Format the current cell. |

## **Conclusion**

Keyboard shortcuts are about more than just speed, they're about maintaining an uninterrupted analytical flow that feels good to use. When you don't have to think about the UI, you can think more deeply about the data.

Mastering these shortcuts transforms the user experience from a series of clicks and into a conversation with your data. It brings a sense of craftsmanship back to the process of writing SQL, letting you get in the zone and focus on what truly matters: solving the problem at hand.

**What's your go-to shortcut that we missed?** Let us know! We invite you to join the [MotherDuck community Slack](https://slack.motherduck.com/) to share more tips.

### TABLE OF CONTENTS

[Prerequisites](https://motherduck.com/blog/sql-keyboard-shortcuts-for-joyful-querying/#prerequisites)

[The Workflow](https://motherduck.com/blog/sql-keyboard-shortcuts-for-joyful-querying/#the-workflow)

[Your Keyboard Shortcut Cheat Sheet](https://motherduck.com/blog/sql-keyboard-shortcuts-for-joyful-querying/#your-keyboard-shortcut-cheat-sheet)

[Conclusion](https://motherduck.com/blog/sql-keyboard-shortcuts-for-joyful-querying/#conclusion)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![4 Senior Data Engineers Answer 10 Top Reddit Questions](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Foct_25_simon_blog_455f822c25.png&w=3840&q=75)](https://motherduck.com/blog/data-engineers-answer-10-top-reddit-questions/)

[2025/10/30 - Simon Späti](https://motherduck.com/blog/data-engineers-answer-10-top-reddit-questions/)

### [4 Senior Data Engineers Answer 10 Top Reddit Questions](https://motherduck.com/blog/data-engineers-answer-10-top-reddit-questions)

A great panel answering the most voted/commented data questions on Reddit

[![DuckDB Ecosystem: November 2025](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FThree_items_Duck_DB_Ecosystem_36d7966f34.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2025/)

[2025/11/12 - Simon Späti](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2025/)

### [DuckDB Ecosystem: November 2025](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2025)

DuckDB Monthly #35: DuckDB extensions, DuckLake, DataFrame, and more!

[View all](https://motherduck.com/blog/)

Authorization Response