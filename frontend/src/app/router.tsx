import { Routes, Route, Navigate } from 'react-router-dom';
import Chat from './routes/Chat';
import Dashboard from './routes/Dashboard';
import Help from './routes/Help';
import Integrations from './routes/Integrations';
import Login from './routes/Login';
import Settings from './routes/Settings';

// Define props for AppRouter if it needs to pass down session state
interface AppRouterProps {
  currentSessionId: number | null;
  setCurrentSessionId: (id: number | null) => void;
  setRefreshSessionsTrigger: React.Dispatch<React.SetStateAction<number>>; // ADDED
}

// Update AppRouter to accept and pass props
const AppRouter: React.FC<AppRouterProps> = ({ currentSessionId, setCurrentSessionId, setRefreshSessionsTrigger }) => {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      {/* Pass session state and refresh trigger to Chat component */}
      <Route 
        path="/chat" 
        element={<Chat currentSessionId={currentSessionId} setCurrentSessionId={setCurrentSessionId} setRefreshSessionsTrigger={setRefreshSessionsTrigger} />} 
      />
      <Route 
        path="/chat/:sessionId" 
        element={<Chat currentSessionId={currentSessionId} setCurrentSessionId={setCurrentSessionId} setRefreshSessionsTrigger={setRefreshSessionsTrigger} />} 
      />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/integrations" element={<Integrations />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/help" element={<Help />} />
      <Route path="/" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

export default AppRouter;

