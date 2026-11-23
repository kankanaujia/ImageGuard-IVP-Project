"use client";
import { Suspense, useEffect, useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { X, ZoomIn } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Shell } from "@/components/shell";
import { AnalysisLayout, EvidenceHeader, Limitations, MethodCard, Metric, NotesPanel, fmt, useAnalysis } from "@/components/analysis";
import { apiUrl, artifactUrl } from "@/services/api";
import type { ImageResult, Investigation } from "@/types/api";

const ACCEPT = ".jpg,.jpeg,.png,.tiff,.tif,.bmp,.webp";

export default function ImageAnalysisPage() {
  return <Shell><Suspense fallback={null}><ImageAnalysis /></Suspense></Shell>;
}

function ImageAnalysis() {
  const state = useAnalysis<ImageResult>("image");
  return <AnalysisLayout kind="image" eyebrow="Image examination" title="Image forensics" accept={ACCEPT} state={state}>
    {state.detail && <ImageReport key={state.detail.id} item={state.detail} onDelete={() => state.remove(state.detail!.id)} />}
  </AnalysisLayout>;
}

function ImageReport({ item, onDelete }: { item: Investigation<ImageResult>; onDelete: () => Promise<void> }) {
  const r = item.result;
  const { ela, orb, noise, compression, histogram, metadata } = r.algorithms;
  const exifCount = metadata?.status === "completed" ? Object.keys(metadata.exif).length : undefined;
  const flagged = orb?.flagged ?? (orb?.candidate_matches ?? 0) >= 4;   // older results have no "flagged" field
  const pct = (v?: number) => v === undefined ? "—" : `${(100 * v).toFixed(1)}%`;

  return <div className="stack">
    <EvidenceHeader item={item} onDelete={onDelete} facts={[
      ["Format", r.original_image.format], ["Dimensions", `${r.original_image.width} × ${r.original_image.height}`],
      ["Colour mode", r.original_image.mode], ["File size", `${(item.original_file.size_bytes / 1024).toFixed(1)} KB`],
      ["Processed in", `${r.processing_seconds}s`], ["Analysed", new Date(item.created_at).toLocaleString()],
    ]} />

    <div className="metrics">
      <Metric label="Candidate indicators" value={r.indicator_summary.candidate_indicators} note="Checks that flagged something" />
      <Metric label="Copy-move" value={orb?.status === "completed" ? (flagged ? "Flagged" : "Not flagged") : "—"}
        note={orb?.status !== "completed" ? "check failed" : orb.geometrically_consistent_matches === 0 ? "No consistent match group"
          : `${orb.geometrically_consistent_matches} consistent matches${orb.copy_shift_px ? ` · ${fmt(orb.copy_shift_px, 0)} px apart` : ""}`} />
      <Metric label="ELA unusual blocks" value={pct(ela?.unusual_block_share)} note={ela?.block_z_max !== undefined ? `Strongest ${fmt(ela.block_z_max, 1)} deviations` : "Re-analyse for the heat map"} />
      <Metric label="Noise unusual blocks" value={pct(noise?.unusual_block_share)} note={noise?.block_z_max_abs !== undefined ? `Strongest ${fmt(noise.block_z_max_abs, 1)} deviations` : "Re-analyse for the heat map"} />
      <Metric label="JPEG quality" value={compression?.estimated_quality !== undefined ? `≈ ${compression.estimated_quality}` : compression?.is_jpeg === false ? "Not JPEG" : "—"}
        note={compression?.standard_ijg_tables === undefined ? `${exifCount ?? "—"} EXIF tags` : compression.standard_ijg_tables ? "Standard (software) tables" : "Custom (camera) tables"} />
    </div>

    <CompareViewer item={item} />

    <div className="result-grid">
      <MethodCard title="Error level analysis (ELA)" result={ela}
        what="Re-saves the image as JPEG at quality 90 and shows the per-pixel difference. The heat map compares every 16×16 block with the rest of this image."
        read="In the heat map, bright blocks recompress differently from their surroundings and may have a different compression history. The global peak mostly reflects how the whole file was last saved, so rely on the map, not the peak."
        caveat={ela?.map_note ?? ela?.note}>
        {ela?.status === "completed" && <>
          {ela.unusual_block_share !== undefined && <div className="kv"><span>Unusual blocks (≥ 3.5 deviations)</span><span>{pct(ela.unusual_block_share)} · strongest {fmt(ela.block_z_max, 1)}</span></div>}
          <div className="kv"><span>Peak difference (whole image)</span><span>{ela.difference_peak} / 255 at quality {ela.quality}</span></div>
        </>}
      </MethodCard>

      <MethodCard title="Copy-move detection (ORB)" result={orb}
        what="Matches ORB keypoints within the image and keeps groups of matches that agree on one shift or rotation (RANSAC). The image is flagged when a group of at least 5 matches has its copy at least 40 px from the source."
        read="Lines join each source point (green) to its copy (red). A bundle of parallel lines between two areas is worth a close look; natural repetition such as windows, tiles or foliage can also match."
        caveat={orb?.interpretation}>
        {orb?.status === "completed" && <>
          <div className="kv"><span>Keypoints · raw self-matches</span><span>{orb.keypoints} · {orb.raw_candidate_matches}</span></div>
          <div className="kv"><span>Largest consistent group</span><span>{orb.geometrically_consistent_matches === 0 ? "None found"
            : `${orb.geometrically_consistent_matches} matches${orb.copy_shift_px !== undefined ? `, copy ${fmt(orb.copy_shift_px, 0)} px from source` : ""}`}</span></div>
          <div className="kv"><span>Result</span><span>{flagged ? <span className="badge badge-warn">flagged for review</span> : "Not flagged"}</span></div>
        </>}
      </MethodCard>

      <MethodCard title="Noise consistency" result={noise}
        what="Estimates the local noise level of every 16×16 block from the finest wavelet detail band (median absolute coefficient ÷ 0.6745) and compares it with the rest of the image."
        read="Bright blocks are much smoother or much noisier than the rest of the photo, as content pasted from another camera or processing chain often is. Sky, saturated highlights and blurred backgrounds can also stand out."
        caveat={noise?.map_note ?? noise?.note}>
        {noise?.status === "completed" && <>
          {noise.unusual_block_share !== undefined && <div className="kv"><span>Unusual blocks (≥ 3.5 deviations)</span><span>{pct(noise.unusual_block_share)} · strongest {fmt(noise.block_z_max_abs, 1)}</span></div>}
          <div className="kv"><span>Residual mean · σ</span><span>{fmt(noise.residual_mean)} · {fmt(noise.residual_std)}</span></div>
        </>}
      </MethodCard>

      <MethodCard title="Compression history" result={compression}
        what="Reads the JPEG quantization tables, which record how the file was last saved, and estimates the quality setting."
        read="Standard IJG tables suggest the file was last saved by software (an editor, app or website) rather than straight from a camera. That is common and legitimate, but worth knowing when a file is claimed to be a camera original."
        caveat={compression?.note}>
        {compression?.status === "completed" && <>
          {compression.is_jpeg && compression.estimated_quality !== undefined && <>
            <div className="kv"><span>Estimated quality</span><span>≈ {compression.estimated_quality}</span></div>
            <div className="kv"><span>Quantization tables</span><span>{compression.standard_ijg_tables ? "Standard IJG (software)" : "Custom (camera or editor)"}</span></div>
            <div className="kv"><span>Chroma subsampling · progressive</span><span>{compression.chroma_subsampling} · {compression.progressive ? "yes" : "no"}</span></div>
          </>}
          {compression.observations.map(o => <p className="subtle" key={o} style={{ margin: "6px 0" }}>• {o}</p>)}
        </>}
      </MethodCard>

      <MethodCard title="Colour histogram" result={histogram}
        what="Counts how many pixels have each brightness value (0–255) in the red, green and blue channels."
        read="Gaps or regular comb-like spikes can come from contrast or levels adjustments. Clipping at 0 or 255 shows lost shadow or highlight detail."
        caveat="Histograms describe the whole image and cannot locate an edit.">
        {histogram?.status === "completed" && <>
          <HistogramChart counts={histogram.rgb_counts} />
          <div className="kv"><span>Grey mean · σ</span><span>{fmt(histogram.grayscale_mean, 1)} · {fmt(histogram.grayscale_std, 1)}</span></div>
        </>}
      </MethodCard>

      <MethodCard title="Metadata (EXIF)" result={metadata}
        what="Reads the file's embedded metadata: camera make and model, capture time, software and similar tags."
        read="A Software tag naming an editor, or capture dates that conflict with the story, are leads to check. Missing EXIF is common and proves nothing on its own."
        caveat="Metadata is easy to remove or rewrite.">
        {metadata?.status === "completed" && (Object.keys(metadata.exif).length
          ? <div className="exif">{Object.entries(metadata.exif).map(([k, v]) => <div className="kv" key={k}><span>{k}</span><span style={{ wordBreak: "break-all" }}>{v}</span></div>)}</div>
          : metadata.observations.map(o => <p className="subtle" key={o}>{o}</p>))}
      </MethodCard>
    </div>

    <NotesPanel id={item.id} initial={item.notes ?? ""} />
    <Limitations items={r.limitations} statement={r.indicator_summary.statement} />
  </div>;
}

