---
title: 4-lightning-talks-on-practical-ai-workflows-from-notion-1password-motherduck-evidence
content_type: event
source_url: https://motherduck.com/videos/4-lightning-talks-on-practical-ai-workflows-from-notion-1password-motherduck-evidence
indexed_at: '2025-11-25T20:44:57.137674'
content_hash: d8a3ee7180f822b7
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[BACK TO VIDEOS](https://motherduck.com/videos/)

4 Lightning Talks on Practical AI Workflows from Notion, 1Password, MotherDuck & Evidence - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[4 Lightning Talks on Practical AI Workflows from Notion, 1Password, MotherDuck & Evidence](https://www.youtube.com/watch?v=bluySdbHlYY)

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

[Watch on](https://www.youtube.com/watch?v=bluySdbHlYY&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 58:56

•Live

•

YouTube

# 4 Lightning Talks on Practical AI Workflows from Notion, 1Password, MotherDuck & Evidence

2025/04/10

## How Data Teams Are Using AI to Transform Their Workflows

Four data professionals from MotherDuck, Notion, 1Password, and Evidence shared practical approaches to integrating AI into their daily workflows, demonstrating how artificial intelligence is reshaping the modern data stack.

## Using Cursor IDE for Rapid BI Development

Archie from Evidence demonstrated how Cursor, an AI-powered IDE built on VS Code, dramatically accelerates the development of data applications. Unlike traditional chat-based interfaces, Cursor provides comprehensive context about your entire codebase, enabling more accurate code generation.

The key advantages include:

- Automatic awareness of all files and dependencies in your project
- Integration with documentation (like Evidence docs) for enhanced context
- Real-time code generation with diff-style visualization
- Natural language commands for complex tasks

During the demonstration, Cursor successfully generated a complete deep-dive analytics page with multiple components on the first attempt, showcasing its ability to understand both the codebase structure and the specific requirements of BI tools.

## Enriching CRM Data with LLMs in Snowflake

Nate from 1Password tackled a common go-to-market challenge: incomplete CRM data. Historically, teams would manually update Salesforce records, with team members updating 20 accounts each morning—a time-consuming and error-prone process.

Using Snowflake's LLM integration, Nate developed an automated approach to classify companies by industry:

### Key Implementation Details:

- **Model Selection**: Llama models provided the best results for industry classification
- **Prescriptive Boundaries**: Defining 10-15 specific industries rather than letting the LLM choose freely
- **Prompt Engineering**: Including industry descriptions and definitions for accuracy
- **Data Enrichment**: Passing company names, domains, and notes to provide context

The solution achieved over 90% accuracy in returning single-word industry classifications, dramatically reducing manual data entry while improving data quality for territory planning and lead routing.

## Automating Data Catalog Documentation at Notion

Evelyn from Notion addressed the perpetual challenge of maintaining data catalog documentation. Despite significant investments in data catalog tools, many organizations struggle with incomplete metadata, rendering these tools less effective.

### The Documentation Generation Process:

1. **Context Gathering**: Providing SQL definitions, upstream schemas, data types, and internal documentation
2. **Lineage Awareness**: Using generated upstream descriptions to ensure consistency across tables
3. **Human Review**: All AI-generated descriptions undergo review before publication
4. **Feedback Loop**: Table owners can suggest improvements that the LLM incorporates

The system successfully generates table descriptions, column definitions, and example queries, though human oversight remains crucial—especially for nuanced details like date partitioning that could lead to expensive query mistakes.

## Streamlining Data Pipeline Development with MCP

Mehdi from MotherDuck showcased how the Model Context Protocol (MCP) revolutionizes data pipeline development. Traditional data engineering involves slow feedback loops between writing, testing, and debugging code against actual data sources.

MCP enables LLMs to:

- Execute queries directly against data sources
- Validate schemas and data types in real-time
- Generate and test DBT models automatically
- Provision data directly in cloud warehouses

The demonstration showed an LLM independently:

1. Querying S3 files to understand data structure
2. Handling errors (like type mismatches) through iterative testing
3. Creating validated DBT staging models
4. Loading processed data into MotherDuck

This approach significantly reduces the traditional back-and-forth between code generation and testing, though it requires guidance to follow senior engineering best practices rather than brute-force solutions.

## Common Challenges and Best Practices

### Trust and Validation

All panelists emphasized the importance of skepticism when reviewing AI-generated outputs. Results often appear reasonable but may contain subtle errors that only domain expertise can catch. The recommendation: always implement human review processes, especially for production systems.

### Model Selection Matters

Different models excel at different tasks. While GPT-4 might excel at product specification, Claude often performs better for code implementation. Mistral's Code Stral model specifically targets code generation without unnecessary markdown explanations. Teams should evaluate multiple models for their specific use cases.

### Shifting Skill Requirements

AI tools are changing how data professionals spend their time:

- **Less time writing boilerplate code**: AI handles routine coding tasks
- **More time reviewing and validating**: Engineers become code reviewers rather than writers
- **Focus on patterns and architecture**: Understanding the "why" becomes more important than the "how"
- **Reduced interruptions**: Fewer requests to senior engineers for basic questions

### The Junior Engineer Challenge

A surprising challenge emerged around supporting junior team members. As senior engineers become more self-sufficient with AI tools, they may inadvertently provide less mentorship. Teams need to actively ensure junior members receive adequate support and aren't just relying on AI without understanding fundamentals.

## Key Takeaways for Implementation

1. **Start with Sandboxed Environments**: Test AI workflows in controlled settings before production deployment
2. **Provide Rich Context**: The quality of AI outputs directly correlates with the metadata and context provided
3. **Maintain Human Oversight**: AI accelerates workflows but doesn't replace the need for expert validation
4. **Document AI Boundaries**: Clearly define what AI should and shouldn't do in your workflows
5. **Iterate on Prompts**: Invest time in crafting effective prompts rather than accepting first results

The consensus among panelists: AI tools are transforming data workflows by eliminating routine tasks and accelerating development cycles. However, success requires thoughtful implementation, continuous validation, and a clear understanding that these tools augment rather than replace human expertise. As data teams adopt these technologies, the focus shifts from manual execution to strategic thinking and quality assurance—ultimately enabling teams to deliver more value in less time.

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

[!["Lies, Damn Lies, and Benchmarks" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FLies_Damn_Lies_and_Benchmarks_Thumbnail_404db1bf46.png&w=3840&q=75)](https://motherduck.com/videos/lies-damn-lies-and-benchmarks/)

[2025-10-31](https://motherduck.com/videos/lies-damn-lies-and-benchmarks/)

### [Lies, Damn Lies, and Benchmarks](https://motherduck.com/videos/lies-damn-lies-and-benchmarks)

Why do database benchmarks so often mislead? MotherDuck CEO Jordan Tigani discusses the pitfalls of performance benchmarking, lessons from BigQuery, and why your own workload is the only benchmark that truly matters.

Stream

Interview

[View all](https://motherduck.com/videos/)

Authorization Response