"use client";
import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Area, AreaChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CategoricalChartState } from "recharts/types/chart/types";
import { Shell } from "@/components/shell";
import { AnalysisLayout, EvidenceHeader, Limitations, MethodCard, Metric, fmt, fmtTime, useAnalysis } from "@/components/analysis";
import { artifactUrl, frameUrl } from "@/services/api";
import type { Investigation, VideoFrame, VideoResult } from "@/types/api";

const ACCEPT = ".mp4,.avi,.mov,.mkv";
const COLORS = { ssim: "#61a9ff", motion: "#5fd0b5", scene: "#f0a35e", spike: "#ff7aa8" };

export default function VideoAnalysisPage() {
  return <Shell><Suspense fallback={null}><VideoAnalysis /></Suspense></Shell>;
}

function VideoAnalysis() {
  const state = useAnalysis<VideoResult>("video");
  // Keyed by id so the selected frame resets when switching investigations.
  return <AnalysisLayout kind="video" eyebrow="Video examination" title="Video forensics" accept={ACCEPT} state={state}>
    {state.detail && <VideoReport key={state.detail.id} item={state.detail} />}
  </AnalysisLayout>;
}

type EventKind = "scene" | "exact" | "near_duplicate" | "motion";
type Event = { index: number; time: number; kind: EventKind; detail: string };
const EVENT_LABEL: Record<EventKind, [string, string]> = {
  scene: ["scene change", "badge-warn"], exact: ["exact repeat", "badge-dup"], near_duplicate: ["near repeat", "badge-dup"], motion: ["motion spike", "badge-spike"],
};
const same = (a: number, b: number) => Math.abs(a - b) < 1e-6;
/** Mirrors backend optical_flow.flow_file: motion from the previous sample into this frame. */
const flowFile = (f: VideoFrame) => `flow_${String(f.index).padStart(8, "0")}.jpg`;
const axis = { tick: { fill: "#74849a", fontSize: 10 }, stroke: "#2a3c55" };
const tooltipStyle = { background: "#101a28", border: "1px solid #2a3c55", fontSize: 11 };