type View = { key: string; label: string; file?: string };

/** Original vs. one visualisation: side by side, or overlaid with a wipe slider; any view can be zoomed. */
function CompareViewer({ item }: { item: Investigation<ImageResult> }) {
  const a = item.result.algorithms;
  const ok = <T extends { status: string }>(v?: T) => v?.status === "completed" ? v : undefined;
  const views: View[] = [
    { key: "ela_map", label: "ELA heat map", file: ok(a.ela)?.map_visualization },
    { key: "noise_map", label: "Noise heat map", file: ok(a.noise)?.map_visualization },
    { key: "orb", label: "Copy-move matches", file: ok(a.orb)?.visualization },
    { key: "ela", label: "ELA difference", file: ok(a.ela)?.visualization },
    { key: "noise", label: "Noise residual", file: ok(a.noise)?.visualization },
  ].filter(v => v.file);
  // ?view=orb&mode=slider opens a specific comparison (shareable deep link)
  const params = useSearchParams();
  const [key, setKey] = useState(views.some(v => v.key === params.get("view")) ? params.get("view")! : views[0]?.key);
  const [mode, setMode] = useState<"side" | "slider">(params.get("mode") === "slider" ? "slider" : "side");
  const [split, setSplit] = useState(50);
  const [zoom, setZoom] = useState<{ src: string; label: string } | null>(null);
  const view = views.find(v => v.key === key) ?? views[0];
  const original = apiUrl(`/api/investigations/${item.id}/original`);
  if (!view) return <div className="panel error">No visualizations are available for this investigation.</div>;
  const visual = artifactUrl(item.id, view.file!);

  return <div className="panel">
    <div className="method-head">
      <div className="section-title">Visual comparison</div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <div className="tabs">{views.map(v => <button key={v.key} className={view.key === v.key ? "active" : ""} onClick={() => setKey(v.key)}>{v.label}</button>)}</div>
        <div className="tabs">
          <button className={mode === "side" ? "active" : ""} onClick={() => setMode("side")}>Side by side</button>
          <button className={mode === "slider" ? "active" : ""} onClick={() => setMode("slider")}>Slider</button>
        </div>
      </div>
    </div>
    {mode === "side" ? <div className="compare">
      <figure><button className="zoomable" onClick={() => setZoom({ src: original, label: "Original" })}><img className="artifact" src={original} alt="Original evidence" /><ZoomIn size={15} className="zoom-icon" /></button>
        <figcaption>Original · click to zoom</figcaption></figure>
      <figure><button className="zoomable" onClick={() => setZoom({ src: visual, label: view.label })}><img className="artifact" src={visual} alt={view.label} /><ZoomIn size={15} className="zoom-icon" /></button>
        <figcaption>{view.label} · click to zoom</figcaption></figure>
    </div> : <div>
      <div className="wipe">
        <img src={original} alt="Original evidence" />
        <img src={visual} alt={view.label} style={{ clipPath: `inset(0 0 0 ${split}%)` }} />
        <div className="wipe-line" style={{ left: `${split}%` }} />
      </div>
      <div className="wipe-controls">
        <span className="stat-note">Original</span>
        <input type="range" min={0} max={100} value={split} onChange={e => setSplit(Number(e.target.value))} aria-label="Wipe between original and visualization" />
        <span className="stat-note">{view.label}</span>
      </div>
    </div>}
    {zoom && <ZoomDialog src={zoom.src} label={zoom.label} onClose={() => setZoom(null)} />}
  </div>;
}

