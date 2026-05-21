import React from 'react';
import { render } from '@testing-library/react-native';
import { Text } from 'react-native';
import { Card } from '../../src/components/Card';
import { ThemeProvider } from '../../src/theme/ThemeProvider';

const W = ({ children }: { children: React.ReactNode }) => <ThemeProvider>{children}</ThemeProvider>;

describe('Card', () => {
  it('renders without crashing', () => {
    const { getByText } = render(<W><Card><Text>Content</Text></Card></W>);
    expect(getByText('Content')).toBeTruthy();
  });

  it('renders elevated variant', () => {
    const { getByText } = render(<W><Card elevated><Text>Elevated</Text></Card></W>);
    expect(getByText('Elevated')).toBeTruthy();
  });
});
