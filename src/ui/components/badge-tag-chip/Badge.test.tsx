/**
 * Badge component tests
 * Tests all variants and features
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import Badge from "./Badge";

describe("Badge", () => {
  describe("Rendering", () => {
    it("should render badge with text", () => {
      const { container } = render(<Badge>New</Badge>);
      const badge = container.querySelector(".badge");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveTextContent("New");
    });

    it("should use span element", () => {
      const { container } = render(<Badge>New</Badge>);
      const badge = container.querySelector(".badge");
      expect(badge?.tagName).toBe("SPAN");
    });
  });

  describe("Variants", () => {
    it("should render default variant", () => {
      const { container } = render(<Badge>New</Badge>);
      const badge = container.querySelector(".badge");
      expect(badge).toHaveClass("badge-default");
    });

    it("should render success variant", () => {
      const { container } = render(<Badge variant="success">Done</Badge>);
      const badge = container.querySelector(".badge");
      expect(badge).toHaveClass("badge-success");
    });

    it("should render warning variant", () => {
      const { container } = render(<Badge variant="warning">Pending</Badge>);
      const badge = container.querySelector(".badge");
      expect(badge).toHaveClass("badge-warning");
    });

    it("should render error variant", () => {
      const { container } = render(<Badge variant="error">Failed</Badge>);
      const badge = container.querySelector(".badge");
      expect(badge).toHaveClass("badge-error");
    });

    it("should render info variant", () => {
      const { container } = render(<Badge variant="info">Info</Badge>);
      const badge = container.querySelector(".badge");
      expect(badge).toHaveClass("badge-info");
    });
  });

  describe("Sizes", () => {
    it("should render small size", () => {
      const { container } = render(<Badge size="sm">New</Badge>);
      const badge = container.querySelector(".badge");
      expect(badge).toHaveClass("badge-sm");
    });

    it("should render medium size by default", () => {
      const { container } = render(<Badge>New</Badge>);
      const badge = container.querySelector(".badge");
      expect(badge).toHaveClass("badge-md");
    });
  });

  describe("Icons", () => {
    it("should render with icon", () => {
      const { container } = render(
        <Badge icon={<span data-testid="icon">✓</span>}>Complete</Badge>
      );
      const icon = screen.getByTestId("icon");
      expect(icon).toBeInTheDocument();
      expect(container.querySelector(".badge-icon")).toContainElement(icon);
    });

    it("should render icon and text separately", () => {
      const { container } = render(
        <Badge icon={<span>✓</span>}>Complete</Badge>
      );
      const iconContainer = container.querySelector(".badge-icon");
      const textContainer = container.querySelector(".badge-text");
      expect(iconContainer).toBeInTheDocument();
      expect(textContainer).toBeInTheDocument();
    });
  });

  describe("Custom className", () => {
    it("should merge custom className", () => {
      const { container } = render(
        <Badge className="custom-badge">New</Badge>
      );
      const badge = container.querySelector(".badge");
      expect(badge).toHaveClass("badge");
      expect(badge).toHaveClass("custom-badge");
    });
  });

  describe("Forward ref", () => {
    it("should forward ref", () => {
      const ref = React.createRef<HTMLSpanElement>();
      render(<Badge ref={ref}>New</Badge>);
      expect(ref.current).toBeInstanceOf(HTMLSpanElement);
    });
  });

  describe("Accessibility", () => {
    it("should be semantically correct", () => {
      const { container } = render(<Badge>New</Badge>);
      const badge = container.querySelector(".badge");
      expect(badge?.tagName).toBe("SPAN");
    });
  });
});
