---
title: motherduck-ai-sql-fixit-inline-editing-features
content_type: blog
source_url: https://motherduck.com/blog/motherduck-ai-sql-fixit-inline-editing-features
indexed_at: '2025-11-25T19:57:05.212000'
content_hash: c77c17e270567559
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# MotherDuck's Latest AI Features: Smarter SQL Error Fixes and Natural Language Editing

2025/07/25 - 6 min read

BY

[Hamilton Ulmer](https://motherduck.com/authors/hamilton-ulmer/)
,
[Jacob Matson](https://motherduck.com/authors/jacob-matson/)

Modern AI tools have fundamentally altered the craft of software engineering. Those of us who use coding agents feel like we're rafting down a raging river; constantly changing, moving relentlessly fast, absolutely thrilling, sometimes reckless, clutching our life vests. We all know this moment on the exponential productivity curve will probably look flat in hindsight. Such is life in this moment in technology.

SQL seems to be resisting this trend. Since the tooling around SQL lags tragically behind all other programming languages, humans _must_ be at the center of the process. Good luck vibecoding a business-critical query! That's why we believe SQL development needs immediate, visible feedback, making every change instantly apparent like [playing an instrument](https://www.youtube.com/watch?v=GSeBSoxAWFg). We're focused on making [SQL more observable for humans and AI](https://motherduck.com/blog/introducing-instant-sql/), but whether it's with parser tools or LLMs, our goal remains singular: how can we help you to move faster with confidence and joy?

The latest MotherDuck release updates our AI tooling around FixIt, our SQL error assistant, and introduces inline edits, a familiar `Cmd + K`-style query editing tool that efficiently exploits your catalog. We've been enjoying playing with these over the last few months, and are excited to see how you use them.

## Stay in flow with Improved FixIt

[FixIt](https://motherduck.com/docs/getting-started/interfaces/motherduck-quick-tour/#writing-sql-with-confidence-using-fixit-and-edit) is one of our most popular UI features. The premise is simple: when you hit a SQL error, FixIt suggests quick fixes to keep you in flow rather than forcing you to break your concentration to figure out how to do the fix yourself.

While FixIt excels at simple fixes, more complex scenarios can disrupt your flow. Long queries, complicated changes, or times when you need uninterrupted focus can make the current implementation feel intrusive. Today's enhanced version addresses these pain points.

![Screenshot 2025-07-25 at 10.48.18 AM.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2025_07_25_at_10_48_18_AM_8974f5d15a.png&w=3840&q=75)

In order to make this work nicely in the UI, we had to change a few things.

First, we redesigned the UI around FixIt. Rather than embedding the controls next to the Fix line, we stick it to the bottom of the editor pane. This makes it much easier to work with very long queries and will support multi-line fixes in the future.

Second, new key bindings. We got feedback from users that they'd love to be able to accept or reject fixes with key binding so that their hands can stay on the keyboard. Simply press `Cmd/Ctrl + Enter` to accept the change and run the query, or `Shift + Cmd/Ctrl + Enter` to reject it.

Third, the ability to toggle FixIt on and off from within the editor. When FixIt works, it works incredibly well. But when you don't want it on, you previously would have to go to the Settings panel and then go to Preferences and then toggle off FixIt. This made it really cumbersome to turn it off when you just needed to be in your own flow state, and it also made it really easy to forget about it when you might have actually wanted it later. So now it's dead simple to turn FixIt on and off from within the same flow. When FixIt is off, you have the option to manually run it for a given error.

## Inline Edits: Natural Language to SQL

We've also rolled out a new inline editing feature. If you use popular AI IDEs such as Cursor, you're probably familiar with the `Cmd + K` feature. The idea is that wherever your cursor is or whatever you've selected, you can pop up a tiny prompt window, ask it to change something in natural language, then see the suggestion.

We've been using our new inline edit feature internally, and we all love it. While FixIt helps you fix errors, inline edits help you write correct SQL from the start. Sometimes you know what you want, but you don't know how to express it in SQL. Inline edits makes it really simple to just say what you want and then get to something that actually will run.

Your browser does not support the video tag.

If you use inline edits on an empty cell, we will pass the prompt to our server and use it to filter out the columns, tables, and schemas of the currently selected database. So you can use natural language to write your initial query and get most of the table and column references right on first pass. It's a really great way to jump-start a query.

Inline edits work great when you're just trying to work on a query, but it works even better when you're running it with instant SQL. As the AI suggests SQL changes, Instant SQL updates your results in real-time, making it easy to verify that the suggestions are correct.

## Getting Started with the New Features

Both of these features are live now in the MotherDuck UI, available for you to use.

**FixIt** runs automatically on your behalf when a SQL query returns an error.

Your browser does not support the video tag.

As a user, you can accept or reject the changes, or disable FixIt for your user. Accepting the changes runs the query immediately. Rejecting them removes the change, or if its not helpful for the query you are debugging, you can disable it entirely.

For **inline edits**, you can activate the feature with `Cmd/Ctrl + K`. There are two modes for using this: an empty page, where you can write a sql query from scratch, or to modify an existing query - the highlighted text will be passed into the prompt as further context. This feature is designed to help you stay in flow while working on solving problems with SQL, and highlights our commitment to delightful SQL workflows.

To really cook with this feature, its best to enable [Instant SQL](https://motherduck.com/blog/introducing-instant-sql/) first, by clicking the icon or by pressing `Shift + Cmd/Ctrl + .` Once it is enabled, the SQL queries from inline edits will render against a sample of the data, allowing you to troubleshoot and identify correctness with lightning speed.

Your browser does not support the video tag.

We hope you find these new features are both a joy to use and incredibly functional. Now get quacking!

P.S. Ready to truly play SQL like an instrument? Explore all our [keyboard shortcuts](https://motherduck.com/docs/getting-started/interfaces/motherduck-quick-tour/#keyboard-shortcuts) to unlock the full potential of the MotherDuck experience.

### TABLE OF CONTENTS

[Stay in flow with Improved FixIt](https://motherduck.com/blog/motherduck-ai-sql-fixit-inline-editing-features/#stay-in-flow-with-improved-fixit)

[Inline Edits: Natural Language to SQL](https://motherduck.com/blog/motherduck-ai-sql-fixit-inline-editing-features/#inline-edits-natural-language-to-sql)

[Getting Started with the New Features](https://motherduck.com/blog/motherduck-ai-sql-fixit-inline-editing-features/#getting-started-with-the-new-features)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Small Data SF Returns November 4-5, 2025: First Speakers Announced](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fsmall_data_sf_2025_961a26b2f1.png&w=3840&q=75)](https://motherduck.com/blog/announcing-small-data-sf-2025/)

[2025/07/17 - Ryan Boyd](https://motherduck.com/blog/announcing-small-data-sf-2025/)

### [Small Data SF Returns November 4-5, 2025: First Speakers Announced](https://motherduck.com/blog/announcing-small-data-sf-2025)

Conference with two days of practical innovation on data and AI: workshops and talks from industry leaders, including Benn Stancil, Joe Reis, Adi Polak, George Fraser, Jordan Tigani, Holden Karau, Ravin Kumar, Sam Alexander and more!

[![Introducing Mega and Giga Ducklings: Scaling Up, Way Up](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckling_sizes_social_cards_3c29d6c212.png&w=3840&q=75)](https://motherduck.com/blog/announcing-mega-giga-instance-sizes-huge-scale/)

[2025/07/17 - Ryan Boyd](https://motherduck.com/blog/announcing-mega-giga-instance-sizes-huge-scale/)

### [Introducing Mega and Giga Ducklings: Scaling Up, Way Up](https://motherduck.com/blog/announcing-mega-giga-instance-sizes-huge-scale)

New MotherDuck instance sizes allow data warehousing users more flexibility for complex queries and transformations. Need more compute to scale up? Megas and Gigas will help!

[View all](https://motherduck.com/blog/)

Authorization Response