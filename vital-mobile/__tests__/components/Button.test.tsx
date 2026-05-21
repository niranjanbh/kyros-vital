import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Button } from '../../src/components/Button';
import { ThemeProvider } from '../../src/theme/ThemeProvider';

const W = ({ children }: { children: React.ReactNode }) => <ThemeProvider>{children}</ThemeProvider>;

describe('Button', () => {
  it('renders without crashing', () => {
    const { getByText } = render(<W><Button onPress={() => {}}>Press me</Button></W>);
    expect(getByText('Press me')).toBeTruthy();
  });

  it('calls onPress', () => {
    const handler = jest.fn();
    const { getByText } = render(<W><Button onPress={handler}>Click</Button></W>);
    fireEvent.press(getByText('Click'));
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it('renders secondary variant', () => {
    const { getByText } = render(<W><Button onPress={() => {}} variant="secondary">Secondary</Button></W>);
    expect(getByText('Secondary')).toBeTruthy();
  });

  it('renders ghost variant', () => {
    const { getByText } = render(<W><Button onPress={() => {}} variant="ghost">Ghost</Button></W>);
    expect(getByText('Ghost')).toBeTruthy();
  });
});
