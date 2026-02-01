/**
 * Card Storybook stories
 * Demonstrates all variants and section combinations
 */

import React from "react";
import { Meta, StoryObj } from "@storybook/react";
import Card, { CardHeader, CardBody, CardFooter } from "./Card";
import Button from "../button/Button";

const meta: Meta<typeof Card> = {
  title: "Components/Card",
  component: Card,
  parameters: {
    layout: "centered",
  },
  tags: ["autodocs"],
  argTypes: {
    shadow: {
      control: "select",
      options: ["none", "sm", "md", "lg"],
    },
    padding: {
      control: "select",
      options: ["sm", "md", "lg"],
    },
    bordered: {
      control: "boolean",
    },
    clickable: {
      control: "boolean",
    },
  },
};

export default meta;
type Story = StoryObj<typeof Card>;

export const Basic: Story = {
  args: {
    children: "Card content goes here",
  },
};

export const WithHeader: Story = {
  render: () => (
    <Card>
      <CardHeader>Card Title</CardHeader>
      <CardBody>This is the main content of the card.</CardBody>
    </Card>
  ),
};

export const WithHeaderAndFooter: Story = {
  render: () => (
    <Card>
      <CardHeader>Card Title</CardHeader>
      <CardBody>This is the main content of the card.</CardBody>
      <CardFooter>
        <Button variant="secondary" size="sm">
          Cancel
        </Button>
        <Button variant="primary" size="sm">
          Save
        </Button>
      </CardFooter>
    </Card>
  ),
};

export const ShadowVariants: Story = {
  render: () => (
    <div style={{ display: "flex", gap: "2rem", flexWrap: "wrap" }}>
      <div style={{ width: 250 }}>
        <Card shadow="none" bordered>
          <CardBody>No Shadow</CardBody>
        </Card>
      </div>
      <div style={{ width: 250 }}>
        <Card shadow="sm">
          <CardBody>Small Shadow</CardBody>
        </Card>
      </div>
      <div style={{ width: 250 }}>
        <Card shadow="md">
          <CardBody>Medium Shadow</CardBody>
        </Card>
      </div>
      <div style={{ width: 250 }}>
        <Card shadow="lg">
          <CardBody>Large Shadow</CardBody>
        </Card>
      </div>
    </div>
  ),
};

export const PaddingVariants: Story = {
  render: () => (
    <div style={{ display: "flex", gap: "2rem", flexWrap: "wrap" }}>
      <div style={{ width: 250 }}>
        <Card padding="sm">
          <CardBody>Small Padding</CardBody>
        </Card>
      </div>
      <div style={{ width: 250 }}>
        <Card padding="md">
          <CardBody>Medium Padding</CardBody>
        </Card>
      </div>
      <div style={{ width: 250 }}>
        <Card padding="lg">
          <CardBody>Large Padding</CardBody>
        </Card>
      </div>
    </div>
  ),
};

export const Bordered: Story = {
  args: {
    bordered: true,
    children: "Bordered card",
  },
};

export const Clickable: Story = {
  render: () => (
    <div style={{ width: 300 }}>
      <Card clickable onClick={() => alert("Card clicked!")}>
        <CardHeader>Clickable Card</CardHeader>
        <CardBody>Click me to see an alert</CardBody>
      </Card>
    </div>
  ),
};

export const ProductCard: Story = {
  render: () => (
    <div style={{ width: 300 }}>
      <Card>
        <CardBody>
          <div style={{ marginBottom: "1rem" }}>
            <div
              style={{
                width: "100%",
                height: 150,
                backgroundColor: "#e5e7eb",
                borderRadius: "0.375rem",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              Image
            </div>
          </div>
          <h3 style={{ margin: "0 0 0.5rem 0" }}>Product Name</h3>
          <p style={{ margin: "0 0 1rem 0", color: "#6b7280" }}>
            Product description goes here
          </p>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <span style={{ fontWeight: "600" }}>$99.99</span>
          </div>
        </CardBody>
        <CardFooter>
          <Button variant="secondary" size="sm">
            View
          </Button>
          <Button variant="primary" size="sm">
            Add to Cart
          </Button>
        </CardFooter>
      </Card>
    </div>
  ),
};

export const EmptyCard: Story = {
  render: () => (
    <div style={{ width: 300 }}>
      <Card>
        <CardBody style={{ textAlign: "center", color: "#9ca3af" }}>
          No content available
        </CardBody>
      </Card>
    </div>
  ),
};

export const BodyOnlyCard: Story = {
  render: () => (
    <div style={{ width: 300 }}>
      <Card>
        <CardBody>Simple card with just a body section</CardBody>
      </Card>
    </div>
  ),
};

export const ComplexLayout: Story = {
  render: () => (
    <div style={{ width: 400 }}>
      <Card>
        <CardHeader>Order Details</CardHeader>
        <CardBody>
          <div style={{ marginBottom: "1rem" }}>
            <p style={{ margin: "0 0 0.5rem 0", fontSize: "0.875rem", color: "#6b7280" }}>
              Order ID
            </p>
            <p style={{ margin: 0, fontWeight: "600" }}>ORD-12345</p>
          </div>
          <div style={{ marginBottom: "1rem" }}>
            <p style={{ margin: "0 0 0.5rem 0", fontSize: "0.875rem", color: "#6b7280" }}>
              Status
            </p>
            <p style={{ margin: 0, fontWeight: "600", color: "#10b981" }}>
              Delivered
            </p>
          </div>
          <div>
            <p style={{ margin: "0 0 0.5rem 0", fontSize: "0.875rem", color: "#6b7280" }}>
              Total
            </p>
            <p style={{ margin: 0, fontWeight: "600", fontSize: "1.25rem" }}>
              $299.99
            </p>
          </div>
        </CardBody>
        <CardFooter>
          <Button variant="ghost" size="sm">
            Download Invoice
          </Button>
        </CardFooter>
      </Card>
    </div>
  ),
};
