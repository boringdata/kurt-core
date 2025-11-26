---
title: from-core-to-custom-unlocking-new-possibilities-with-duckdb-extensions
content_type: event
source_url: https://motherduck.com/videos/from-core-to-custom-unlocking-new-possibilities-with-duckdb-extensions
indexed_at: '2025-11-25T20:44:59.605092'
content_hash: f4215ebfa96f68e9
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[BACK TO VIDEOS](https://motherduck.com/videos/)

From Core to Custom: Unlocking new possibilities with DuckDB Extensions - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[From Core to Custom: Unlocking new possibilities with DuckDB Extensions](https://www.youtube.com/watch?v=flhTXeAHVy8)

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

[Watch on](https://www.youtube.com/watch?v=flhTXeAHVy8&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 49:07

•Live

•

YouTube

# From Core to Custom: Unlocking new possibilities with DuckDB Extensions

2025/02/10

## Understanding DuckDB Extensions: Core and Community Options

DuckDB extensions are powerful add-ons that expand the database's functionality without modifying its core codebase. Extensions fall into two main categories: core extensions maintained by the DuckDB team, and community extensions developed by users.

### Core Extensions and Autoload Magic

Core extensions like spatial, httpfs, and parquet come bundled with DuckDB. Previously, users needed to manually install and load each extension. However, the autoload feature introduced around version 0.9 streamlines this process - DuckDB now automatically detects when an extension is needed and loads it transparently.

For example, when querying data from an S3 bucket, DuckDB automatically loads the httpfs extension without requiring manual intervention. This user-first philosophy removes friction from the workflow while maintaining transparency by notifying users which extensions are being loaded.

### Community Extensions: Opening the Ecosystem

The community extension repository represents a significant shift in how users can contribute to DuckDB. Instead of navigating the complex process of submitting pull requests to the core repository, developers can now create standalone extensions that integrate seamlessly with DuckDB.

To install a community extension, users simply specify:

```sql
Copy code

INSTALL extension_name FROM community;
```

### Building Your Own Extensions

Creating extensions has become remarkably accessible through multiple templates:

- **C++ Template**: The most comprehensive option, supporting scalar functions, table functions, secrets, and more
- **C Template**: The newer standard that will likely become the preferred approach
- **Rust Template**: Currently supports table functions, perfect for specific use cases

The process is straightforward:

1. Clone an extension template
2. Implement your functionality
3. Submit metadata to the community repository
4. Automated CI/CD handles building for all platforms

### Real-World Extension Examples

Several community extensions demonstrate the ecosystem's potential:

- **ClickHouse SQL**: Implements over 100 ClickHouse-compatible SQL functions as macros
- **pcap**: Reads Wireshark packet capture files as tables
- **Google Sheets**: Provides comprehensive integration including authentication and special data types
- **Avro**: One of the most downloaded community extensions

### The C API Revolution

The new C API represents a paradigm shift for extension development. Despite its name, the C API actually enables developers to create extensions in any language that supports Foreign Function Interface (FFI) - including Python, Go, Zig, and V.

This approach offers several advantages:

- Cross-version compatibility (extensions may work across DuckDB versions)
- Language flexibility without sacrificing performance
- Simplified development process

### Future Directions

The extension ecosystem is rapidly evolving with several exciting developments:

- **Arrow Flight Integration**: Enabling high-performance data transfer between DuckDB instances
- **HTTP Server Extensions**: Creating REST APIs for DuckDB databases
- **Cross-loading Capabilities**: Extensions becoming more portable across versions

The community extension model serves as an incubator for innovative features. Popular community extensions may eventually graduate to core extensions, as seen with other successful open-source projects.

### Getting Started with Extension Development

For developers interested in creating extensions:

1. Start with SQL-only extensions using macros - the simplest entry point
2. Browse existing community extensions for inspiration and examples
3. Join the DuckDB Discord or GitHub Discussions to connect with other developers
4. Use the automated build pipeline - no need to compile for every platform locally

The extension system democratizes contribution to DuckDB, allowing developers to add functionality without the overhead of core development requirements. Whether solving specific use cases or experimenting with new ideas, extensions provide a powerful way to extend DuckDB's capabilities while maintaining its lean, efficient core.

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