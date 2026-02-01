/**
 * Tests for Pagination component
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import Pagination from '../Pagination';

describe('Pagination', () => {
  it('renders pagination with correct page numbers', () => {
    const mockOnChange = jest.fn();
    render(
      <Pagination
        currentPage={1}
        totalPages={5}
        onPageChange={mockOnChange}
      />
    );

    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('disables previous button on first page', () => {
    const mockOnChange = jest.fn();
    render(
      <Pagination
        currentPage={1}
        totalPages={5}
        onPageChange={mockOnChange}
      />
    );

    const prevButton = screen.getByLabelText('Previous page');
    expect(prevButton).toBeDisabled();
  });

  it('disables next button on last page', () => {
    const mockOnChange = jest.fn();
    render(
      <Pagination
        currentPage={5}
        totalPages={5}
        onPageChange={mockOnChange}
      />
    );

    const nextButton = screen.getByLabelText('Next page');
    expect(nextButton).toBeDisabled();
  });

  it('calls onPageChange when page number is clicked', () => {
    const mockOnChange = jest.fn();
    render(
      <Pagination
        currentPage={1}
        totalPages={5}
        onPageChange={mockOnChange}
      />
    );

    fireEvent.click(screen.getByLabelText('Page 3'));
    expect(mockOnChange).toHaveBeenCalledWith(3);
  });

  it('highlights current page', () => {
    const mockOnChange = jest.fn();
    render(
      <Pagination
        currentPage={2}
        totalPages={5}
        onPageChange={mockOnChange}
      />
    );

    const currentPage = screen.getByLabelText('Page 2');
    expect(currentPage).toHaveAttribute('aria-current', 'page');
  });

  it('displays page info', () => {
    const mockOnChange = jest.fn();
    render(
      <Pagination
        currentPage={2}
        totalPages={5}
        onPageChange={mockOnChange}
      />
    );

    expect(screen.getByText('Page 2 of 5')).toBeInTheDocument();
  });
});
