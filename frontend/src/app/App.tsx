// filepath: c:\dev-projects\dora_insight\frontend\src\app\App.tsx
import { useLocation } from 'react-router-dom';
import AppRouter from './router';
import AppProviders from './provider';
import Sidebar from '../components/Sidebar';
import '../App.css';
import { useState } from 'react'; // Import useState

export default function App() {
  const location = useLocation();
  const showSidebar = location.pathname !== '/login';
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
  const [refreshSessionsTrigger, setRefreshSessionsTrigger] = useState<number>(0); // ADDED

  return (
    <AppProviders>
      <div className={`app-container ${showSidebar ? 'with-sidebar' : ''}`}>
        {showSidebar && <Sidebar setCurrentSessionId={setCurrentSessionId} refreshSessionsTrigger={refreshSessionsTrigger} />}  {/* MODIFIED */}
        <div 
          className={`main-content ${showSidebar ? 'sidebar-present' : 'no-sidebar'}`}
        >
          <div className="page-content-area">
            {/* Pass currentSessionId and setCurrentSessionId to AppRouter */}
            {/* AppRouter will then need to pass them to the Chat component */}
            <AppRouter 
              currentSessionId={currentSessionId} 
              setCurrentSessionId={setCurrentSessionId} 
              setRefreshSessionsTrigger={setRefreshSessionsTrigger} // ADDED
            />
          </div>
        </div>
      </div>
    </AppProviders>
  );
}
