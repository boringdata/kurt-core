/**
 * Badge Storybook stories
 * Demonstrates all variants and sizes
 */

import React from "react";
import { Meta, StoryObj } from "@storybook/react";
import Badge from "./Badge";

const meta: Meta<typeof Badge> = {
  title: "Components/Badge",
  component: Badge,
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
  },
};

export default meta;
type Story = StoryObj<typeof Badge>;

export const Default: Story = {
  args: {
    variant: "default",
    children: "New",
  },
};

export const Success: Story = {
  args: {
    variant: "success",
    children: "Complete",
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
    children: "Failed",
  },
};

export const Info: Story = {
  args: {
    variant: "info",
    children: "Update",
  },
};

export const Small: Story = {
  args: {
    size: "sm",
    children: "New",
  },
};

export const Medium: Story = {
  args: {
    size: "md",
    children: "New",
  },
};

export const WithIcon: Story = {
  args: {
    variant: "success",
    icon: <span>✓</span>,
    children: "Done",
  },
};

export const AllVariants: Story = {
  render: () => (
    <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
      <Badge variant="default">Default</Badge>
      <Badge variant="success">Success</Badge>
      <Badge variant="warning">Warning</Badge>
      <Badge variant="error">Error</Badge>
      <Badge variant="info">Info</Badge>
    </div>
  ),
};

export const AllSizes: Story = {
  render: () => (
    <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
      <Badge size="sm">Small</Badge>
      <Badge size="md">Medium</Badge>
    </div>
  ),
};

export const WithIcons: Story = {
  render: () => (
    <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
      <Badge variant="success" icon={<span>✓</span>}>
        Complete
      </Badge>
      <Badge variant="error" icon={<span>✕</span>}>
        Failed
      </Badge>
      <Badge variant="warning" icon={<span>!</span>}>
        Warning
      </Badge>
      <Badge variant="info" icon={<span>ℹ</span>}>
        Info
      </Badge>
    </div>
  ),
};

export const InContext: Story = {
  render: () => (
    <div
      style={{
        padding: "1rem",
        borderRadius: "0.5rem",
        backgroundColor: "#f3f4f6",
      }}
    >
      <h3>Product Status</h3>
      <p>
        Current Status: <Badge variant="success">In Stock</Badge>
      </p>
      <p>
        Rating: <Badge variant="info">4.5 stars</Badge>
      </p>
      <p>
        Availability: <Badge variant="warning">Limited</Badge>
      </p>
    </div>
  ),
};
