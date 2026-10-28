import { Suspense, lazy } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './context/AuthContext.jsx';
import TopBar from './components/TopBar.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import Spinner from './components/Spinner.jsx';
import Login from './pages/Login.jsx';

/**
 * Every authenticated page is code-split with React.lazy.
 *
 * Why: Recharts alone is ~300 kB, and it's only needed by Dashboard, Reports,
 * NetWorth and ModelInsights. Loading it eagerly meant the login screen — the
 * one page every user hits first, often on mobile data — paid for charting code
 * it never renders. Splitting drops the initial bundle to the shell plus Login,
 * and each page's chunk arrives on navigation.
 *
 * Login is deliberately NOT lazy: it's the first paint for an unauthenticated
 * visitor, so a separate round-trip for it would be a regression, not a win.
 */
const Dashboard     = lazy(() => import('./pages/Dashboard.jsx'));
const Import        = lazy(() => import('./pages/Import.jsx'));
const Transactions  = lazy(() => import('./pages/Transactions.jsx'));
const Reports       = lazy(() => import('./pages/Reports.jsx'));
const ModelInsights = lazy(() => import('./pages/ModelInsights.jsx'));
const Portfolio     = lazy(() => import('./pages/Portfolio.jsx'));
const NetWorth      = lazy(() => import('./pages/NetWorth.jsx'));
const Loans         = lazy(() => import('./pages/Loans.jsx'));

function PageLoader() {
  return (
    <div className="flex h-full flex-1 items-center justify-center">
      <Spinner size={28} className="text-accent-text"/>
    </div>
  );
}

function Shell({ children }) {
  return (
    <div className="flex h-full flex-col">
      <TopBar/>
      <main className="flex flex-1 flex-col overflow-hidden">
        <Suspense fallback={<PageLoader/>}>{children}</Suspense>
      </main>
    </div>
  );
}

function GuestOnly({ children }) {
  const { isAuthenticated, initializing } = useAuth();
  if (initializing) return <PageLoader/>;
  return isAuthenticated ? <Navigate to="/dashboard" replace/> : children;
}

/** Wraps a lazy page in both the auth gate and the app shell. */
function Page({ children }) {
  return <ProtectedRoute><Shell>{children}</Shell></ProtectedRoute>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace/>}/>
      <Route path="/login" element={<GuestOnly><Login/></GuestOnly>}/>
      <Route path="/dashboard"    element={<Page><Dashboard/></Page>}/>
      <Route path="/import"       element={<Page><Import/></Page>}/>
      <Route path="/transactions" element={<Page><Transactions/></Page>}/>
      <Route path="/reports"      element={<Page><Reports/></Page>}/>
      <Route path="/ml"           element={<Page><ModelInsights/></Page>}/>
      <Route path="/portfolio"    element={<Page><Portfolio/></Page>}/>
      <Route path="/networth"     element={<Page><NetWorth/></Page>}/>
      <Route path="/loans"        element={<Page><Loans/></Page>}/>
      <Route path="*" element={<Navigate to="/dashboard" replace/>}/>
    </Routes>
  );
}
