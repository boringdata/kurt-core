/**
 * Pagination Component - Navigate through pages of data
 *
 * WCAG 2.1 AA Compliant:
 * - Proper button semantics
 * - Keyboard navigation support
 * - Current page indication
 * - Accessible labels
 */

import React from 'react';

interface PaginationProps {
  /** Current page number (1-indexed) */
  currentPage: number;
  /** Total number of pages */
  totalPages: number;
  /** Callback when page changes */
  onPageChange: (page: number) => void;
  /** Number of page numbers to show on each side of current page */
  siblingsCount?: number;
  /** Show first/last page buttons */
  showFirstLast?: boolean;
  /** Optional class name */
  className?: string;
}

/**
 * Generate array of page numbers for pagination
 */
function generatePageNumbers(
  currentPage: number,
  totalPages: number,
  siblingsCount: number = 1
): (number | string)[] {
  const pages: (number | string)[] = [];

  // Add first page
  pages.push(1);

  // Calculate start and end of middle range
  const leftSiblingIndex = Math.max(currentPage - siblingsCount, 2);
  const rightSiblingIndex = Math.min(currentPage + siblingsCount, totalPages - 1);

  // Add ellipsis if needed
  if (leftSiblingIndex > 2) {
    pages.push('...');
  }

  // Add middle pages
  for (let i = leftSiblingIndex; i <= rightSiblingIndex; i++) {
    pages.push(i);
  }

  // Add ellipsis if needed
  if (rightSiblingIndex < totalPages - 1) {
    pages.push('...');
  }

  // Add last page
  if (totalPages > 1) {
    pages.push(totalPages);
  }

  return pages;
}

/**
 * Pagination Component
 * Provides navigation controls for paginated data
 *
 * Usage:
 * ```tsx
 * <Pagination
 *   currentPage={page}
 *   totalPages={totalPages}
 *   onPageChange={setPage}
 * />
 * ```
 */
export const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  onPageChange,
  siblingsCount = 1,
  showFirstLast = true,
  className = '',
}) => {
  const pageNumbers = generatePageNumbers(currentPage, totalPages, siblingsCount);
  const hasPrevious = currentPage > 1;
  const hasNext = currentPage < totalPages;

  const handlePageClick = (page: number) => {
    if (page !== currentPage && page >= 1 && page <= totalPages) {
      onPageChange(page);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent, page: number) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handlePageClick(page);
    }
  };

  return (
    <nav
      className={`flex items-center justify-center gap-2 ${className}`}
      aria-label="Pagination navigation"
    >
      {/* Previous button */}
      <button
        onClick={() => handlePageClick(currentPage - 1)}
        disabled={!hasPrevious}
        className={`px-3 py-2 rounded border transition-colors ${
          hasPrevious
            ? 'border-gray-300 bg-white hover:bg-gray-50 cursor-pointer'
            : 'border-gray-200 bg-gray-50 text-gray-400 cursor-not-allowed'
        }`}
        aria-label="Previous page"
        aria-disabled={!hasPrevious}
      >
        Previous
      </button>

      {/* Page numbers */}
      <div className="flex gap-1">
        {pageNumbers.map((page, index) => {
          if (page === '...') {
            return (
              <span
                key={`ellipsis-${index}`}
                className="px-2 py-2 text-gray-500"
                aria-hidden="true"
              >
                ...
              </span>
            );
          }

          const pageNum = page as number;
          const isCurrentPage = pageNum === currentPage;

          return (
            <button
              key={pageNum}
              onClick={() => handlePageClick(pageNum)}
              onKeyDown={(e) => handleKeyDown(e, pageNum)}
              className={`px-3 py-2 rounded border transition-colors ${
                isCurrentPage
                  ? 'border-blue-500 bg-blue-50 text-blue-600 font-medium'
                  : 'border-gray-300 bg-white hover:bg-gray-50'
              }`}
              aria-current={isCurrentPage ? 'page' : undefined}
              aria-label={`Page ${pageNum}`}
            >
              {pageNum}
            </button>
          );
        })}
      </div>

      {/* Next button */}
      <button
        onClick={() => handlePageClick(currentPage + 1)}
        disabled={!hasNext}
        className={`px-3 py-2 rounded border transition-colors ${
          hasNext
            ? 'border-gray-300 bg-white hover:bg-gray-50 cursor-pointer'
            : 'border-gray-200 bg-gray-50 text-gray-400 cursor-not-allowed'
        }`}
        aria-label="Next page"
        aria-disabled={!hasNext}
      >
        Next
      </button>

      {/* Page info */}
      <span className="ml-4 text-sm text-gray-600" aria-live="polite">
        Page {currentPage} of {totalPages}
      </span>
    </nav>
  );
};

Pagination.displayName = 'Pagination';

export default Pagination;
