import type { Investigation, InvestigationSummary, Job } from "@/types/api";
const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function json<T>(r: Response, fallback: string): Promise<T> {
  if (!r.ok) { let detail = fallback; try { detail = (await r.json()).detail || fallback; } catch {} throw new Error(typeof detail === "string" ? detail : fallback); }
  return r.json();
}

export async function getInvestigations():Promise<InvestigationSummary[]> { return json(await fetch(`${API}/api/investigations`,{cache:"no-store"}), "Could not load investigations"); }
export async function getInvestigation<R>(id:string):Promise<Investigation<R>> { return json(await fetch(`${API}/api/investigations/${id}`,{cache:"no-store"}), "Could not load investigation details"); }
export async function getHealth():Promise<{status:string}> { return json(await fetch(`${API}/api/health`,{cache:"no-store"}), "API unavailable"); }

export async function deleteInvestigation(id:string):Promise<void> {
  const r = await fetch(`${API}/api/investigations/${id}`, { method: "DELETE" });
  if (!r.ok && r.status !== 404) throw new Error("Could not delete the investigation");
}

export async function saveNotes(id:string, notes:string):Promise<string> {
  const r = await fetch(`${API}/api/investigations/${id}/notes`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ notes }) });
  return (await json<{notes:string}>(r, "Could not save notes")).notes;
}

const VIDEO_EXTS=[".mp4",".avi",".mov",".mkv"];
export const IMAGE_EXTS=[".jpg",".jpeg",".png",".tiff",".tif",".bmp",".webp"];
export const ACCEPTED=[...IMAGE_EXTS,...VIDEO_EXTS];
export const MAX_UPLOAD_BYTES=100*1024*1024;
export const extensionOf=(name:string)=>name.slice(name.lastIndexOf(".")).toLowerCase();
/** Browsers often report an empty MIME type for .mkv/.avi, so fall back to the extension. */
export function mediaKind(file:File):"image"|"video" { return file.type.startsWith("video/")||VIDEO_EXTS.includes(extensionOf(file.name))?"video":"image"; }

/** Upload with real upload progress, then analyse in the background; resolves with the queued job. */
export function startAnalysis(file:File, kind:"image"|"video"=mediaKind(file), onUpload?:(fraction:number)=>void):Promise<Job> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API}/api/${kind}/analyze?background=true`);
    xhr.upload.onprogress = e => { if (e.lengthComputable && onUpload) onUpload(e.loaded / e.total); };
    xhr.onload = () => {
      let body: unknown = null; try { body = JSON.parse(xhr.responseText); } catch {}
      if (xhr.status === 202) resolve(body as Job);
      else reject(new Error((body as {detail?:string})?.detail || `Upload failed (${xhr.status})`));
    };
    xhr.onerror = () => reject(new Error("Could not reach the ImageGuard API. Is the backend running?"));
    const data = new FormData(); data.append("file", file); xhr.send(data);
  });
}

export async function getJob(id:string):Promise<Job> { return json(await fetch(`${API}/api/jobs/${id}`,{cache:"no-store"}), "Could not read analysis progress"); }

/** Poll a job until it finishes, reporting each update; resolves with the investigation id. */
export async function waitForJob(id:string, onUpdate?:(job:Job)=>void, intervalMs=500):Promise<string> {
  for (;;) {
    const job = await getJob(id);
    onUpdate?.(job);
    if (job.status === "done" && job.investigation_id) return job.investigation_id;
    if (job.status === "error") throw new Error(job.error || "Analysis failed");
    await new Promise(r => setTimeout(r, intervalMs));
  }
}

/** Upload, analyse and wait: the whole flow with one progress callback (0..1 overall). */
export async function analyseFile(file:File, onProgress?:(fraction:number, stage:string)=>void):Promise<{id:string;kind:"image"|"video"}> {
  const kind = mediaKind(file);
  const job = await startAnalysis(file, kind, f => onProgress?.(0.3 * f, "Uploading"));
  const id = await waitForJob(job.id, j => onProgress?.(0.3 + 0.7 * j.progress, j.stage));
  return { id, kind };
}

export const apiUrl=(path:string)=>`${API}${path}`;
export const artifactUrl=(id:string,name:string)=>apiUrl(`/api/investigations/${id}/artifacts/${name}`);
export const frameUrl=(id:string,name:string)=>apiUrl(`/api/investigations/${id}/artifacts/frames/${name}`);
export const analysisPath=(kind:"image"|"video", id:string)=>`/${kind}-analysis?id=${id}`;