function VideoReport({ item }: { item: Investigation<VideoResult> }) {
  const r = item.result;
  const { frames, video, ssim, scene_detection: scenes, frame_hashing: hashing, optical_flow: flow } = r;
  const fullFlow = flow?.status === "completed" && !!flow.timestamps; // false for investigations made before full-video flow
  // ?t=<seconds> opens the report at the sampled frame nearest that time (shareable deep link).
  const params = useSearchParams();
  const [selected, setSelected] = useState(() => {
    const t = Number(params.get("t"));
    if (!params.get("t") || Number.isNaN(t)) return 0;
    return frames.reduce((best, f, i) => Math.abs(f.timestamp - t) < Math.abs(frames[best].timestamp - t) ? i : best, 0);
  });

  const at = useMemo(() => (t: number) => frames.findIndex(f => same(f.timestamp, t)), [frames]);

  // Per-frame annotations and the flagged-moments list.
  const { events, marks, series } = useMemo(() => {
    const events: Event[] = [];
    scenes?.candidates?.forEach(c => events.push({ index: at(c.timestamp), time: c.timestamp, kind: "scene", detail: `Histogram distance ${fmt(c.histogram_distance)}` }));
    hashing?.pairs?.forEach(p => events.push({ index: at(p.timestamp), time: p.timestamp, kind: p.kind, detail: `Matches ${fmtTime(p.previous_timestamp)} · hash distance ${p.hamming_distance}` }));
    flow?.spikes?.forEach(s => events.push({ index: at(s.timestamp), time: s.timestamp, kind: "motion", detail: `Mean motion ${fmt(s.mean_motion, 1)} px${s.robust_z !== null ? ` · ${fmt(s.robust_z, 1)}× typical spread above median` : ""}` }));
    events.sort((a, b) => a.time - b.time);
    const marks = new Map<number, Set<EventKind>>();
    events.forEach(e => marks.set(e.index, (marks.get(e.index) ?? new Set()).add(e.kind)));
    // One row per sampled frame after the first: SSIM and motion from the previous sample.
    const byTime = new Map<number, { t: number; s?: number; m?: number; p95?: number }>();
    const row = (t: number) => { const k = Math.round(t * 1e6); if (!byTime.has(k)) byTime.set(k, { t }); return byTime.get(k)!; };
    ssim?.timestamps?.forEach((t, i) => { row(t).s = ssim.scores[i]; });
    flow?.timestamps?.forEach((t, i) => { const x = row(t); x.m = flow.mean_magnitudes![i]; x.p95 = flow.p95_magnitudes![i]; });
    const series = [...byTime.values()].sort((a, b) => a.t - b.t);
    return { events, marks, series };
  }, [scenes, hashing, flow, ssim, at]);

  const ssimPoints = series.filter(p => p.s !== undefined) as { t: number; s: number }[];
  const lowest = ssimPoints.reduce<{ t: number; s: number } | null>((m, p) => !m || p.s < m.s ? p : m, null);
  const current = frames[selected];
  const previous = frames[selected - 1];
  const point = series.find(p => current && same(p.t, current.timestamp));
  const selectFromChart = (e: CategoricalChartState) => { const t = Number(e?.activeLabel); if (!Number.isNaN(t)) { const i = at(t); if (i >= 0) setSelected(i); } };
  const cursorLines = <>
    {scenes?.candidates?.map(c => <ReferenceLine key={`s${c.timestamp}`} x={c.timestamp} stroke={COLORS.scene} strokeDasharray="4 3" />)}
    {flow?.spikes?.map(s => <ReferenceLine key={`m${s.timestamp}`} x={s.timestamp} stroke={COLORS.spike} strokeDasharray="2 3" />)}
    {current && <ReferenceLine x={current.timestamp} stroke="#e8eef7" strokeOpacity={0.35} />}
  </>;

  return <div className="stack">
    <EvidenceHeader item={item} facts={[
      ["Duration", fmtTime(video.duration)], ["Frame rate", `${fmt(video.fps)} fps`],
      ["Resolution", `${video.width} × ${video.height}`], ["Total frames", String(video.frame_count)],
      ["Sampled", `${frames.length} @ every ${video.sample_interval_seconds}s`], ["Processed in", `${r.processing_seconds}s`],
    ]} />

    <div className="metrics">
      <Metric label="Candidate indicators" value={r.indicator_summary.candidate_indicators} note="Scene cuts + repeated frames" />
      <Metric label="Scene-change candidates" value={scenes?.candidates?.length ?? "—"} note="Large colour-distribution jumps" />
      <Metric label="Repeated frames" value={hashing?.pairs?.length ?? "—"} note="Near-identical consecutive samples" />
      <Metric label="Motion spikes" value={fullFlow ? flow!.spikes!.length : "—"} note={fullFlow ? `Peak ${fmt(flow!.peak_mean_magnitude, 1)} px at ${fmtTime(flow!.peak_timestamp!)}` : "Re-analyse for full-video flow"} />
      <Metric label="Lowest SSIM" value={lowest ? fmt(lowest.s) : "—"} note={lowest ? `at ${fmtTime(lowest.t)}` : "Needs 2+ frames"} />
    </div>

    <div className="panel">
      <div className="method-head"><div className="section-title">Timeline</div>
        <div className="legend"><i style={{ background: COLORS.ssim }} />SSIM <i style={{ background: COLORS.motion }} />motion <i style={{ background: COLORS.scene }} />scene cut <i style={{ background: COLORS.spike }} />motion spike</div></div>
      {series.length < 1 ? <div className="subtle">At least two sampled frames are needed.</div> : <>
        <div className="chart-label">Similarity to previous sample (SSIM)</div>
        <div style={{ height: 150 }}>
          <ResponsiveContainer>
            <LineChart data={series} syncId="video" margin={{ top: 6, right: 8, bottom: 0, left: -18 }} onClick={selectFromChart}>
              <CartesianGrid stroke="#1c293a" vertical={false} />
              <XAxis dataKey="t" type="number" domain={[0, "dataMax"]} tickFormatter={fmtTime} {...axis} />
              <YAxis domain={[Math.min(0, ...ssimPoints.map(p => p.s)), 1]} {...axis} />
              <Tooltip contentStyle={tooltipStyle} labelFormatter={t => `At ${fmtTime(Number(t))}`} formatter={v => [fmt(Number(v), 3), "SSIM"]} />
              {cursorLines}
              <Line type="linear" dataKey="s" stroke={COLORS.ssim} strokeWidth={2} dot={{ r: 2 }} activeDot={{ r: 5 }} isAnimationActive={false} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </div>
        {fullFlow && <>
          <div className="chart-label">Motion from previous sample (pixels, mean and 95th percentile)</div>
          <div style={{ height: 150 }}>
            <ResponsiveContainer>
              <AreaChart data={series} syncId="video" margin={{ top: 6, right: 8, bottom: 0, left: -18 }} onClick={selectFromChart}>
                <CartesianGrid stroke="#1c293a" vertical={false} />
                <XAxis dataKey="t" type="number" domain={[0, "dataMax"]} tickFormatter={fmtTime} {...axis} />
                <YAxis {...axis} />
                <Tooltip contentStyle={tooltipStyle} labelFormatter={t => `At ${fmtTime(Number(t))}`} formatter={(v, name) => [`${fmt(Number(v), 1)} px`, name === "m" ? "Mean motion" : "95th percentile"]} />
                {cursorLines}
                <Area type="linear" dataKey="p95" stroke={COLORS.motion} strokeOpacity={0.4} fill={COLORS.motion} fillOpacity={0.08} isAnimationActive={false} connectNulls />
                <Area type="linear" dataKey="m" stroke={COLORS.motion} strokeWidth={2} fill={COLORS.motion} fillOpacity={0.2} dot={{ r: 2 }} activeDot={{ r: 5 }} isAnimationActive={false} connectNulls />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </>}
      </>}
      <p className="stat-note">Click either chart or a frame below to inspect it. SSIM 1.0 means identical to the previous sample. Motion is how far content moved since the previous sample.</p>
    </div>

    <div className="panel">
      <div className="section-title">Sampled frames</div>
      <div className="filmstrip">
        {frames.map((f, i) => <button key={f.file} className={`thumb ${i === selected ? "active" : ""}`} onClick={() => setSelected(i)} title={`Frame ${f.index} at ${fmtTime(f.timestamp)}`}>
          <img src={frameUrl(item.id, f.file)} alt={`Frame at ${fmtTime(f.timestamp)}`} loading="lazy" />
          <span className="stat-note">{fmtTime(f.timestamp)}</span>
          <span className="marks">
            {marks.get(i)?.has("scene") && <span className="mark mark-scene">cut</span>}
            {(marks.get(i)?.has("exact") || marks.get(i)?.has("near_duplicate")) && <span className="mark mark-dup">repeat</span>}
            {marks.get(i)?.has("motion") && <span className="mark mark-spike">motion</span>}
          </span>
        </button>)}
      </div>
      {current && <div className={`compare ${fullFlow ? "compare-3" : ""}`} style={{ marginTop: 6 }}>
        <figure>{previous ? <img className="artifact" src={frameUrl(item.id, previous.file)} alt="Previous sampled frame" /> : <div className="artifact empty">First sampled frame</div>}
          <figcaption>Previous · {previous ? fmtTime(previous.timestamp) : "—"}</figcaption></figure>
        <figure><img className="artifact" src={frameUrl(item.id, current.file)} alt="Selected frame" />
          <figcaption>Selected · frame {current.index} · {fmtTime(current.timestamp)} · SSIM {point?.s !== undefined ? fmt(point.s, 3) : "—"}</figcaption></figure>
        {fullFlow && <figure>{previous ? <img className="artifact" src={frameUrl(item.id, flowFile(current))} alt="Optical flow into selected frame" /> : <div className="artifact empty">No previous frame</div>}
          <figcaption>Motion into selected · mean {point?.m !== undefined ? `${fmt(point.m, 1)} px` : "—"}</figcaption></figure>}
      </div>}
    </div>

    <div className="panel">
      <div className="section-title">Flagged moments</div>
      {events.length === 0 ? <div className="subtle" style={{ marginTop: 8 }}>No scene-change, repeated-frame or motion-spike candidates among the sampled frames.</div> :
        <table className="table"><thead><tr><th>Time</th><th>Type</th><th>Detail</th></tr></thead><tbody>
          {events.map((e, n) => <tr key={n} className="clickable" onClick={() => e.index >= 0 && setSelected(e.index)}>
            <td>{fmtTime(e.time)}</td>
            <td><span className={`badge ${EVENT_LABEL[e.kind][1]}`}>{EVENT_LABEL[e.kind][0]}</span></td>
            <td>{e.detail}</td></tr>)}
        </tbody></table>}
    </div>

    <div className="result-grid">
      <MethodCard title="Structural similarity (SSIM)" result={ssim}
        what="Compares each sampled frame with the one before it on local brightness, contrast and structure, giving a score from −1 to 1."
        read="Steady high values mean continuous footage. A single sharp dip is a cut or fast motion; a dip with no visible reason in the frames is worth checking for removed or inserted footage."
        caveat={ssim?.note}>
        {ssim?.status === "completed" && <div className="kv"><span>Mean · lowest</span><span>{fmt(ssimPoints.reduce((a, p) => a + p.s, 0) / (ssimPoints.length || 1), 3)} · {lowest ? fmt(lowest.s, 3) : "—"}</span></div>}
      </MethodCard>

      <MethodCard title="Scene-change detection" result={scenes}
        what="Builds an 8×8×8 colour histogram for each sampled frame and measures the Bhattacharyya distance to the previous one; distances of 0.55 or more are flagged."
        read="Flags line up with edits. Cuts are normal in edited video, but a cut inside what should be one continuous recording (for example CCTV) needs explaining."
        caveat={scenes?.note}>
        {scenes?.status === "completed" && <div className="kv"><span>Candidates</span><span>{scenes.candidates.length}</span></div>}
      </MethodCard>

      <MethodCard title="Repeated-frame detection (perceptual hash)" result={hashing}
        what="Computes a perceptual hash (pHash) of each sampled frame and compares neighbours. A Hamming distance of 4 or less means they look nearly the same."
        read="Runs of repeats can show frozen, looped or padded footage. In static scenes (a still camera, a slide) repeats are expected."
        caveat={hashing?.note}>
        {hashing?.status === "completed" && <div className="kv"><span>Exact · near repeats</span><span>{hashing.pairs.filter(p => p.kind === "exact").length} · {hashing.pairs.filter(p => p.kind === "near_duplicate").length}</span></div>}
      </MethodCard>

      <MethodCard title="Optical flow (motion)" result={flow}
        what="Estimates how every pixel moves between each pair of adjacent sampled frames (Farnebäck dense flow, frames scaled to 480 px wide). Pairs whose motion is far above the video's typical level (median + 3.5 × MAD) are marked as motion spikes."
        read="In each flow image, colour is direction and brightness is speed (full brightness at the saturation value below). Smooth, coherent motion is normal. A lone spike, or motion that stops sharply at an object's edge, is worth a look."
        caveat={fullFlow ? flow!.note : "This investigation was analysed before full-video flow existed, so only the first two sampled frames are covered. Upload the video again to analyse every pair."}>
        {flow?.status === "completed" && <>
          <img className="artifact" src={artifactUrl(item.id, flow.visualization)} alt="Optical flow of the highest-motion pair" />
          <div className="stat-note" style={{ marginTop: 6 }}>{fullFlow ? `Highest-motion pair, ending at ${fmtTime(flow.peak_timestamp!)}` : "First two sampled frames"}</div>
          <div className="kv"><span>Mean · median motion</span><span>{fmt(flow.mean_motion_magnitude, 1)} · {fullFlow ? fmt(flow.median_motion_magnitude, 1) : "—"} px</span></div>
          <div className="kv"><span>Highest 95th percentile</span><span>{fmt(flow.p95_motion_magnitude, 1)} px</span></div>
          {fullFlow && <div className="kv"><span>Pairs analysed · spikes</span><span>{flow.timestamps!.length} · {flow.spikes!.length}</span></div>}
          {fullFlow && <div className="kv"><span>Brightness saturates at</span><span>{fmt(flow.saturation_px, 1)} px</span></div>}
        </>}
      </MethodCard>
    </div>

    <Limitations items={r.limitations} statement={r.indicator_summary.statement} />
  </div>;
}
