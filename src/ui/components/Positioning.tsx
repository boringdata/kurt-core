/**
 * Positioning Utilities - Handle floating element positioning
 * Used for tooltips, popovers, dropdowns, etc.
 *
 * WCAG 2.1 AA Compliant:
 * - Ensures positioned elements don't go off-screen
 * - Maintains visibility
 */

export type Placement =
  | 'top'
  | 'top-start'
  | 'top-end'
  | 'bottom'
  | 'bottom-start'
  | 'bottom-end'
  | 'left'
  | 'left-start'
  | 'left-end'
  | 'right'
  | 'right-start'
  | 'right-end';

export interface Position {
  top: number;
  left: number;
}

export interface PopperOptions {
  placement?: Placement;
  offset?: [number, number]; // [mainAxis, crossAxis]
  padding?: number;
}

/**
 * Calculate position for a floating element relative to a reference element
 * @param referenceElement The element to position relative to
 * @param floatingElement The element being positioned
 * @param options Positioning options
 * @returns Position object with top and left values
 */
export function calculatePosition(
  referenceElement: HTMLElement,
  floatingElement: HTMLElement,
  options: PopperOptions = {}
): Position {
  const {
    placement = 'bottom',
    offset = [0, 0],
    padding = 8,
  } = options;

  const [mainOffset, crossOffset] = offset;
  const refRect = referenceElement.getBoundingClientRect();
  const floatRect = floatingElement.getBoundingClientRect();
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;

  let top = 0;
  let left = 0;

  // Calculate initial position based on placement
  switch (placement) {
    case 'top':
      top = refRect.top - floatRect.height - mainOffset;
      left = refRect.left + (refRect.width - floatRect.width) / 2 + crossOffset;
      break;

    case 'top-start':
      top = refRect.top - floatRect.height - mainOffset;
      left = refRect.left + crossOffset;
      break;

    case 'top-end':
      top = refRect.top - floatRect.height - mainOffset;
      left = refRect.right - floatRect.width + crossOffset;
      break;

    case 'bottom':
      top = refRect.bottom + mainOffset;
      left = refRect.left + (refRect.width - floatRect.width) / 2 + crossOffset;
      break;

    case 'bottom-start':
      top = refRect.bottom + mainOffset;
      left = refRect.left + crossOffset;
      break;

    case 'bottom-end':
      top = refRect.bottom + mainOffset;
      left = refRect.right - floatRect.width + crossOffset;
      break;

    case 'left':
      top = refRect.top + (refRect.height - floatRect.height) / 2 + crossOffset;
      left = refRect.left - floatRect.width - mainOffset;
      break;

    case 'left-start':
      top = refRect.top + crossOffset;
      left = refRect.left - floatRect.width - mainOffset;
      break;

    case 'left-end':
      top = refRect.bottom - floatRect.height + crossOffset;
      left = refRect.left - floatRect.width - mainOffset;
      break;

    case 'right':
      top = refRect.top + (refRect.height - floatRect.height) / 2 + crossOffset;
      left = refRect.right + mainOffset;
      break;

    case 'right-start':
      top = refRect.top + crossOffset;
      left = refRect.right + mainOffset;
      break;

    case 'right-end':
      top = refRect.bottom - floatRect.height + crossOffset;
      left = refRect.right + mainOffset;
      break;
  }

  // Adjust if goes off-screen horizontally
  if (left < padding) {
    left = padding;
  } else if (left + floatRect.width > viewportWidth - padding) {
    left = viewportWidth - floatRect.width - padding;
  }

  // Adjust if goes off-screen vertically
  if (top < padding) {
    top = padding;
  } else if (top + floatRect.height > viewportHeight - padding) {
    top = viewportHeight - floatRect.height - padding;
  }

  return {
    top: Math.round(top),
    left: Math.round(left),
  };
}

/**
 * Apply position to a floating element
 * @param floatingElement The element to position
 * @param position The position to apply
 */
export function applyPosition(
  floatingElement: HTMLElement,
  position: Position
): void {
  floatingElement.style.position = 'fixed';
  floatingElement.style.top = `${position.top}px`;
  floatingElement.style.left = `${position.left}px`;
  floatingElement.style.zIndex = '1000';
}

/**
 * Hook for managing floating element positioning
 */
export function useFloating(
  referenceElement: HTMLElement | null,
  floatingElement: HTMLElement | null,
  options: PopperOptions = {}
) {
  const updatePosition = () => {
    if (!referenceElement || !floatingElement) {
      return;
    }

    const position = calculatePosition(referenceElement, floatingElement, options);
    applyPosition(floatingElement, position);
  };

  return { updatePosition };
}

export default {
  calculatePosition,
  applyPosition,
  useFloating,
};
