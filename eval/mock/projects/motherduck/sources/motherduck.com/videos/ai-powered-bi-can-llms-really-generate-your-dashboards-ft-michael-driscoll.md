---
title: ai-powered-bi-can-llms-really-generate-your-dashboards-ft-michael-driscoll
content_type: event
source_url: https://motherduck.com/videos/ai-powered-bi-can-llms-really-generate-your-dashboards-ft-michael-driscoll
indexed_at: '2025-11-25T20:44:51.941142'
content_hash: 8c893c6f532741fa
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[BACK TO VIDEOS](https://motherduck.com/videos/)

AI Powered BI: Can LLMs REALLY Generate Your Dashboards? ft. Michael Driscoll - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[AI Powered BI: Can LLMs REALLY Generate Your Dashboards? ft. Michael Driscoll](https://www.youtube.com/watch?v=m0LKRX20PJ8)

MotherDuck

Search

Watch later

Share

Copy link

Info

Shopping

Tap to unmute

If playback doesn't begin shortly, try restarting your device.

More videos

## More videos

You're signed out

Videos you watch may be added to the TV's watch history and influence TV recommendations. To avoid this, cancel and sign in to YouTube on your computer.

CancelConfirm

Share

Include playlist

An error occurred while retrieving sharing information. Please try again later.

[Why am I seeing this?](https://support.google.com/youtube/answer/9004474?hl=en)

[Watch on](https://www.youtube.com/watch?v=m0LKRX20PJ8&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 59:47

•Live

•

YouTubeAI, ML and LLMsBI & Visualization

# AI Powered BI: Can LLMs REALLY Generate Your Dashboards? ft. Michael Driscoll

2025/05/20

## The Evolution of Business Intelligence: From Clicks to Code

Business Intelligence is experiencing a fundamental shift from traditional drag-and-drop interfaces to code-based approaches, accelerated by the rise of large language models (LLMs). This transformation promises to make data analytics more accessible while maintaining the precision and version control benefits that come with code-based solutions.

## Understanding BI as Code

BI as code follows the same principles that revolutionized infrastructure management with infrastructure as code. Instead of configuring dashboards through complex user interfaces, the entire BI stack—data sources, models, semantic layers, and dashboards—exists as declarative code artifacts in a GitHub repository.

This approach offers several advantages:

- **Version control**: Every change is tracked and reversible
- **Collaboration**: Teams can review and contribute through standard development workflows
- **Expressiveness**: Code provides far more flexibility than any UI could offer
- **AI compatibility**: LLMs excel at generating and modifying code

## The Role of LLMs in Modern BI Workflows

Large language models are particularly well-suited for BI as code frameworks. Unlike low-code or no-code interfaces that were trending a few years ago, English has become the universal interface. LLMs can take natural language prompts and generate the necessary code to build metrics, dashboards, and analyses.

### Schema-First AI Generation

One of the most powerful approaches involves sending only the schema of a dataset to an LLM, rather than the entire dataset. This method:

- Preserves data privacy and security
- Reduces processing time significantly
- Still provides enough context for intelligent metric generation
- Allows the LLM to infer meaningful metrics based on column names and data types

## English vs SQL: Finding the Right Balance

The debate between using natural language versus SQL for analytics reveals interesting nuances:

### When English Works Better

- Simple data transformations
- Date truncations and timezone conversions
- Basic aggregations
- Initial exploration of datasets

### When SQL Excels

- Complex window functions
- Precise time-based calculations
- Multi-step algorithms
- Production-grade queries requiring exact specifications

### The Time Complexity Challenge

A compelling example involves specifying time ranges. Asking for "revenue over the last three days" in English seems straightforward, but raises multiple questions:

- Should it include today's partial data?
- Should it truncate to complete hours?
- When comparing periods, should partial days be handled consistently?

These nuances demonstrate why code-based approaches maintain their value even as natural language interfaces improve.

## Local Development with DuckDB

DuckDB has emerged as a powerful engine for local BI development. By embedding DuckDB directly into BI tools, developers can:

- Work with multi-million row datasets on their local machines
- Get instant feedback on metric changes
- Avoid cloud processing costs during development
- Maintain complete data privacy

The combination of DuckDB's performance and BI as code principles creates a development experience similar to modern web development—write code, see immediate results, iterate quickly.

## MCP Servers: Bridging AI and Data

Model Context Protocol (MCP) servers represent a new paradigm for AI-data interactions. Instead of developing separate integrations for each service, MCP provides a common interface that allows AI assistants to:

- Query databases directly
- Access real-time data
- Generate insights without manual data export
- Maintain context across multiple queries

### Local MCP Implementation

Running MCP servers locally with tools like DuckDB offers unique advantages:

- Complete data privacy—no data leaves your machine
- Instant query execution
- Direct access to local datasets
- No cloud infrastructure required

## Practical Implementation: From Data to Dashboard

The modern BI workflow demonstrates impressive efficiency:

1. **Data Import**: Connect to data sources (S3, local files, databases)
2. **AI-Generated Metrics**: LLMs analyze schemas and suggest relevant metrics
3. **Code Generation**: Create YAML configurations for metrics and dashboards
4. **Instant Preview**: See results immediately with local processing
5. **Iterative Refinement**: Use natural language to adjust and improve

### Real-World Example: GitHub Analytics

Analyzing GitHub commit data showcases the power of this approach:

- Identify top contributors across multiple usernames
- Analyze code changes by file type and category
- Generate insights about project focus areas
- Complete complex analyses in minutes rather than hours

## The Future of BI: Notebooks, Dashboards, or Both?

The evolution of BI interfaces suggests multiple modalities will coexist:

### Traditional Dashboards

- Best for monitoring key metrics
- Daily business operations
- Executive reporting
- Standardized views

### Notebook-Style Interfaces

- Ideal for exploratory analysis
- Root cause investigations
- Iterative questioning
- Sharing analytical narratives

## Challenges and Considerations

Despite the excitement around AI-powered BI, several challenges remain:

### Technical Hurdles

- LLMs perform better with established coding patterns
- Innovation in interface design may be constrained by AI training data
- Documentation quality directly impacts AI effectiveness

### Human Factors

- Metadata often exists in people's heads, not systems
- Business logic requires human understanding
- Quality control remains essential

### The Augmentation Perspective

Rather than replacement, AI in BI represents augmentation. Data professionals who embrace these tools will find their capabilities enhanced, not diminished. The technology handles routine tasks while humans provide context, validation, and strategic thinking.

## Best Practices for AI-Powered BI

To maximize success with AI-powered BI:

1. **Follow conventions**: Use established patterns that LLMs recognize
2. **Document thoroughly**: Quality documentation improves AI performance
3. **Start with schemas**: Let AI infer from structure before accessing data
4. **Maintain human oversight**: Verify generated code and results
5. **Iterate quickly**: Leverage local processing for rapid development

## Looking Ahead

The convergence of BI as code, powerful local databases like DuckDB, and sophisticated LLMs creates unprecedented opportunities for data analysis. As these technologies mature, we can expect:

- More sophisticated metric generation
- Better handling of complex business logic
- Seamless integration between exploration and production
- Continued importance of human expertise in context and validation

The future of business intelligence isn't about choosing between humans or AI, dashboards or notebooks, clicks or code. It's about combining these elements to create more powerful, flexible, and accessible analytics experiences for everyone.

...SHOW MORE

## Related Videos

[!["Data-based: Going Beyond the Dataframe" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FData_based_f32745b461.png&w=3840&q=75)](https://motherduck.com/videos/going-beyond-the-dataframe/)

[2025-11-20](https://motherduck.com/videos/going-beyond-the-dataframe/)

### [Data-based: Going Beyond the Dataframe](https://motherduck.com/videos/going-beyond-the-dataframe)

Learn how to turbocharge your Python data work using DuckDB and MotherDuck with Pandas. We walk through performance comparisons, exploratory data analysis on bigger datasets, and an end-to-end ML feature engineering pipeline.

Webinar

Python

AI, ML and LLMs

[!["Empowering Data Teams: Smarter AI Workflows with Hex & MotherDuck" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FHex_Webinar_778e3959e4.png&w=3840&q=75)](https://motherduck.com/videos/smarter-ai-workflows-with-hex-motherduck/)

[2025-11-14](https://motherduck.com/videos/smarter-ai-workflows-with-hex-motherduck/)

### [Empowering Data Teams: Smarter AI Workflows with Hex & MotherDuck](https://motherduck.com/videos/smarter-ai-workflows-with-hex-motherduck)

AI isn't here to replace data work, it's here to make it better. Watch this webinar to see how Hex and MotherDuck build AI workflows that prioritize context, iteration, and real-world impact.

Webinar

AI, ML and LLMs

[!["Can DuckDB replace your data stack?" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FCan_Duck_DB_Replace_Your_Data_Stack_Mother_Duck_Co_Founder_Ryan_Boyd_3_56_screenshot_70e18322ec.png&w=3840&q=75)\\
\\
60:00](https://motherduck.com/videos/can-duckdb-replace-your-data-stack/)

[2025-10-23](https://motherduck.com/videos/can-duckdb-replace-your-data-stack/)

### [Can DuckDB replace your data stack?](https://motherduck.com/videos/can-duckdb-replace-your-data-stack)

MotherDuck co-founder Ryan Boyd joins the Super Data Brothers show to talk about all things DuckDB, MotherDuck, AI agents/LLMs, hypertenancy and more.

YouTube

BI & Visualization

AI, ML and LLMs

Interview

[View all](https://motherduck.com/videos/)

Authorization Response