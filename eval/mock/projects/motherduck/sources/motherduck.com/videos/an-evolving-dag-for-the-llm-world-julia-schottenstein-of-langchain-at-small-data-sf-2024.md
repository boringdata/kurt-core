---
title: an-evolving-dag-for-the-llm-world-julia-schottenstein-of-langchain-at-small-data-sf-2024
content_type: tutorial
source_url: https://motherduck.com/videos/an-evolving-dag-for-the-llm-world-julia-schottenstein-of-langchain-at-small-data-sf-2024
indexed_at: '2025-11-25T20:44:47.149457'
content_hash: a132fefcfd0b7505
has_step_by_step: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[BACK TO VIDEOS](https://motherduck.com/videos/)

An Evolving DAG for the LLM world - Julia Schottenstein of LangChain at Small Data SF - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[An Evolving DAG for the LLM world - Julia Schottenstein of LangChain at Small Data SF](https://www.youtube.com/watch?v=Z-F_uj-V1ao)

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

[Watch on](https://www.youtube.com/watch?v=Z-F_uj-V1ao&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 15:35

•Live

•

YouTube

# An Evolving DAG for the LLM world - Julia Schottenstein of LangChain at Small Data SF 2024

2024/09/24

## Building Agentic Systems with LangChain: From DAGs to Directed Cyclic Graphs

LangChain has emerged as a popular open-source framework for Python and TypeScript developers looking to build agentic systems that combine the power of Large Language Models (LLMs) with organizational data. The framework addresses a fundamental challenge in AI application development: while LLMs possess incredible capabilities, they lack context about specific businesses, applications, and recent events beyond their training cutoff dates.

## Augmenting LLMs with Context and Tools

The core value proposition of LangChain lies in helping developers augment LLMs with:

- **Private documents and data** for domain-specific reasoning
- **Tool usage** through APIs with defined instructions
- **Up-to-date information** to overcome training data limitations

This augmentation typically happens through chains - discrete, ordered steps similar to directed acyclic graphs (DAGs) in data pipelines. The most common implementation is the Retrieval-Augmented Generation (RAG) chain, where:

1. A question enters the system
2. Relevant context is retrieved from a vector database
3. The question, context, and prompt instructions are sent to the LLM
4. The LLM generates a contextually-aware response

## The Evolution from Chains to Agents

While chains provide reliable, predetermined workflows, the future of AI applications increasingly points toward agents. In technical terms, an agent represents a system where the LLM decides the control flow dynamically rather than following predefined code paths. This fundamental shift transforms traditional DAGs into directed graphs that can include cycles.

The ability to iterate and learn from failures becomes crucial in agent design. Unlike deterministic code that produces identical results on repeated execution, LLMs can improve their performance on subsequent attempts by understanding what went wrong in previous iterations. This capability is exemplified by sophisticated code generation agents that:

- Reflect on problems before execution
- Generate and test multiple solution approaches
- Iteratively refine outputs based on test results
- Create cycles in their execution graphs for continuous improvement

## Key Challenges in Building Reliable Agents

### Planning and Reflection

Research demonstrates that agents perform significantly better when given explicit planning and reflection steps. Like a rock climber surveying potential routes before ascending, agents benefit from evaluating possible paths before execution. This pre-processing phase allows for more strategic decision-making and improved task completion rates.

### Memory Management

Complex agent systems often involve multiple specialized sub-agents collaborating on tasks. This architecture, known as cognitive architecture, requires sophisticated memory management to:

- Maintain shared state between agents
- Preserve context across multiple sessions
- Enable agents to learn from previous attempts
- Facilitate collaboration in multi-agent workflows

### Reliability Concerns

Agent reliability faces several obstacles:

- **LLM non-determinism** in response generation
- **Task ambiguity** from natural language inputs
- **Tool misuse** when agents get stuck in repetitive patterns or select inappropriate APIs

## Balancing Flexibility and Control with LangGraph

LangGraph represents LangChain's solution to the flexibility-reliability trade-off. This orchestration framework introduces several key innovations for agent development:

### Controllability

The framework supports both explicit and implicit workflows, allowing developers to define guardrails while maintaining agent autonomy. This hybrid approach enables more predictable behavior without sacrificing the adaptive capabilities that make agents powerful.

### Persistence Layer

A robust persistence layer provides shared memory and state management, essential for both individual agent sessions and multi-agent collaboration scenarios. This ensures continuity and context preservation across complex workflows.

### Human-in-the-Loop Capabilities

Recognizing that fully autonomous agents may struggle with complex tasks, LangGraph incorporates human steering mechanisms. This allows users to guide agents when they encounter difficulties or make routing errors, improving overall task completion rates.

### Streaming Support

To address latency concerns and improve user experience, the framework supports both token-by-token streaming and intermediate step visibility. This transparency helps users understand the agent's problem-solving process, particularly important when operations take extended time to complete.

## Real-World Agent Applications

Several production agents demonstrate the practical applications of these concepts:

- **Roblox Studio AI** creates entire virtual worlds from natural language prompts, generating scripts and assets automatically
- **TripAdvisor's travel agent** builds personalized itineraries based on user preferences, group size, and travel dates
- **Replit's coding agent** generates code, creates tests, and automates pull request creation

These applications showcase how agents can move beyond simple chat interfaces to become sophisticated task-completion systems that understand context, iterate on solutions, and deliver tangible value to users.

## The Future of AI Orchestration

The evolution from traditional DAGs to directed cyclic graphs represents a fundamental shift in how we approach AI application development. While DAGs remain valuable for deterministic data pipelines, the ability to incorporate cycles opens new possibilities for building intelligent systems that can plan, reflect, and improve through iteration. As agent technology continues to mature, frameworks like LangChain and LangGraph provide the necessary tools to build reliable, flexible, and powerful agentic applications that can tackle increasingly complex real-world problems.

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