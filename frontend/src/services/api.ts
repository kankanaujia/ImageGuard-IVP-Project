import type { Investigation, InvestigationSummary, Job, User } from "@/types/api";
/** The API runs on port 8000 of the same host the page was opened on (localhost or 127.0.0.1), so the
 *  sign-in cookie counts as same-site and is sent with fetches, <img> artifacts and PDF links. */
const API = process.env.NEXT_PUBLIC_API_URL || (typeof window !== "undefined" ? `${window.location.protocol}//${window.location.hostname}:8000` : "http://localhost:8000");

/** Thrown when the session has ended; pages send the user to the sign-in screen. */
export class SignedOutError extends Error { constructor() { super("Please sign in"); } }
export const loginPath = (next?: string) => `/login${next && next !== "/login" ? `?next=${encodeURIComponent(next)}` : ""}`;
function signedOut(): never {
  if (typeof window !== "undefined" && window.location.pathname !== "/login") window.location.assign(loginPath(window.location.pathname + window.location.search));
  throw new SignedOutError();
}
const call = (path: string, init: RequestInit = {}) => fetch(`${API}${path}`, { cache: "no-store", credentials: "include", ...init });

async function json<T>(r: Response, fallback: string): Promise<T> {
  if (r.status === 401) signedOut();
  if (!r.ok) { let detail = fallback; try { detail = (await r.json()).detail || fallback; } catch {} throw new Error(typeof detail === "string" ? detail : fallback); }
  return r.json();
}

// ---------------------------------------------------------------- accounts
/** The signed-in analyst, or null when nobody is signed in. Throws only when the API cannot be reached. */
export async function getMe():Promise<User|null> {
  let r: Response;
  try { r = await call("/api/auth/me"); } catch { throw new Error("Could not reach the ImageGuard API. Is the backend running?"); }
  if (r.status === 401) return null;
  return json(r, "Could not check the sign-in");
}
async function credentials(path:string, username:string, password:string, fallback:string):Promise<User> {
  let r: Response;
  try { r = await call(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password }) }); }
  catch { throw new Error("Could not reach the ImageGuard API. Is the backend running?"); }
  if (!r.ok) { let detail = fallback; try { const d = (await r.json()).detail; detail = typeof d === "string" ? d : Array.isArray(d) ? "Check the username and password" : fallback; } catch {} throw new Error(detail); }
  return r.json();
}
export const signIn = (username:string, password:string) => credentials("/api/auth/login", username, password, "Could not sign in");
export const register = (username:string, password:string) => credentials("/api/auth/register", username, password, "Could not create the account");
export async function signOut():Promise<void> { try { await call("/api/auth/logout", { method: "POST" }); } catch {} }

// ---------------------------------------------------------------- investigations
export async function getInvestigations():Promise<InvestigationSummary[]> { return json(await call("/api/investigations"), "Could not load investigations"); }
export async function getInvestigation<R>(id:string):Promise<Investigation<R>> { return json(await call(`/api/investigations/${id}`), "Could not load investigation details"); }
export async function verifyIntegrity(id:string):Promise<{integrity_verified:boolean}> { return json(await call(`/api/investigations/${id}/verify`), "Could not verify the evidence"); }
export async function getHealth():Promise<{status:string}> { return json(await call("/api/health"), "API unavailable"); }

export async function deleteInvestigation(id:string):Promise<void> {
  const r = await call(`/api/investigations/${id}`, { method: "DELETE" });
  if (r.status === 401) signedOut();
  if (!r.ok && r.status !== 404) throw new Error("Could not delete the investigation");
}

export async function saveNotes(id:string, notes:string):Promise<string> {
  const r = await call(`/api/investigations/${id}/notes`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ notes }) });
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
    xhr.withCredentials = true;
    xhr.upload.onprogress = e => { if (e.lengthComputable && onUpload) onUpload(e.loaded / e.total); };
    xhr.onload = () => {
      let body: unknown = null; try { body = JSON.parse(xhr.responseText); } catch {}
      if (xhr.status === 202) resolve(body as Job);
      else if (xhr.status === 401) { try { signedOut(); } catch (e) { reject(e); } }
      else reject(new Error((body as {detail?:string})?.detail || `Upload failed (${xhr.status})`));
    };
    xhr.onerror = () => reject(new Error("Could not reach the ImageGuard API. Is the backend running?"));
    const data = new FormData(); data.append("file", file); xhr.send(data);
  });
}

export async function getJob(id:string):Promise<Job> { return json(await call(`/api/jobs/${id}`), "Could not read analysis progress"); }

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
