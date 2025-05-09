import React from 'react';

// Example Provider component - customize as needed
interface AppProviderProps {
  children: React.ReactNode;
}

const AppProviders: React.FC<AppProviderProps> = ({ children }) => {
  // You can wrap multiple context providers here if needed
  // e.g., <AuthContext.Provider value={{...}}>
  //         <ThemeContext.Provider value={{...}}>
  //           {children}
  //         </ThemeContext.Provider>
  //       </AuthContext.Provider>
  return <>{children}</>;
};

export default AppProviders;
