import React from 'react';
import { render } from '@testing-library/react-native';
import { Text } from '../../src/components/Text';
import { ThemeProvider } from '../../src/theme/ThemeProvider';

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <ThemeProvider>{children}</ThemeProvider>
);

describe('Text', () => {
  it('renders without crashing', () => {
    const { getByText } = render(
      <Wrapper><Text>Hello</Text></Wrapper>
    );
    expect(getByText('Hello')).toBeTruthy();
  });

  it('accepts variant prop', () => {
    const { getByText } = render(
      <Wrapper><Text variant="h1">Heading</Text></Wrapper>
    );
    expect(getByText('Heading')).toBeTruthy();
  });

  it('accepts color prop', () => {
    const { getByText } = render(
      <Wrapper><Text color="slate">Muted</Text></Wrapper>
    );
    expect(getByText('Muted')).toBeTruthy();
  });
});
