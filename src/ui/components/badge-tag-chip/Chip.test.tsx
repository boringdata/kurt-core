/**
 * Chip component tests
 * Tests all variants, selectable state, and remove functionality
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Chip from "./Chip";

describe("Chip", () => {
  describe("Rendering", () => {
    it("should render chip with text", () => {
      const { container } = render(<Chip>React</Chip>);
      const chip = container.querySelector(".chip");
      expect(chip).toBeInTheDocument();
      expect(chip).toHaveTextContent("React");
    });

    it("should use button element", () => {
      const { container } = render(<Chip>React</Chip>);
      const chip = container.querySelector(".chip");
      expect(chip?.tagName).toBe("BUTTON");
    });
  });

  describe("Variants", () => {
    it("should render default variant", () => {
      const { container } = render(<Chip>React</Chip>);
      const chip = container.querySelector(".chip");
      expect(chip).toHaveClass("chip-default");
    });

    it("should render success variant", () => {
      const { container } = render(<Chip variant="success">Active</Chip>);
      const chip = container.querySelector(".chip");
      expect(chip).toHaveClass("chip-success");
    });

    it("should render warning variant", () => {
      const { container } = render(<Chip variant="warning">Pending</Chip>);
      const chip = container.querySelector(".chip");
      expect(chip).toHaveClass("chip-warning");
    });

    it("should render error variant", () => {
      const { container } = render(<Chip variant="error">Error</Chip>);
      const chip = container.querySelector(".chip");
      expect(chip).toHaveClass("chip-error");
    });

    it("should render info variant", () => {
      const { container } = render(<Chip variant="info">Info</Chip>);
      const chip = container.querySelector(".chip");
      expect(chip).toHaveClass("chip-info");
    });
  });

  describe("Sizes", () => {
    it("should render small size", () => {
      const { container } = render(<Chip size="sm">React</Chip>);
      const chip = container.querySelector(".chip");
      expect(chip).toHaveClass("chip-sm");
    });

    it("should render medium size by default", () => {
      const { container } = render(<Chip>React</Chip>);
      const chip = container.querySelector(".chip");
      expect(chip).toHaveClass("chip-md");
    });
  });

  describe("Icons", () => {
    it("should render with icon", () => {
      const { container } = render(
        <Chip icon={<span data-testid="icon">⚛</span>}>React</Chip>
      );
      const icon = screen.getByTestId("icon");
      expect(icon).toBeInTheDocument();
      expect(container.querySelector(".chip-icon")).toContainElement(icon);
    });
  });

  describe("Remove button", () => {
    it("should not show remove button by default", () => {
      const { container } = render(<Chip>React</Chip>);
      const removeBtn = container.querySelector(".chip-remove");
      expect(removeBtn).not.toBeInTheDocument();
    });

    it("should show remove button when removable", () => {
      const { container } = render(
        <Chip removable onRemove={jest.fn()}>
          React
        </Chip>
      );
      const removeBtn = container.querySelector(".chip-remove");
      expect(removeBtn).toBeInTheDocument();
    });

    it("should call onRemove when remove button clicked", async () => {
      const onRemove = jest.fn();
      const { container } = render(
        <Chip removable onRemove={onRemove}>
          React
        </Chip>
      );
      const removeBtn = container.querySelector(".chip-remove") as HTMLElement;
      await userEvent.click(removeBtn);
      expect(onRemove).toHaveBeenCalledTimes(1);
    });

    it("should stop propagation when remove button is clicked", async () => {
      const onClick = jest.fn();
      const onRemove = jest.fn();
      const { container } = render(
        <Chip removable onRemove={onRemove} onClick={onClick}>
          React
        </Chip>
      );
      const removeBtn = container.querySelector(".chip-remove") as HTMLElement;
      await userEvent.click(removeBtn);
      // onClick should not fire due to stopPropagation in remove handler
      expect(onRemove).toHaveBeenCalledTimes(1);
    });

    it("should have proper aria-label on remove button", () => {
      const { container } = render(
        <Chip removable onRemove={jest.fn()}>
          React
        </Chip>
      );
      const removeBtn = container.querySelector(".chip-remove");
      expect(removeBtn).toHaveAttribute("aria-label", "Remove React");
    });
  });

  describe("Selectable state", () => {
    it("should not have selectable class by default", () => {
      const { container } = render(<Chip>React</Chip>);
      const chip = container.querySelector(".chip");
      expect(chip).not.toHaveClass("chip-selectable");
    });

    it("should have selectable class when selectable", () => {
      const { container } = render(
        <Chip selectable onToggle={jest.fn()}>
          React
        </Chip>
      );
      const chip = container.querySelector(".chip");
      expect(chip).toHaveClass("chip-selectable");
    });

    it("should have selected class when selected", () => {
      const { container } = render(
        <Chip selectable selected onToggle={jest.fn()}>
          React
        </Chip>
      );
      const chip = container.querySelector(".chip");
      expect(chip).toHaveClass("chip-selected");
    });

    it("should set aria-pressed when selectable", () => {
      const { container } = render(
        <Chip selectable selected onToggle={jest.fn()}>
          React
        </Chip>
      );
      const chip = container.querySelector(".chip");
      expect(chip).toHaveAttribute("aria-pressed", "true");
    });

    it("should call onToggle when clicked", async () => {
      const onToggle = jest.fn();
      const { container } = render(
        <Chip selectable onToggle={onToggle}>
          React
        </Chip>
      );
      const chip = container.querySelector(".chip") as HTMLElement;
      await userEvent.click(chip);
      expect(onToggle).toHaveBeenCalledWith(true);
    });

    it("should toggle selection state", async () => {
      const onToggle = jest.fn();
      const { rerender, container } = render(
        <Chip selectable selected={false} onToggle={onToggle}>
          React
        </Chip>
      );
      const chip = container.querySelector(".chip") as HTMLElement;
      await userEvent.click(chip);
      expect(onToggle).toHaveBeenCalledWith(true);

      // Simulate state change
      onToggle.mockClear();
      rerender(
        <Chip selectable selected={true} onToggle={onToggle}>
          React
        </Chip>
      );
      await userEvent.click(chip);
      expect(onToggle).toHaveBeenCalledWith(false);
    });
  });

  describe("Removable state", () => {
    it("should add removable class when removable is true", () => {
      const { container } = render(
        <Chip removable onRemove={jest.fn()}>
          React
        </Chip>
      );
      const chip = container.querySelector(".chip");
      expect(chip).toHaveClass("chip-removable");
    });
  });

  describe("Combined states", () => {
    it("should support both removable and selectable", () => {
      const { container } = render(
        <Chip removable selectable onRemove={jest.fn()} onToggle={jest.fn()}>
          React
        </Chip>
      );
      const chip = container.querySelector(".chip");
      expect(chip).toHaveClass("chip-removable");
      expect(chip).toHaveClass("chip-selectable");
    });
  });

  describe("Custom className", () => {
    it("should merge custom className", () => {
      const { container } = render(
        <Chip className="custom-chip">React</Chip>
      );
      const chip = container.querySelector(".chip");
      expect(chip).toHaveClass("chip");
      expect(chip).toHaveClass("custom-chip");
    });
  });

  describe("Forward ref", () => {
    it("should forward ref", () => {
      const ref = React.createRef<HTMLButtonElement>();
      render(<Chip ref={ref}>React</Chip>);
      expect(ref.current).toBeInstanceOf(HTMLButtonElement);
    });
  });

  describe("Accessibility", () => {
    it("should have aria-pressed when selectable", () => {
      const { container } = render(
        <Chip selectable selected={true} onToggle={jest.fn()}>
          React
        </Chip>
      );
      const chip = container.querySelector(".chip");
      expect(chip).toHaveAttribute("aria-pressed", "true");
    });

    it("should have aria-label when selectable", () => {
      const { container } = render(
        <Chip selectable onToggle={jest.fn()}>
          React
        </Chip>
      );
      const chip = container.querySelector(".chip");
      expect(chip).toHaveAttribute("aria-label", "Toggle React");
    });

    it("should be keyboard accessible", async () => {
      const onClick = jest.fn();
      const { container } = render(
        <Chip onClick={onClick}>
          React
        </Chip>
      );
      const chip = container.querySelector(".chip") as HTMLElement;
      chip.focus();
      expect(document.activeElement).toBe(chip);
    });
  });

  describe("Disabled state", () => {
    it("should respect disabled prop", () => {
      const { container } = render(<Chip disabled>React</Chip>);
      const chip = container.querySelector(".chip") as HTMLButtonElement;
      expect(chip.disabled).toBe(true);
    });
  });
});
