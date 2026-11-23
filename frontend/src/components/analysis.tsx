"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { CheckCircle2, Download, FileText, Loader2, ShieldAlert, ShieldCheck, StickyNote, Trash2, Upload } from "lucide-react";
import { analyseFile, apiUrl, deleteInvestigation, getInvestigation, getInvestigations, saveNotes } from "@/services/api";
import type { AlgorithmStatus, Investigation, InvestigationSummary } from "@/types/api";

export type Progress = { fraction: number; stage: string } | null;

/**
 * Shared state for the image/video analysis pages: the investigation list for one
 * media type, the selected investigation (?id=, defaulting to the newest), uploads
 * with real progress, and deletion.
 */
export function useAnalysis<R>(kind: "image" | "video") {
  const params = useSearchParams();
  const router = useRouter();
  const [list, setList] = useState<InvestigationSummary[] | null>(null);
  const [detail, setDetail] = useState<Investigation<R> | null>(null);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState<Progress>(null);
  const selected = params.get("id") ?? list?.[0]?.id ?? null;

  async function refresh() {
    try { setList((await getInvestigations()).filter(i => i.media_type === kind)); }
    catch (e) { setList([]); setError(e instanceof Error ? e.message : "Could not load investigations"); }
  }
  useEffect(() => { refresh(); }, [kind]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!selected) { setDetail(null); return; }
    let live = true;
    setDetail(null);
    getInvestigation<R>(selected)
      .then(d => { if (!live) return; if (d.media_type !== kind) throw new Error(`That investigation is a ${d.media_type}, not a ${kind}.`); setDetail(d); })
      .catch(e => live && setError(e.message));
    return () => { live = false; };
  }, [selected, kind]);

  async function upload(file: File) {
    setProgress({ fraction: 0, stage: "Uploading" }); setError("");
    try {
      const { id } = await analyseFile(file, (fraction, stage) => setProgress({ fraction, stage }));
      await refresh();
      router.replace(`?id=${id}`);
    } catch (e) { setError(e instanceof Error ? e.message : "Upload failed"); }
    finally { setProgress(null); }
  }

  async function remove(id: string) {
    try {
      await deleteInvestigation(id);
      const rest = (list ?? []).filter(i => i.id !== id);
      setList(rest);
      router.replace(rest[0] ? `?id=${rest[0].id}` : "?");
    } catch (e) { setError(e instanceof Error ? e.message : "Delete failed"); }
  }

  return { list, detail, selected, error, progress, uploading: progress !== null, upload, remove };
}

export function ProgressBar({ progress }: { progress: Progress }) {
  if (!progress) return null;
  const pct = Math.round(progress.fraction * 100);
  return <div className="progress" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={progress.stage}>
    <div className="progress-label"><span>{progress.stage}…</span><span>{pct}%</span></div>
    <div className="progress-track"><div className="progress-fill" style={{ width: `${pct}%` }} /></div>
  </div>;
}

export function AnalysisLayout({ kind, eyebrow, title, accept, state, children }: {
  kind: "image" | "video"; eyebrow: string; title: string; accept: string;
  state: { list: InvestigationSummary[] | null; selected: string | null; error: string; uploading: boolean; progress: Progress; upload: (f: File) => void; detail: Investigation<unknown> | null };
  children: React.ReactNode;
}) {
  const input = useRef<HTMLInputElement>(null);
  const { list, selected, error, uploading, progress, upload, detail } = state;
  return <>
    <div className="topline">
      <div><div className="eyebrow">{eyebrow}</div><h1 className="title">{title}</h1></div>
      <div style={{ display: "flex", gap: 8 }}>
        {detail && <a className="btn btn-secondary" href={apiUrl(`/api/reports/${detail.id}/download`)}><Download size={15} /> PDF report</a>}
        <input ref={input} type="file" accept={accept} hidden onChange={e => { const f = e.target.files?.[0]; if (f) upload(f); e.target.value = ""; }} />
        <button className="btn" disabled={uploading} onClick={() => input.current?.click()}>
          {uploading ? <><Loader2 size={15} className="spin" /> Analysing {Math.round((progress?.fraction ?? 0) * 100)}%</> : <><Upload size={15} /> Analyse {kind}</>}
        </button>
      </div>
    </div>
    {progress && <div style={{ marginBottom: 16 }}><ProgressBar progress={progress} /></div>}
    {error && <div className="error" style={{ marginBottom: 16 }}>{error}</div>}
    <div className="analysis-layout">
      <aside className="panel case-list">
        <div className="section-title" style={{ marginBottom: 10 }}>{kind === "image" ? "Image" : "Video"} investigations</div>
        {list === null ? <div className="subtle">Loading…</div>
          : list.length === 0 ? <div className="subtle">None yet. Use “Analyse {kind}” to upload one.</div>
          : list.map(i => <Link key={i.id} href={`?id=${i.id}`} className={`case ${i.id === selected ? "active" : ""}`}>
              <b>{i.original_name}</b>
              <span className="stat-note">{new Date(i.created_at).toLocaleString()} · {(i.size_bytes / 1024).toFixed(0)} KB{i.has_notes ? " · notes" : ""}</span>
            </Link>)}
      </aside>
      <section style={{ minWidth: 0 }}>
        {detail ? children
          : selected ? <div className="panel empty"><Loader2 size={20} className="spin" /><p>Loading analysis…</p></div>
          : <div className="panel empty"><FileText size={22} /><p>Select or upload {kind === "image" ? "an image" : "a video"} to see its analysis.</p></div>}
      </section>
    </div>
  </>;
}

