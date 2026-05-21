import React, { createContext, useContext } from 'react';
import { tokens } from './tokens';
import { typography } from './typography';

const ThemeContext = createContext({ tokens, typography });

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <ThemeContext.Provider value={{ tokens, typography }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
