import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import ErrorBanner from '../components/ErrorBanner.jsx';
import Spinner from '../components/Spinner.jsx';

/**
 * Sign-in as a cover: a Medium Slate Blue panel carries the identity (the one
 * large block of brand colour in the whole app), the form sits on Rich Black.
 * On narrow screens the cover collapses to a slim header.
 */
export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [form, setForm] = useState({ email:'', password:'' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const from = loc.state?.from?.pathname || '/dashboard';
  const submit = async e => {
    e.preventDefault(); setError(''); setLoading(true);
    try { await login(form); nav(from, { replace: true }); }
    catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };
  return (
    <div className="flex min-h-screen flex-col bg-paper md:flex-row">
      <section className="flex flex-col justify-between bg-brand-600 px-8 py-8 text-white md:w-[44%] md:py-12">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-sm bg-richblack">
            <i className="ti ti-chart-pie text-lg text-periwinkle"/>
          </span>
          <span className="font-mono text-base font-medium">FinTrack Pro</span>
        </div>
        <div className="hidden md:block">
          <h1 className="max-w-xs text-3xl font-semibold leading-tight tracking-tight">
            Every rupee, filed where it belongs.
          </h1>
          <p className="mt-4 max-w-sm text-sm leading-relaxed text-white">
            Import statements from HDFC, SBI and ICICI. A model sorts the spending,
            and tells you when it is not sure.
          </p>
        </div>
        <span className="stamp hidden self-start border-white/80 text-white md:inline-flex"
          style={{ boxShadow:'inset 0 0 0 2px #5B5BF2, inset 0 0 0 3px rgba(255,255,255,.45)' }}>
          <i className="ti ti-check"/>categorised by model
        </span>
      </section>

      <section className="flex flex-1 items-center justify-center px-6 py-10">
        <div className="w-full max-w-sm">
          <h2 className="page-title mb-1">Sign in</h2>
          <div className="mb-6 h-px w-12 bg-accent"/>
          <form onSubmit={submit} className="flex flex-col gap-4">
            <ErrorBanner message={error}/>
            <div>
              <label htmlFor="email" className="mb-1 block text-xs font-medium text-slate-600">Email</label>
              <input id="email" type="email" required className="input-field w-full" value={form.email}
                onChange={e => setForm(f => ({...f, email:e.target.value}))}/>
            </div>
            <div>
              <label htmlFor="password" className="mb-1 block text-xs font-medium text-slate-600">Password</label>
              <input id="password" type="password" required className="input-field w-full" value={form.password}
                onChange={e => setForm(f => ({...f, password:e.target.value}))}/>
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? <><Spinner size={16}/> Signing in...</> : 'Sign in'}
            </button>
          </form>
          <p className="mt-5 border-t border-line pt-3 text-xs text-slate-500">
            Demo account <span className="font-mono text-ink">demo@fintrack.app</span> with password <span className="font-mono text-ink">demo12345</span>
          </p>
        </div>
      </section>
    </div>
  );
}
