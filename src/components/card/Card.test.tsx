/**
 * Card component tests
 * Tests all variants, sections, and accessibility
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import Card, { CardHeader, CardBody, CardFooter } from "./Card";

describe("Card", () => {
  describe("Rendering", () => {
    it("should render card container", () => {
      const { container } = render(<Card>Content</Card>);
      const card = container.querySelector(".card");
      expect(card).toBeInTheDocument();
      expect(card).toHaveTextContent("Content");
    });

    it("should render with article role by default", () => {
      const { container } = render(<Card>Content</Card>);
      const card = container.querySelector(".card");
      expect(card).toHaveAttribute("role", "article");
    });

    it("should render with button role when clickable", () => {
      const { container } = render(<Card clickable>Content</Card>);
      const card = container.querySelector(".card");
      expect(card).toHaveAttribute("role", "button");
    });
  });

  describe("Shadow variants", () => {
    it("should render with no shadow by default (md)", () => {
      const { container } = render(<Card>Content</Card>);
      const card = container.querySelector(".card");
      expect(card).toHaveClass("card-shadow-md");
    });

    it("should render with small shadow", () => {
      const { container } = render(<Card shadow="sm">Content</Card>);
      const card = container.querySelector(".card");
      expect(card).toHaveClass("card-shadow-sm");
    });

    it("should render with large shadow", () => {
      const { container } = render(<Card shadow="lg">Content</Card>);
      const card = container.querySelector(".card");
      expect(card).toHaveClass("card-shadow-lg");
    });

    it("should render with no shadow variant", () => {
      const { container } = render(<Card shadow="none">Content</Card>);
      const card = container.querySelector(".card");
      expect(card).toHaveClass("card-shadow-none");
    });
  });

  describe("Bordered variant", () => {
    it("should render with border when bordered is true", () => {
      const { container } = render(<Card bordered>Content</Card>);
      const card = container.querySelector(".card");
      expect(card).toHaveClass("card-bordered");
    });

    it("should not have border by default", () => {
      const { container } = render(<Card>Content</Card>);
      const card = container.querySelector(".card");
      expect(card).not.toHaveClass("card-bordered");
    });
  });

  describe("Padding variants", () => {
    it("should render with medium padding by default", () => {
      const { container } = render(<Card>Content</Card>);
      const card = container.querySelector(".card");
      expect(card).toHaveClass("card-padding-md");
    });

    it("should render with small padding", () => {
      const { container } = render(<Card padding="sm">Content</Card>);
      const card = container.querySelector(".card");
      expect(card).toHaveClass("card-padding-sm");
    });

    it("should render with large padding", () => {
      const { container } = render(<Card padding="lg">Content</Card>);
      const card = container.querySelector(".card");
      expect(card).toHaveClass("card-padding-lg");
    });
  });

  describe("Clickable variant", () => {
    it("should have tabIndex when clickable", () => {
      const { container } = render(<Card clickable>Content</Card>);
      const card = container.querySelector(".card");
      expect(card).toHaveAttribute("tabIndex", "0");
    });

    it("should not have tabIndex when not clickable", () => {
      const { container } = render(<Card>Content</Card>);
      const card = container.querySelector(".card");
      expect(card).not.toHaveAttribute("tabIndex");
    });

    it("should be focusable when clickable", () => {
      const { container } = render(<Card clickable>Content</Card>);
      const card = container.querySelector(".card") as HTMLElement;
      card.focus();
      expect(document.activeElement).toBe(card);
    });
  });

  describe("CardHeader", () => {
    it("should render header section", () => {
      const { container } = render(<CardHeader>Header</CardHeader>);
      const header = container.querySelector(".card-header");
      expect(header).toBeInTheDocument();
      expect(header).toHaveTextContent("Header");
    });

    it("should apply custom className", () => {
      const { container } = render(
        <CardHeader className="custom-header">Header</CardHeader>
      );
      const header = container.querySelector(".card-header");
      expect(header).toHaveClass("custom-header");
      expect(header).toHaveClass("card-header");
    });
  });

  describe("CardBody", () => {
    it("should render body section", () => {
      const { container } = render(<CardBody>Body content</CardBody>);
      const body = container.querySelector(".card-body");
      expect(body).toBeInTheDocument();
      expect(body).toHaveTextContent("Body content");
    });

    it("should apply custom className", () => {
      const { container } = render(
        <CardBody className="custom-body">Body</CardBody>
      );
      const body = container.querySelector(".card-body");
      expect(body).toHaveClass("custom-body");
      expect(body).toHaveClass("card-body");
    });
  });

  describe("CardFooter", () => {
    it("should render footer section", () => {
      const { container } = render(<CardFooter>Footer</CardFooter>);
      const footer = container.querySelector(".card-footer");
      expect(footer).toBeInTheDocument();
      expect(footer).toHaveTextContent("Footer");
    });

    it("should apply custom className", () => {
      const { container } = render(
        <CardFooter className="custom-footer">Footer</CardFooter>
      );
      const footer = container.querySelector(".card-footer");
      expect(footer).toHaveClass("custom-footer");
      expect(footer).toHaveClass("card-footer");
    });
  });

  describe("Composed card", () => {
    it("should render with all sections", () => {
      const { container } = render(
        <Card>
          <CardHeader>Title</CardHeader>
          <CardBody>Content</CardBody>
          <CardFooter>Actions</CardFooter>
        </Card>
      );
      expect(container.querySelector(".card-header")).toHaveTextContent(
        "Title"
      );
      expect(container.querySelector(".card-body")).toHaveTextContent(
        "Content"
      );
      expect(container.querySelector(".card-footer")).toHaveTextContent(
        "Actions"
      );
    });

    it("should handle optional sections", () => {
      const { container } = render(
        <Card>
          <CardBody>Just content</CardBody>
        </Card>
      );
      expect(container.querySelector(".card-body")).toBeInTheDocument();
      expect(container.querySelector(".card-header")).not.toBeInTheDocument();
      expect(container.querySelector(".card-footer")).not.toBeInTheDocument();
    });
  });

  describe("Custom className", () => {
    it("should merge custom className on Card", () => {
      const { container } = render(
        <Card className="custom-card">Content</Card>
      );
      const card = container.querySelector(".card");
      expect(card).toHaveClass("card");
      expect(card).toHaveClass("custom-card");
    });
  });

  describe("Forward ref", () => {
    it("should forward ref on Card", () => {
      const ref = React.createRef<HTMLDivElement>();
      render(<Card ref={ref}>Content</Card>);
      expect(ref.current).toBeInstanceOf(HTMLDivElement);
    });

    it("should forward ref on CardHeader", () => {
      const ref = React.createRef<HTMLDivElement>();
      render(<CardHeader ref={ref}>Header</CardHeader>);
      expect(ref.current).toBeInstanceOf(HTMLDivElement);
    });

    it("should forward ref on CardBody", () => {
      const ref = React.createRef<HTMLDivElement>();
      render(<CardBody ref={ref}>Body</CardBody>);
      expect(ref.current).toBeInstanceOf(HTMLDivElement);
    });

    it("should forward ref on CardFooter", () => {
      const ref = React.createRef<HTMLDivElement>();
      render(<CardFooter ref={ref}>Footer</CardFooter>);
      expect(ref.current).toBeInstanceOf(HTMLDivElement);
    });
  });

  describe("Accessibility", () => {
    it("should be keyboard accessible when clickable", () => {
      const { container } = render(<Card clickable>Content</Card>);
      const card = container.querySelector(".card") as HTMLElement;
      card.focus();
      expect(document.activeElement).toBe(card);
    });

    it("should announce as article by default", () => {
      const { container } = render(<Card>Content</Card>);
      const card = container.querySelector(".card");
      expect(card).toHaveAttribute("role", "article");
    });
  });
});
