import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './routes/Login';
import Dashboard from './routes/Dashboard';
import Integrations from './routes/Integrations';

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/integrations" element={<Integrations />} />
      <Route path="/" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
