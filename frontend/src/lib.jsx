const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8001/api";

const money = n => new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 }).format(n || 0);

const fmtDate = s => s ? String(s).split("-").reverse().join("/") : "";

const initials = name => name.split(" ").map(x => x[0]).slice(0, 2).join("").toUpperCase();

const AVATARS = ["#4f46e5", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6"];
function avatarColor(name) {
  let h = 0;
  for (const ch of name) h = (h + ch.charCodeAt(0)) % 997;
  return AVATARS[h % AVATARS.length];
}

async function api(path, opts = {}) {
  const token = localStorage.getItem("pf_token");
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  if (token) headers["Authorization"] = "Bearer " + token;
  const res = await fetch(API + path, { ...opts, headers });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && !path.startsWith("/auth/")) {
    window.dispatchEvent(new CustomEvent("auth:logout"));
  }
  if (!res.ok) throw new Error(data.detail || "Error");
  return data;
}

function highlight(text, term) {
  const t = term.trim().toLowerCase();
  if (!t) return text;
  const i = String(text).toLowerCase().indexOf(t);
  if (i === -1) return text;
  return <>{String(text).slice(0, i)}<b className="hl">{String(text).slice(i, i + t.length)}</b>{String(text).slice(i + t.length)}</>;
}

export { API, money, fmtDate, initials, avatarColor, AVATARS, api, highlight };