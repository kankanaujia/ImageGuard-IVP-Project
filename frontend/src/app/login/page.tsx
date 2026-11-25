"use client";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, Shield } from "lucide-react";
import { getMe, register, signIn } from "@/services/api";

/** Only same-app paths are followed after sign-in, never another site. */
function safeNext(next: string | null) {
  return next && next.startsWith("/") && !next.startsWith("//") && !next.startsWith("/login") ? next : "/";
}

function LoginForm() {
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));
  const [mode, setMode] = useState<"signin" | "register">("signin");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // Already signed in: go straight on.
  useEffect(() => { getMe().then(me => { if (me) router.replace(next); }).catch(() => {}); }, [router, next]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (mode === "register" && password !== confirm) { setError("The passwords do not match"); return; }
    setBusy(true);
    try {
      await (mode === "signin" ? signIn : register)(username.trim(), password);
      router.replace(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setBusy(false);
    }
  }

  const switchTo = (m: "signin" | "register") => { setMode(m); setError(""); setConfirm(""); };

  return <div className="login-page">
    <form className="panel login-card" onSubmit={submit}>
      <div className="brand" style={{ padding: "0 0 18px" }}><span className="brand-mark"><Shield size={18} /></span>ImageGuard</div>
      <div className="eyebrow">{mode === "signin" ? "Welcome back" : "New analyst"}</div>
      <h1 className="title" style={{ marginBottom: 6 }}>{mode === "signin" ? "Sign in" : "Create an account"}</h1>
      <p className="subtle" style={{ marginTop: 0 }}>Each analyst sees only the investigations they ran.</p>
      <label className="field"><span>Username</span>
        <input autoFocus autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} required minLength={3} maxLength={32} />
      </label>
      <label className="field"><span>Password</span>
        <input type="password" autoComplete={mode === "signin" ? "current-password" : "new-password"} value={password}
          onChange={e => setPassword(e.target.value)} required minLength={mode === "register" ? 8 : 1} maxLength={128} />
      </label>
      {mode === "register" && <label className="field"><span>Confirm password</span>
        <input type="password" autoComplete="new-password" value={confirm} onChange={e => setConfirm(e.target.value)} required minLength={8} maxLength={128} />
      </label>}
      {mode === "register" && <p className="stat-note" style={{ margin: "2px 0 0" }}>3–32 letters, digits, &quot;.&quot;, &quot;_&quot; or &quot;-&quot;; password at least 8 characters.</p>}
      {error && <div className="error" role="alert">{error}</div>}
      <button className="btn" type="submit" disabled={busy} style={{ width: "100%", marginTop: 18 }}>
        {busy && <Loader2 size={14} className="spin" />}{mode === "signin" ? "Sign in" : "Create account"}
      </button>
      <p className="subtle" style={{ textAlign: "center", marginBottom: 0 }}>
        {mode === "signin" ? <>New here? <button type="button" className="link-btn" onClick={() => switchTo("register")}>Create an account</button></>
          : <>Already have an account? <button type="button" className="link-btn" onClick={() => switchTo("signin")}>Sign in</button></>}
      </p>
    </form>
  </div>;
}

export default function LoginPage() {
  return <Suspense fallback={null}><LoginForm /></Suspense>;
}
