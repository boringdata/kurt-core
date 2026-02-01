/**
 * Storybook stories for all Boring UI components
 * Demonstrates usage and accessibility features
 */

import React, { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';

// Infrastructure
import Portal from './Portal';
import FocusTrap from './FocusTrap';
import { calculatePosition } from './Positioning';

// Components
import Pagination from './Pagination';
import Skeleton, { SkeletonGroup, SkeletonCard } from './Skeleton';
import Spinner, { LoadingOverlay } from './Spinner';
import Avatar, { AvatarGroup } from './Avatar';
import Dropdown from './Dropdown';
import { Container, Grid, Flex, Stack, VStack, HStack } from './Layout';
import ProgressBar, { CircularProgress, SteppedProgress } from './ProgressBar';
import Divider, { SectionDivider, TextDivider } from './Divider';
import Icon, { IconButton } from './Icon';
import Tooltip, { Popover } from './Tooltip';

/**
 * Pagination Stories
 */
export const PaginationStories: Meta<typeof Pagination> = {
  component: Pagination,
  title: 'Components/Pagination',
  parameters: {
    layout: 'centered',
  },
};

export const PaginationDefault: StoryObj<typeof Pagination> = {
  render: () => {
    const [page, setPage] = useState(1);
    return (
      <Pagination
        currentPage={page}
        totalPages={10}
        onPageChange={setPage}
      />
    );
  },
};

/**
 * Skeleton Stories
 */
export const SkeletonStories: Meta<typeof Skeleton> = {
  component: Skeleton,
  title: 'Components/Skeleton',
};

export const SkeletonDefault: StoryObj<typeof Skeleton> = {
  render: () => (
    <div className="space-y-4">
      <Skeleton height={20} />
      <Skeleton height={20} width="80%" />
      <Skeleton height={40} width={40} radius="full" />
    </div>
  ),
};

export const SkeletonCards: StoryObj<typeof Skeleton> = {
  render: () => <SkeletonCard count={3} />,
};

/**
 * Spinner Stories
 */
export const SpinnerStories: Meta<typeof Spinner> = {
  component: Spinner,
  title: 'Components/Spinner',
};

export const SpinnerDefault: StoryObj<typeof Spinner> = {
  render: () => (
    <div className="space-y-4">
      <Spinner size="small" />
      <Spinner size="medium" />
      <Spinner size="large" variant="dots" />
    </div>
  ),
};

/**
 * Avatar Stories
 */
export const AvatarStories: Meta<typeof Avatar> = {
  component: Avatar,
  title: 'Components/Avatar',
};

export const AvatarDefault: StoryObj<typeof Avatar> = {
  render: () => (
    <div className="flex gap-4">
      <Avatar initials="JD" status="online" />
      <Avatar initials="AB" status="away" />
      <AvatarGroup
        avatars={[
          { initials: 'JD' },
          { initials: 'AB' },
          { initials: 'CD' },
        ]}
      />
    </div>
  ),
};

/**
 * Dropdown Stories
 */
export const DropdownStories: Meta<typeof Dropdown> = {
  component: Dropdown,
  title: 'Components/Dropdown',
};

export const DropdownDefault: StoryObj<typeof Dropdown> = {
  render: () => (
    <Dropdown
      trigger="Actions"
      items={[
        { id: 'edit', label: 'Edit' },
        { id: 'delete', label: 'Delete', divider: true },
        { id: 'archive', label: 'Archive' },
      ]}
      onSelect={(id) => console.log(id)}
    />
  ),
};

/**
 * Layout Stories
 */
export const LayoutStories: Meta<typeof Container> = {
  component: Container,
  title: 'Components/Layout',
};

export const LayoutGrid: StoryObj<typeof Container> = {
  render: () => (
    <Grid columns={3} gap="16px">
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <div key={i} className="bg-blue-100 p-4 rounded">
          Item {i}
        </div>
      ))}
    </Grid>
  ),
};

export const LayoutFlex: StoryObj<typeof Container> = {
  render: () => (
    <Flex justify="between" align="center" className="bg-gray-100 p-4 rounded">
      <div>Left</div>
      <div>Center</div>
      <div>Right</div>
    </Flex>
  ),
};

export const LayoutStack: StoryObj<typeof Container> = {
  render: () => (
    <VStack spacing="12px" className="w-full max-w-sm">
      <button className="px-4 py-2 bg-blue-500 text-white rounded">
        Cancel
      </button>
      <button className="px-4 py-2 bg-gray-500 text-white rounded">
        Save
      </button>
    </VStack>
  ),
};

