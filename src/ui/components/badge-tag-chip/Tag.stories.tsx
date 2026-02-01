/**
 * Tag Storybook stories
 * Demonstrates all variants and interactive features
 */

import React, { useState } from "react";
import { Meta, StoryObj } from "@storybook/react";
import Tag from "./Tag";

const meta: Meta<typeof Tag> = {
  title: "Components/Tag",
  component: Tag,
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
  },
};

export default meta;
type Story = StoryObj<typeof Tag>;

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

export const Error: Story = {
  args: {
    variant: "error",
    children: "Blocked",
  },
};

export const Removable: Story = {
  args: {
    variant: "default",
    removable: true,
    children: "JavaScript",
  },
};

export const WithIcon: Story = {
  args: {
    variant: "success",
    icon: <span>⚛</span>,
    removable: true,
    children: "React",
  },
};

export const Small: Story = {
  args: {
    size: "sm",
    children: "Tag",
  },
};

export const Medium: Story = {
  args: {
    size: "md",
    children: "Tag",
  },
};

export const AllVariants: Story = {
  render: () => (
    <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
      <Tag variant="default">Default</Tag>
      <Tag variant="success">Success</Tag>
      <Tag variant="warning">Warning</Tag>
      <Tag variant="error">Error</Tag>
      <Tag variant="info">Info</Tag>
    </div>
  ),
};

export const Removable_List: Story = {
  render: () => {
    const [tags, setTags] = useState([
      "React",
      "JavaScript",
      "TypeScript",
      "CSS",
    ]);

    const handleRemove = (index: number) => {
      setTags(tags.filter((_, i) => i !== index));
    };

    return (
      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
        {tags.map((tag, index) => (
          <Tag
            key={index}
            removable
            onRemove={() => handleRemove(index)}
            variant="default"
          >
            {tag}
          </Tag>
        ))}
      </div>
    );
  },
};

export const With_Icons_and_Remove: Story = {
  render: () => (
    <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
      <Tag variant="success" icon={<span>✓</span>} removable>
        Approved
      </Tag>
      <Tag variant="warning" icon={<span>!</span>} removable>
        Pending
      </Tag>
      <Tag variant="error" icon={<span>✕</span>} removable>
        Rejected
      </Tag>
    </div>
  ),
};

export const FilterTags: Story = {
  render: () => (
    <div>
      <p style={{ marginBottom: "1rem" }}>Selected tags:</p>
      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
        <Tag variant="info" removable>
          Frontend
        </Tag>
        <Tag variant="info" removable>
          React
        </Tag>
        <Tag variant="info" removable>
          TypeScript
        </Tag>
      </div>
    </div>
  ),
};

export const InContext: Story = {
  render: () => (
    <div style={{ padding: "1.5rem", backgroundColor: "#f3f4f6", borderRadius: "0.5rem" }}>
      <h3 style={{ marginTop: 0 }}>Article Tags</h3>
      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
        <Tag variant="default" removable>
          React
        </Tag>
        <Tag variant="default" removable>
          TypeScript
        </Tag>
        <Tag variant="default" removable>
          Web Dev
        </Tag>
      </div>
    </div>
  ),
};
