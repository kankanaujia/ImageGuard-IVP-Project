"use client";
import { createContext, useContext, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Shield, LayoutDashboard, Upload, Image, Film, FileText, LogOut, UserRound, Loader2 } from "lucide-react";
import { getMe, loginPath, signOut } from "@/services/api";
import type { User } from "@/types/api";

const links = [["/", "Overview", LayoutDashboard], ["/investigation", "New investigation", Upload], ["/image-analysis", "Image forensics", Image],
  ["/video-analysis", "Video forensics", Film], ["/reports", "Reports", FileText]] as const;

const UserContext = createContext<User | null>(null);
/** The signed-in analyst; available inside any page wrapped in <Shell>. */
export const useUser = () => useContext(UserContext);

/** App frame. Pages render only once the sign-in is confirmed; otherwise the user is sent to /login. */
export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let live = true;
    getMe().then(me => {
      if (!live) return;
      if (me) setUser(me);
      else router.replace(loginPath(window.location.pathname + window.location.search));
    }).catch(e => live && setError(e instanceof Error ? e.message : "Could not reach the API"));
    return () => { live = false; };
  }, [router]);

  async function logout() {
    await signOut();
    router.replace("/login");
  }

  return <div className="shell">
    <aside className="sidebar">
      <Link href="/" className="brand"><span className="brand-mark"><Shield size={18} /></span>ImageGuard</Link>
      <div className="nav-label">Workspace</div>
      <nav className="nav">{links.map(([href, label, Icon]) => <Link key={href} href={href} className={path === href ? "active" : ""}><Icon size={16} /><span>{label}</span></Link>)}</nav>
      <div className="sidebar-foot">
        {user ? <>
          <div className="account"><UserRound size={14} /><span title={user.username}>{user.username}</span>{user.is_admin && <span className="badge">Admin</span>}</div>
          <button className="link-btn" onClick={logout}><LogOut size={13} /> Sign out</button>
        </> : <>Forensic analysis workspace<br />Local evidence storage</>}
      </div>
    </aside>
    <main className="main">
      {user ? <UserContext.Provider value={user}>{children}</UserContext.Provider>
        : error ? <div className="panel empty"><b>ImageGuard API unavailable</b><p className="subtle">{error}</p></div>
        : <div className="empty"><Loader2 size={18} className="spin" /></div>}
    </main>
  </div>;
}
