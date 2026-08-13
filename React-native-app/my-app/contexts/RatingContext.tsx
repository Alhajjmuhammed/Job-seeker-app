import React, { createContext, useContext, useState, useCallback } from 'react';

interface RatingContextType {
  refreshTrigger: number;
  triggerRatingRefresh: () => void;
}

const RatingContext = createContext<RatingContextType | undefined>(undefined);

export const RatingProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const triggerRatingRefresh = useCallback(() => {
    console.log('Rating refresh triggered!');
    setRefreshTrigger(prev => prev + 1);
  }, []);

  return (
    <RatingContext.Provider value={{ refreshTrigger, triggerRatingRefresh }}>
      {children}
    </RatingContext.Provider>
  );
};

export const useRatingRefresh = () => {
  const context = useContext(RatingContext);
  if (context === undefined) {
    throw new Error('useRatingRefresh must be used within a RatingProvider');
  }
  return context;
};