/**
 * Custom render utilities for testing React components
 */
import React, { ReactElement, ReactNode } from 'react'
import { render, RenderOptions, RenderResult } from '@testing-library/react'

// Wrapper that can provide context providers
interface WrapperProps {
  children: ReactNode
}

const DefaultWrapper: React.FC<WrapperProps> = ({ children }) => {
  return <>{children}</>
}

// Custom render function that includes any necessary providers
export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'> & { wrapper?: React.ComponentType<WrapperProps> }
): RenderResult {
  const Wrapper = options?.wrapper || DefaultWrapper
  return render(ui, { wrapper: Wrapper, ...options })
}

// Re-export everything from testing library
export * from '@testing-library/react'
export { renderWithProviders as render }
