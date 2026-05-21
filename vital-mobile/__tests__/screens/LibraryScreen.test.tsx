import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from '../../src/theme/ThemeProvider';

jest.mock('expo-router', () => ({ router: { push: jest.fn(), replace: jest.fn() } }));

const mockUseTrackedItems = jest.fn(() => ({ data: [], isLoading: false }));
const mockUseLabReports = jest.fn(() => ({ data: [] }));
jest.mock('../../src/api/queries', () => ({
  useTrackedItems: (...a: any[]) => mockUseTrackedItems(...a),
  useLabReports: (...a: any[]) => mockUseLabReports(...a),
}));

import LibraryScreen from '../../app/(tabs)/library';

function W({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}><ThemeProvider>{children}</ThemeProvider></QueryClientProvider>;
}

describe('LibraryScreen', () => {
  it('renders without crashing', () => {
    const { toJSON } = render(<LibraryScreen />, { wrapper: W });
    expect(toJSON()).toBeTruthy();
  });

  it('shows Library heading', () => {
    const { getByText } = render(<LibraryScreen />, { wrapper: W });
    expect(getByText('Library')).toBeTruthy();
  });

  it('shows empty state when no items', () => {
    const { getByText } = render(<LibraryScreen />, { wrapper: W });
    expect(getByText('No tracked items yet')).toBeTruthy();
  });

  it('shows filter chips', () => {
    const { getByText } = render(<LibraryScreen />, { wrapper: W });
    expect(getByText('All')).toBeTruthy();
    expect(getByText('Medication')).toBeTruthy();
    expect(getByText('Water')).toBeTruthy();
  });

  it('renders items when data is present', () => {
    mockUseTrackedItems.mockReturnValueOnce({
      data: [
        {
          id: 'item-001',
          category: 'medication',
          name: 'Metformin 500mg',
          status: 'active',
          metadata: { drug_name: 'Metformin', dosage: '500mg' },
          reminders: [],
        },
      ],
      isLoading: false,
    });
    const { getByText } = render(<LibraryScreen />, { wrapper: W });
    expect(getByText('Metformin 500mg')).toBeTruthy();
  });
});