/** Re-hash the stored original on demand and show the answer inline. */
export function VerifyIntegrity({ id }: { id: string }) {
  const [state, setState] = useState<"idle" | "checking" | "ok" | "changed" | "error">("idle");
  useEffect(() => setState("idle"), [id]);
  async function check() {
    setState("checking");
    try { const r = await (await fetch(apiUrl(`/api/investigations/${id}/verify`))).json(); setState(r.integrity_verified ? "ok" : "changed"); }
    catch { setState("error"); }
  }
  if (state === "ok") return <span className="verify ok"><CheckCircle2 size={13} /> Unchanged since intake</span>;
  if (state === "changed") return <span className="verify bad"><ShieldAlert size={13} /> Original has CHANGED since intake</span>;
  return <button className="link-btn" onClick={check} disabled={state === "checking"}>
    <ShieldCheck size={13} /> {state === "checking" ? "Checking…" : state === "error" ? "Could not verify, retry" : "Verify integrity"}</button>;
}

/** Delete with a confirmation step (the original, outputs and report are all removed). */
export function DeleteButton({ name, onDelete }: { name: string; onDelete: () => Promise<void> | void }) {
  const [busy, setBusy] = useState(false);
  async function confirmAndDelete() {
    const message = `Delete the investigation for "${name}"?\n\nThe stored original, its analysis outputs and the PDF report will be permanently removed.`;
    if (!window.confirm(message)) return;
    setBusy(true);
    try { await onDelete(); } finally { setBusy(false); }
  }
  return <button className="link-btn danger" disabled={busy} onClick={confirmAndDelete}><Trash2 size={13} /> {busy ? "Deleting…" : "Delete"}</button>;
}

export function EvidenceHeader({ item, facts, onDelete }: { item: Investigation<unknown>; facts: [string, string][]; onDelete?: () => Promise<void> | void }) {
  return <div className="panel">
    <div className="method-head">
      <div className="section-title">{item.original_file.name}</div>
      {onDelete && <DeleteButton name={item.original_file.name} onDelete={onDelete} />}
    </div>
    <div className="facts">
      {facts.map(([k, v]) => <div key={k}><div className="stat-note">{k}</div><div className="fact">{v}</div></div>)}
    </div>
    <div className="kv" style={{ borderBottom: 0 }}>
      <span>SHA-256</span>
      <span><span className="hash">{item.sha256}</span>{" "}<VerifyIntegrity id={item.id} /></span>
    </div>
  </div>;
}

/** Investigator's free-text notes, saved to the investigation and included in the PDF report. */
export function NotesPanel({ id, initial }: { id: string; initial: string }) {
  const [text, setText] = useState(initial);
  const [saved, setSaved] = useState(initial);
  const [state, setState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  useEffect(() => { setText(initial); setSaved(initial); setState("idle"); }, [id, initial]);
  async function save() {
    setState("saving");
    try { const stored = await saveNotes(id, text); setSaved(stored); setText(stored); setState("saved"); }
    catch { setState("error"); }
  }
  const status = state === "saving" ? "Saving…" : state === "error" ? "Could not save" : text !== saved ? "Unsaved changes"
    : state === "saved" ? "Saved · included in the PDF report" : "";
  return <div className="panel">
    <div className="method-head">
      <div className="section-title"><StickyNote size={15} style={{ verticalAlign: -2 }} /> Case notes</div>
      <span className="stat-note">{status}</span>
    </div>
    <textarea className="notes" value={text} maxLength={10000} onChange={e => setText(e.target.value)}
      placeholder="Record what you checked, who you contacted and your conclusions. Notes are kept with the investigation and printed in its PDF report." />
    <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}>
      <button className="btn btn-secondary" disabled={text === saved || state === "saving"} onClick={save}>Save notes</button>
    </div>
  </div>;
}

export function Metric({ label, value, note }: { label: string; value: React.ReactNode; note?: string }) {
  return <div className="stat"><div className="stat-label">{label}</div><div className="stat-value" style={{ fontSize: 22, margin: "10px 0 4px" }}>{value}</div>{note && <div className="stat-note">{note}</div>}</div>;
}

/** One forensic technique: what it measures, how to read it, its outputs and its caveat. */
export function MethodCard({ title, result, what, read, caveat, children }: {
  title: string; result?: AlgorithmStatus; what: string; read: string; caveat?: string; children?: React.ReactNode;
}) {
  return <div className="panel method">
    <div className="method-head"><div className="section-title">{title}</div>
      <span className={`badge ${result?.status === "error" ? "badge-error" : ""}`}>{result?.status ?? "not run"}</span></div>
    <p className="subtle"><b>What it does.</b> {what}</p>
    <p className="subtle"><b>How to read it.</b> {read}</p>
    {result?.status === "error" ? <div className="error">This check failed: {result.error}</div> : result ? children : <div className="subtle">No result recorded.</div>}
    {caveat && result?.status === "completed" && <p className="caveat">{caveat}</p>}
  </div>;
}

export function Limitations({ items, statement }: { items: string[]; statement?: string }) {
  return <div className="panel" style={{ marginTop: 14 }}>
    <div className="section-title">Interpretation limits</div>
    {items.map(v => <p className="subtle" key={v} style={{ margin: "6px 0" }}>• {v}</p>)}
    {statement && <p className="subtle"><b>{statement}</b></p>}
  </div>;
}

export const fmt = (v: number | undefined, digits = 2) => v === undefined || Number.isNaN(v) ? "—" : v.toFixed(digits);
export const fmtTime = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toFixed(1).padStart(4, "0")}`;
