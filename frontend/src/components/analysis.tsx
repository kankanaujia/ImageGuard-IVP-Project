"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Download, FileText, Loader2, ShieldCheck, Upload } from "lucide-react";
import { apiUrl, getInvestigation, getInvestigations, uploadEvidence } from "@/services/api";
import type { AlgorithmStatus, Investigation, InvestigationSummary } from "@/types/api";

/**
 * Shared state for the image/video analysis pages: the investigation list for one
 * media type, the selected investigation (?id=, defaulting to the newest) and uploads.
 */
export function useAnalysis<R>(kind: "image" | "video") {
  const params = useSearchParams();
  const router = useRouter();
  const [list, setList] = useState<InvestigationSummary[] | null>(null);
  const [detail, setDetail] = useState<Investigation<R> | null>(null);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const selected = params.get("id") ?? list?.[0]?.id ?? null;

  useEffect(() => {
    getInvestigations().then(all => setList(all.filter(i => i.media_type === kind))).catch(e => { setList([]); setError(e.message); });
  }, [kind]);

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
    setUploading(true); setError("");
    try {
      const result = await uploadEvidence(file, kind);
      setList(prev => [{ id: result.id, media_type: kind, original_name: result.original_file.name, size_bytes: result.original_file.size_bytes, sha256: result.sha256, created_at: result.created_at }, ...(prev ?? [])]);
      router.replace(`?id=${result.id}`);
    } catch (e) { setError(e instanceof Error ? e.message : "Upload failed"); }
    finally { setUploading(false); }
  }

  return { list, detail, selected, error, uploading, upload };
}

export function AnalysisLayout({ kind, eyebrow, title, accept, state, children }: {
  kind: "image" | "video"; eyebrow: string; title: string; accept: string;
  state: { list: InvestigationSummary[] | null; selected: string | null; error: string; uploading: boolean; upload: (f: File) => void; detail: Investigation<unknown> | null };
  children: React.ReactNode;
}) {
  const input = useRef<HTMLInputElement>(null);
  const { list, selected, error, uploading, upload, detail } = state;
  return <>
    <div className="topline">
      <div><div className="eyebrow">{eyebrow}</div><h1 className="title">{title}</h1></div>
      <div style={{ display: "flex", gap: 8 }}>
        {detail && <a className="btn btn-secondary" href={apiUrl(`/api/reports/${detail.id}/download`)}><Download size={15} /> PDF report</a>}
        <input ref={input} type="file" accept={accept} hidden onChange={e => { const f = e.target.files?.[0]; if (f) upload(f); e.target.value = ""; }} />
        <button className="btn" disabled={uploading} onClick={() => input.current?.click()}>
          {uploading ? <><Loader2 size={15} className="spin" /> Analysing…</> : <><Upload size={15} /> Analyse {kind}</>}
        </button>
      </div>
    </div>
    {error && <div className="error" style={{ marginBottom: 16 }}>{error}</div>}
    <div className="analysis-layout">
      <aside className="panel case-list">
        <div className="section-title" style={{ marginBottom: 10 }}>{kind === "image" ? "Image" : "Video"} investigations</div>
        {list === null ? <div className="subtle">Loading…</div>
          : list.length === 0 ? <div className="subtle">None yet. Use “Analyse {kind}” to upload one.</div>
          : list.map(i => <Link key={i.id} href={`?id=${i.id}`} className={`case ${i.id === selected ? "active" : ""}`}>
              <b>{i.original_name}</b>
              <span className="stat-note">{new Date(i.created_at).toLocaleString()} · {(i.size_bytes / 1024).toFixed(0)} KB</span>
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

export function EvidenceHeader({ item, facts }: { item: Investigation<unknown>; facts: [string, string][] }) {
  return <div className="panel">
    <div className="section-title">{item.original_file.name}</div>
    <div className="facts">
      {facts.map(([k, v]) => <div key={k}><div className="stat-note">{k}</div><div className="fact">{v}</div></div>)}
    </div>
    <div className="kv" style={{ borderBottom: 0 }}>
      <span>SHA-256</span>
      <span><span className="hash">{item.sha256}</span>{" "}
        <a href={apiUrl(`/api/investigations/${item.id}/verify`)} target="_blank" rel="noreferrer" style={{ color: "#74d4a3", fontSize: 11, whiteSpace: "nowrap" }}><ShieldCheck size={12} /> Verify</a></span>
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
