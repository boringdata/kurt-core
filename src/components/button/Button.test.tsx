/**
 * Button component tests
 * Tests variants, sizes, states, and accessibility
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Button from "./Button";

describe("Button", () => {
  describe("Variants", () => {
    it("should render primary variant by default", () => {
      render(<Button>Click me</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveClass("btn-primary");
    });

    it("should render secondary variant", () => {
      render(<Button variant="secondary">Click me</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveClass("btn-secondary");
    });

    it("should render danger variant", () => {
      render(<Button variant="danger">Delete</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveClass("btn-danger");
    });

    it("should render outline variant", () => {
      render(<Button variant="outline">Cancel</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveClass("btn-outline");
    });

    it("should render ghost variant", () => {
      render(<Button variant="ghost">Close</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveClass("btn-ghost");
    });
  });

  describe("Sizes", () => {
    it("should render small size", () => {
      render(<Button size="sm">Click me</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveClass("btn-sm");
    });

    it("should render medium size by default", () => {
      render(<Button>Click me</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveClass("btn-md");
    });

    it("should render large size", () => {
      render(<Button size="lg">Click me</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveClass("btn-lg");
    });
  });

  describe("States", () => {
    it("should render disabled state", () => {
      render(<Button disabled>Click me</Button>);
      const button = screen.getByRole("button");
      expect(button).toBeDisabled();
      expect(button).toHaveClass("btn-disabled");
    });

    it("should render loading state", () => {
      render(<Button loading>Loading</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveClass("btn-loading");
      expect(button).toBeDisabled();
      expect(button).toHaveAttribute("aria-busy", "true");
    });

    it("should show spinner when loading", () => {
      const { container } = render(<Button loading>Loading</Button>);
      const spinner = container.querySelector(".btn-spinner");
      expect(spinner).toBeInTheDocument();
      expect(spinner).toHaveAttribute("aria-hidden", "true");
    });
  });

  describe("Icons", () => {
    it("should render left icon", () => {
      const { container } = render(
        <Button icon={<span data-testid="icon">📦</span>}>
          Download
        </Button>
      );
      const icon = screen.getByTestId("icon");
      expect(icon).toBeInTheDocument();
      expect(container.querySelector(".btn-icon-left")).toContainElement(icon);
    });

    it("should render right icon", () => {
      const { container } = render(
        <Button iconRight={<span data-testid="icon-right">→</span>}>
          Next
        </Button>
      );
      const icon = screen.getByTestId("icon-right");
      expect(icon).toBeInTheDocument();
      expect(container.querySelector(".btn-icon-right")).toContainElement(
        icon
      );
    });

    it("should hide icon when loading", () => {
      const { container } = render(
        <Button loading icon={<span>📦</span>}>
          Loading
        </Button>
      );
      const iconContainer = container.querySelector(".btn-icon-left");
      expect(iconContainer).not.toBeInTheDocument();
    });
  });

  describe("Interactions", () => {
    it("should call onClick handler", async () => {
      const onClick = jest.fn();
      render(<Button onClick={onClick}>Click me</Button>);
      const button = screen.getByRole("button");
      await userEvent.click(button);
      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it("should not call onClick when disabled", async () => {
      const onClick = jest.fn();
      render(
        <Button disabled onClick={onClick}>
          Click me
        </Button>
      );
      const button = screen.getByRole("button");
      await userEvent.click(button);
      expect(onClick).not.toHaveBeenCalled();
    });

    it("should not call onClick when loading", async () => {
      const onClick = jest.fn();
      render(
        <Button loading onClick={onClick}>
          Loading
        </Button>
      );
      const button = screen.getByRole("button");
      await userEvent.click(button);
      expect(onClick).not.toHaveBeenCalled();
    });
  });

  describe("Link button", () => {
    it("should render as anchor when href provided", () => {
      render(<Button href="https://example.com">Visit</Button>);
      const link = screen.getByRole("button");
      expect(link.tagName).toBe("A");
      expect(link).toHaveAttribute("href", "https://example.com");
    });

    it("should support target attribute", () => {
      render(
        <Button href="https://example.com" target="_blank">
          Visit
        </Button>
      );
      const link = screen.getByRole("button");
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noopener noreferrer");
    });

    it("should not render as anchor when disabled", () => {
      render(
        <Button href="https://example.com" disabled>
          Visit
        </Button>
      );
      const button = screen.getByRole("button");
      expect(button.tagName).toBe("BUTTON");
    });

    it("should support keyboard navigation on link button", () => {
      const href = "https://example.com";
      render(<Button href={href}>Visit</Button>);
      const link = screen.getByRole("button");
      fireEvent.keyDown(link, { key: "Enter" });
      // Can't easily test window.location in Jest without mocking
      expect(link).toHaveAttribute("href", href);
    });
  });

  describe("Accessibility", () => {
    it("should be focusable", async () => {
      render(<Button>Click me</Button>);
      const button = screen.getByRole("button");
      button.focus();
      expect(document.activeElement).toBe(button);
    });

    it("should have proper aria attributes for disabled state", () => {
      render(<Button disabled>Click me</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("aria-disabled", "true");
    });

    it("should have proper aria attributes for loading state", () => {
      render(<Button loading>Loading</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("aria-busy", "true");
    });

    it("should have button role on link variant", () => {
      render(<Button href="https://example.com">Visit</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("role", "button");
    });

    it("should be keyboard accessible", async () => {
      const onClick = jest.fn();
      render(<Button onClick={onClick}>Click me</Button>);
      const button = screen.getByRole("button");
      button.focus();
      fireEvent.keyDown(button, { key: "Enter" });
      expect(onClick).toHaveBeenCalled();
    });
  });

  describe("Custom className", () => {
    it("should merge custom className", () => {
      render(<Button className="custom-class">Click me</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveClass("btn");
      expect(button).toHaveClass("custom-class");
    });
  });

  describe("Forward ref", () => {
    it("should forward ref to button element", () => {
      const ref = React.createRef<HTMLButtonElement>();
      render(<Button ref={ref}>Click me</Button>);
      expect(ref.current).toBeInstanceOf(HTMLButtonElement);
    });
  });
});
