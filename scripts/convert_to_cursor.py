#!/usr/bin/env python3
"""
Convert Claude Code plugin to Cursor IDE format.

This script converts:
- CLAUDE.md → kurt-main.mdc (with YAML frontmatter and references)
- instructions/*.md → rules/*.mdc (with frontmatter, agent-requested)
- kurt/templates/ → copied as-is (referenced with @)
- settings.json, commands/ → skipped (no Cursor equivalent)
"""

import re
import shutil
from pathlib import Path


def infer_description(content: str) -> str:
    """Infer description from 'When to use' section or first heading."""
    # Try to find "When to use this instruction" section
    when_match = re.search(
        r"##\s+When to use this instruction\s*\n(.+?)(?:\n\n|\n##|$)",
        content,
        re.MULTILINE | re.DOTALL,
    )
    if when_match:
        desc = when_match.group(1).strip()
        # Clean up and truncate if too long
        desc = desc.replace("\n", " ").strip()
        if len(desc) > 100:
            desc = desc[:97] + "..."
        return desc

    # Fallback to first heading
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if match:
        heading = match.group(1).strip()
        # Remove .md suffix if present
        if heading.endswith(".md"):
            heading = heading[:-3]
        return heading
    return "Kurt workflow instruction"


def convert_file_references_to_xml(content: str, instructions_dir: Path) -> str:
    """
    Convert markdown file references to XML reference blocks.

    Example:
        `instructions/add-profile.md` → XML reference to add-profile.mdc
    """
    references = {}  # Use dict to track unique references

    # Find all references to instructions/*.md
    pattern = r"`instructions/([\w-]+)\.md`"

    def replace_reference(match):
        instruction_name = match.group(1)
        instruction_file = instructions_dir / f"{instruction_name}.md"

        if instruction_file.exists():
            # Only read and store if we haven't seen this reference before
            if instruction_name not in references:
                # Read the instruction to get description
                with open(instruction_file) as f:
                    instruction_content = f.read()
                desc = infer_description(instruction_content)

                # Track reference for XML block (deduplicated)
                references[instruction_name] = desc

            # Replace inline reference with mention of the workflow
            return f"the `{instruction_name}` workflow"

        return match.group(0)

    content = re.sub(pattern, replace_reference, content)

    # Add XML references block at the top if we found any
    if references:
        xml_block = "\n<references>\n"
        # Sort by name for consistent ordering
        for name in sorted(references.keys()):
            desc = references[name]
            xml_block += (
                f'  <reference as="workflow" href=".cursor/rules/{name}.mdc" reason="{desc}">\n'
            )
            xml_block += f"    {name}\n"
            xml_block += "  </reference>\n"
        xml_block += "</references>\n\n"

        # Insert after first heading
        parts = content.split("\n", 1)
        if len(parts) == 2:
            content = parts[0] + "\n" + xml_block + parts[1]

    return content


def convert_template_references(content: str) -> str:
    """Convert template file references to @ mentions."""
    # kurt/templates/... → @kurt/templates/...
    content = re.sub(
        r"`(kurt/templates/[^`]+)`",
        r"@\1",
        content,
    )
    return content


def convert_claude_md_to_main_mdc(
    claude_md: Path,
    output_path: Path,
    instructions_dir: Path,
) -> None:
    """Convert CLAUDE.md to kurt-main.mdc."""
    print(f"Converting {claude_md} → {output_path}")

    with open(claude_md) as f:
        content = f.read()

    # Convert file references
    content = convert_file_references_to_xml(content, instructions_dir)
    content = convert_template_references(content)

    # Remove references to Claude Code-specific features
    content = re.sub(
        r".*Claude Code.*\n?",
        "",
        content,
        flags=re.IGNORECASE,
    )

    # Add frontmatter
    frontmatter = """---
description: Kurt content creation assistant - main instructions
alwaysApply: true
---

"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(frontmatter + content)

    print(f"  ✓ Created {output_path}")


def convert_instruction_to_mdc(
    instruction_md: Path,
    output_path: Path,
) -> None:
    """Convert an instruction .md file to .mdc format."""
    print(f"Converting {instruction_md} → {output_path}")

    with open(instruction_md) as f:
        content = f.read()

    # Infer description
    description = infer_description(content)

    # Convert template references
    content = convert_template_references(content)

    # Convert cross-references to other instructions
    content = re.sub(
        r"`instructions/([\w-]+)\.md`",
        r"@\1 rule",
        content,
    )

    # Add frontmatter
    frontmatter = f"""---
description: {description}
alwaysApply: false
---

"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(frontmatter + content)

    print(f"  ✓ Created {output_path}")


def convert_claude_to_cursor(
    claude_plugin_dir: Path,
    cursor_plugin_dir: Path,
) -> None:
    """Main conversion function."""
    print("=" * 60)
    print("Converting Claude Code plugin to Cursor format")
    print("=" * 60)

    # Clean output directory
    if cursor_plugin_dir.exists():
        shutil.rmtree(cursor_plugin_dir)
    cursor_plugin_dir.mkdir(parents=True)

    rules_dir = cursor_plugin_dir / "rules"
    rules_dir.mkdir()

    # Convert CLAUDE.md → kurt-main.mdc
    claude_md = claude_plugin_dir / "CLAUDE.md"
    if claude_md.exists():
        convert_claude_md_to_main_mdc(
            claude_md,
            rules_dir / "kurt-main.mdc",
            claude_plugin_dir / "instructions",
        )

    # Convert instructions/*.md → rules/*.mdc
    instructions_dir = claude_plugin_dir / "instructions"
    if instructions_dir.exists():
        print(f"\nConverting instructions from {instructions_dir}")
        for instruction_md in instructions_dir.glob("*.md"):
            output_path = rules_dir / f"{instruction_md.stem}.mdc"
            convert_instruction_to_mdc(instruction_md, output_path)

    # Copy kurt/templates/ as-is
    templates_src = claude_plugin_dir / "kurt"
    if templates_src.exists():
        print(f"\nCopying templates from {templates_src}")
        templates_dest = cursor_plugin_dir / "kurt"
        shutil.copytree(templates_src, templates_dest)
        print(f"  ✓ Copied {templates_src} → {templates_dest}")

    print("\n" + "=" * 60)
    print("Conversion complete!")
    print(f"Output: {cursor_plugin_dir}")
    print("=" * 60)
    print("\nCursor plugin structure:")
    print(f"  {cursor_plugin_dir}/")
    print("    rules/")
    print("      kurt-main.mdc (alwaysApply: true)")
    for mdc in sorted(rules_dir.glob("*.mdc")):
        if mdc.name != "kurt-main.mdc":
            print(f"      {mdc.name} (agent requested)")
    print("    kurt/")
    print("      templates/")


if __name__ == "__main__":
    # Default paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    claude_plugin = project_root / "src" / "kurt" / "claude_plugin"
    cursor_plugin = project_root / "src" / "kurt" / "cursor_plugin"

    if not claude_plugin.exists():
        print(f"Error: Claude plugin directory not found: {claude_plugin}")
        exit(1)

    convert_claude_to_cursor(claude_plugin, cursor_plugin)
