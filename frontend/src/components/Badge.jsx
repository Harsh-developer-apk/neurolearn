export default function Badge({ children, tone = "blue" }) {
  const tones = {
    blue: "bg-blue-50 text-blue-800 border-blue-200",
    green: "bg-emerald-50 text-emerald-800 border-emerald-200",
    orange: "bg-orange-50 text-orange-800 border-orange-200",
    gray: "bg-slate-50 text-slate-700 border-slate-200"
  };

  return (
    <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${tones[tone]}`}>
      {children}
    </span>
  );
}
