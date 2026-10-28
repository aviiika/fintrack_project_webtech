export default function StubPage({ title }) {
  return (
    <div className="flex h-full items-center justify-center text-slate-400">
      <div className="text-center">
        <i className="ti ti-tool text-4xl mb-3 block"/>
        <p className="text-sm">{title} — port from base FinTrack</p>
        <p className="text-xs mt-1">Open src/pages/{title}.jsx from the base zip</p>
      </div>
    </div>
  );
}
