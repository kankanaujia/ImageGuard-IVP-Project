import type { Investigation, InvestigationSummary } from "@/types/api";
const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
export async function getInvestigations():Promise<InvestigationSummary[]> { const r=await fetch(`${API}/api/investigations`,{cache:"no-store"}); if(!r.ok) throw new Error("Could not load investigations"); return r.json(); }
export async function getInvestigation<R>(id:string):Promise<Investigation<R>> { const r=await fetch(`${API}/api/investigations/${id}`,{cache:"no-store"}); if(!r.ok) throw new Error("Could not load investigation details"); return r.json(); }
export async function getHealth():Promise<{status:string}> { const r=await fetch(`${API}/api/health`,{cache:"no-store"}); if(!r.ok) throw new Error("API unavailable"); return r.json(); }
const VIDEO_EXTS=[".mp4",".avi",".mov",".mkv"];
/** Browsers often report an empty MIME type for .mkv/.avi, so fall back to the extension. */
export function mediaKind(file:File):"image"|"video" { const ext=file.name.slice(file.name.lastIndexOf(".")).toLowerCase(); return file.type.startsWith("video/")||VIDEO_EXTS.includes(ext)?"video":"image"; }
export async function uploadEvidence(file:File,kind:"image"|"video"=mediaKind(file)):Promise<Investigation> { const data=new FormData(); data.append("file",file); const r=await fetch(`${API}/api/${kind}/analyze`,{method:"POST",body:data}); const body=await r.json(); if(!r.ok) throw new Error(body.detail||"Analysis failed"); return body; }
export const apiUrl=(path:string)=>`${API}${path}`;
export const artifactUrl=(id:string,name:string)=>apiUrl(`/api/investigations/${id}/artifacts/${name}`);
export const frameUrl=(id:string,name:string)=>apiUrl(`/api/investigations/${id}/artifacts/frames/${name}`);