/**
 * ProgressBar Stories
 */
export const ProgressStories: Meta<typeof ProgressBar> = {
  component: ProgressBar,
  title: 'Components/Progress',
};

export const ProgressDefault: StoryObj<typeof ProgressBar> = {
  render: () => (
    <div className="space-y-6 w-full max-w-md">
      <ProgressBar value={33} label="Download Progress" />
      <ProgressBar value={65} variant="warning" label="Processing" />
      <CircularProgress value={75} label="Complete" />
      <SteppedProgress current={2} total={4} />
    </div>
  ),
};

/**
 * Divider Stories
 */
export const DividerStories: Meta<typeof Divider> = {
  component: Divider,
  title: 'Components/Divider',
};

export const DividerDefault: StoryObj<typeof Divider> = {
  render: () => (
    <div className="space-y-4 w-full max-w-md">
      <Divider />
      <Divider label="Or" />
      <SectionDivider title="New Section" />
      <TextDivider text="Continue Below" />
    </div>
  ),
};

/**
 * Icon Stories
 */
export const IconStories: Meta<typeof Icon> = {
  component: Icon,
  title: 'Components/Icon',
};

export const IconDefault: StoryObj<typeof Icon> = {
  render: () => (
    <div className="flex gap-4">
      <Icon icon="★" size="small" />
      <Icon icon="★" size="medium" color="#f59e0b" />
      <Icon icon="★" size="large" color="#ef4444" />
      <IconButton icon="✎" aria-label="Edit" onClick={() => console.log('edit')} />
    </div>
  ),
};

/**
 * Tooltip Stories
 */
export const TooltipStories: Meta<typeof Tooltip> = {
  component: Tooltip,
  title: 'Components/Tooltip',
};

export const TooltipDefault: StoryObj<typeof Tooltip> = {
  render: () => (
    <div className="flex gap-6">
      <Tooltip content="Helpful tip" placement="top">
        <button className="px-4 py-2 bg-blue-500 text-white rounded">
          Hover me
        </button>
      </Tooltip>
      <Popover
        trigger={<button className="px-4 py-2 bg-green-500 text-white rounded">Open Popover</button>}
        title="Popover Title"
      >
        <p>This is popover content with more information.</p>
      </Popover>
    </div>
  ),
};

/**
 * Portal Stories
 */
export const PortalStories: Meta<typeof Portal> = {
  component: Portal,
  title: 'Infrastructure/Portal',
};

export const PortalDefault: StoryObj<typeof Portal> = {
  render: () => {
    const [isOpen, setIsOpen] = useState(false);

    return (
      <>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="px-4 py-2 bg-blue-500 text-white rounded"
        >
          {isOpen ? 'Close' : 'Open'} Portal
        </button>

        {isOpen && (
          <Portal>
            <div className="fixed inset-0 bg-black/30 flex items-center justify-center">
              <div className="bg-white p-6 rounded-lg shadow-lg">
                <h2 className="text-xl font-bold mb-4">Portal Content</h2>
                <p>This is rendered outside the component hierarchy.</p>
              </div>
            </div>
          </Portal>
        )}
      </>
    );
  },
};

/**
 * FocusTrap Stories
 */
export const FocusTrapStories: Meta<typeof FocusTrap> = {
  component: FocusTrap,
  title: 'Infrastructure/FocusTrap',
};

export const FocusTrapDefault: StoryObj<typeof FocusTrap> = {
  render: () => {
    const [isActive, setIsActive] = useState(false);

    return (
      <>
        <button
          onClick={() => setIsActive(!isActive)}
          className="px-4 py-2 bg-blue-500 text-white rounded mb-4"
        >
          {isActive ? 'Deactivate' : 'Activate'} Focus Trap
        </button>

        <FocusTrap
          active={isActive}
          onEscapeKey={() => setIsActive(false)}
          className={`p-4 rounded border-2 ${
            isActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
          }`}
        >
          <p className="mb-4">
            {isActive
              ? 'Focus is trapped! Try tabbing - focus will cycle within this area. Press Escape to exit.'
              : 'Activate to trap focus.'}
          </p>
          <div className="space-y-2">
            <button className="block w-full px-4 py-2 bg-gray-500 text-white rounded">
              Button 1
            </button>
            <button className="block w-full px-4 py-2 bg-gray-500 text-white rounded">
              Button 2
            </button>
            <button className="block w-full px-4 py-2 bg-gray-500 text-white rounded">
              Button 3
            </button>
          </div>
        </FocusTrap>
      </>
    );
  },
};

export default {
  title: 'Boring UI Components',
};
