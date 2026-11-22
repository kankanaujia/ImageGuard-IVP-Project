"use client";
import { Suspense, useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Shell } from "@/components/shell";
import { AnalysisLayout, EvidenceHeader, Limitations, MethodCard, Metric, fmt, useAnalysis } from "@/components/analysis";
import { apiUrl, artifactUrl } from "@/services/api";
import type { ImageResult, Investigation } from "@/types/api";

const ACCEPT = ".jpg,.jpeg,.png,.tiff,.tif,.bmp,.webp";

export default function ImageAnalysisPage() {
  return <Shell><Suspense fallback={null}><ImageAnalysis /></Suspense></Shell>;
}

function ImageAnalysis() {
  const state = useAnalysis<ImageResult>("image");
  return <AnalysisLayout kind="image" eyebrow="Image examination" title="Image forensics" accept={ACCEPT} state={state}>
    {state.detail && <ImageReport item={state.detail} />}
  </AnalysisLayout>;
}

function ImageReport({ item }: { item: Investigation<ImageResult> }) {
  const r = item.result;
  const { ela, orb, noise, histogram, metadata } = r.algorithms;
  const tileRatio = noise?.status === "completed" && noise.tile_variance_min > 0 ? noise.tile_variance_max / noise.tile_variance_min : undefined;
  const exifCount = metadata?.status === "completed" ? Object.keys(metadata.exif).length : undefined;
  const flagged = (orb?.candidate_matches ?? 0) >= 4;

  return <div className="stack">
    <EvidenceHeader item={item} facts={[
      ["Format", r.original_image.format], ["Dimensions", `${r.original_image.width} × ${r.original_image.height}`],
      ["Colour mode", r.original_image.mode], ["File size", `${(item.original_file.size_bytes / 1024).toFixed(1)} KB`],
      ["Processed in", `${r.processing_seconds}s`], ["Analysed", new Date(item.created_at).toLocaleString()],
    ]} />

    <div className="metrics">
      <Metric label="Candidate indicators" value={r.indicator_summary.candidate_indicators} note="Checks that flagged something" />
      <Metric label="Copy-move matches" value={orb?.status === "completed" ? orb.geometrically_consistent_matches : "—"} note={orb?.status === "completed" ? `${orb.raw_candidate_matches} raw · ${flagged ? "review" : "below threshold"}` : "check failed"} />
      <Metric label="ELA peak difference" value={ela?.status === "completed" ? ela.difference_peak : "—"} note={`At JPEG quality ${ela?.quality ?? "—"}`} />
      <Metric label="Noise tile variance ratio" value={tileRatio ? `${fmt(tileRatio, 1)}×` : "—"} note="Max ÷ min across 8×8 grid" />
      <Metric label="EXIF tags" value={exifCount ?? "—"} note={exifCount === 0 ? "No camera metadata" : "Embedded metadata"} />
    </div>

    <CompareViewer item={item} />

    <div className="result-grid">
      <MethodCard title="Error level analysis (ELA)" result={ela}
        what="Re-saves the image as JPEG at a known quality and shows the per-pixel difference, brightened so the largest difference is white."
        read="Areas compressed the same number of times should look similarly bright. A region that glows much more or less than similar content around it may have a different compression history."
        caveat={ela?.note}>
        {ela?.status === "completed" && <>
          <div className="kv"><span>Recompression quality</span><span>{ela.quality}</span></div>
          <div className="kv"><span>Peak difference</span><span>{ela.difference_peak} / 255</span></div>
          <div className="kv"><span>Max difference R · G · B</span><span>{ela.channel_ranges.map(c => c[1]).join(" · ")}</span></div>
        </>}
      </MethodCard>

      <MethodCard title="Copy-move detection (ORB)" result={orb}
        what="Finds ORB keypoints and matches the image against itself. Matches between distant points that agree on one shared shift or rotation (RANSAC) suggest a duplicated region."
        read="Lines join each keypoint to its match. Many parallel lines between the same two areas are worth a closer look; scattered single lines are usually noise."
        caveat={orb?.interpretation}>
        {orb?.status === "completed" && <>
          <div className="kv"><span>Keypoints found</span><span>{orb.keypoints}</span></div>
          <div className="kv"><span>Raw self-matches</span><span>{orb.raw_candidate_matches}</span></div>
          <div className="kv"><span>Geometrically consistent</span><span>{orb.geometrically_consistent_matches} {flagged && <span className="badge badge-warn">review</span>}</span></div>
        </>}
      </MethodCard>

      <MethodCard title="Noise residual analysis" result={noise}
        what="Subtracts a lightly blurred copy from the image, leaving the fine sensor noise and texture, then measures its variance in an 8×8 grid of tiles."
        read="A single camera image tends to have fairly even noise. A tile or region with much smoother or noisier residual than similar content nearby can point to pasted or retouched material."
        caveat={noise?.note}>
        {noise?.status === "completed" && <>
          <div className="kv"><span>Residual mean · σ</span><span>{fmt(noise.residual_mean)} · {fmt(noise.residual_std)}</span></div>
          <div className="kv"><span>Tile variance min · max</span><span>{fmt(noise.tile_variance_min)} · {fmt(noise.tile_variance_max)}</span></div>
          <div className="kv"><span>Variance ratio</span><span>{tileRatio ? `${fmt(tileRatio, 1)}×` : "—"}</span></div>
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
    </div>

    <MethodCard title="Metadata (EXIF)" result={metadata}
      what="Reads the file's embedded metadata: camera make and model, capture time, software and similar tags."
      read="A Software tag naming an editor, or capture dates that conflict with the story, are leads to check. Missing EXIF is common and proves nothing on its own."
      caveat="Metadata is easy to remove or rewrite.">
      {metadata?.status === "completed" && (Object.keys(metadata.exif).length
        ? <div className="exif">{Object.entries(metadata.exif).map(([k, v]) => <div className="kv" key={k}><span>{k}</span><span style={{ wordBreak: "break-all" }}>{v}</span></div>)}</div>
        : metadata.observations.map(o => <p className="subtle" key={o}>{o}</p>))}
    </MethodCard>

    <Limitations items={r.limitations} statement={r.indicator_summary.statement} />
  </div>;
}

const VIEWS = [
  { key: "ela", label: "ELA" }, { key: "noise", label: "Noise residual" }, { key: "orb", label: "Copy-move matches" },
] as const;

/** Original next to a chosen visualization. The ORB output already holds two copies, so it is shown full width. */
function CompareViewer({ item }: { item: Investigation<ImageResult> }) {
  const [view, setView] = useState<(typeof VIEWS)[number]["key"]>("ela");
  const result = item.result.algorithms[view];
  const original = apiUrl(`/api/investigations/${item.id}/original`);
  return <div className="panel">
    <div className="method-head">
      <div className="section-title">Visual comparison</div>
      <div className="tabs">{VIEWS.map(v => <button key={v.key} className={view === v.key ? "active" : ""} onClick={() => setView(v.key)}>{v.label}</button>)}</div>
    </div>
    {result?.status !== "completed" ? <div className="error">This visualization is unavailable{result?.error ? `: ${result.error}` : "."}</div>
      : view === "orb" ? <img className="artifact" src={artifactUrl(item.id, result.visualization)} alt="ORB copy-move matches" />
      : <div className="compare">
          <figure><img className="artifact" src={original} alt="Original evidence" /><figcaption>Original</figcaption></figure>
          <figure><img className="artifact" src={artifactUrl(item.id, result.visualization)} alt={`${view} visualization`} /><figcaption>{VIEWS.find(v => v.key === view)?.label}</figcaption></figure>
        </div>}
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
