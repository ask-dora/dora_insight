// filepath: c:\dev-projects\dora_insight\frontend\src\app\App.tsx
import AppRouter from './router';
import AppProviders from './provider';

export default function App() {
  return (
    <AppProviders>
      <AppRouter />
    </AppProviders>
  );
}
