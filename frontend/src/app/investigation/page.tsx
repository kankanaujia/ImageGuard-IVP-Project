"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { CheckCircle2, FileUp, FolderOpen, Loader2, ShieldCheck, UploadCloud, XCircle } from "lucide-react";
import { Shell } from "@/components/shell";
import { ACCEPTED, MAX_UPLOAD_BYTES, analyseFile, analysisPath, extensionOf, mediaKind } from "@/services/api";

const CONCURRENCY = 2; // matches the backend's analysis workers

type Item = { key: string; file: File; kind: "image" | "video"; status: "ready" | "working" | "done" | "error" | "rejected";
  fraction: number; stage: string; id?: string; error?: string };

function check(file: File): string | null {
  if (!ACCEPTED.includes(extensionOf(file.name))) return "Unsupported format";
  if (file.size > MAX_UPLOAD_BYTES) return "Larger than 100 MB";
  if (file.size === 0) return "Empty file";
  return null;
}

export default function NewInvestigation() {
  const fileInput = useRef<HTMLInputElement>(null);
  const folderInput = useRef<HTMLInputElement>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [drag, setDrag] = useState(false);
  const [running, setRunning] = useState(false);
  const router = useRouter();

  const update = (key: string, patch: Partial<Item>) => setItems(list => list.map(i => i.key === key ? { ...i, ...patch } : i));

  function add(files: FileList | File[] | null) {
    if (!files) return;
    const fresh = Array.from(files)
      .filter(f => !f.name.startsWith("."))                                     // skip hidden files from folders
      .map((file, n): Item => {
        const problem = check(file);
        return { key: `${Date.now()}-${n}-${file.name}`, file, kind: mediaKind(file), status: problem ? "rejected" : "ready",
          fraction: 0, stage: problem ? problem : "Ready", error: problem ?? undefined };
      });
    setItems(list => [...list.filter(i => i.status !== "ready" || !fresh.some(f => f.file.name === i.file.name && f.file.size === i.file.size)), ...fresh]);
  }

  async function start() {
    const queue = items.filter(i => i.status === "ready");
    if (!queue.length) return;
    setRunning(true);
    let next = 0;
    const results: Item[] = [];
    async function worker() {
      while (next < queue.length) {
        const item = queue[next++];
        update(item.key, { status: "working", stage: "Uploading", fraction: 0 });
        try {
          const { id } = await analyseFile(item.file, (fraction, stage) => update(item.key, { fraction, stage }));
          update(item.key, { status: "done", stage: "Complete", fraction: 1, id });
          results.push({ ...item, id, status: "done" });
        } catch (e) {
          update(item.key, { status: "error", stage: "Failed", error: e instanceof Error ? e.message : "Analysis failed" });
        }
      }
    }
    await Promise.all(Array.from({ length: Math.min(CONCURRENCY, queue.length) }, worker));
    setRunning(false);
    if (queue.length === 1 && results[0]?.id) router.push(analysisPath(results[0].kind, results[0].id));   // single file: open it
  }

  const ready = items.filter(i => i.status === "ready").length;
  const done = items.filter(i => i.status === "done").length;
  const single = items.length === 1 && items[0].kind === "image" && items[0].status === "ready" ? items[0].file : null;
  const preview = useMemo(() => single ? URL.createObjectURL(single) : "", [single]);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  return <Shell>
    <div className="topline">
      <div><div className="eyebrow">Evidence intake</div><h1 className="title">New investigation</h1></div>
      <span className="health"><span className="dot" /> Local processing</span>
    </div>
    <p className="subtle">Original evidence is retained byte for byte and analysed from a separate working directory. Add one file, several files or a whole folder.</p>
    <div className="grid2" style={{ marginTop: 24 }}>
      <section className="panel">
        <div className={`drop ${drag ? "drag" : ""}`} onClick={() => fileInput.current?.click()}
          onDragOver={e => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
          onDrop={e => { e.preventDefault(); setDrag(false); add(e.dataTransfer.files); }}>
          <input ref={fileInput} type="file" accept={ACCEPTED.join(",")} multiple hidden onChange={e => { add(e.target.files); e.target.value = ""; }} />
          <UploadCloud size={30} color="#7ab9fa" />
          <h3 style={{ fontSize: 15, marginBottom: 5 }}>Drop evidence files here</h3>
          <div className="subtle">or click to browse • several images and videos at once, up to 100 MB each</div>
          <div className="stat-note" style={{ marginTop: 16 }}>JPG · PNG · TIFF · BMP · WEBP · MP4 · AVI · MOV · MKV</div>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 10 }}>
          {/* webkitdirectory lets the browser pick a whole folder; React does not type it, so it is set via ref */}
          <input ref={el => { folderInput.current = el; el?.setAttribute("webkitdirectory", ""); }} type="file" multiple hidden onChange={e => { add(e.target.files); e.target.value = ""; }} />
          <button className="link-btn" onClick={() => folderInput.current?.click()}><FolderOpen size={14} /> Add a whole folder</button>
          {items.length > 0 && !running && <button className="link-btn" onClick={() => setItems([])}>Clear list</button>}
        </div>

        {preview && <img className="artifact" style={{ maxHeight: 260, objectFit: "contain" }} src={preview} alt="Selected evidence preview" />}

        {items.length > 0 && <div className="queue">
          {items.map(i => <div key={i.key} className={`queue-item ${i.status}`}>
            <div className="queue-head">
              {i.status === "done" ? <CheckCircle2 size={16} color="#74d4a3" /> : i.status === "error" || i.status === "rejected" ? <XCircle size={16} color="#ff9b9b" />
                : i.status === "working" ? <Loader2 size={16} className="spin" color="#77b4f9" /> : <FileUp size={16} color="#77b4f9" />}
              <div style={{ flex: 1, minWidth: 0 }}>
                <b className="queue-name">{i.file.name}</b>
                <div className="stat-note">{(i.file.size / 1024 / 1024).toFixed(2)} MB · {i.status === "error" || i.status === "rejected" ? i.error : i.status === "working" ? `${i.stage} · ${Math.round(i.fraction * 100)}%` : i.stage}</div>
              </div>
              <span className="badge">{i.kind.toUpperCase()}</span>
              {i.status === "done" && i.id && <Link className="link-btn" href={analysisPath(i.kind, i.id)}>Open analysis</Link>}
            </div>
            {i.status === "working" && <div className="progress-track"><div className="progress-fill" style={{ width: `${Math.round(i.fraction * 100)}%` }} /></div>}
          </div>)}
        </div>}
      </section>

      <section>
        <div className="panel">
          <div className="section-title">Analysis pipeline</div>
          <p className="subtle">Images are checked for compression differences (ELA heat map), copied regions (ORB with RANSAC), spliced regions (JPEG ghosts), compression history and metadata. Videos are sampled once per second for repeated frames, similarity changes, scene cuts and motion spikes.</p>
          <div className="kv"><span>Evidence integrity</span><span>SHA-256 at intake</span></div>
          <div className="kv"><span>Working files</span><span>Stored separately</span></div>
          <div className="kv"><span>Batch processing</span><span>{CONCURRENCY} files at a time</span></div>
          <div className="kv"><span>Result language</span><span>Indicators with limitations</span></div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 16, color: "#77caa2", fontSize: 11 }}><ShieldCheck size={15} /> Original files are never modified</div>
        </div>
        <button disabled={!ready || running} className="btn" style={{ width: "100%", marginTop: 14, opacity: (!ready || running) ? 0.55 : 1 }} onClick={start}>
          {running ? `Analysing… ${done} of ${items.filter(i => i.status !== "rejected").length} done` : ready > 1 ? `Start analysis of ${ready} files` : "Start analysis"}
        </button>
        {!running && done > 0 && items.length > 1 && <p className="subtle" style={{ marginTop: 10 }}>{done} file{done === 1 ? "" : "s"} analysed. Open each result above, or see them all in <Link href="/reports" style={{ color: "#8dc4ff" }}>Reports</Link>.</p>}
      </section>
    </div>
  </Shell>;
}
