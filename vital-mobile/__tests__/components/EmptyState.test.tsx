import React from 'react';
import { render } from '@testing-library/react-native';
import { EmptyState } from '../../src/components/EmptyState';
import { ThemeProvider } from '../../src/theme/ThemeProvider';

const W = ({ children }: { children: React.ReactNode }) => <ThemeProvider>{children}</ThemeProvider>;

describe('EmptyState', () => {
  it('renders title', () => {
    const { getByText } = render(<W><EmptyState title="No items" /></W>);
    expect(getByText('No items')).toBeTruthy();
  });

  it('renders body text', () => {
    const { getByText } = render(<W><EmptyState title="Title" body="Description here" /></W>);
    expect(getByText('Description here')).toBeTruthy();
  });

  it('renders CTA button when provided', () => {
    const { getByText } = render(
      <W><EmptyState title="T" cta={{ label: 'Add item', onPress: () => {} }} /></W>
    );
    expect(getByText('Add item')).toBeTruthy();
  });
});
