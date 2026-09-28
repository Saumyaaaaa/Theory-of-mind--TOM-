export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 bg-slate-50 text-slate-800">
      <div className="max-w-xl w-full bg-white border border-slate-200 rounded-xl p-8 shadow-sm text-center">
        <div className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 mb-4">
          Phase 1 Active
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 mb-2">
          Learner-State Scaffolding Tutor
        </h1>
        <p className="text-slate-600 mb-6 text-sm">
          Dual-Agent Monitor/Actor Socratic Tutoring System.
        </p>
        <div className="rounded-lg bg-slate-50 border border-slate-200 p-4 text-left text-sm space-y-2">
          <div className="flex justify-between items-center text-xs text-slate-500 font-mono">
            <span>FastAPI Backend:</span>
            <span className="text-emerald-600 font-semibold">http://localhost:8000</span>
          </div>
          <div className="flex justify-between items-center text-xs text-slate-500 font-mono">
            <span>Next.js Frontend:</span>
            <span className="text-indigo-600 font-semibold">http://localhost:3000</span>
          </div>
        </div>
      </div>
    </main>
  );
}
