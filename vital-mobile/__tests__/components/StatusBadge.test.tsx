import React from 'react';
import { render } from '@testing-library/react-native';
import { StatusBadge } from '../../src/components/StatusBadge';
import { ThemeProvider } from '../../src/theme/ThemeProvider';

const W = ({ children }: { children: React.ReactNode }) => <ThemeProvider>{children}</ThemeProvider>;

describe('StatusBadge', () => {
  it('renders label', () => {
    const { getByText } = render(<W><StatusBadge label="Active" variant="positive" /></W>);
    expect(getByText('Active')).toBeTruthy();
  });

  it('renders all variants without crashing', () => {
    (['positive', 'warning', 'critical', 'neutral'] as const).forEach((v) => {
      const { unmount } = render(<W><StatusBadge label="X" variant={v} /></W>);
      unmount();
    });
  });
});
