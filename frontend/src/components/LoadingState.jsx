export default function LoadingState() {
  return (
    <div className="mx-auto flex min-h-screen max-w-6xl items-center justify-center px-6">
      <div className="section-card text-center">
        <p className="text-lg font-semibold text-ink">Loading prototype profile</p>
        <p className="mt-2 text-sm text-muted">Reading Phase 1A and 1B data from FastAPI.</p>
      </div>
    </div>
  );
}
