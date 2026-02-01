import type { StorybookConfig } from '@storybook/react';

const config: StorybookConfig = {
  stories: ['../src/**/*.stories.ts', '../src/**/*.stories.tsx'],
  addons: ['@storybook/addon-essentials'],
  framework: {
    name: '@storybook/react',
    options: {},
  },
  docs: {
    autodocs: 'tag',
  },
};

export default config;
