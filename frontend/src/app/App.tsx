// filepath: c:\dev-projects\dora_insight\frontend\src\app\App.tsx
import { useLocation } from 'react-router-dom';
import AppRouter from './router';
import AppProviders from './provider';
import Sidebar from '../components/Sidebar';
import '../App.css';

export default function App() {
  const location = useLocation();
  const showSidebar = location.pathname !== '/login';

  return (
    <AppProviders>
      <div className={`app-container ${showSidebar ? 'with-sidebar' : ''}`}>
        {showSidebar && <Sidebar />}
        <div 
          className={`main-content ${showSidebar ? 'sidebar-present' : 'no-sidebar'}`}
        >
          <div className="page-content-area">
            <AppRouter />
          </div>
        </div>
      </div>
    </AppProviders>
  );
}
