---
title: data-engineering-toolkit-essential-tools
content_type: guide
source_url: https://motherduck.com/blog/data-engineering-toolkit-essential-tools
indexed_at: '2025-11-25T19:56:37.132722'
content_hash: 956399317babebac
has_code_examples: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# The Data Engineering Toolkit: Essential Tools for Your Machine

2025/01/22 - 20 min read

BY

[Simon Späti](https://motherduck.com/authors/simon-sp%C3%A4ti/)

To be proficient as a data engineer, you need to know various toolkits—from fundamental Linux commands to different virtual environments and optimizing efficiency as a data engineer.

This article focuses on the building blocks of data engineering work, such as operating systems, development environments, and essential tools. We'll start from the ground up—exploring crucial Linux commands, containerization with Docker, and the development environments that make modern data engineering possible. We look at current programming languages and how they influence our work—providing a comprehensive overview of the tools of a modern data engineer.

* * *

Before we start, you don't need to know everything discussed here, but over time, you may use all of them in various roles as a data engineer at different companies. I hope this article will give you a good overview and guidelines on what is essential and what is not.

Again, each selection might differ slightly depending on the company's setup, preferred vendors, and whether it uses a low-code or a building approach. Let's start with the first choice you must make at any company, the operation system to work on.

## Operating Systems & Environment

Before starting as a data engineer, your laptop, operating system (OS), and environment are your first choices. Here, we discuss the different OSs and virtualization you will encounter, such as Docker and ENV variables, to configure different environments.

### Operating System Choices (Windows/Mac/Linux)

Choosing the right operating system might seem significant. Primarily, it's a preference for what you like and know. Still, there is the fact that most **data platforms** that run on a server will run on a Linux-based OS system. Working on Linux OS on the client might give you skills you can reuse, but you can also have that with Windows with [WSL](https://en.wikipedia.org/wiki/Windows_Subsystem_for_Linux) [1](https://motherduck.com/blog/data-engineering-toolkit-essential-tools/#fn1) and MacOS running a Darwin-based Linux.

Your employer also defines it. If you are a Microsoft shop, you use tools such as Power BI, Visual Studio (not Visual Studio Code), and C#. This requires using Windows or at least a VM with Windows.

If you work at a startup and need great hardware that is easy to use, the company will probably provide you with the latest MacBook with MacOS installed. However, if you are a power user or need your [Dotfiles](https://www.freecodecamp.org/news/dotfiles-what-is-a-dot-file-and-how-to-create-it-in-mac-and-linux/), you may not use anything other than a Linux-based operating system. We will look later at fundamental Linux commands that make the life of every data engineer easier.

### Virtual Machine (VM)

As mentioned, you could run MacOS and Windows in a VM with VMware or Parallels. These are not native installations, but close to it, and they allow you to do most things.

The same goes if you are on Windows; instead of using WSL, which sometimes can get tricky with companies' proxies and network routing, you could use a Linux VM locally or somewhere hosted that you just SSH into or an [advanced example with Nix](https://www.youtube.com/live/LA8KF9Fs2sk?si=_nQRGKJIa_NlFHn2&t=1072). There are other solutions to explore; e.g., your whole machine could be a VM provided by your company or deploy a [VS Code server](https://code.visualstudio.com/docs/remote/vscode-server) to run VS Code instances inside your company network.

### ENV variables

The next layer that you commonly use is ENV variables. This is already a little more advanced. But think of your reproducible environments with your co-workers or managing different environments (dev/staging/prod) instead of hard copying all settings, which won't work on other environments with different OS or other expectations.

If you type `env` in a Linux-based OS terminal, you can see all your local env sets. To illustrate some, I have set these ENVs:

```sh
Copy code

❯ env
AIRFLOW_HOME=~/.airflow
SPARK_HOME=~/Documents/spark/spark-3.5.1-bin-hadoop3.3
MINIO_ENDPOINT=http://127.0.0.1:9000
GITHUB_USER=sspaeti
AWS_SECRET_ACCESS_KEY=my-secure-key
AWS_ACCESS_KEY_ID=my-access-key
```

These can be set in a projects-repositories folder, usually in `.env`, and which will be picked up automatically. However, the recommended approach is using SSO CLI tools (like `aws sso login` or `gcloud auth login`), which will automatically populate credentials in the expected locations, or alternatively adding them to your shell config (`~/.bashrc`, `~/.zshrc`).

Never commit \`.env\` files to version control

They often contain sensitive credentials. Add \`.env\` to your \`.gitignore\` file. Instead, provide an example file like \`.env.example\` with dummy values.


### Docker and Container Images

Another virtualized environment is [Docker](https://www.docker.com/), and specifically **[Dockerfiles](https://docs.docker.com/build/concepts/dockerfile/)**. Docker is the engine that runs your Dockerfile on all platforms and architectures, letting you create a container image and build it for Linux on a Windows machine.

That makes containers so powerful: you can **package and containerize complex data engineering requirements into a single Dockerfile**, and everyone can run it on any machine—whether locally, in CI/CD pipelines, or orchestrated in Kubernetes clusters. Think of container packages on ships that transport goods; the breakthrough was the standardized container size that fits on every boat; every harbor could maneuver them. Similarly, container images have become the standard for packaging data and software ecosystems, with formats originally defined by Docker now being widely supported across [different container runtimes and platforms](https://kubernetes.io/blog/2020/12/02/dont-panic-kubernetes-and-docker/).

A simple nginx (webserver) example:

```bash
Copy code

# Use the official NGINX image from Docker Hub
FROM nginx:latest

# Copy your custom NGINX configuration file (if you have one)
COPY nginx.conf /etc/nginx/nginx.conf

# Copy static website files to the appropriate directory
COPY . /usr/share/nginx/html

# Expose the port NGINX listens on
EXPOSE 80
```

Docker also supports [different instructions](https://docs.docker.com/reference/dockerfile/) that you can use in a Dockerfile.

Different Architectures (amd64, arm64) and Line Feeds

When building `docker build` images, be aware of the **different architectures**. Whether you build Docker images or want to run them on other servers, **line endings** can cause issues in Dockerfiles and scripts—Windows uses CRLF (`\r\n`). In contrast, Linux/Mac uses LF (`\n`), which can break shell scripts and Docker builds. Use `.gitattributes` or configure your editor to use LF consistently.


Devcontainers

Like Docker, Devcontainers is an extra file in `devcontainer.json`. It works well with VS Code, allowing you to use Docker containers as full-featured development environments with predefined tools and runtime stacks.


## Linux DE Fundamentals

Even though you might use Windows, Linux is key to a data engineer. You don't need to be an expert, but you shouldn't be afraid of command line tools and know some basic Linux commands. And be aware that some of them are powerful.

### Opening and Editing a File with Nano/Vim

Editing or creating a new file might not be as easy as it seems. Command line text editors such as [Nano](https://de.wikipedia.org/wiki/Nano_(Texteditor)) or [Vim](https://en.wikipedia.org/wiki/Vim_(text_editor)) can be used for this task. Recommended is Nano, which displays the shortcuts to save or exit. Vim can be intimidating at first, but it's a [worthwhile investment](https://www.ssp.sh/blog/why-using-neovim-data-engineer-and-writer-2023/) when working 8 hours a day on the terminal, even more so [Vim Motions](https://youtu.be/qZO9A5F6BZs?feature=shared).

![image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimg1_toolkit_d326b20df2.png&w=3840&q=75)
Example of editing above Dockerfile in Nano.

### Basic Linux Tools and Commands

In addition to the Linux basic commands you have probably used or encountered like `cp, mv, ssh` as seen below, which are also super helpful on a server, we focus on the data engineering Linux commands you run on your laptop, where you can install things.

![image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimg2_toolkit_91b0bc67e9.png&w=3840&q=75)
Image from [Linux is a MUST. Seriously...](https://blog.amigoscode.com/p/linux-is-a-must-seriously) \| Also, check more on the book [Efficient Linux at the Command Line](https://danieljbarrett.com/books/efficient-linux-at-the-command-line/) by Daniel J. Barrett.

Most tools are Python-related to achieve the core tasks of a data engineer: ingestion of data, transforming and serving it to the organization or users. But the additional DE Linux commands I often use to quickly check an API, copy something over, or check processes are:

- `curl`: Quickly check an API is available through the cmd line.
- `make` / `cron`: Simple orchestration with the command line. More on this in the next chapter
- `ssh` / `rsync`: Ssh to connect to another machine and Rsync for a fast, versatile, synchronization tool to quickly back up or move data from your machine to the server.
- `bat`: Show data of a file nicely format and git integration.
- `tail`: Displays the last part of a file, which is helpful if the file is big and cat/bat would take long.
- `which`: Locate a program in the user's path to check if the right tool is running.
- `brew`: MacOS-specific package manager is the easiest way to install tools and cmd line utils.

Related to the above basic Linux commands:

- `grep`: Used for everything attached to an existing run. E.g. quickly search AWS env variables:

```sh
Copy code

❯ env | grep AWS
AWS_ACCESS_KEY_ID=my-access-key
AWS_BUCKET=my-bucket
AWS_SECRET_ACCESS_KEY=my-secret
```

- `ps aux` and `htop`: To check the current process. Ps is also handy in combination with grep (`ps aux | my-program.py`)

- `rg` and `fzf`: Ripgrep (rg) is a recursive line-oriented search tool that searches through all files, and fzf is a fuzzy finder. In combination, you can interactively search fuzzy find the content of Python files in the current folder easily with `rg -t python "def main" . | fzf`. (Also check out [Recursive Search in Terminal with fzf](https://www.ssp.sh/brain/recursive-search-in-terminal-with-fzf/), this will change your cmd-line life with reverse search `ctrl+r`).


TUIs for More Efficiency (and Fun!)

If you frequently use **git** or **docker**, please check out
[Lazygit](https://github.com/jesseduffield/lazygit/),
[Lazydocker](https://github.com/jesseduffield/lazydocker), and
[k9s](https://github.com/derailed/k9s). These TUIs show all commands within a single command. Instead of memorizing or typing lengthy commands, you can use a graphical user interface in the terminal and navigate with the keyboard.


### Simple Orchestration

The core responsibility of a data engineer is to orchestrate different jobs in the correct order and fully automate them. We use data orchestrators ( [Airflow](https://github.com/apache/airflow), [Dagster](https://github.com/dagster-io/dagster), [Prefect](https://github.com/PrefectHQ/prefect) etc.), but Linux also covers us.

**[Makefile](https://makefiletutorial.com/)** and **[cron](https://en.wikipedia.org/wiki/Cron)** jobs are out of the box and installed on every Linux system. For example, Makefiles let us store a combination of commands like this:

```makefile
Copy code

API_URL := "https://api.coincap.io/v2/assets"
DATA_DIR := /tmp/data

etl: extract transform load

extract:
  mkdir -p $(DATA_DIR)
  curl -s $(API_URL) | \
    jq -r '.data[] | [.symbol, .priceUsd, .marketCapUsd] | @csv' > \
    $(DATA_DIR)/crypto_raw.csv

transform:
  ./scripts/transform_data.sh

load:
  cat $(DATA_DIR)/crypto_raw.csv | \
    sort -t',' -k3,3nr | \
    head -n 10 > $(DATA_DIR)/top_10_crypto.csv

clean:
  rm -rf $(DATA_DIR)/*
```

Running `make extract` will create download data from the HTTPS API and store it as CSV, which we can check with `tail`:

```sh
Copy code

❯ make extract
mkdir -p /tmp/data
curl -s "https://api.coincap.io/v2/assets" | \
                jq -r '.data[] | [.symbol, .priceUsd, .marketCapUsd] | @csv' > \
                /tmp/data/crypto_raw.csv

❯ tail -n 3 /tmp/data/crypto_raw.csv
"ZEN","25.2499663234287359","399199442.5767759717054100"
"SUSHI","1.4507020739095067","381986878.5063751499688694"
"JST","0.0384023939139102","380183699.7477109800000000"
```

Combining these commands can be quick and super powerful. Make is just one example of storing and checking the commands into git so everyone can use them.

[Crontabs](https://en.wikipedia.org/wiki/Cron) are another way to schedule them daily, for example.

##### Pipeline command: Join different commands together `|`

In line with the [Unix Philosophy](https://en.wikipedia.org/wiki/Unix_philosophy), to make one tool do one thing as best as possible, you can combine " [pipe](https://en.wikipedia.org/wiki/Pipeline_(Unix))" different tools with `|` as we've seen examples already above with `grep` and others.

Here is another example of checking if any Python packages for SQL have been installed

```sh
Copy code

pip freeze | grep SQL
```

This allows the making of data pipelines within the terminal and a single cmd line by stacking different operations together. Example of powerful command chaining with pipes:

```sh
Copy code

❯ bat /tmp/data/crypto_raw.csv | tr -d '"' | cut -d',' -f1,3 | sort -t',' -k2 -nr | head -n 4
BTC,1920648934960.3101078883559601
ETH,386675369242.2018025632681003
XRP,161734797349.4803555794799785
USDT,137222181131.1690655355161784
```

The pipeline reads the above CSV file and extracts the coin name and market cap only (using `cut`), removes the quotes (`tr`), and then sorts by the market cap value numerically in descending order to show the top 4 biggest cryptocurrencies by market capitalization.

#### Data Processing

Another example could be data processing within the command line—e.g., quickly splitting a large CSV that you are unable to open with a text editor:

```sh
Copy code

# Split large CSV while keeping header
head -n1 large_file.csv > header.csv
split -l 1000000 --filter='tail -n +2' large_file.csv chunk_
# Add header back to each chunk
for f in chunk_*; do cat header.csv "$f" > "with_header_$f"; done
```

I hope you can imagine how you could build any small, efficient data pipeline with a Makefile and the Pipe commands.

## Developer Productivity

Next, we will look at the newer tools that can be added above the terminal and CLIs: powerful IDEs, notebooks, or workspaces, and git for version controlling everything.

### IDE (Working environment)

An integrated development environment (IDE) is where we program our code and get code completion, linters, and AI assistance to make us (hopefully) more productive.

Popular IDEs are with their used based on the [StackOverflow Survey 2024](https://survey.stackoverflow.co/2024/technology#most-popular-technologies-new-collab-tools-prof):

- **[Visual Studio Code](https://code.visualstudio.com/)** (73.6%) - Microsoft's lightweight but powerful source code editor with extensive plugin support and language coverage.
- **[Visual Studio](https://visualstudio.microsoft.com/)** (29.3%) - Microsoft's full-featured IDE, powerful for .NET development and enterprise applications.
- Other editors sorted percentage-wise are [IntelliJ IDEA](https://www.jetbrains.com/idea/) (26.8%), [Notepad++](https://notepad-plus-plus.org/) (23.9%), [Vim](https://www.vim.org/) (21.6%), [PyCharm](https://www.jetbrains.com/pycharm/) (15.1%), [Jupyter](https://jupyter.org/) (12.8%), [Neovim](https://neovim.io/) (12.5%), [Sublime Text](https://www.sublimetext.com/) (10.9%), [Eclipse](https://www.eclipse.org/) (9.4%), [Xcode](https://developer.apple.com/xcode/) (9.3%)

Not even on the map 2024 were the IDEs that go all in with AI:

- **[Cursor](https://cursor.sh/)** \- A VS Code-based editor explicitly built for AI-assisted development, featuring GitHub Copilot integration and specialized AI tooling for code completion and refactoring.
- **[Windsurf](https://www.windsurf.ai/)** \- An AI-first code editor designed to streamline development workflow with features like natural language code generation and intelligent code suggestions.
- **[Zed](https://zed.dev/)** \- A high-performance, multiplayer code editor with AI capabilities created by former Atom developers.

### Codespaces and Workspaces

In addition to IDEs that are usually installed locally, we also have codespaces (or workspaces, depending on the naming) that live in the browser. These are super handy because everyone has the same environment, and the days of "does not work on my machine" are gone.

These tools include **[GitHub Codespaces](https://github.com/features/codespaces)**, **[Devpod](https://devpod.sh/)**, **[Replit](https://replit.com/)**, **[Stackblitz](https://stackblitz.com/)**, **[CodeSandbox](https://codesandbox.io/)** **[Gitpod](https://www.gitpod.io/)**, and many others.

### Notebooks

In addition to IDEs and Codespaces, you can use a notebook that runs locally or in the cloud. This option is generally more flexible and allows you to visualize results and document the code. However, putting it in production has a downside: It's harder to restart, backfill, or configure with different variables.

It’s more flexible and easier to get started, but transitioning notebooks to production remains challenging even on platforms like Databricks, which are designed to support a development-to-production workflow.

Notebooks like **[Jupyter Notebook](https://jupyter.org/)** / **[JupyterHub](https://jupyter.org/hub)**, **[Apache Zeppelin](https://zeppelin.apache.org/)**, or **[Databricks Notebook](https://www.databricks.com/product/collaborative-notebooks)**. Newer versions of Jupyter Notebooks with more integrated features and a robust cloud behind them are **[Deepnote](https://deepnote.com/)**, **[Hex](https://hex.tech/)**, and **[Count.co](https://count.co/)**, **[Enso](https://ensoanalytics.com/)**, or **[MotherDuck](https://motherduck.com/docs/getting-started/motherduck-quick-tour/)**, which combines the flexibility of notebooks with the power of DuckDB's analytics engine.

Spreadsheets

There is even one more category: **spreadsheet-style apps**. They are similar to notebooks as they can also run **Python** and **JavaScript** inside cells. Think
[Quadratic](https://www.quadratichq.com/), Excel, and others.


### Git Version Control

[Git](https://git-scm.com/) is probably the most used version control in data engineering nowadays. There was a time of [TortoiseSVN](https://tortoisesvn.net/) and others.

As a data engineer, you need to version your code and product to easily roll back in case of error or work together as a team. The most common git workflow are:

```sh
Copy code

git pull origin main # Pull latest changes
git status # Check status of your changes
git add pipeline.py #stage
git commit -m "fix: update extraction logic for new API version" #commit
git push origin main # Push to remote repository
git checkout -b feature/new-data-source # Create and switch to a new branch
```

For more complex operations, consider using a Git GUI client. Some popular options include [GitKraken](https://www.gitkraken.com/), [SourceTree](https://www.sourcetreeapp.com/), [Lazygit](https://github.com/jesseduffield/lazygit) (terminal UI), and [many more](https://github.com/dictcp/awesome-git#client).

## Data Engineer Programming Languages

Before we wrap up, let's look at a data engineer's programming language. This will change depending on whether you are working more on infrastructure, pipeline, or business extraction.

The most prominent language you will use is still **SQL**, as the language to query each BI tool, doing most transformations with dbt and others, and even having an API on the most popular DE libraries makes it the best first language to master. Just after, especially if you build a lot of data pipelines and do a bit above basic transformations, you won't get around **Python**. Python is the tooling language of a data engineer; think of it as the Swiss army knife.

Lastly, if you are in infrastructure and need to deploy the data stack, you primarily work with **YAML** as a definition language for Helm, Kubernetes, Terraform, or other deployments. You could write some Rust if you are developing infrastructure and performance-heavy optimization.

We can see the most popular languages as with the [StackOverflow 2024](https://survey.stackoverflow.co/2024/technology#admired-and-desired) data, query with DuckDB with a shared DB on MotherDuck—simply [sign up](https://app.motherduck.com/) (if you haven't) and [create a token](https://motherduck.com/docs/key-tasks/authenticating-and-connecting-to-motherduck/authenticating-to-motherduck/) to query the database with this [SQL-query](https://gist.github.com/sspaeti/64405c15ef5b0f969435195cbdd05c04):

```sh
Copy code

┌─────────────────────────┬───────┬──────────────────────────────────────────┐
│        language         │ count │                  chart                   │
│         varchar         │ int64 │                 varchar                  │
├─────────────────────────┼───────┼──────────────────────────────────────────┤
│ JavaScript              │ 37492 │ ████████████████████████████████████████ │
│ HTML/CSS                │ 31816 │ █████████████████████████████████▉       │
│ Python                  │ 30719 │ ████████████████████████████████▊        │
│ SQL                     │ 30682 │ ████████████████████████████████▋        │
│ TypeScript              │ 23150 │ ████████████████████████▋                │
│ Bash/Shell (all shells) │ 20412 │ █████████████████████▊                   │
│ Java                    │ 18239 │ ███████████████████▍                     │
│ C#                      │ 16318 │ █████████████████▍                       │
│ C++                     │ 13827 │ ██████████████▊                          │
│ C                       │ 12184 │ ████████████▉                            │
├─────────────────────────┴───────┴──────────────────────────────────────────┤
│ 10 rows                                                          3 columns │
└────────────────────────────────────────────────────────────────────────────┘
```

### Beyond Languages

Beyond programming languages, you must get to know various **databases and their concepts**, such as [relational database theory](https://www.seas.upenn.edu/~zives/03f/cis550/codd.pdf). It does not matter which SQL dialect you learn, as they are all related, but knowing the fundamentals of a specific database, such as Postgres, DuckDB, or a NoSQL database, will help you on your journey.

Python libraries and frameworks are the last we observe and where you can spend most of your time. Instead of learning as many as possible, I suggest investing in a few used at your company and where you benefit most.

Typical starter libraries include [DuckDB](https://duckdb.org/docs/api/python/overview.html) (a powerful in-memory transformation library and database with [scale-up](https://motherduck.com/blog/the-simple-joys-of-scaling-up/) capabilities via MotherDuck[2](https://motherduck.com/blog/data-engineering-toolkit-essential-tools/#fn2), ideal for offloading interactive queries to [reduce Snowflake costs](https://motherduck.com/learn-more/reduce-snowflake-costs-duckdb)), [Pandas](https://pandas.pydata.org/) (flexible data manipulation), [PyArrow](https://arrow.apache.org/docs/python/index.html) (optimized for columnar data), [Polars](https://pola.rs/) (fast and scalable DataFrame library), and [PySpark](https://spark.apache.org/docs/latest/api/python/index.html) (for distributed data processing with Apache Spark).

### Python Libraries

There are many more libraries available, especially when you need to quickly access an API or perform a task that a CLI can't. Some key libraries can be beneficial depending on the use case you are working on.

Data Ingestion:

- [Requests](https://requests.readthedocs.io/en/latest/) \- HTTP library for API queries and web scraping
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) \- HTML parsing library for web scraping

Developer Tools:

- [uv](https://github.com/astral-sh/uv) / [pip](https://pip.pypa.io/) \- Package installers for Python, with uv being a modern, fast alternative to pip
- [Ruff](https://docs.astral.sh/ruff/) \- Fast linter and code formatter
- [Pytest](https://docs.pytest.org/) \- A testing framework for Python

Data Validation:

- [Pydantic](https://docs.pydantic.dev/) \- Data validation for Python objects
- [Pandera](https://pandera.readthedocs.io/) \- Schema validation for dataframes
- [Great Expectations](https://github.com/great-expectations/great_expectations) / [OpenLineage](https://github.com/OpenLineage/OpenLineage) \- Data quality validation framework and data lineage tracking tools

We could go on forever. Libraries exist for virtually everything: data ingestion, orchestration, BI tools, you name it. We could discuss setting up a Python project (it's not a solved problem, and there are many ways of doing it), discuss DevOps and how to use a simple Helm script, set up a local storage system that mimics S3, and more.

## Wrapping Up

Instead, we wrap it up, and I hope you enjoyed this article. It gave you an overview and a sense of how much is asked from a data engineer these days. But as this might be overwhelming, I suggest always focusing on fundamentals and, second, taking it step by step. It's better to understand why than skip over it quickly. — Also, as we are in the AI area, use ChatGPT to explain a command or a CLI tool to you; it will do a much better job than any Google Search.

We've covered the **foundational** tools and environments of modern data engineering, skills that are often overlooked but crucial for any data engineer. From selecting the proper OS and virtualization setup to mastering Linux fundamentals and CLIs, these building blocks enable efficient data pipeline development without always requiring complex tools.

This foundation reminds us that sometimes the simplest solution is the most effective—a well-chosen Linux command can often replace a complex toolchain. I hope that these technical skills, provided by a modern data engineer, will help you along your journey when working from the command line on your machine.

* * *

MotherDuck strives for [modern data development](https://motherduck.com/docs/getting-started/) and developer productivity. For instance, its approach to developer productivity allows seamless scaling from local development to production: developers can work with DuckDB locally using `path: "local.duckdb"` for their development environment, then simply point their production environment to MotherDuck with `path: "md:prod_database"`. This lets engineers focus on feature implementation while MotherDuck handles the scaling and performance.

For a practical example, check out this implementation in the [Deep Dive - Shifting Left and Moving Forward with MotherDuck](https://youtu.be/z3trqkKPbsI?si=mcLeiUi-5YBMs5oI&t=613):
![image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimg3_toolkit_05cc762b6d.png&w=3840&q=75)
Code snippet available on [GitHub](https://github.com/dagster-io/dagster/blob/1750e8fa2a2d56b38063baecc4257d650ffb15ef/examples/project_atproto_dashboard/dbt_project/profiles.yml#L19)

1Although it's not 100% the same, it's a good option and alternative to use both Windows and Linux in one, as someone who has used WSL extensively, if you are challenged to work mainly in Linux and the command line, Linux or MacOS are still the better option.

2This is also where MotherDuck makes all the difference for a simple local machine to experiment, but using the hybrid power of MotherDuck to scale up when needed, as Yuki
[shared](https://www.amazon.com/Polars-Cookbook-practical-transform-manipulate-ebook/dp/B0CLRS4B8T).


### TABLE OF CONTENTS

[Operating Systems & Environment](https://motherduck.com/blog/data-engineering-toolkit-essential-tools/#operating-systems-environment)

[Linux DE Fundamentals](https://motherduck.com/blog/data-engineering-toolkit-essential-tools/#linux-de-fundamentals)

[Developer Productivity](https://motherduck.com/blog/data-engineering-toolkit-essential-tools/#developer-productivity)

[Data Engineer Programming Languages](https://motherduck.com/blog/data-engineering-toolkit-essential-tools/#data-engineer-programming-languages)

[Wrapping Up](https://motherduck.com/blog/data-engineering-toolkit-essential-tools/#wrapping-up)

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