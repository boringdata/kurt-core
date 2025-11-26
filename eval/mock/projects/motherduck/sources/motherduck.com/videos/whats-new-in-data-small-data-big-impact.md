---
title: whats-new-in-data-small-data-big-impact
content_type: tutorial
source_url: https://motherduck.com/videos/whats-new-in-data-small-data-big-impact
indexed_at: '2025-11-25T20:45:00.311767'
content_hash: dc0c7070100a4f40
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[BACK TO VIDEOS](https://motherduck.com/videos/)

Small Data, Big Impact: Insights from MotherDuck's Jacob Matson - YouTube

[Photo image of Striim](https://www.youtube.com/channel/UCduNv6TDK3eNcG_ye0PetqQ?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

Striim

1.66K subscribers

[Small Data, Big Impact: Insights from MotherDuck's Jacob Matson](https://www.youtube.com/watch?v=MDCbdrp-E-s)

Striim

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

[Watch on](https://www.youtube.com/watch?v=MDCbdrp-E-s&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 41:36

•Live

•

InterviewYouTube

# What's New in Data: Small Data, Big Impact

2024/09/19

_**Editor's note:** What follows is an AI-generated summary of the video transcript_

In an era where data is dubbed the new oil, navigating the complex and ever-evolving landscape of data management and analysis can be a daunting endeavor. Yet, amidst these challenges lies an untold story of adaptation and innovation, exemplified by the career trajectory of Jacob Matson. Once a hands-on operator renowned for his mastery of SQL Server, dbt, and Excel, Matson has taken a bold leap into the realm of Developer Advocacy with MotherDuck. This transition is not merely a career shift but a testament to the transformative power of DuckDB in addressing intricate data problems. Through Matson's journey, we unravel the significance of DuckDB, a tool heralded for its adaptability across both local and cloud environments, showcasing its potential to redefine our approach to data analysis. As we delve into the reasons behind Matson's move and the broader industry trend towards roles that demand adaptability and a thirst for continuous learning, we set the stage for a deeper exploration of DuckDB's impact on the data landscape. Are you ready to explore how DuckDB and the transition of one individual can signal shifts in the broader technological ecosystem?

## Introduction to Jacob Matson and MotherDuck

Jacob Matson's career evolution from an experienced operator in data management tools like SQL Server, dbt, and Excel to a Developer Advocate at MotherDuck marks a significant shift in the data technology landscape. This transition is not just a personal career move but a reflection of a broader industry trend where professionals increasingly align their careers with emerging technologies that promise to solve complex data problems more effectively. Matson's pivot towards MotherDuck, a company at the forefront of enhancing DuckDB's capabilities, underscores his dedication to addressing specific data challenges that modern organizations face.

DuckDB emerges as a critical player in this narrative, offering unique solutions that stand out for their adaptability in both local and cloud environments. The tool's design and functionality cater to a growing need for flexible, efficient, and scalable data analysis tools. Matson's journey epitomizes the growing importance of adaptability and continuous learning in the tech industry, highlighting the necessity for professionals to evolve alongside technological advancements.

As we explore Matson's transition and the reasons behind his move to MotherDuck, we gain insights into the significance of DuckDB in revolutionizing data management and analysis. This evolution from operator to Developer Advocate not only reflects Matson's career growth but also serves as a catalyst for a broader conversation about the technological advancements shaping the future of data analytics.

## DuckDB: Revolutionizing Data Analysis - Understanding the Core of DuckDB's Design and Functionality

At the heart of DuckDB lies an architecture that sets it apart from conventional databases. Often likened to SQLite for its simplicity and ease of use in analytics, DuckDB's design philosophy hinges on an embeddable, in-process database model. This foundational choice simplifies a myriad of traditional database concerns, effectively removing the burden of complex setup and management overhead from developers and analysts alike. Unlike systems that require dedicated servers or complex configurations, DuckDB integrates directly into applications, offering a seamless data processing experience.

One of DuckDB's standout features is its design tailored for **multi-core machines**. In an era where computing hardware is no longer constrained by single-core limitations but instead boasts multiple cores, DuckDB's architecture leverages this shift to its advantage. The database is built from the ground up to maximize the computing power of modern hardware. By efficiently distributing workloads across all available cores, DuckDB ensures that analytical queries are processed at lightning speed, making it an ideal choice for data-intensive applications.

The simplified security model of DuckDB offers a fresh perspective on data management. In traditional databases, securing data involves complex role-based access controls and various levels of permissions. DuckDB's approach simplifies this by focusing on local data processing. This model assumes that if you have access to the machine running DuckDB, you are authorized to access the data within. While this may seem unconventional, it streamlines data access for analytical workloads, where the primary concern is processing efficiency rather than multi-user access control.

A critical aspect of DuckDB that reassures users of its reliability is its compliance with **ACID properties**. Despite its streamlined security model and focus on local processing, DuckDB does not compromise on transaction reliability. By adhering to the principles of Atomicity, Consistency, Isolation, and Durability, DuckDB ensures that even in a simplified environment, data integrity and transactional reliability are upheld. This makes DuckDB a dependable choice for applications that demand both analytical performance and data consistency.

Looking towards the future, the strategic implications of DuckDB's design are profound for the landscape of analytical workloads. By prioritizing efficiency, simplicity, and the effective use of modern hardware, DuckDB presents a compelling alternative to more cumbersome, traditional analytical databases. Its emphasis on leveraging local resources for data analysis not only reduces dependency on cloud-based solutions but also offers a cost-effective and high-performance option for data analysts and scientists. As the volume of data continues to grow exponentially, the ability to perform fast, reliable analytics on local machines becomes increasingly valuable. DuckDB, with its innovative design and strategic advantages, positions itself as a key player in the future of data analysis, challenging the status quo and paving the way for a new era of data-driven decision-making.

## Hybrid Execution and Cloud Integration with MotherDuck - Advancing DuckDB's Capabilities into Cloud Services

MotherDuck ushers in a new era of data processing with its innovative approach to **hybrid execution**, effectively bridging the gap between local and cloud environments. This model enables queries to intelligently assess and execute across the most suitable environment, leveraging both the power of local processing units and the scalability of cloud resources. The seamless integration of DuckDB with cloud services through MotherDuck represents a significant leap forward, making data analytics more flexible and efficient.

Addressing the challenges of adapting DuckDB for cloud environments, MotherDuck has had to innovate extensively, particularly in areas such as **security model creation** and **resource allocation**. These challenges stem from DuckDB's original design for local execution, which did not account for the complexities of cloud-based data management. MotherDuck's solution involves the creation of robust security frameworks and intelligent resource allocation algorithms to ensure that DuckDB's transition to the cloud does not compromise its performance or the security of the data being processed.

A cornerstone of MotherDuck's cloud strategy is its **innovative tenancy model**. Each user receives isolated compute resources, affectionately dubbed 'ducklings,' which ensure that queries from one user do not interfere with another's. This model not only optimizes performance by preventing resource contention but also enhances security by isolating users' computational processes. Such isolation is critical in a cloud environment, where multiple users often share underlying infrastructure.

**WebAssembly (WASM)** plays a pivotal role in MotherDuck's strategy, enabling DuckDB to run directly in browsers. This capability opens up new avenues for data interaction and visualization, allowing users to perform complex data analysis without the need for server round trips. The use of WASM significantly enhances the user experience by reducing latency and making it possible to leverage DuckDB's powerful analytics capabilities in web applications, dashboards, and interactive tools.

The broader implications of MotherDuck's enhancements on DuckDB are profound, particularly in terms of **making advanced data analysis more accessible and cost-effective**. By extending DuckDB's capabilities into the cloud while retaining its efficiency and simplicity, MotherDuck democratizes data analytics. Small to medium-sized enterprises, individual researchers, and educational institutions stand to benefit immensely from this development, as it lowers the barriers to entry for sophisticated data analysis.

MotherDuck's contributions to DuckDB highlight a future where data analytics is not bound by the constraints of hardware or the complexities of cloud integration. This vision aligns with the evolving needs of the data industry, prioritizing accessibility, efficiency, and the democratization of data tools. As DuckDB continues to gain traction across various sectors, MotherDuck's innovations ensure that its journey into the cloud is both impactful and aligned with the needs of a diverse user base.

## Real-World Applications and Future Directions - Leveraging DuckDB and MotherDuck in Operational Workloads

In the realm of data analytics, DuckDB and MotherDuck are emerging as game-changers, particularly in how they are applied to solve real-world data problems. From simplifying intricate data extraction processes to facilitating efficient local development workflows, these technologies are proving their worth across various industries. For instance, companies are leveraging DuckDB for rapid, on-the-fly analysis of large datasets without the overhead of moving data to a conventional data warehouse. This capability is invaluable for businesses that require immediate insights from their data, such as real-time financial analysis or just-in-time inventory management.

MotherDuck's partnership with other cutting-edge technologies like Hydra for Postgres integration further amplifies DuckDB's utility. This collaboration enables seamless data movement between operational databases and analytical workloads, allowing DuckDB to complement existing data management systems rather than replace them. Such integrations highlight DuckDB's flexibility and its potential to enhance the data infrastructure of organizations without necessitating a complete overhaul of their existing setups.

The democratization of data analytics is perhaps one of the most significant contributions of DuckDB and MotherDuck. By making powerful data analysis tools accessible to companies and individuals without requiring extensive infrastructure, these technologies level the playing field. Small startups, independent researchers, and educational institutions can now harness the same analytical power that was once the exclusive domain of large corporations with deep pockets.

Looking to the future, the evolving data landscape appears ripe for DuckDB and MotherDuck to make an even more significant impact. Speculations about new features, integrations, and the potential influence on big data and cloud computing paradigms are abundant. Possible advancements include enhanced machine learning capabilities directly within DuckDB, tighter integration with cloud storage solutions for seamless data access, and expanded support for complex data types to cater to a broader range of analytical needs.

For data professionals and organizations contemplating the adoption of DuckDB and MotherDuck within their data stacks, the message is clear: stay adaptable. The technological environment, especially in the data sector, is in constant flux. Tools and platforms that offer flexibility, efficiency, and the ability to integrate with existing systems while preparing for future demands are invaluable. DuckDB and MotherDuck epitomize these qualities, promising a robust foundation for data analytics now and in the years to come.

## Small Data SF Conference - Spotlighting the Small Data Movement

The tech industry's relentless pursuit of bigger data sets has overshadowed a powerful undercurrent: the small data movement. It's a shift that's gaining momentum, and nowhere is this more evident than at the upcoming Small Data SF conference. This gathering is set to illuminate the potential of small data and DuckDB's technology in solving complex problems that don't necessarily require vast data lakes to navigate. Here's what participants can look forward to:

- **Practical AI Applications and Data Analytics**: The conference will shed light on how small data powers AI applications in ways previously dominated by big data paradigms. Attendees will explore methodologies for extracting meaningful insights from smaller, more manageable datasets, showcasing that quality often trumps quantity in data analysis.

- **A Rich Tapestry of Speakers and Topics**: The diversity of speakers lined up for Small Data SF is a testament to the wide-ranging impact of small data across industries. From healthcare to retail, finance to entertainment, experts will share how DuckDB's technology has revolutionized their approach to data analysis, often simplifying processes and reducing costs without compromising on analytical depth or accuracy.

- **Challenging the Big Data Paradigm**: The core mission of Small Data SF is to question the inevitability of big data as the sole solution for technological advancement. By presenting scalable, efficient alternatives for data analysis, the conference aims to broaden the industry's perspective, showcasing that small data can often fulfill the same needs as big data, but with greater agility and less overhead.

- **Networking with Leading Experts**: Beyond the educational opportunities, Small Data SF represents a prime networking venue. Attendees will rub elbows with some of the brightest minds in data science, AI, and technology innovation. It's a chance to form collaborations, exchange ideas, and perhaps even lay the groundwork for future breakthroughs in the field.

- **A Call to Reconsider Data Strategies**: Perhaps most importantly, Small Data SF encourages participants to reassess their own data strategies. Whether you're a startup founder, a data analyst, or a product manager, the insights garnered from the conference could inspire a shift towards more efficient, scalable solutions for data analysis within your own projects or organizations.


As the conference approaches, it's clear that Small Data SF is not just an event; it's a burgeoning movement. It challenges the status quo, offering a fresh perspective on how we collect, analyze, and leverage data. In an era where the size of your data set has been seen as a measure of potential, Small Data SF stands as a beacon for those who believe in the power of precision, efficiency, and accessibility in data analytics. This conference is poised to redefine what success looks like in the tech industry, proving that when it comes to data, bigger isn't always better.

...SHOW MORE

## Related Videos

[!["Lies, Damn Lies, and Benchmarks" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FLies_Damn_Lies_and_Benchmarks_Thumbnail_404db1bf46.png&w=3840&q=75)](https://motherduck.com/videos/lies-damn-lies-and-benchmarks/)

[2025-10-31](https://motherduck.com/videos/lies-damn-lies-and-benchmarks/)

### [Lies, Damn Lies, and Benchmarks](https://motherduck.com/videos/lies-damn-lies-and-benchmarks)

Why do database benchmarks so often mislead? MotherDuck CEO Jordan Tigani discusses the pitfalls of performance benchmarking, lessons from BigQuery, and why your own workload is the only benchmark that truly matters.

Stream

Interview

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

[!["The Death of Big Data and Why It’s Time To Think Small | Jordan Tigani, CEO, MotherDuck" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fmaxresdefault_d2281b0894.jpg&w=3840&q=75)\\
\\
59:07](https://motherduck.com/videos/the-death-of-big-data-and-why-its-time-to-think-small-jordan-tigani-ceo-motherduck/)

[2024-10-24](https://motherduck.com/videos/the-death-of-big-data-and-why-its-time-to-think-small-jordan-tigani-ceo-motherduck/)

### [The Death of Big Data and Why It’s Time To Think Small \| Jordan Tigani, CEO, MotherDuck](https://motherduck.com/videos/the-death-of-big-data-and-why-its-time-to-think-small-jordan-tigani-ceo-motherduck)

A founding engineer on Google BigQuery and now at the helm of MotherDuck, Jordan Tigani challenges the decade-long dominance of Big Data and introduces a compelling alternative that could change how companies handle data.

YouTube

Interview

[View all](https://motherduck.com/videos/)

Authorization Response