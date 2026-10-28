import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext.jsx';
import App from './App.jsx';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode><BrowserRouter><AuthProvider><App/></AuthProvider></BrowserRouter></React.StrictMode>
);

/*
 * Register the service worker in production builds only.
 *
 * Registering it in dev would have the SW intercept Vite's module requests and
 * serve stale JS, which looks exactly like "my edit didn't apply" and wastes an
 * afternoon. Production-only keeps HMR honest.
 */
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js').catch((err) => {
      // A failed SW registration must never break the app — it's an enhancement.
      console.warn('Service worker registration failed:', err);
    });
  });
}
