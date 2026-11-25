// Capture full-page screenshots of the running app with headless Microsoft Edge.
// The app needs a signed-in session, so the script signs in through the API and gives the
// session cookie to Edge over the DevTools protocol (Node's built-in fetch and WebSocket).
//
// Requires both servers running (backend :8000, frontend :3000), ideally on a demo data folder:
//   node screenshots.js --user demo --password <pw> --image <id> --splice <id> --video <id> [--time 5] [--register]
// Writes screenshots/raw/<page>.png; crop_screenshots.py turns them into the figure images.
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, all) =>
  a.startsWith("--") ? [...acc, [a.slice(2), all[i + 1] && !all[i + 1].startsWith("--") ? all[i + 1] : true]] : acc, []));
const API = "http://localhost:8000", WEB = "http://localhost:3000";
const EDGE = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const RAW = path.join(__dirname, "screenshots", "raw");
const PORT = 9333;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function signIn() {
  const route = args.register ? "register" : "login";
  const r = await fetch(`${API}/api/auth/${route}`, { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: args.user, password: args.password }) });
  if (!r.ok) throw new Error(`Sign-in failed: ${r.status} ${await r.text()}`);
  const cookie = r.headers.get("set-cookie").split(";")[0];          // imageguard_session=<token>
  return cookie.slice(cookie.indexOf("=") + 1);
}

/** Minimal DevTools client: send a command, await its reply. */
function devtools(wsUrl) {
  const ws = new WebSocket(wsUrl);
  let id = 0; const waiting = new Map();
  ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && waiting.has(m.id)) { waiting.get(m.id)(m); waiting.delete(m.id); } };
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const n = ++id; waiting.set(n, (m) => m.error ? reject(new Error(`${method}: ${m.error.message}`)) : resolve(m.result));
    ws.send(JSON.stringify({ id: n, method, params }));
  });
  return new Promise((resolve) => { ws.onopen = () => resolve({ send, close: () => ws.close() }); });
}

async function shoot(cdp, name, url, width, height) {
  await cdp.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
  await cdp.send("Page.navigate", { url });
  await sleep(7000);                                            // data, images and charts load
  const { data } = await cdp.send("Page.captureScreenshot", { format: "png" });
  fs.writeFileSync(path.join(RAW, `${name}.png`), Buffer.from(data, "base64"));
  console.log("ok ", name);
}

(async () => {
  fs.mkdirSync(RAW, { recursive: true });
  const token = await signIn();
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "imageguard-shot-"));
  const edge = spawn(EDGE, ["--headless=new", "--disable-gpu", "--hide-scrollbars", `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, "about:blank"], { stdio: "ignore" });
  try {
    let target;
    for (let i = 0; i < 40 && !target; i++) {
      await sleep(250);
      try { target = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).find((t) => t.type === "page"); } catch {}
    }
    if (!target) throw new Error("Edge did not start");
    const cdp = await devtools(target.webSocketDebuggerUrl);
    await cdp.send("Page.enable"); await cdp.send("Network.enable");

    await shoot(cdp, "login", `${WEB}/login`, 1400, 800);        // signed out first
    await cdp.send("Network.setCookie", { name: "imageguard_session", value: token, domain: "localhost", path: "/", httpOnly: true, sameSite: "Lax" });
    const pages = [
      ["overview", `${WEB}/`, 1400, 1000],
      ["investigation", `${WEB}/investigation`, 1400, 1000],
      ["image", `${WEB}/image-analysis?id=${args.image}`, 1400, 3400],
      ["ghost", `${WEB}/image-analysis?id=${args.splice || args.image}&view=ghost_map`, 1400, 2000],
      ["slider", `${WEB}/image-analysis?id=${args.image}&view=orb&mode=slider`, 1400, 2000],
      ["video", `${WEB}/video-analysis?id=${args.video}&t=${args.time || 0}`, 1400, 3600],
      ["reports", `${WEB}/reports?id=${args.image}`, 1400, 2400],
    ];
    for (const p of pages) await shoot(cdp, ...p);
    cdp.close();
  } finally {
    edge.kill();
    await sleep(500);
    fs.rmSync(profile, { recursive: true, force: true });
  }
})().catch((e) => { console.error(e.message); process.exit(1); });
