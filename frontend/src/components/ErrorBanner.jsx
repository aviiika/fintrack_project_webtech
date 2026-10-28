export default function ErrorBanner({ message }) {
  if (!message) return null;
  return (<div role="alert" className="rounded-sm bg-debit/10 border border-debit/40 px-3 py-2 text-sm text-debit mb-3">{message}</div>);
}
