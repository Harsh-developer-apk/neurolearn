import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import LoadingState from "../components/LoadingState.jsx";
import { getStoredProfileId } from "../components/ProfileSelector.jsx";
import { generateLearningBlock, getLearningPlan } from "../services/api.js";

function InlineLessonText({ text }) {
  const parts = String(text ?? "").split(/(\*\*.+?\*\*|__.+?__|`[^`]+`|\*[^*\n]+\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={index}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("__") && part.endsWith("__")) return <strong key={index}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("*") && part.endsWith("*")) return <em key={index}>{part.slice(1, -1)}</em>;
    if (part.startsWith("`") && part.endsWith("`")) return <code className="lesson-inline-code" key={index}>{part.slice(1, -1)}</code>;
    return part;
  });
}

function LessonText({ text, className = "" }) {
  const lines = String(text ?? "").replace(/\r\n?/g, "\n").split("\n");
  const blocks = [];
  let paragraph = [];
  let listItems = [];
  let listType = null;
  let codeLines = [];
  let inCode = false;

  const flushParagraph = () => {
    if (paragraph.length) blocks.push({ type: "paragraph", text: paragraph.join(" ") });
    paragraph = [];
  };
  const flushList = () => {
    if (listItems.length) blocks.push({ type: listType, items: listItems });
    listItems = [];
    listType = null;
  };

  lines.forEach((sourceLine) => {
    const line = sourceLine.trim();
    if (line.startsWith("```")) {
      flushParagraph();
      flushList();
      if (inCode) {
        blocks.push({ type: "code", text: codeLines.join("\n") });
        codeLines = [];
      }
      inCode = !inCode;
      return;
    }
    if (inCode) {
      codeLines.push(sourceLine);
      return;
    }
    if (!line) {
      flushParagraph();
      flushList();
      return;
    }
    const heading = line.match(/^#{1,6}\s+(.+)$/);
    if (heading) {
      flushParagraph();
      flushList();
      blocks.push({ type: "heading", text: heading[1].replace(/\s*#+\s*$/, "") });
      return;
    }
    const bullet = line.match(/^[-*+]\s+(.+)$/);
    const number = line.match(/^\d+[.)]\s+(.+)$/);
    if (bullet || number) {
      flushParagraph();
      const nextType = bullet ? "unordered" : "ordered";
      if (listType && listType !== nextType) flushList();
      listType = nextType;
      listItems.push(bullet ? bullet[1] : number[1]);
      return;
    }
    flushList();
    const quote = line.match(/^>\s?(.*)$/);
    if (quote) {
      flushParagraph();
      blocks.push({ type: "quote", text: quote[1] });
      return;
    }
    paragraph.push(line);
  });
  flushParagraph();
  flushList();
  if (codeLines.length) blocks.push({ type: "code", text: codeLines.join("\n") });

  return <div className={`lesson-formatted-text ${className}`}>
    {blocks.map((block, index) => {
      if (block.type === "heading") return <h4 className="mb-2 mt-4 text-base font-bold first:mt-0" key={index}><InlineLessonText text={block.text} /></h4>;
      if (block.type === "unordered" || block.type === "ordered") {
        const List = block.type === "unordered" ? "ul" : "ol";
        return <List className={`my-2 space-y-1.5 pl-6 ${block.type === "unordered" ? "list-disc" : "list-decimal"}`} key={index}>{block.items.map((item, itemIndex) => <li className="pl-1" key={itemIndex}><InlineLessonText text={item} /></li>)}</List>;
      }
      if (block.type === "quote") return <blockquote className="my-3 border-l-2 border-violet-300/50 pl-4 italic text-white/70" key={index}><InlineLessonText text={block.text} /></blockquote>;
      if (block.type === "code") return <pre className="my-3 overflow-x-auto rounded-xl border border-white/10 bg-[#090a10] p-4 text-sm leading-6 text-violet-100" key={index}><code>{block.text}</code></pre>;
      return <p className="my-2 whitespace-pre-wrap leading-7" key={index}><InlineLessonText text={block.text} /></p>;
    })}
  </div>;
}

function MisconceptionIndicators({ indicators, guidance = [] }) {
  if (!indicators?.length) return null;
  return (
    <aside className="rounded-xl border border-amber-200 bg-amber-50 p-4" aria-label="Diagnostic learning signals">
      <p className="text-sm font-bold text-amber-950">Areas to reinforce from your diagnostic</p>
      <ul className="mt-2 space-y-2">
        {indicators.map((item, index) => {
          const correction = guidance.find((entry) => entry.indicator === item.indicator && entry.topic === item.topic);
          return (
            <li className="text-sm text-amber-950" key={`${item.skill_node_id}-${item.indicator}-${index}`}>
              <span className="font-semibold">{item.topic}:</span> {item.indicator} <span className="text-amber-800">({item.evidence_count} incorrect response{item.evidence_count === 1 ? "" : "s"}, excluding low-confidence guesses)</span>
              {correction ? <p className="mt-1 leading-6">{correction.correction}</p> : null}
            </li>
          );
        })}
      </ul>
    </aside>
  );
}

function DiagramBlock({ block }) {
  const nodes = block.nodes || [];
  const positions = new Map(nodes.map((node) => [node.id, node]));
  const edges = (block.edges || []).filter((edge) => positions.has(edge.from) && positions.has(edge.to));
  if (!nodes.length) return null;
  return (
    <section className="overflow-hidden rounded-xl border border-slate-200 bg-white p-4">
      <h3 className="font-bold text-ink">{block.title || "Concept diagram"}</h3>
      <div className="mt-3 overflow-x-auto">
        <svg className="h-64 min-w-[32rem] w-full" viewBox="0 0 100 100" role="img" aria-label={block.title || "Concept diagram"}>
          <defs><marker id="lesson-arrow" markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto"><path d="M0,0 L5,2.5 L0,5 z" fill="#64748b" /></marker></defs>
          {edges.map((edge, index) => {
            const from = positions.get(edge.from);
            const to = positions.get(edge.to);
            const x1 = Math.max(5, Math.min(95, Number(from.x) || 50));
            const y1 = Math.max(8, Math.min(92, Number(from.y) || 50));
            const x2 = Math.max(5, Math.min(95, Number(to.x) || 50));
            const y2 = Math.max(8, Math.min(92, Number(to.y) || 50));
            return <g key={`${edge.from}-${edge.to}-${index}`}><line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#8f86b3" strokeWidth="0.7" markerEnd="url(#lesson-arrow)" />{edge.label ? <text x={(x1 + x2) / 2} y={(y1 + y2) / 2 - 2} textAnchor="middle" fontSize="3" fill="#d0c8e8">{edge.label}</text> : null}</g>;
          })}
          {nodes.map((node) => {
            const x = Math.max(5, Math.min(95, Number(node.x) || 50));
            const y = Math.max(8, Math.min(92, Number(node.y) || 50));
            return <g key={node.id}><rect x={x - 9} y={y - 5} width="18" height="10" rx="2" fill="#211d31" stroke="#a998f4" strokeWidth="0.7" /><text x={x} y={y + 1} textAnchor="middle" fontSize="3" fill="#f3efff">{node.label}</text></g>;
          })}
        </svg>
      </div>
    </section>
  );
}

function ContentBlock({ block, index, onCopy, copied }) {
  if (block.type === "text") {
    return <section key={index}><h3 className="text-lg font-bold text-ink">{block.heading}</h3><LessonText className="mt-2 text-slate-700" text={block.content} /></section>;
  }
  if (block.type === "code") {
    const codeKey = `${index}-${block.title}`;
    return (
      <section className="overflow-hidden rounded-xl border border-slate-700 bg-slate-950 text-slate-100" key={index}>
        <div className="flex items-center justify-between gap-3 border-b border-slate-700 px-4 py-3">
          <div><span className="rounded bg-slate-800 px-2 py-1 text-xs font-bold uppercase tracking-wide text-indigo-200">{block.language}</span><span className="ml-3 text-sm font-semibold">{block.title}</span></div>
          <button type="button" onClick={() => onCopy(block.code, codeKey)} className="rounded-md border border-slate-600 px-3 py-1.5 text-xs font-bold hover:bg-slate-800">{copied === codeKey ? "Copied" : "Copy code"}</button>
        </div>
        <pre className="overflow-x-auto p-4 text-sm leading-6"><code>{block.code}</code></pre>
        {block.explanation ? <LessonText className="border-t border-slate-700 px-4 py-2 text-sm leading-6 text-slate-300" text={block.explanation} /> : null}
      </section>
    );
  }
  if (block.type === "table") {
    return (
      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white" key={index}>
        <h3 className="px-4 pt-4 font-bold text-ink">{block.title}</h3>
        <div className="mt-3 overflow-x-auto"><table className="min-w-full border-collapse text-left text-sm"><thead className="bg-slate-100 text-slate-800"><tr>{block.columns.map((column, i) => <th className="border-y border-slate-200 px-4 py-3 font-bold" key={i}>{column}</th>)}</tr></thead><tbody>{block.rows.map((row, rowIndex) => <tr className={rowIndex % 2 ? "bg-slate-50" : "bg-white"} key={rowIndex}>{row.map((cell, colIndex) => <td className="border-b border-slate-100 px-4 py-3 align-top leading-6 text-slate-700" key={colIndex}>{String(cell)}</td>)}</tr>)}</tbody></table></div>
      </section>
    );
  }
  if (block.type === "steps") {
    return <section className="rounded-xl border border-line bg-white p-4" key={index}><h3 className="font-bold text-ink">{block.title}</h3><ol className="mt-2 list-decimal space-y-2 pl-5 text-sm leading-6 text-slate-700">{block.items.map((item, i) => <li key={i}>{item}</li>)}</ol></section>;
  }
  if (block.type === "callout") {
    const style = block.tone === "common_mistake" || block.tone === "warning" ? "border-rose-200 bg-rose-50 text-rose-950" : block.tone === "tip" ? "border-emerald-200 bg-emerald-50 text-emerald-950" : "border-indigo-200 bg-indigo-50 text-indigo-950";
    return <aside className={`rounded-xl border p-4 ${style}`} key={index}><p className="font-bold">{block.title}</p><LessonText className="mt-1 text-sm leading-6" text={block.content} /></aside>;
  }
  if (block.type === "complexity") {
    return <section className="rounded-xl border border-indigo-100 bg-indigo-50 p-4" key={index}><h3 className="font-bold text-ink">Complexity</h3><div className="mt-3 grid gap-3 sm:grid-cols-2"><div className="rounded-lg bg-white p-3"><span className="text-xs font-bold uppercase tracking-wide text-muted">Time</span><p className="mt-1 font-mono text-lg font-bold text-ink">{block.time}</p></div><div className="rounded-lg bg-white p-3"><span className="text-xs font-bold uppercase tracking-wide text-muted">Space</span><p className="mt-1 font-mono text-lg font-bold text-ink">{block.space}</p></div></div>{block.explanation ? <p className="mt-3 text-sm leading-6 text-slate-700">{block.explanation}</p> : null}</section>;
  }
  if (block.type === "diagram") return <DiagramBlock block={block} key={index} />;
  return null;
}

export default function LessonPage() {
  const { skillNodeId } = useParams();
  const [searchParams] = useSearchParams();
  const profileId = searchParams.get("profile_id") || getStoredProfileId();
  const [plan, setPlan] = useState(null);
  const [activeIndex, setActiveIndex] = useState(null);
  const [lessons, setLessons] = useState({});
  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState("");
  const [loadingBlock, setLoadingBlock] = useState(false);
  const [copiedCode, setCopiedCode] = useState("");

  useEffect(() => {
    let alive = true;
    getLearningPlan(profileId, skillNodeId)
      .then((value) => { if (alive) setPlan(value); })
      .catch((err) => { if (alive) setError(err.message || "Unable to create the learning plan."); });
    return () => { alive = false; };
  }, [profileId, skillNodeId]);

  const activeBlock = useMemo(() => activeIndex !== null && activeIndex < (plan?.blocks.length || 0) ? plan.blocks[activeIndex] : null, [activeIndex, plan]);
  const extraIndex = plan?.blocks.length || 0;
  const extraBlock = { title: "Explore further", objective: `Explore a useful next idea in ${plan?.topic || "this topic"}`, subtopics: [] };

  async function openBlock(index, block = plan.blocks[index], force = false) {
    setActiveIndex(index);
    if (!force && lessons[index]) return;
    setLoadingBlock(true);
    setError("");
    try {
      const result = await generateLearningBlock({
        profile_id: profileId,
        skill_node_id: skillNodeId,
        block_index: index,
        block,
        feedback,
        completed_blocks: Object.entries(lessons).map(([i, value]) => ({
          title: value.lesson.title,
          objective: plan.blocks[Number(i)]?.objective || ""
        }))
      });
      setLessons((current) => ({ ...current, [index]: result }));
    } catch (err) {
      setError(err.message || "Unable to generate this lesson block.");
    } finally {
      setLoadingBlock(false);
    }
  }

  async function regenerate() {
    if (activeIndex === null) return;
    setLessons((current) => {
      const next = { ...current };
      delete next[activeIndex];
      return next;
    });
    await openBlock(activeIndex, activeBlock || extraBlock, true);
  }

  async function copyCode(code, key) {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedCode(key);
      window.setTimeout(() => setCopiedCode(""), 1600);
    } catch {
      setError("Clipboard access is unavailable in this browser.");
    }
  }

  if (error && !plan) return <main className="lesson-page mx-auto max-w-5xl px-6 py-8"><section className="section-card"><p>{error}</p><Link className="mt-4 inline-block text-indigo" to="/roadmap">Back to roadmap</Link></section></main>;
  if (!plan) return <LoadingState />;
  const current = activeIndex === null ? null : lessons[activeIndex];
  const displayedBlockNumber = activeIndex === null ? 0 : Math.min(activeIndex + 1, plan.blocks.length);

  return (
    <main className="lesson-page mx-auto max-w-6xl px-6 py-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-4"><Link to="/roadmap" className="text-sm font-bold text-indigo">Back to roadmap</Link><Link to={`/assessment/topic?skill_node_id=${encodeURIComponent(skillNodeId)}&profile_id=${encodeURIComponent(profileId)}`} className="text-sm font-bold text-indigo">Take topic assessment</Link></div>
        <span className="text-xs text-muted">Generated by {current?.provider || plan.provider} / {current?.model || plan.model}; lesson text is temporary in this page.</span>
      </div>
      <header className="section-card mb-4">
        <p className="text-sm font-bold uppercase tracking-wide text-indigo">Personalized learning</p>
        <h1 className="mt-2 text-3xl font-bold text-ink">{plan.topic}</h1>
        <p className="mt-2 max-w-3xl text-slate-700">This plan has {plan.blocks.length} focused block{plan.blocks.length === 1 ? "" : "s"}. The number is based on the concepts needed to teach this topic.</p>
        <p className="mt-2 text-sm text-muted">Choose a block to generate its lesson. You can request a programming language or a different explanation style in the tutor prompt.</p>
      </header>

      <MisconceptionIndicators indicators={plan.misconception_indicators} />

      <div className="mt-4 grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
        <section className="space-y-3" aria-label="Topic lesson plan">
          {plan.blocks.map((block, index) => (
            <button key={`${block.title}-${index}`} type="button" onClick={() => openBlock(index)} className={`w-full rounded-xl border p-4 text-left ${activeIndex === index ? "border-indigo bg-indigo/5" : "border-line bg-white"}`}>
              <span className="text-xs font-bold uppercase tracking-wide text-indigo">Block {index + 1}</span>
              <h2 className="mt-1 font-bold text-ink">{block.title}</h2>
              <p className="mt-1 text-sm text-slate-600">{block.objective}</p>
              {lessons[index] ? <span className="mt-2 inline-block text-xs font-bold text-emerald-700">Lesson generated</span> : null}
            </button>
          ))}
          <div className="rounded-xl border border-dashed border-slate-300 bg-white p-4">
            <h2 className="font-bold text-ink">Want to explore further?</h2>
            <p className="mt-1 text-sm text-slate-600">Ask for one optional extension after completing this plan.</p>
            <button type="button" className="mt-3 rounded-lg border border-indigo px-4 py-2 text-sm font-bold text-indigo" onClick={() => openBlock(extraIndex, extraBlock)}>Generate optional extension</button>
          </div>
        </section>

        <section className="section-card min-h-96">
          <label className="block text-sm font-bold text-ink" htmlFor="lesson-feedback">Prompt the tutor</label>
          <textarea id="lesson-feedback" className="mt-2 w-full rounded-lg border border-line p-3 text-sm" rows="3" maxLength={400} placeholder="For example: make this simpler, add a real-world example, or show code in C++, Python, Java, or Kotlin" value={feedback} onChange={(event) => setFeedback(event.target.value)} />
          {error ? <p className="mt-3 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p> : null}
          {loadingBlock ? <div className="mt-6"><LoadingState /></div> : null}
          {!loadingBlock && !current ? <p className="mt-6 text-slate-600">Choose a block to generate and read its lesson.</p> : null}
          {!loadingBlock && current ? (
            <article className="mt-5 space-y-5">
              <div><p className="text-xs font-bold uppercase tracking-wide text-indigo">{activeIndex >= plan.blocks.length ? "Optional extension" : `Block ${displayedBlockNumber}`}</p><h2 className="mt-1 text-2xl font-bold text-ink">{current.lesson.title}</h2><LessonText className="mt-3 text-slate-700" text={current.lesson.overview} /></div>
              <MisconceptionIndicators indicators={current.misconception_indicators} guidance={current.lesson.misconception_guidance} />
              {current.lesson.content_blocks.map((block, index) => <ContentBlock block={block} index={index} key={`${block.type}-${index}`} onCopy={copyCode} copied={copiedCode} />)}
              <section><h3 className="font-bold text-ink">Key takeaways</h3><ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-slate-700">{current.lesson.key_takeaways.map((point, index) => <li key={index}><InlineLessonText text={point} /></li>)}</ul></section>
              {current.sources.length ? <details className="rounded-lg border border-line p-3 text-xs text-slate-600"><summary className="cursor-pointer font-bold">Retrieved context ({current.sources.length} items)</summary><ul className="mt-2 space-y-2">{current.sources.map((source) => <li key={source.source_id}><strong>{source.source_id}</strong>: {source.content}</li>)}</ul></details> : null}
              <div className="flex flex-wrap gap-2">
                <button className="rounded-lg border border-indigo px-4 py-2 text-sm font-bold text-indigo" onClick={regenerate} type="button">Regenerate with my prompt</button>
                {activeIndex < plan.blocks.length - 1 ? <button className="rounded-lg bg-indigo px-4 py-2 text-sm font-bold text-white" onClick={() => openBlock(activeIndex + 1)} type="button">Next block</button> : activeIndex < plan.blocks.length ? <Link to="/roadmap" className="rounded-lg bg-indigo px-4 py-2 text-sm font-bold text-white">Return to roadmap</Link> : <Link to="/roadmap" className="rounded-lg bg-indigo px-4 py-2 text-sm font-bold text-white">Return to roadmap</Link>}
              </div>
            </article>
          ) : null}
        </section>
      </div>
      <p className="mt-4 text-xs text-muted">Lessons are generated on demand and remain in this page only. Retrieved snippets come from the seeded DSA question explanations.</p>
    </main>
  );
}
