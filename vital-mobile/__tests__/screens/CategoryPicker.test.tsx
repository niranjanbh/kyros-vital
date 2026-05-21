import React from 'react';
import { render } from '@testing-library/react-native';
import { ThemeProvider } from '../../src/theme/ThemeProvider';

jest.mock('expo-router', () => ({ router: { push: jest.fn(), back: jest.fn() } }));

import CategoryPickerScreen from '../../app/item/new';

const W = ({ children }: { children: React.ReactNode }) => <ThemeProvider>{children}</ThemeProvider>;

describe('CategoryPickerScreen', () => {
  it('renders without crashing', () => {
    const { toJSON } = render(<CategoryPickerScreen />, { wrapper: W });
    expect(toJSON()).toBeTruthy();
  });

  it('shows all 6 categories', () => {
    const { getByText } = render(<CategoryPickerScreen />, { wrapper: W });
    expect(getByText('Medication')).toBeTruthy();
    expect(getByText('Water')).toBeTruthy();
    expect(getByText('Workout')).toBeTruthy();
    expect(getByText('Meal')).toBeTruthy();
    expect(getByText('Vitals')).toBeTruthy();
    expect(getByText('Custom')).toBeTruthy();
  });
});
