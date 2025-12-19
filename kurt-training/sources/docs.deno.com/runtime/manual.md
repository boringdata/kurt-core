---
title: Welcome to Deno
url: https://docs.deno.com/runtime/manual
hostname: deno.com
description: Learn the basics of Deno, a secure JavaScript, TypeScript, and WebAssembly runtime.
sitename: Deno
date: 2025-01-01
tags: ['Deno, JavaScript, TypeScript, reference, documentation, guide, tutorial, example']
---
## On this page

[Deno](https://deno.com)
([/ˈdiːnoʊ/](https://ipa-reader.com/?text=%CB%88di%CB%90no%CA%8A), pronounced
`dee-no`

) is an
[open source](https://github.com/denoland/deno/blob/main/LICENSE.md) JavaScript,
TypeScript, and WebAssembly runtime with secure defaults and a great developer
experience. It's built on [V8](https://v8.dev/),
[Rust](https://www.rust-lang.org/), and [Tokio](https://tokio.rs/).

## Why Deno? [Jump to heading](https://docs.deno.com#why-deno%3F)

- Deno is
Zero config or additional steps necessary.[TypeScript-ready out of the box](https://docs.deno.com/runtime/fundamentals/typescript/). - Deno is
Where other runtimes give full access every script they run, Deno allows you to enforce granular permissions.[secure by default](https://docs.deno.com/runtime/fundamentals/security/). - Deno has a
**robust built-in toolchain.**Unlike Node or browser JavaScript, Deno includes a[standard library](https://docs.deno.com/runtime/reference/std/), along with a first-party[linter/formatter](https://docs.deno.com/runtime/fundamentals/linting_and_formatting/),[test runner](https://docs.deno.com/runtime/fundamentals/testing/), and more. - Deno is
**fully compatible with**[Node and npm](https://docs.deno.com/runtime/fundamentals/node/). - Deno is
**fast and reliable**. [Deno is open-source](https://github.com/denoland/deno).

## Quick install [Jump to heading](https://docs.deno.com#quick-install)

Install the Deno runtime on your system using one of the terminal commands below:

```
curl -fsSL https://deno.land/install.sh | sh
```


In Windows PowerShell:

```
irm https://deno.land/install.ps1 | iex
```


```
curl -fsSL https://deno.land/install.sh | sh
```


[Additional installation options can be found here](https://docs.deno.com/runtime/getting_started/installation/).
After installation, you should have the `deno`

executable available on your
system path. You can verify the installation by running:

```
deno --version
```


## First steps [Jump to heading](https://docs.deno.com#first-steps)

Deno can run JavaScript and [TypeScript](https://www.typescriptlang.org/) with
no additional tools or configuration required, all in a secure,
batteries-included runtime.