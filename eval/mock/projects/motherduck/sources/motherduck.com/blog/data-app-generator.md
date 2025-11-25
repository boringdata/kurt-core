---
title: data-app-generator
content_type: blog
source_url: https://motherduck.com/blog/data-app-generator
indexed_at: '2025-11-25T19:57:22.358527'
content_hash: 322a3c5165968989
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Generating a data app with your MotherDuck data

2024/09/06 - 9 min read

BY

[Till Döhmen](https://motherduck.com/authors/till-d%C3%B6hmen/)

## Introduction

In this blog post, we'll share the journey of our experimentation with [Claude Artifacts](https://support.anthropic.com/en/articles/9487310-what-are-artifacts-and-how-do-i-use-them) and how it led to the creation of the MotherDuck data app Generator ( [GitHub](https://github.com/motherduckdb/wasm-client/tree/main/data-app-generator)). This tool might just be the easiest way for you to get started with building MotherDuck data apps (definition below).

AI coding assistants like Claude Artifacts, [LlamaCoder](https://llamacoder.together.ai/), [GPT Engineer](https://gptengineer.app/), and [v0.dev](https://v0.dev/) can build web applications using only natural language instructions. But creating data applications remains challenging for current coding assistants. They often lack an analytical database component to efficiently process data and are missing context about your specific database schema.

Inspired by this challenge, we developed an experimental AI tool that generates MotherDuck data apps in seconds based on your instructions and your specific database schema, all running in JS in the browser. It worked so well that we're excited to share it with you.

## What is a Data App?

A data app is an interactive web application designed to offer insights or automate actions using data, including examples like data visualizations and custom reporting tools for business groups. These apps integrate data processing, storage, and visualization technologies to provide real-time analytics embedded into the software that teams and customers already use. Motherduck data apps are special because they utilize a novel 1.5-tier architecture, combining client-side processing with cloud storage to deliver efficient, low-latency data analytics.
![dataapps](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage2_69fdc4da03.png&w=3840&q=75)[Learn more about Data Apps](https://motherduck.com/docs/key-tasks/data-apps/)

## Testing Claude Artifacts

We started the journey by trying out Claude Artifacts, an AI tool that can generate code and is specifically well suited for generating web applications. Here's what happened when we tested it:

We started by generating a simple calculator, which Claude handled routinely.

![claude](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage9_d00a6f4f05.png&w=3840&q=75)

Next, we tried to get it to use [MotherDuck's WebAssembly (WASM) npm package](https://www.npmjs.com/package/@motherduck/wasm-client), which is an SDK that allows you to run DuckDB with MotherDuck in the browser. We started with a simple instruction, that just asked the AI to create an app that connects to MotherDuck and shows a list of all databases. This is where we ran into some problems:

1. We found out that Claude doesn't know about how to use the MotherDuck WASM SDK, so we had to give it information about that.
2. Claude couldn't actually preview the app, because it didn’t have the wasm-client dependency pre-installed.

![unsup](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage3_66e7c4a3ff.png&w=3840&q=75)
3. We also realized that, even if this worked, it would be difficult for Claude to generate correct SQL queries because it wouldn’t have any context about the user’s database schemas. And it would be cumbersome for users to provide the schema in the prompt.

This motivated us to experiment with developing our own MotherDuck data app generator.

## How the Data App Generator Works

Using what we learned from our tests, we created the MotherDuck Data App Generator. Here's how we put it together.

#### System Prompt

In our system prompt we instruct the model to only generate one self-contained component and wrap it into `<component>` tags to make it easier to extract from the output. We furthermore provide instructions that are teaching the model how to write MotherDuck Data Apps. This includes providing context on which React components to use, how to connect to MotherDuck and run queries, and how to leverage DuckDB's and MotherDuck's extensive SQL features (for example how to read files directly from S3 or Hugging Face, and how to use MotherDuck’s prompt function to generate summaries of text, etc.).

#### Scaffolding

We want the model to focus on generating the component, without getting distracted by the project setup. Hence, we provide a pre-existing React project scaffolding into which the generated component can be seamlessly integrated.

#### App Generator Overview\*\*

The generator interface itself is a simple [Streamlit](https://streamlit.io/) app. The reason we use Streamlit is that it makes it super easy to set up a [chat interface](https://docs.streamlit.io/develop/api-reference/chat), allowing for a more user-friendly experience when interacting with the generator. Funnily enough, the first prototype of Claude Artifacts was also a Streamlit app (Read more about the backstory [here](https://newsletter.pragmaticengineer.com/p/how-anthropic-built-artifacts)). The drawing below provides a high-level overview of the app generator components.

![overview](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage4_6e38ad7db8.png&w=3840&q=75)

Detailed overview:

- **Database Connection**: Connect to MotherDuck and fetch databases. Users can select the database they want to develop an app on from a dropdown menu. This automatically fetches schemas from the database and adds them to the context of the chat session.
- **Chat Interface**: Users can type in instructions such as "Show the users over time in a bar chart" or follow-up questions like "Make the bars blue" or "Add a dropdown menu where I can select the region of users". The app displays "Generating app" or "Updating app" and shows a summary of the changes to the user once completed. There is both an internal and user-facing chat session; we only surface high-level summaries to the user, while the internal session contains the conversation history, including the generated code.
- **Code Generation**: Our system prompt instructs the LLM to generate code within `<component>` tags. We extract this code from responses and write it into the "MyApp.jsx" component in our app scaffolding.
- **Model Integration**: We integrate the app with OpenRouter.ai and use the anthropic/Claude-3.5-Sonnet model as the default model.
- **App Preview**: We start an npm dev server in the background and provide an "Open App" button to the user, which opens the generated app in a new tab. The app remains open and automatically updates to reflect changes to the component.
- **User Guide**: Through experimentation, we identified useful usage patterns and troubleshooting advice, which we included in a side panel of the UI.
- **Cursor Integration**: [Cursor](https://www.cursor.com/) is an AI-centered development environment that has gained [popularity](https://x.com/karpathy/status/1827143768459637073) lately. As it is sometimes easier to work with the code directly, we automatically generate a .cursorrules file containing schema information from the connected database and general instructions for building MotherDuck data apps. This makes it possible to switch to Cursor and continue AI-assisted app development there.

## An Example: Building a Simple Data App

To show how our Data App Generator works in practice, let's walk through creating a simple app that shows basic summary stats of our hacker news [sample dataset](https://motherduck.com/docs/category/example-datasets/).

We started by asking the AI to "Make a simple dashboard that shows the number of hacker news posts between January 2022 and December 2022." It creates a basic bar chart with this information. Then we ask to add another plot showing the distribution of posts across the top 10 domains in the selected month. It then adds a second plot and generates a SQL query to fetch the information from the database, whenever the user selects a specific month.

The video below shows the development process and the resulting app:

![gifdemo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage1_ac0b85ff53.gif&w=3840&q=75)

This wasn't the only thing we tried. Below are some more examples of apps we created while testing the tool.

Prompt: “Create a dashboard for hacker news posts”

![hackernews](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage10_7d16d1560e.png&w=3840&q=75)
Prompt: “Create a dashboard for air quality across different times and regions”

![airregion](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage6_5b4f841aa3.png&w=3840&q=75)

It is not unusual to encounter errors in the generated code or issues in the user interface. However, after we highlight the problem, the generator generally proceeds into the right direction. We included some best practices and troubleshooting tips below and in an information panel within the Data App Generator.

**To build apps effectively**

1. Start with a basic version of your app.
2. Build iteratively by adding new features one at a time.
3. Be specific in your requests for each iteration.
4. Review and test each change before moving to the next.
5. If something isn't working as expected, provide the error messages to the agent for troubleshooting.
6. Complex apps are built step by step. Take your time and enjoy the process!

**Troubleshooting**

1. Check for errors in the UI and the Browser console.
2. Check the browser console (F12 > Console) for JavaScript errors.
3. If you encounter UI issues, describe them to the agent. \|

Below is an example of a task where we had to provide some follow-up instructions to achieve our desired outcome.

Prompt: “Show a timeline of DuckDB versions over time, using the DuckDB version csv at [https://duckdb.org/data/duckdb-releases.csv](https://duckdb.org/data/duckdb-releases.csv). Columns are: release\_date, version\_number, codename, duck\_species\_primary, duck\_species\_secondary, duck\_wikipage, blog\_post. Make the dots darkgreen and show an infobox at the bottom when I select a dot which contains the link to the wikipedia article and some additional information”

![pointflat](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage5_7888869800.png&w=3840&q=75)
Follow-up Prompt: “All dots are in the same line. Scale the y-axis properly.”

![pointflat2](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage7_8e369aa801.png&w=3840&q=75)

Follow-up Prompt: “Make the y-axis categorical and make the plot more in the style of a timeline”

![pointflat3](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage8_598aef61ea.png&w=3840&q=75)

The shown examples:

- Took less than 2 minutes to create
- Costed less than twenty cents in OpenRouter API credits!

## Current limitations

As it’s an early project, we believe the code should not be used in production without an additional review to ensure its reliability and security. Although the code is written in JavaScript because the model is better at writing JavaScript than TypeScript, we recommend using TypeScript for production applications to benefit from its type-checking capabilities.

Additionally, the code employs JavaScript string-templated queries, which can pose security risks; we advise using prepared statements instead. For detailed information on prepared statements, you can refer to [our docs](https://motherduck.com/docs/key-tasks/data-apps/wasm-client/#prepared-statements). If you are looking to implement an authentication flow, a starting point can be found in [this example](https://github.com/motherduckdb/wasm-client/blob/main/examples/nypd-complaints/src/ConnectPane.tsx).

## Wrapping Up

Creating the MotherDuck Data App Generator has been an interesting journey. We started with an idea about using AI to help build data apps, and through testing and problem-solving, we ended up with a tool that can create useful apps quickly and easily.

In the world of data and app development, tools like this are making it easier than ever to turn data into something useful. We're excited to see what people will create! We encourage you to try out the MotherDuck Data App Generator yourself. See what kind of apps you can create with it, and let us know how it goes. Your experiences and feedback will help us make the tool even better.

You can find the full source code and documentation of our Data App Generator on [GitHub](https://github.com/motherduckdb/wasm-client/tree/main/data-app-generator)

Additionally, we recognize that there are existing limitations and that working with a local tool can be challenging for end users. We are excited about the idea of a cloud-based version of the Data App Generator. So, Stay tuned for updates!

Happy coding!

### TABLE OF CONTENTS

[Introduction](https://motherduck.com/blog/data-app-generator/#introduction)

[What is a Data App?](https://motherduck.com/blog/data-app-generator/#what-is-a-data-app)

[Testing Claude Artifacts](https://motherduck.com/blog/data-app-generator/#testing-claude-artifacts)

[How the Data App Generator Works](https://motherduck.com/blog/data-app-generator/#how-the-data-app-generator-works)

[An Example: Building a Simple Data App](https://motherduck.com/blog/data-app-generator/#an-example-building-a-simple-data-app)

[Current limitations](https://motherduck.com/blog/data-app-generator/#current-limitations)

[Wrapping Up](https://motherduck.com/blog/data-app-generator/#wrapping-up)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Swimming in Google Sheets with MotherDuck](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2024_09_03_at_10_13_04_PM_9b7eafd794.png&w=3840&q=75)](https://motherduck.com/blog/google-sheets-motherduck/)

[2024/09/04 - Jacob Matson](https://motherduck.com/blog/google-sheets-motherduck/)

### [Swimming in Google Sheets with MotherDuck](https://motherduck.com/blog/google-sheets-motherduck)

Learn how to use DuckDB's read\_csv functionality to easily load data from Google Sheets into MotherDuck for Analysis!

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response