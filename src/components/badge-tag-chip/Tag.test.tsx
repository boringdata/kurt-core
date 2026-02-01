/**
 * Tag component tests
 * Tests all variants, remove functionality, and accessibility
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Tag from "./Tag";

describe("Tag", () => {
  describe("Rendering", () => {
    it("should render tag with text", () => {
      const { container } = render(<Tag>React</Tag>);
      const tag = container.querySelector(".tag");
      expect(tag).toBeInTheDocument();
      expect(tag).toHaveTextContent("React");
    });

    it("should have group role", () => {
      const { container } = render(<Tag>React</Tag>);
      const tag = container.querySelector(".tag");
      expect(tag).toHaveAttribute("role", "group");
    });
  });

  describe("Variants", () => {
    it("should render default variant", () => {
      const { container } = render(<Tag>React</Tag>);
      const tag = container.querySelector(".tag");
      expect(tag).toHaveClass("tag-default");
    });

    it("should render success variant", () => {
      const { container } = render(<Tag variant="success">Active</Tag>);
      const tag = container.querySelector(".tag");
      expect(tag).toHaveClass("tag-success");
    });

    it("should render error variant", () => {
      const { container } = render(<Tag variant="error">Blocked</Tag>);
      const tag = container.querySelector(".tag");
      expect(tag).toHaveClass("tag-error");
    });
  });

  describe("Sizes", () => {
    it("should render small size", () => {
      const { container } = render(<Tag size="sm">React</Tag>);
      const tag = container.querySelector(".tag");
      expect(tag).toHaveClass("tag-sm");
    });

    it("should render medium size by default", () => {
      const { container } = render(<Tag>React</Tag>);
      const tag = container.querySelector(".tag");
      expect(tag).toHaveClass("tag-md");
    });
  });

  describe("Icons", () => {
    it("should render with icon", () => {
      const { container } = render(
        <Tag icon={<span data-testid="icon">⚛</span>}>React</Tag>
      );
      const icon = screen.getByTestId("icon");
      expect(icon).toBeInTheDocument();
      expect(container.querySelector(".tag-icon")).toContainElement(icon);
    });
  });

  describe("Remove button", () => {
    it("should not show remove button by default", () => {
      const { container } = render(<Tag>React</Tag>);
      const removeBtn = container.querySelector(".tag-remove");
      expect(removeBtn).not.toBeInTheDocument();
    });

    it("should show remove button when removable", () => {
      const { container } = render(
        <Tag removable onRemove={jest.fn()}>
          React
        </Tag>
      );
      const removeBtn = container.querySelector(".tag-remove");
      expect(removeBtn).toBeInTheDocument();
    });

    it("should call onRemove when remove button clicked", async () => {
      const onRemove = jest.fn();
      const { container } = render(
        <Tag removable onRemove={onRemove}>
          React
        </Tag>
      );
      const removeBtn = container.querySelector(".tag-remove") as HTMLElement;
      await userEvent.click(removeBtn);
      expect(onRemove).toHaveBeenCalledTimes(1);
    });

    it("should have proper aria-label on remove button", () => {
      const { container } = render(
        <Tag removable onRemove={jest.fn()}>
          React
        </Tag>
      );
      const removeBtn = container.querySelector(".tag-remove");
      expect(removeBtn).toHaveAttribute("aria-label", "Remove React");
    });

    it("should have hidden SVG for accessibility", () => {
      const { container } = render(
        <Tag removable onRemove={jest.fn()}>
          React
        </Tag>
      );
      const svg = container.querySelector(".tag-remove svg");
      expect(svg).toHaveAttribute("aria-hidden", "true");
    });
  });

  describe("Removable state", () => {
    it("should add removable class when removable is true", () => {
      const { container } = render(
        <Tag removable onRemove={jest.fn()}>
          React
        </Tag>
      );
      const tag = container.querySelector(".tag");
      expect(tag).toHaveClass("tag-removable");
    });
  });

  describe("Custom className", () => {
    it("should merge custom className", () => {
      const { container } = render(
        <Tag className="custom-tag">React</Tag>
      );
      const tag = container.querySelector(".tag");
      expect(tag).toHaveClass("tag");
      expect(tag).toHaveClass("custom-tag");
    });
  });

  describe("Forward ref", () => {
    it("should forward ref", () => {
      const ref = React.createRef<HTMLDivElement>();
      render(<Tag ref={ref}>React</Tag>);
      expect(ref.current).toBeInstanceOf(HTMLDivElement);
    });
  });

  describe("Accessibility", () => {
    it("should have group role for semantic structure", () => {
      const { container } = render(<Tag>React</Tag>);
      const tag = container.querySelector(".tag");
      expect(tag).toHaveAttribute("role", "group");
    });
  });
});
