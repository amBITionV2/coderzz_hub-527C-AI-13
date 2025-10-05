import { createContext, useContext, useState, ReactNode } from 'react';

interface HighlightContextType {
  highlightedFloats: number[];
  setHighlightedFloats: (floats: number[]) => void;
  clearHighlights: () => void;
}

const HighlightContext = createContext<HighlightContextType | undefined>(undefined);

export const HighlightProvider = ({ children }: { children: ReactNode }) => {
  const [highlightedFloats, setHighlightedFloats] = useState<number[]>([]);

  const clearHighlights = () => {
    setHighlightedFloats([]);
  };

  return (
    <HighlightContext.Provider value={{ highlightedFloats, setHighlightedFloats, clearHighlights }}>
      {children}
    </HighlightContext.Provider>
  );
};

export const useHighlight = () => {
  const context = useContext(HighlightContext);
  if (context === undefined) {
    throw new Error('useHighlight must be used within a HighlightProvider');
  }
  return context;
};
