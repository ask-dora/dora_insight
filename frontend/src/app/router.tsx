import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './routes/Login';
import Chat from './routes/Chat'; 
import Dashboard from './routes/Dashboard';
import Integrations from './routes/Integrations';
import Settings from './routes/Settings';
import Help from './routes/Help';

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/chat" element={<Chat />} /> 
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/integrations" element={<Integrations />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/help" element={<Help />} />
      <Route path="/" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

