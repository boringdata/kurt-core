/**
 * Layout Utilities - Container, Grid, Flex, and Stack components
 *
 * WCAG 2.1 AA Compliant:
 * - Semantic HTML
 * - Responsive design support
 * - Proper spacing and alignment
 */

import React, { ReactNode, CSSProperties } from 'react';

interface ResponsiveValue<T> {
  base?: T;
  sm?: T;
  md?: T;
  lg?: T;
  xl?: T;
  '2xl'?: T;
}

interface ContainerProps {
  /** Container content */
  children: ReactNode;
  /** Max width: sm, md, lg, xl, 2xl, or custom */
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | string;
  /** Center content horizontally */
  center?: boolean;
  /** Padding */
  padding?: string | number;
  /** Optional class name */
  className?: string;
}

interface GridProps {
  /** Grid content */
  children: ReactNode;
  /** Number of columns */
  columns?: number | ResponsiveValue<number>;
  /** Gap between items */
  gap?: string | number;
  /** Optional class name */
  className?: string;
}

interface FlexProps {
  /** Flex content */
  children: ReactNode;
  /** Flex direction */
  direction?: 'row' | 'column' | 'row-reverse' | 'column-reverse';
  /** Justify content alignment */
  justify?: 'start' | 'end' | 'center' | 'between' | 'around' | 'evenly';
  /** Align items */
  align?: 'start' | 'end' | 'center' | 'baseline' | 'stretch';
  /** Gap between items */
  gap?: string | number;
  /** Flex wrap */
  wrap?: 'nowrap' | 'wrap' | 'wrap-reverse';
  /** Optional class name */
  className?: string;
  /** Optional style */
  style?: CSSProperties;
}

interface StackProps extends Omit<FlexProps, 'direction'> {
  /** Stack direction (defaults to column) */
  direction?: 'vertical' | 'horizontal';
  /** Spacing between items */
  spacing?: string | number;
}

const maxWidthMap = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
};

const justifyMap = {
  start: 'justify-start',
  end: 'justify-end',
  center: 'justify-center',
  between: 'justify-between',
  around: 'justify-around',
  evenly: 'justify-evenly',
};

const alignMap = {
  start: 'items-start',
  end: 'items-end',
  center: 'items-center',
  baseline: 'items-baseline',
  stretch: 'items-stretch',
};

const directionMap = {
  row: 'flex-row',
  column: 'flex-col',
  'row-reverse': 'flex-row-reverse',
  'column-reverse': 'flex-col-reverse',
};

const wrapMap = {
  nowrap: 'flex-nowrap',
  wrap: 'flex-wrap',
  'wrap-reverse': 'flex-wrap-reverse',
};

/**
 * Container Component
 * Max-width constrained container for page width
 *
 * Usage:
 * ```tsx
 * <Container maxWidth="lg" center>
 *   <h1>Page Title</h1>
 * </Container>
 * ```
 */
export const Container: React.FC<ContainerProps> = ({
  children,
  maxWidth = 'lg',
  center = true,
  padding = '16px',
  className = '',
}) => {
  const maxWidthValue =
    maxWidthMap[maxWidth as keyof typeof maxWidthMap] || maxWidth;
  const paddingValue =
    typeof padding === 'number' ? `${padding}px` : padding;

  return (
    <div
      className={`${center ? 'mx-auto' : ''} ${className}`}
      style={{
        maxWidth: maxWidthValue,
        paddingLeft: paddingValue,
        paddingRight: paddingValue,
      }}
    >
      {children}
    </div>
  );
};

/**
 * Grid Component
 * CSS Grid layout wrapper
 *
 * Usage:
 * ```tsx
 * <Grid columns={3} gap="16px">
 *   <div>Item 1</div>
 *   <div>Item 2</div>
 *   <div>Item 3</div>
 * </Grid>
 * ```
 */
export const Grid: React.FC<GridProps> = ({
  children,
  columns = 1,
  gap = '16px',
  className = '',
}) => {
  const columnValue = typeof columns === 'number' ? columns : columns.base || 1;
  const gapValue = typeof gap === 'number' ? `${gap}px` : gap;

  return (
    <div
      className={`grid ${className}`}
      style={{
        gridTemplateColumns: `repeat(${columnValue}, minmax(0, 1fr))`,
        gap: gapValue,
      }}
    >
      {children}
    </div>
  );
};

/**
 * Flex Component
 * Flexbox layout wrapper
 *
 * Usage:
 * ```tsx
 * <Flex justify="between" align="center">
 *   <div>Left</div>
 *   <div>Right</div>
 * </Flex>
 * ```
 */
export const Flex: React.FC<FlexProps> = ({
  children,
  direction = 'row',
  justify = 'start',
  align = 'stretch',
  gap = '8px',
  wrap = 'nowrap',
  className = '',
  style,
}) => {
  const gapValue = typeof gap === 'number' ? `${gap}px` : gap;

  const classes = [
    'flex',
    directionMap[direction],
    justifyMap[justify],
    alignMap[align],
    wrapMap[wrap],
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div
      className={classes}
      style={{
        gap: gapValue,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

/**
 * Stack Component
 * Convenience wrapper for vertical flex layout
 *
 * Usage:
 * ```tsx
 * <Stack spacing="12px">
 *   <div>Item 1</div>
 *   <div>Item 2</div>
 * </Stack>
 * ```
 */
export const Stack: React.FC<StackProps> = ({
  children,
  direction = 'vertical',
  spacing,
  gap,
  justify,
  align,
  className = '',
  style,
}) => {
  const finalDirection =
    direction === 'vertical' ? 'column' : 'row';
  const finalGap = spacing || gap || '8px';

  return (
    <Flex
      direction={finalDirection}
      gap={finalGap}
      justify={justify}
      align={align}
      className={className}
      style={style}
    >
      {children}
    </Flex>
  );
};

/**
 * VStack - Vertical Stack (convenience)
 */
export const VStack: React.FC<Omit<StackProps, 'direction'>> = (props) => (
  <Stack {...props} direction="vertical" />
);

/**
 * HStack - Horizontal Stack (convenience)
 */
export const HStack: React.FC<Omit<StackProps, 'direction'>> = (props) => (
  <Stack {...props} direction="horizontal" />
);

/**
 * Spacer - Flexible spacer element
 */
export const Spacer: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`flex-1 ${className}`} />
);

/**
 * Divider - Visual divider between elements
 */
export const LayoutDivider: React.FC<{
  direction?: 'horizontal' | 'vertical';
  className?: string;
}> = ({ direction = 'horizontal', className = '' }) => {
  const classes =
    direction === 'horizontal'
      ? `h-px w-full bg-gray-200 ${className}`
      : `w-px h-full bg-gray-200 ${className}`;

  return <div className={classes} role="separator" />;
};

Container.displayName = 'Container';
Grid.displayName = 'Grid';
Flex.displayName = 'Flex';
Stack.displayName = 'Stack';
VStack.displayName = 'VStack';
HStack.displayName = 'HStack';
Spacer.displayName = 'Spacer';
LayoutDivider.displayName = 'LayoutDivider';

export {
  Grid,
  Flex,
  Stack,
  VStack,
  HStack,
  Spacer,
  LayoutDivider,
};

export default Container;