function ZoomDialog({ src, label, onClose }: { src: string; label: string; onClose: () => void }) {
  const [scale, setScale] = useState(2);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return <div className="lightbox" role="dialog" aria-modal="true" aria-label={`${label} zoomed`} onClick={onClose}>
    <div className="lightbox-bar" onClick={e => e.stopPropagation()}>
      <b>{label}</b>
      <div className="tabs">{[1, 2, 4].map(s => <button key={s} className={scale === s ? "active" : ""} onClick={() => setScale(s)}>{s}×</button>)}</div>
      <button className="link-btn" onClick={onClose} aria-label="Close"><X size={16} /> Close</button>
    </div>
    <div className="lightbox-body" onClick={e => e.stopPropagation()}>
      <img src={src} alt={label} style={{ width: `${scale * 100}%`, maxWidth: "none" }} />
    </div>
  </div>;
}

function HistogramChart({ counts }: { counts: number[][] }) {
  // OpenCV returns channels in B, G, R order.
  const data = useMemo(() => counts[0].map((_, i) => ({ v: i, b: counts[0][i], g: counts[1][i], r: counts[2][i] })), [counts]);
  return <div style={{ height: 180, marginTop: 10 }}>
    <ResponsiveContainer>
      <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -18 }}>
        <CartesianGrid stroke="#1c293a" vertical={false} />
        <XAxis dataKey="v" ticks={[0, 64, 128, 192, 255]} tick={{ fill: "#74849a", fontSize: 10 }} stroke="#2a3c55" />
        <YAxis tick={{ fill: "#74849a", fontSize: 10 }} stroke="#2a3c55" tickFormatter={n => n >= 1000 ? `${Math.round(n / 1000)}k` : n} />
        <Tooltip contentStyle={{ background: "#101a28", border: "1px solid #2a3c55", fontSize: 11 }} labelFormatter={v => `Value ${v}`} />
        <Area type="monotone" dataKey="r" name="Red" stroke="#ef6262" fill="#ef6262" fillOpacity={0.15} dot={false} isAnimationActive={false} />
        <Area type="monotone" dataKey="g" name="Green" stroke="#6fcf97" fill="#6fcf97" fillOpacity={0.15} dot={false} isAnimationActive={false} />
        <Area type="monotone" dataKey="b" name="Blue" stroke="#61a9ff" fill="#61a9ff" fillOpacity={0.15} dot={false} isAnimationActive={false} />
      </AreaChart>
    </ResponsiveContainer>
  </div>;
}
