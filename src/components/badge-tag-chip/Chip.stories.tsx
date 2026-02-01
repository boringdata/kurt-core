/**
 * Chip Storybook stories
 * Demonstrates all variants and interactive features
 */

import React, { useState } from "react";
import { Meta, StoryObj } from "@storybook/react";
import Chip from "./Chip";

const meta: Meta<typeof Chip> = {
  title: "Components/Chip",
  component: Chip,
  parameters: {
    layout: "centered",
  },
  tags: ["autodocs"],
  argTypes: {
    variant: {
      control: "select",
      options: ["default", "success", "warning", "error", "info"],
    },
    size: {
      control: "select",
      options: ["sm", "md"],
    },
    removable: {
      control: "boolean",
    },
    selectable: {
      control: "boolean",
    },
    selected: {
      control: "boolean",
    },
  },
};

export default meta;
type Story = StoryObj<typeof Chip>;

export const Default: Story = {
  args: {
    variant: "default",
    children: "React",
  },
};

export const Success: Story = {
  args: {
    variant: "success",
    children: "Active",
  },
};

export const Warning: Story = {
  args: {
    variant: "warning",
    children: "Pending",
  },
};

export const Error: Story = {
  args: {
    variant: "error",
    children: "Error",
  },
};

export const Info: Story = {
  args: {
    variant: "info",
    children: "Update",
  },
};

export const Removable: Story = {
  args: {
    variant: "default",
    removable: true,
    children: "JavaScript",
  },
};

export const Selectable: Story = {
  args: {
    variant: "default",
    selectable: true,
    children: "React",
  },
};

export const Selected: Story = {
  args: {
    variant: "default",
    selectable: true,
    selected: true,
    children: "React",
  },
};

export const WithIcon: Story = {
  args: {
    variant: "success",
    icon: <span>⚛</span>,
    children: "React",
  },
};

export const Small: Story = {
  args: {
    size: "sm",
    children: "Chip",
  },
};

export const Medium: Story = {
  args: {
    size: "md",
    children: "Chip",
  },
};

export const AllVariants: Story = {
  render: () => (
    <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
      <Chip variant="default">Default</Chip>
      <Chip variant="success">Success</Chip>
      <Chip variant="warning">Warning</Chip>
      <Chip variant="error">Error</Chip>
      <Chip variant="info">Info</Chip>
    </div>
  ),
};

export const SelectableChips: Story = {
  render: () => {
    const [selected, setSelected] = useState(new Set(["react"]));

    const handleToggle = (id: string) => {
      const newSelected = new Set(selected);
      if (newSelected.has(id)) {
        newSelected.delete(id);
      } else {
        newSelected.add(id);
      }
      setSelected(newSelected);
    };

    const technologies = [
      { id: "react", label: "React" },
      { id: "vue", label: "Vue" },
      { id: "angular", label: "Angular" },
      { id: "svelte", label: "Svelte" },
    ];

    return (
      <div>
        <p style={{ marginBottom: "1rem" }}>Select your favorite frameworks:</p>
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
          {technologies.map((tech) => (
            <Chip
              key={tech.id}
              selectable
              selected={selected.has(tech.id)}
              onToggle={() => handleToggle(tech.id)}
              variant="default"
            >
              {tech.label}
            </Chip>
          ))}
        </div>
        <p style={{ marginTop: "1rem", fontSize: "0.875rem", color: "#6b7280" }}>
          Selected: {Array.from(selected).join(", ") || "None"}
        </p>
      </div>
    );
  },
};

export const RemovableChips: Story = {
  render: () => {
    const [chips, setChips] = useState([
      "JavaScript",
      "TypeScript",
      "React",
      "Vue",
    ]);

    const handleRemove = (index: number) => {
      setChips(chips.filter((_, i) => i !== index));
    };

    return (
      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
        {chips.map((chip, index) => (
          <Chip
            key={index}
            removable
            onRemove={() => handleRemove(index)}
            variant="info"
          >
            {chip}
          </Chip>
        ))}
      </div>
    );
  },
};

export const WithIconsAndRemove: Story = {
  render: () => (
    <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
      <Chip variant="success" icon={<span>✓</span>} removable>
        Approved
      </Chip>
      <Chip variant="warning" icon={<span>!</span>} removable>
        Pending
      </Chip>
      <Chip variant="error" icon={<span>✕</span>} removable>
        Rejected
      </Chip>
    </div>
  ),
};

export const FilterChips: Story = {
  render: () => {
    const [filters, setFilters] = useState(new Set(["featured"]));

    const toggleFilter = (filter: string) => {
      const newFilters = new Set(filters);
      if (newFilters.has(filter)) {
        newFilters.delete(filter);
      } else {
        newFilters.add(filter);
      }
      setFilters(newFilters);
    };

    return (
      <div>
        <p style={{ marginBottom: "1rem" }}>Filter by:</p>
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
          <Chip
            selectable
            selected={filters.has("featured")}
            onToggle={() => toggleFilter("featured")}
            variant="default"
          >
            Featured
          </Chip>
          <Chip
            selectable
            selected={filters.has("bestseller")}
            onToggle={() => toggleFilter("bestseller")}
            variant="default"
          >
            Best Sellers
          </Chip>
          <Chip
            selectable
            selected={filters.has("new")}
            onToggle={() => toggleFilter("new")}
            variant="default"
          >
            New Arrivals
          </Chip>
          <Chip
            selectable
            selected={filters.has("sale")}
            onToggle={() => toggleFilter("sale")}
            variant="default"
          >
            On Sale
          </Chip>
        </div>
        <p style={{ marginTop: "1rem", fontSize: "0.875rem", color: "#6b7280" }}>
          Active filters: {Array.from(filters).join(", ") || "None"}
        </p>
      </div>
    );
  },
};

export const InContext: Story = {
  render: () => (
    <div style={{ padding: "1.5rem", backgroundColor: "#f3f4f6", borderRadius: "0.5rem" }}>
      <h3 style={{ marginTop: 0 }}>Selected Skills</h3>
      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
        <Chip variant="info" removable icon={<span>✓</span>}>
          React
        </Chip>
        <Chip variant="info" removable icon={<span>✓</span>}>
          TypeScript
        </Chip>
        <Chip variant="info" removable icon={<span>✓</span>}>
          Node.js
        </Chip>
      </div>
    </div>
  ),
};
