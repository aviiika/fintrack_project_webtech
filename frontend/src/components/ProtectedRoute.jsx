import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import Spinner from './Spinner.jsx';
export default function ProtectedRoute({ children }) {
  const { isAuthenticated, initializing } = useAuth();
  const loc = useLocation();
  if (initializing) return <div className="flex h-full items-center justify-center"><Spinner size={32} className="text-accent-text"/></div>;
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: loc }} replace/>;
  return children;
}
