import React, { useEffect, useMemo, useState, useCallback, useRef } from "react";
import { createRoot } from "react-dom/client";
import {
  LayoutDashboard, Users, WalletCards, Plus, Search, Bell, TrendingUp,
  Percent, CircleDollarSign, ArrowDownLeft, MoreHorizontal, X, CheckCircle2,
  History, RefreshCw, UserPlus, Inbox, Sparkles, AlertCircle, Pencil, Trash2,
  Archive, RotateCcw, Lock, LogOut, Eye, EyeOff, KeyRound, Loader2, ShieldCheck, ShieldAlert,
  ScrollText, Undo2, Download, Menu, CalendarClock, Clock
} from "lucide-react";
import "./styles.css";
import { API, money, fmtDate, api, highlight, avatarColor, initials } from "./lib.jsx";

const daysUntil = v => {
  if (!v) return null;
  const d = new Date(v).setHours(0, 0, 0, 0);
  const today = new Date().setHours(0, 0, 0, 0);
  return Math.round((d - today) / 86400000);
};

function Logo({ size = 22 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9.3" stroke="currentColor" strokeWidth="2.1" />
      <path d="M6.3 9.1c.9-1.5 2.5-2.5 4.4-2.5 2 0 3.4 1 3.4 2.8 0 1.8-1.5 2.6-3.1 3.1-1.9.6-3.6 1.5-3.6 3.4 0 1.7 1.8 2.8 3.7 2.8 1.7 0 3.2-.9 4-2.2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M12 3.4v2.9M12 12.1v2.6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function App() {
  const [page, setPage] = useState("dashboard");
  const [people, setPeople] = useState([]);
  const [loans, setLoans] = useState([]);
  const [stats, setStats] = useState({});
  const [q, setQ] = useState("");
  const [modal, setModal] = useState(null);
  const [toasts, setToasts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [notifOpen, setNotifOpen] = useState(false);
  const [notifSeen, setNotifSeen] = useState(() => localStorage.getItem("pf_notifs_read") === "1");

  const toggleNotif = useCallback(() => {
    setNotifOpen(o => {
      const next = !o;
      if (next) { setNotifSeen(true); localStorage.setItem("pf_notifs_read", "1"); }
      return next;
    });
  }, []);

  const [showArchived, setShowArchived] = useState(false);
  const [auth, setAuth] = useState(null);
  const [authPending, setAuthPending] = useState(true);

  const logout = useCallback(() => {
    localStorage.removeItem("pf_token");
    setAuth(null);
  }, []);

  useEffect(() => {
    const onLogout = () => logout();
    window.addEventListener("auth:logout", onLogout);
    return () => window.removeEventListener("auth:logout", onLogout);
  }, [logout]);

  useEffect(() => {
    const token = localStorage.getItem("pf_token");
    if (!token) { setAuthPending(false); return; }
    api("/auth/mi")
      .then(u => setAuth({ token, usuario: u.usuario, nombre: u.nombre }))
      .catch(() => localStorage.removeItem("pf_token"))
      .finally(() => setAuthPending(false));
  }, []);

  const notifications = useMemo(() => {
    const pending = loans.filter(l => l.balance > 0);
    const overdue = pending.filter(l => l.mora_dias > 0);
    const dueSoon = pending.filter(l => {
      const n = daysUntil(l.vencimiento);
      return l.mora_dias <= 0 && n !== null && n >= 0 && n <= 7;
    });
    const inCourse = pending.filter(l => !(l.mora_dias > 0) && !(daysUntil(l.vencimiento) !== null && daysUntil(l.vencimiento) >= 0 && daysUntil(l.vencimiento) <= 7));
    return { pending, overdue, dueSoon, inCourse, archived: people.filter(p => !p.activa).length };
  }, [loans, people]);

  const searchResults = useMemo(() => {
    const t = q.trim().toLowerCase();
    if (!t) return null;
    const m = x => x.toLowerCase().includes(t);
    const peopleHits = people.filter(p => m(p.nombre)).slice(0, 4);
    const loanHits = loans.filter(l => m(l.person)).slice(0, 4);
    return { people: peopleHits, loans: loanHits, any: peopleHits.length > 0 || loanHits.length > 0 };
  }, [people, loans, q]);

  const notify = useCallback((msg, type = "success") => {
    const id = Date.now() + Math.random();
    setToasts(t => [...t, { id, msg, type }]);
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 3600);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [a, b, c] = await Promise.all([api("/personas?incluir_archivadas=1"), api("/prestamos"), api("/dashboard")]);
      setPeople(a); setLoans(b); setStats(c);
      setNotifSeen(false);
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(
    () => loans.filter(x => x.person.toLowerCase().includes(q.toLowerCase())),
    [loans, q]
  );

  const personSummary = useMemo(() => {
    const m = {};
    for (const l of loans) {
      m[l.persona_id] = m[l.persona_id] || { lent: 0, paid: 0, balance: 0 };
      m[l.persona_id].lent += l.amount;
      m[l.persona_id].paid += l.paid;
      m[l.persona_id].balance += l.balance;
    }
    return m;
  }, [loans]);

  const run = useCallback(async (path, method, body, okMsg) => {
    try {
      await api(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });
      setModal(null);
      notify(okMsg || "Guardado correctamente");
      load();
    } catch (e) {
      notify(e.message, "error");
    }
  }, [load, notify]);

  const backup = useCallback(async () => {
    try {
      const token = localStorage.getItem("pf_token");
      const res = await fetch(API + "/backup", { headers: { Authorization: "Bearer " + token } });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Error al respaldar");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "respaldo-prestamosflow-" + new Date().toISOString().slice(0, 10) + ".db";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      notify("Respaldo descargado");
    } catch (e) {
      notify(e.message, "error");
    }
  }, [notify]);

  if (authPending) return <Splash />;
  if (!auth) return <LoginScreen onOk={u => { localStorage.setItem("pf_token", u.token); setAuth(u); load(); }} />;

  return (
    <div className="app">
      <Sidebar page={page} setPage={setPage} user={auth} onLogout={logout} onChangePass={() => setModal({ t: "pass" })} onRecovery={() => setModal({ t: "recovery" })} onBackup={backup} />

      <main className="main">
        <UpdateBanner />
        <Header
          q={q}
          setQ={setQ}
          page={page}
          setPage={setPage}
          onRefresh={load}
          results={searchResults}
          onPickPerson={p => { setQ(p.nombre); setPage("people"); setShowArchived(!p.activa); }}
          onPickLoan={l => { setQ(l.person); setPage("loans"); }}
          notifOpen={notifOpen}
          onToggleNotif={toggleNotif}
          pendingLoans={notifications.pending}
          overdue={notifications.overdue}
          dueSoon={notifications.dueSoon}
          inCourseCount={notifications.inCourse.length}
          archivedCount={notifications.archived}
          showBadge={!notifSeen && notifications.pending.length > 0}
          onOpenLoans={() => { setPage("loans"); setNotifOpen(false); }}
          onOpenLoan={l => { setPage("loans"); setNotifOpen(false); setModal({ t: "hist", id: l.id }); }}
        />
        <div className="content">
          {loading && <Skeleton />}
          {!loading && page === "dashboard" && (
            <Dashboard
              stats={stats}
              loans={loans}
              onAdd={() => setModal("loan")}
              onSeeAll={() => setPage("loans")}
            />
          )}
          {!loading && page === "people" && (
            <People
              people={people}
              q={q}
              summaries={personSummary}
              showArchived={showArchived}
              setShowArchived={setShowArchived}
              onAdd={() => setModal({ t: "person" })}
              onEdit={p => setModal({ t: "person", person: p })}
              onDelete={p => setModal({ t: "confirm", person: p })}
              onRestore={p => run("/personas/" + p.id + "/restaurar", "POST", undefined, "Persona restaurada")}
            />
          )}
          {!loading && page === "loans" && (
            <LoansPage
              loans={filtered}
              q={q}
              onAdd={() => setModal("loan")}
              onPay={id => setModal({ t: "pay", id })}
              onHist={id => setModal({ t: "hist", id })}
            />
          )}
          {!loading && page === "audit" && <AuditPage />}
        </div>
      </main>

      {modal?.t === "person" && (
        <PersonModal
          person={modal.person}
          close={() => setModal(null)}
          save={n => modal.person
            ? run("/personas/" + modal.person.id, "PUT", { nombre: n }, "Persona actualizada")
            : run("/personas", "POST", { nombre: n }, "Persona creada")}
        />
      )}
      {modal?.t === "confirm" && (
        <ConfirmModal
          person={modal.person}
          close={() => setModal(null)}
          onConfirm={() => run("/personas/" + modal.person.id, "DELETE", undefined, "Persona archivada")}
        />
      )}
      {modal === "loan" && (
        <LoanModal people={people.filter(p => p.activa)} close={() => setModal(null)} save={(a, b, r, v) => run("/prestamos", "POST", { persona_id: +a, monto: +b, tasa: +(r || 0), vencimiento: v }, "Préstamo registrado")} />
      )}
      {modal?.t === "pay" && (
        <PayModal loan={loans.find(x => x.id === modal.id)} close={() => setModal(null)} save={(a, m) => run("/pagos", "POST", { prestamo_id: +a, monto: +m }, "Pago registrado")} />
      )}
      {modal?.t === "pass" && (
        <PassModal close={() => setModal(null)} onDone={() => notify("Contraseña actualizada")} />
      )}
      {modal?.t === "recovery" && (
        <RecoveryModal close={() => setModal(null)} onDone={() => notify("Nueva clave de recuperación generada")} />
      )}
      {modal?.t === "hist" && (
        <HistModal
          loan={loans.find(x => x.id === modal.id)}
          close={() => setModal(null)}
          onChanged={() => { load(); }}
        />
      )}

      <Toasts items={toasts} />
    </div>
  );
}

function Sidebar({ page, setPage, user, onLogout, onChangePass, onRecovery, onBackup }) {
  const items = [
    { id: "dashboard", label: "Resumen", icon: <LayoutDashboard /> },
    { id: "people", label: "Personas", icon: <Users /> },
    { id: "loans", label: "Préstamos", icon: <WalletCards /> },
    { id: "audit", label: "Auditoría", icon: <ScrollText /> },
  ];
  const [menu, setMenu] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!menu) return;
    const onDoc = e => { if (ref.current && !ref.current.contains(e.target)) setMenu(false); };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [menu]);
  return (
    <aside>
      <div className="brand">
        <div className="logo"><Logo /></div>
        <div className="brand-text">
          <strong>Prestamo<span>Flow</span></strong>
          <small>Control personal</small>
        </div>
      </div>
      <p className="label">Menú</p>
      <nav className="nav-list">
        {items.map(i => (
          <button
            key={i.id}
            className={"nav" + (page === i.id ? " active" : "")}
            onClick={() => setPage(i.id)}
          >
            {i.icon}<span>{i.label}</span>
          </button>
        ))}
      </nav>
      <div className="bottom">
        <div className="mini">
          <div className="mini-icon"><ShieldCheck /></div>
          <span><b>Acceso protegido</b>Datos seguros con inicio de sesión</span>
        </div>
        <div className="profile" ref={ref} onClick={() => setMenu(o => !o)}>
          <Avatar name={user?.nombre || "Usuario"} size="sm" />
          <span><b>{user?.nombre || "Cuenta"}</b><small>@{user?.usuario || "usuario"}</small></span>
          <MoreHorizontal />
          {menu && (
            <div className="profile-menu">
              <button className="profile-item" onClick={() => { setMenu(false); onChangePass(); }}><KeyRound />Cambiar contraseña</button>
              <button className="profile-item" onClick={() => { setMenu(false); onRecovery(); }}><ShieldAlert />Clave de recuperación</button>
              <button className="profile-item" onClick={() => { setMenu(false); onBackup(); }}><Download />Descargar respaldo</button>
              <button className="profile-item danger" onClick={() => { setMenu(false); onLogout(); }}><LogOut />Cerrar sesión</button>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}

function Header({ q, setQ, page, setPage, results, onPickPerson, onPickLoan, onRefresh, notifOpen, onToggleNotif, pendingLoans, overdue, dueSoon, inCourseCount, archivedCount, showBadge, onOpenLoans, onOpenLoan }) {
  const searchRef = useRef(null);
  const notifRef = useRef(null);
  const [searchFocus, setSearchFocus] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const searchOpen = searchFocus && q.trim().length > 0;

  const navItems = [
    { id: "dashboard", label: "Resumen", icon: <LayoutDashboard /> },
    { id: "people", label: "Personas", icon: <Users /> },
    { id: "loans", label: "Préstamos", icon: <WalletCards /> },
    { id: "audit", label: "Auditoría", icon: <ScrollText /> },
  ];
  const goTo = id => { setPage(id); setDrawer(false); };

  useEffect(() => {
    if (!notifOpen) return;
    const onDoc = e => { if (notifRef.current && !notifRef.current.contains(e.target)) onToggleNotif(); };
    const onKey = e => { if (e.key === "Escape") onToggleNotif(); };
    document.addEventListener("mousedown", onDoc);
    window.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      window.removeEventListener("keydown", onKey);
    };
  }, [notifOpen, onToggleNotif]);

  useEffect(() => {
    if (!searchOpen) return;
    const onDoc = e => { if (searchRef.current && !searchRef.current.contains(e.target)) setSearchFocus(false); };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [searchOpen]);

  const go = fn => { fn(); setSearchFocus(false); };
  const firstPerson = results?.people[0];
  const firstLoan = results?.loans[0];

  return (
    <>
    <header>
      <button className="icon-btn ghost mobile-menu" title="Menú" onClick={() => setDrawer(true)}><Menu /></button>
      <div className="mobile-brand">Prestamo<span>Flow</span></div>
      <div className="search" ref={searchRef}>
        <Search />
        <input
          placeholder="Buscar persona o préstamo..."
          value={q}
          onChange={e => setQ(e.target.value)}
          onFocus={() => setSearchFocus(true)}
          onKeyDown={e => {
            if (e.key === "Enter" && results?.any) {
              e.preventDefault();
              if (firstPerson) go(() => onPickPerson(firstPerson));
              else if (firstLoan) go(() => onPickLoan(firstLoan));
            }
            if (e.key === "Escape") setSearchFocus(false);
          }}
        />
        {q && <button className="search-clear" title="Limpiar búsqueda" onClick={() => setQ("")}><X /></button>}
        {searchOpen && (
          <div className="search-results">
            <div className="search-head">
              <span>Resultados de búsqueda</span>
              <em>{results.people.length + results.loans.length} coincidencia(s)</em>
            </div>
            {results.any ? (
              <>
                {results.people.length > 0 && (
                  <div className="search-group">Personas</div>
                )}
                {results.people.map(p => (
                  <button className="search-result" key={"p" + p.id} onClick={() => go(() => onPickPerson(p))}>
                    <Avatar name={p.nombre} size="sm" />
                    <span className="meta"><b>{highlight(p.nombre, q)}</b><small>{p.activa ? "Persona activa" : "Persona archivada"}</small></span>
                    <span className={"badge" + (p.activa ? "" : " ghost")}>Persona</span>
                  </button>
                ))}
                {results.loans.length > 0 && <div className="search-group">Préstamos</div>}
                {results.loans.map(l => (
                  <button className="search-result" key={"l" + l.id} onClick={() => go(() => onPickLoan(l))}>
                    <Avatar name={l.person} size="sm" />
                    <span className="meta"><b>{highlight(l.person, q)}</b><small>{l.tasa > 0 ? l.tasa + "% de interés · " : ""}Saldo {money(l.balance)}</small></span>
                    <span className={"badge" + (l.balance > 0 ? "" : " ok")}>{l.balance > 0 ? "Debe" : "Pagado"}</span>
                  </button>
                ))}
              </>
            ) : (
              <div className="search-empty">Sin resultados para "<b>{q.trim()}</b>"</div>
            )}
            <div className="search-foot"><strong>↵</strong> Enter para abrir el primer resultado</div>
          </div>
        )}
      </div>
      <div className="notif-wrap" ref={notifRef}>
        <button className={"icon-btn ghost" + (notifOpen ? " active" : "")} title="Notificaciones" onClick={onToggleNotif}>
          <Bell />
          {showBadge && <i className="badge-count">{overdue.length + dueSoon.length}</i>}
        </button>
        {notifOpen && (
          <div className="notif-panel">
            <div className="notif-head">
              <h3>Notificaciones</h3>
              {overdue.length + dueSoon.length ? <span>{overdue.length + dueSoon.length} pendiente(s)</span> : <span className="ok">Todo al día</span>}
            </div>
            <div className="notif-body">
              {overdue.length > 0 && (
                <>
                  <p className="notif-group">Vencidos</p>
                  {overdue.map(l => (
                    <button className="notif-item" key={"o" + l.id} onClick={() => onOpenLoan(l)}>
                      <span className="notif-icon danger"><Clock /></span>
                      <div><b>{l.person}</b><small>Vencido hace <b className="red">{l.mora_dias}</b> día(s) · Debe {money(l.balance)}</small></div>
                      <span className="badge mora">Mora</span>
                    </button>
                  ))}
                </>
              )}
              {dueSoon.length > 0 && (
                <>
                  <p className="notif-group">Por vencer</p>
                  {dueSoon.map(l => (
                    <button className="notif-item" key={"s" + l.id} onClick={() => onOpenLoan(l)}>
                      <span className="notif-icon warn"><CalendarClock /></span>
                      <div><b>{l.person}</b><small>Vence en <b className="amber">{daysUntil(l.vencimiento)}</b> día(s) · Debe {money(l.balance)}</small></div>
                      <span className="badge ghost">Pronto</span>
                    </button>
                  ))}
                </>
              )}
              {overdue.length + dueSoon.length === 0 && (
                <div className="empty compact"><div className="empty-icon"><CheckCircle2 /></div><p>No hay saldos pendientes por cobrar.</p></div>
              )}
            </div>
            {inCourseCount > 0 && <div className="notif-foot">Tienes <b>{inCourseCount}</b> préstamo(s) en curso al día</div>}
            {archivedCount > 0 && <div className="notif-foot">Tienes <b>{archivedCount}</b> persona(s) archivada(s)</div>}
            {overdue.length + dueSoon.length > 0 && (
              <div className="notif-cta"><button className="btn primary block" onClick={onOpenLoans}>Ver préstamos pendientes</button></div>
            )}
          </div>
        )}
      </div>
      <button className="icon-btn ghost" title="Actualizar" onClick={onRefresh}><RefreshCw /></button>
    </header>
    {drawer && (
      <div className="drawer-overlay" onClick={() => setDrawer(false)}>
        <div className="drawer" onClick={e => e.stopPropagation()}>
          <div className="drawer-head">
            <div className="brand"><div className="logo"><Logo /></div><div className="brand-text"><strong>Prestamo<span>Flow</span></strong></div></div>
            <button className="icon-btn ghost" onClick={() => setDrawer(false)}><X /></button>
          </div>
          <nav className="nav-list">
            {navItems.map(i => (
              <button key={i.id} className={"nav drawer-item" + (page === i.id ? " active" : "")} onClick={() => goTo(i.id)}>
                {i.icon}<span>{i.label}</span>
              </button>
            ))}
          </nav>
        </div>
      </div>
    )}
  </>
  );
}

function PageHead({ eyebrow, title, sub, onAdd, cta, icon }) {
  return (
    <div className="page-head">
      <div className="page-head-text">
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <span className="sub">{sub}</span>
      </div>
      {onAdd && (
        <button className="btn primary" onClick={onAdd}>{icon}{cta}</button>
      )}
    </div>
  );
}

function Dashboard({ stats, loans, onAdd, onSeeAll }) {
  const cards = [
    { t: "Total prestado", v: money(stats.total_lent), i: <WalletCards />, c: "indigo" },
    { t: "Total recuperado", v: money(stats.total_paid), i: <ArrowDownLeft />, c: "green" },
    { t: "Interés generado", v: money(stats.total_interest), i: <Percent />, c: "violet" },
    { t: "Saldo por cobrar", v: money(stats.total_balance), i: <CircleDollarSign />, c: "amber" },
    { t: "Préstamos activos", v: stats.active_loans || 0, i: <TrendingUp />, c: "blue" },
  ];
  return (
    <section className="page">
      <PageHead eyebrow="Resumen" title="Resumen financiero" sub="Aquí tienes una vista general de tu cartera." onAdd={onAdd} cta="Nuevo préstamo" icon={<Plus />} />
      <div className="stats-grid">
          {cards.map(c => <StatCard key={c.t} {...c} />)}
        </div>
      <div className="panel">
        <div className="panel-head">
          <div><h2>Préstamos recientes</h2><p>Últimos movimientos registrados</p></div>
          <button className="link" onClick={onSeeAll}>Ver todos</button>
        </div>
        <div className="panel-body"><LoanTable rows={loans.slice(0, 6)} /></div>
      </div>
    </section>
  );
}

function StatCard({ t, v, i, c }) {
  return (
    <div className={"stat " + c}>
      <div className="stat-top"><span>{t}</span><div className="stat-icon">{i}</div></div>
      <strong className="stat-value">{v}</strong>
      <small className="stat-foot"><TrendingUp /> Datos actualizados</small>
    </div>
  );
}

function People({ people, q, summaries, showArchived, setShowArchived, onAdd, onEdit, onDelete, onRestore }) {
  const matches = x => x.nombre.toLowerCase().includes(q.toLowerCase());
  const visible = showArchived ? people.filter(matches) : people.filter(x => x.activa && matches(x));
  const archived = people.filter(x => !x.activa && matches(x));
  return (
    <section className="page">
      <PageHead eyebrow="Gestión" title="Personas" sub="Personas registradas en el sistema." onAdd={onAdd} cta="Nueva persona" icon={<UserPlus />} />
      <div className="filter-row">
        <label className="switch">
          <input type="checkbox" checked={showArchived} onChange={e => setShowArchived(e.target.checked)} />
          <i />
          <span>Incluir archivadas {archived.length > 0 && <em>({archived.length})</em>}</span>
        </label>
      </div>
      {visible.length ? (
        <div className="people-grid">
          {visible.map(a => (
            <div className={"person-card" + (a.activa ? "" : " archived")} key={a.id}>
              <div className="person-top">
                <Avatar name={a.nombre} size="lg" />
                <div className="person-actions">
                  <button className="icon-btn ghost sm" title="Editar persona" onClick={() => onEdit(a)}><Pencil /></button>
                  {a.activa
                    ? <button className="icon-btn danger sm" title="Archivar persona" onClick={() => onDelete(a)}><Trash2 /></button>
                    : <button className="icon-btn ghost sm restore" title="Restaurar persona" onClick={() => onRestore(a)}><RotateCcw /></button>}
                </div>
              </div>
              <h3>{a.nombre}</h3>
              {a.activa ? <span className="tag">ID #{a.id}</span> : <span className="tag archived-tag">Archivada</span>}
              {(() => {
                const s = summaries[a.id];
                return (
                  <div className="person-footer">
                    <span>{!s ? "Sin préstamos" : s.balance > 0 ? "Saldo pendiente" : "Al día"}</span>
                    <b className={s && s.balance > 0 ? "text-amber" : ""}>
                      {s && s.balance > 0 ? money(s.balance) : s && s.lent > 0 ? "✓" : a.created_at.slice(0, 10)}
                    </b>
                  </div>
                );
              })()}
            </div>
          ))}
        </div>
      ) : (
        <Empty text={showArchived ? "No hay personas archivadas." : "Aún no hay personas registradas."} />
      )}
    </section>
  );
}

function LoansPage({ loans, onAdd, onPay, onHist }) {
  const [estado, setEstado] = useState("todos");
  const active = loans.filter(l => l.balance > 0).length;
  const mora = loans.filter(l => l.mora_dias > 0).length;
  const paid = loans.length - active;
  const visible = loans.filter(l =>
    estado === "mora" ? l.mora_dias > 0
      : estado === "en_curso" ? (l.balance > 0 && l.mora_dias === 0)
      : estado === "pagados" ? l.balance <= 0 : true
  );
  const chips = [
    { id: "todos", label: "Todos", n: loans.length },
    { id: "en_curso", label: "En curso", n: active, extra: "blue" },
    { id: "mora", label: "En mora", n: mora, extra: "danger" },
    { id: "pagados", label: "Pagados", n: paid, extra: "green" },
  ];
  return (
    <section className="page">
      <PageHead eyebrow="Cartera" title="Préstamos" sub="Consulta y administra tus préstamos." onAdd={onAdd} cta="Nuevo préstamo" icon={<Plus />} />
      {loans.length > 0 && (
        <div className="chips">
          {chips.map(x => (
            <button key={x.id} className={"chip " + (x.extra || "") + (estado === x.id ? " active" : "")} onClick={() => setEstado(x.id)}>
              <b>{x.n}</b>{x.label}
            </button>
          ))}
        </div>
      )}
      <div className="panel">
        <div className="panel-body"><LoanTable rows={visible} onPay={onPay} onHist={onHist} /></div>
      </div>
    </section>
  );
}

function LoanTable({ rows, onPay, onHist }) {
  const actions = !!onPay;
  if (!rows.length) return <Empty text="No hay registros." icon={<Inbox />} />;
  return (
    <div className="table-wrap">
      <table className="table loan-table">
        <thead>
          <tr>
            <th>Persona</th><th>Fecha</th><th>Vencimiento</th><th>Prestado</th><th>Interés</th>
            <th>Pagado</th><th>Progreso</th><th>Saldo</th>{actions && <th>Acciones</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map(r => {
            const pct = r.total ? Math.min(100, (r.paid / r.total) * 100) : 0;
            const done = r.balance <= 0;
            return (
              <tr key={r.id}>
                <td data-label="Persona"><div className="person-cell"><Avatar name={r.person} /><b>{r.person}</b></div></td>
                <td data-label="Fecha" className="muted">{r.date}</td>
                <td data-label="Vencimiento">
                  {r.mora_dias > 0 ? (
                    <span className="badge danger">Mora {r.mora_dias}d</span>
                  ) : r.vencimiento ? (
                    <span className="muted">{fmtDate(r.vencimiento)}</span>
                  ) : (
                    <span className="muted">—</span>
                  )}
                </td>
                <td data-label="Prestado" className="num"><b>{money(r.amount)}</b></td>
                <td data-label="Interés">
                  <div className="interest-cell">
                    {r.tasa > 0 ? <><span className="rate-chip">{r.tasa}%</span><span className="muted">{money(r.interest)}</span></> : <span className="muted">—</span>}
                  </div>
                </td>
                <td data-label="Pagado" className="num">{money(r.paid)}</td>
                <td data-label="Progreso">
                  <div className={"progress" + (done ? " ok" : "")}>
                    <i style={{ width: pct + "%" }} />
                  </div>
                </td>
                <td data-label="Saldo" className="num">
                  <b className={done ? "text-green" : "text-strong"}>{money(r.balance)}</b>
                  {done && <span className="badge ok">Pagado</span>}
                </td>
                {actions && (
                  <td data-label="Acciones">
                    <div className="row-actions">
                      <button className="btn small" disabled={!r.balance} onClick={() => onPay(r.id)}>
                        {r.balance ? "Registrar pago" : "Pagado"}
                      </button>
                      <button className="icon-btn ghost" title="Historial de pagos" onClick={() => onHist(r.id)}>
                        <History />
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Modal({ title, icon, children, close }) {
  useEffect(() => {
    const onKey = e => { if (e.key === "Escape") close(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [close]);
  return (
    <div className="overlay" onMouseDown={e => e.target === e.currentTarget && close()}>
      <div className="modal" role="dialog" aria-modal="true">
        <div className="modal-head">
          <div className="modal-title">{icon && <span className="modal-icon">{icon}</span>}<h2>{title}</h2></div>
          <button className="icon-btn ghost" onClick={close}><X /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

function PersonModal({ close, save, person }) {
  const [n, setN] = useState(person?.nombre || "");
  const submit = e => {
    e.preventDefault();
    const name = n.trim();
    if (name) save(name);
  };
  return (
    <Modal title={person ? "Editar persona" : "Nueva persona"} icon={<UserPlus />} close={close}>
      <form onSubmit={submit}>
        <label className="field"><span>Nombre completo</span>
          <input autoFocus value={n} onChange={e => setN(e.target.value)} placeholder="Ej. Carlos Pérez" />
        </label>
        <div className="actions">
          <button type="button" className="btn ghost" onClick={close}>Cancelar</button>
          <button type="submit" className="btn primary" disabled={!n.trim()}><CheckCircle2 />{person ? "Guardar cambios" : "Guardar persona"}</button>
        </div>
      </form>
    </Modal>
  );
}

function ConfirmModal({ person, close, onConfirm }) {
  return (
    <Modal title="Archivar persona" icon={<Archive />} close={close}>
      <p className="confirm-text">¿Seguro que deseas archivar a <b>{person?.nombre}</b>? Desaparecerá de la lista activa, pero <b>su historial de préstamos y pagos se conserva</b> y podrás restaurarla cuando quieras.</p>
      <div className="actions">
        <button className="btn ghost" onClick={close}>Cancelar</button>
        <button className="btn danger" onClick={onConfirm}><Trash2 />Archivar</button>
      </div>
    </Modal>
  );
}

function LoanModal({ people, close, save }) {
  const [persona, setPersona] = useState(people[0]?.id || "");
  const [monto, setMonto] = useState("");
  const [tasa, setTasa] = useState("");
  const [venc, setVenc] = useState("");
  const m = parseFloat(monto) || 0;
  const r = parseFloat(tasa) || 0;
  const interest = m * r / 100;
  const total = m + interest;
  const submit = e => {
    e.preventDefault();
    if (m > 0) save(persona, m, r, venc || null);
  };
  if (!people.length) {
    return (
      <Modal title="Nuevo préstamo" icon={<WalletCards />} close={close}>
        <div className="empty"><div className="empty-icon"><Users /></div><p>Primero registra una persona para poder crear un préstamo.</p></div>
        <div className="actions"><button className="btn primary" onClick={close}>Entendido</button></div>
      </Modal>
    );
  }
  return (
    <Modal title="Nuevo préstamo" icon={<WalletCards />} close={close}>
      <form onSubmit={submit}>
        <label className="field"><span>Persona</span>
          <select value={persona} onChange={e => setPersona(e.target.value)}>
            {people.map(p => <option key={p.id} value={p.id}>{p.nombre}</option>)}
          </select>
        </label>
        <div className="field-row">
          <label className="field"><span>Monto</span>
            <input type="number" inputMode="numeric" min="1" value={monto} onChange={e => setMonto(e.target.value)} placeholder="1.000.000" />
          </label>
          <label className="field"><span>Tasa de interés (%)</span>
            <input type="number" inputMode="decimal" min="0" max="100" value={tasa} onChange={e => setTasa(e.target.value)} placeholder="10" />
          </label>
          <label className="field"><span>Vence el (opcional)</span>
            <input type="date" value={venc} onChange={e => setVenc(e.target.value)} title="Fecha límite de pago" />
          </label>
        </div>
        {(m > 0 || r > 0) && (
          <div className="summary">
            <div><span>Interés ({r}%)</span><b>{money(interest)}</b></div>
            <div><span>Total a pagar</span><b className="total">{money(total)}</b></div>
          </div>
        )}
        <div className="actions">
          <button type="button" className="btn ghost" onClick={close}>Cancelar</button>
          <button type="submit" className="btn primary" disabled={m <= 0}><CheckCircle2 />Registrar préstamo</button>
        </div>
      </form>
    </Modal>
  );
}

function PayModal({ loan, close, save }) {
  const [amt, setAmt] = useState("");
  const a = parseFloat(amt) || 0;
  const pct = loan ? Math.min(100, (loan.paid / loan.total) * 100) : 0;
  const submit = e => {
    e.preventDefault();
    if (a > 0 && a <= loan.balance) save(loan.id, a);
  };
  return (
    <Modal title="Registrar pago" icon={<ArrowDownLeft />} close={close}>
      {loan ? (
        <form onSubmit={submit}>
          <div className="loan-summary">
            <div className="person-cell"><Avatar name={loan.person} /><b>{loan.person}</b></div>
            <div className="loan-totals">
              <span>Total <b>{money(loan.total)}</b></span>
              <span>Pagado <b className="text-green">{money(loan.paid)}</b></span>
              <span>Saldo <b>{money(loan.balance)}</b></span>
            </div>
          </div>
          <div className="progress big"><i style={{ width: pct + "%" }} /></div>
          <label className="field"><span>Valor del pago</span>
            <input type="number" inputMode="numeric" min="1" max={loan.balance} value={amt} onChange={e => setAmt(e.target.value)} placeholder="250.000" />
          </label>
          <div className="actions">
            <button type="button" className="btn ghost" onClick={close}>Cancelar</button>
            <button type="submit" className="btn primary" disabled={a <= 0 || a > loan.balance}><CheckCircle2 />Guardar pago</button>
          </div>
        </form>
      ) : (
        <Empty text="Préstamo no encontrado." />
      )}
    </Modal>
  );
}

function HistModal({ loan, close, onChanged }) {
  const [rows, setRows] = useState(null);
  const [editing, setEditing] = useState(null);
  useEffect(() => {
    if (!loan) return;
    api("/prestamos/" + loan.id + "/pagos").then(setRows).catch(() => setRows([]));
  }, [loan]);
  const anular = x => {
    if (!window.confirm("¿Anular el pago de " + money(x.monto) + " del " + x.fecha + "?\nEl saldo del préstamo se recalculará.")) return;
    api("/pagos/" + x.id + "/anular", { method: "POST" })
      .then(() => { onChanged(); return api("/prestamos/" + loan.id + "/pagos"); })
      .then(setRows)
      .catch(e => alert(e.message));
  };
  const guardarEdit = (m, f) => {
    api("/pagos/" + editing.id, { method: "PUT", body: JSON.stringify({ monto: m, fecha: f || null }) })
      .then(() => { onChanged(); setEditing(null); return api("/prestamos/" + loan.id + "/pagos"); })
      .then(setRows)
      .catch(e => alert(e.message));
  };
  return (
    <Modal title={"Historial · " + loan.person} icon={<History />} close={close}>
      {loan && (
        <div className="loan-summary compact">
          <div className="person-cell"><Avatar name={loan.person} /><b>{money(loan.total)}</b></div>
          <span className="muted">{loan.tasa > 0 ? `${loan.tasa}% de interés` : "Sin interés"}</span>
        </div>
      )}
      <div className="history">
        {rows === null ? (
          <div className="loading-light">Cargando historial…</div>
        ) : rows.length ? (
          rows.map(x => (
            <div className="history-row" key={x.id}>
              <span>{x.fecha}</span><b>{money(x.monto)}</b>
              <div className="row-actions">
                <button className="icon-btn ghost sm" title="Editar pago" onClick={() => setEditing(x)}><Pencil /></button>
                <button className="icon-btn danger sm" title="Anular pago" onClick={() => anular(x)}><Undo2 /></button>
              </div>
            </div>
          ))
        ) : (
          <Empty text="No hay pagos registrados." />
        )}
      </div>
      {editing && (
        <EditPayModal pago={editing} close={() => setEditing(null)} save={guardarEdit} />
      )}
    </Modal>
  );
}

function EditPayModal({ pago, close, save }) {
  const [monto, setMonto] = useState(pago.monto);
  const [fecha, setFecha] = useState(pago.fecha || "");
  const m = parseFloat(monto) || 0;
  const submit = e => {
    e.preventDefault();
    if (m > 0) save(m, fecha || null);
  };
  return (
    <Modal title="Editar pago" icon={<Pencil />} close={close}>
      <form onSubmit={submit}>
        <div className="loan-summary compact">
          <div className="person-cell"><b>Pago del {pago.fecha}</b></div>
          <span className="muted">Valor actual {money(pago.monto)}</span>
        </div>
        <div className="field-row">
          <label className="field"><span>Monto</span>
            <input type="number" inputMode="numeric" min="1" autoFocus value={monto} onChange={e => setMonto(e.target.value)} />
          </label>
          <label className="field"><span>Fecha</span>
            <input type="date" value={fecha} onChange={e => setFecha(e.target.value)} />
          </label>
        </div>
        <div className="actions">
          <button type="button" className="btn ghost" onClick={close}>Cancelar</button>
          <button type="submit" className="btn primary" disabled={m <= 0}><CheckCircle2 />Guardar cambios</button>
        </div>
      </form>
    </Modal>
  );
}

const AUDIT_LABELS = {
  registro: "Cuenta creada", login: "Inicio de sesión", login_fallido: "Intento fallido de acceso",
  crear_persona: "Persona creada", editar_persona: "Persona editada", archivar_persona: "Persona archivada",
  restaurar_persona: "Persona restaurada", crear_prestamo: "Préstamo creado", crear_pago: "Pago registrado",
  anular_pago: "Pago anulado", cambiar_password: "Contraseña cambiada", regenerar_clave: "Clave regenerada",
  recuperacion: "Contraseña recuperada",
};

function AuditPage() {
  const [rows, setRows] = useState(null);
  const load = () => {
    setRows(null);
    api("/auditoria?limite=300").then(setRows).catch(() => setRows([]));
  };
  useEffect(load, []);
  return (
    <section className="page">
      <PageHead eyebrow="Seguridad" title="Auditoría" sub="Registro de todos los eventos del sistema." />
      <div className="filter-row">
        <button className="btn ghost" onClick={load}><RefreshCw />Actualizar</button>
        {rows !== null && <span className="muted">{rows.length} evento(s)</span>}
      </div>
      <div className="panel">
        <div className="panel-body">
          {rows === null ? (
            <div className="loading-light">Cargando auditoría…</div>
          ) : rows.length ? (
            <div className="table-wrap">
              <table className="table audit-table">
                <thead>
                  <tr><th>Fecha</th><th>Usuario</th><th>Evento</th><th>Detalle</th></tr>
                </thead>
                <tbody>
                  {rows.map(a => (
                    <tr key={a.id}>
                      <td data-label="Fecha" className="muted">{a.created_at.replace("T", " ")}</td>
                      <td data-label="Usuario"><b>{a.usuario}</b></td>
                      <td data-label="Evento"><span className="badge ghost">{AUDIT_LABELS[a.accion] || a.accion}</span></td>
                      <td data-label="Detalle" className="muted">{a.detalle}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty text="Aún no hay eventos registrados." icon={<ScrollText />} />
          )}
        </div>
      </div>
    </section>
  );
}

function Splash() {
  return (
    <div className="auth-screen">
      <div className="auth-splash">
        <div className="auth-logo"><Logo size={26} /></div>
        <Loader2 className="icon-spin" />
      </div>
    </div>
  );
}

function LoginScreen({ onOk }) {
  const [mode, setMode] = useState("check");
  const [username, setUsername] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [nueva, setNueva] = useState("");
  const [nueva2, setNueva2] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [pendingUser, setPendingUser] = useState(null);
  const [recoveryKey, setRecoveryKey] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api("/auth/estado")
      .then(r => setMode(r.tiene_usuarios ? "login" : "register"))
      .catch(() => setMode("login"));
  }, []);

  const submit = async e => {
    e.preventDefault();
    setError(""); setSuccess("");
    if (mode === "forgot" && nueva.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres"); return;
    }
    if (mode === "forgot" && nueva !== nueva2) {
      setError("Las contraseñas no coinciden"); return;
    }
    if (mode === "register" && password.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres"); return;
    }
    setBusy(true);
    try {
      if (mode === "forgot") {
        await api("/auth/olvide_password", { method: "POST", body: JSON.stringify({ usuario: username, codigo: code, nueva }) });
        setBusy(false);
        setSuccess("Contraseña restablecida. Inicia sesión con tu nueva contraseña.");
        setMode("login"); setPassword(""); setCode(""); setNueva(""); setNueva2("");
        return;
      }
      const body = mode === "register"
        ? { usuario: username, nombre: name, password }
        : { usuario: username, password };
      const u = await api("/auth/" + (mode === "register" ? "registro" : "login"), { method: "POST", body: JSON.stringify(body) });
      if (mode === "register" && u.recovery) {
        setPendingUser(u); setRecoveryKey(u.recovery); setMode("key"); setBusy(false);
        return;
      }
      onOk(u);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  const copyKey = async () => {
    try { await navigator.clipboard.writeText(recoveryKey); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch {}
  };

  return (
    <div className="auth-screen">
      {mode === "key" ? (
        <div className="auth-card">
          <div className="auth-logo"><ShieldCheck /></div>
          <h1>Guarda tu clave de recuperación</h1>
          <span className="auth-sub">Si olvidas tu contraseña, esta clave es la única forma de recuperar el acceso. <b>Se muestra solo una vez.</b> Guárdala en un lugar seguro.</span>
          <div className="recovery-box">
            <code className="recovery-key" title="Clave de recuperación">{recoveryKey}</code>
            <button type="button" className="btn small" onClick={copyKey}>{copied ? <CheckCircle2 /> : <KeyRound />}{copied ? "Copiada" : "Copiar"}</button>
          </div>
          <p className="auth-hint">Consejo: guárdala en tu gestor de contraseñas o en papel.</p>
          <button type="button" className="btn primary block" onClick={() => pendingUser && onOk(pendingUser)}><CheckCircle2 />Ya la guardé, entrar</button>
        </div>
      ) : (
        <form className="auth-card" onSubmit={submit}>
          <div className="auth-logo"><Logo size={26} /></div>
          <h1>{mode === "register" ? "Crea tu cuenta" : mode === "forgot" ? "Recuperar contraseña" : "Bienvenido de nuevo"}</h1>
          <span className="auth-sub">
            {mode === "check" ? "Verificando configuración…" :
              mode === "register" ? "Este será el administrador del sistema. Solo puedes crear una cuenta." :
              mode === "forgot" ? "Escribe tu usuario y la clave de recuperación para restablecer la contraseña." :
              "Inicia sesión para acceder a tus datos financieros."}
          </span>

          {error && <div className="auth-error"><AlertCircle />{error}</div>}
          {success && <div className="auth-success"><CheckCircle2 />{success}</div>}

          {mode === "register" && (
            <label className="field"><span>Nombre completo</span>
              <input autoFocus value={name} onChange={e => setName(e.target.value)} placeholder="Ej. Carlos Pérez" />
            </label>
          )}
          <label className="field"><span>Usuario</span>
            <input
              autoFocus={mode !== "register"}
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="Tu usuario"
              autoComplete="username"
            />
          </label>
          {mode !== "forgot" ? (
            <label className="field"><span>Contraseña</span>
              <div className="pw-wrap">
                <input
                  type={show ? "text" : "password"}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete={mode === "register" ? "new-password" : "current-password"}
                />
                <button type="button" className="pw-toggle" onClick={() => setShow(o => !o)} title={show ? "Ocultar" : "Mostrar"}>
                  {show ? <EyeOff /> : <Eye />}
                </button>
              </div>
            </label>
          ) : (
            <>
              <label className="field"><span>Clave de recuperación</span>
                <input value={code} onChange={e => setCode(e.target.value)} placeholder="XXXX-XXXX-XXXX" autoComplete="off" />
              </label>
              <div className="field-row">
                <label className="field"><span>Nueva contraseña</span>
                  <input type="password" value={nueva} onChange={e => setNueva(e.target.value)} placeholder="Mínimo 6 caracteres" autoComplete="new-password" />
                </label>
                <label className="field"><span>Confirmar</span>
                  <input type="password" value={nueva2} onChange={e => setNueva2(e.target.value)} placeholder="Repite" autoComplete="new-password" />
                </label>
              </div>
            </>
          )}
          {mode === "register" && !nueva && <p className="auth-hint">Mínimo 6 caracteres.</p>}

          <button className="btn primary block" type="submit" disabled={busy || mode === "check" || !username.trim() || (mode !== "forgot" ? !password : !code || nueva.length < 6)}>
            {busy ? <Loader2 className="icon-spin" /> :
              mode === "register" ? <><Lock />Crear cuenta</> :
              mode === "forgot" ? <><KeyRound />Restablecer contraseña</> :
              <><Lock />Iniciar sesión</>}
          </button>

          {(mode === "login" || mode === "forgot") && (
            <button type="button" className="auth-link" onClick={() => { setMode(mode === "forgot" ? "login" : "forgot"); setError(""); setSuccess(""); }}>
              {mode === "forgot" ? "Volver a iniciar sesión" : "¿Olvidaste tu contraseña?"}
            </button>
          )}

          {mode !== "forgot" && (
            <p className="auth-foot"><ShieldCheck /> Tus datos están <b className="auth-brand">protegidos</b> con acceso seguro.</p>
          )}
        </form>
      )}
    </div>
  );
}

function PassModal({ close, onDone }) {
  const [a, setA] = useState("");
  const [n, setN] = useState("");
  const [n2, setN2] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const submit = async e => {
    e.preventDefault();
    setErr("");
    if (n !== n2) { setErr("Las contraseñas no coinciden"); return; }
    setBusy(true);
    try {
      await api("/auth/cambiar_password", { method: "POST", body: JSON.stringify({ actual: a, nueva: n }) });
      onDone();
      close();
    } catch (ex) {
      setErr(ex.message);
      setBusy(false);
    }
  };
  return (
    <Modal title="Cambiar contraseña" icon={<KeyRound />} close={close}>
      <form onSubmit={submit}>
        {err && <div className="auth-error">{err}</div>}
        <label className="field"><span>Contraseña actual</span>
          <input type="password" value={a} onChange={e => setA(e.target.value)} placeholder="••••••••" autoComplete="current-password" />
        </label>
        <label className="field"><span>Nueva contraseña</span>
          <input type="password" value={n} onChange={e => setN(e.target.value)} placeholder="Mínimo 6 caracteres" autoComplete="new-password" />
        </label>
        <label className="field"><span>Confirmar nueva contraseña</span>
          <input type="password" value={n2} onChange={e => setN2(e.target.value)} placeholder="Repite la contraseña" autoComplete="new-password" />
        </label>
        <div className="actions">
          <button type="button" className="btn ghost" onClick={close}>Cancelar</button>
          <button type="submit" className="btn primary" disabled={busy || !a || n.length < 6}>
            {busy ? <Loader2 className="icon-spin" /> : <CheckCircle2 />}Actualizar
          </button>
        </div>
      </form>
    </Modal>
  );
}

function RecoveryModal({ close, onDone }) {
  const [code, setCode] = useState(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    api("/auth/regenerar_clave", { method: "POST" })
      .then(r => { setCode(r.recovery); onDone(); })
      .catch(e => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const copy = async () => {
    if (!code) return;
    try { await navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch {}
  };
  return (
    <Modal title="Clave de recuperación" icon={<ShieldAlert />} close={close}>
      {error ? (
        <>
          <div className="auth-error"><AlertCircle />{error}</div>
          <div className="actions"><button className="btn ghost" onClick={close}>Cerrar</button></div>
        </>
      ) : !code ? (
        <div className="loading-light"><Loader2 className="icon-spin" /> Generando clave…</div>
      ) : (
        <>
          <span className="auth-sub">Guarda esta clave: es la única forma de recuperar el acceso si olvidas tu contraseña. <b>Generar una nueva invalida la anterior.</b></span>
          <div className="recovery-box">
            <code className="recovery-key">{code}</code>
            <button type="button" className="btn small" onClick={copy}>{copied ? <CheckCircle2 /> : <KeyRound />}{copied ? "Copiada" : "Copiar"}</button>
          </div>
          <div className="actions">
            <button className="btn ghost" onClick={close}>Cerrar</button>
            <button className="btn primary" onClick={copy}>{copied ? <CheckCircle2 /> : <KeyRound />}{copied ? "Copiada" : "Copiar y cerrar"}</button>
          </div>
        </>
      )}
    </Modal>
  );
}

function Avatar({ name, size = "md" }) {
  const c = avatarColor(name);
  return <span className={"avatar " + size} style={{ background: c + "1f", color: c }}>{initials(name)}</span>;
}

function Empty({ text, icon }) {
  return <div className="empty"><div className="empty-icon">{icon || <Inbox />}</div><p>{text}</p></div>;
}

function Skeleton() {
  return (
    <div className="page">
      <div className="sk head" />
      <div className="stats-grid">
        {[0, 1, 2, 3, 4].map(i => <div key={i} className="sk card" />)}
      </div>
      <div className="sk panel" />
    </div>
  );
}

function UpdateBanner() {
  const [info, setInfo] = useState(null);
  const [state, setState] = useState("idle");
  const [err, setErr] = useState("");
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    api("/updates").then(setInfo).catch(() => {});
  }, []);

  if (!info || !info.update || dismissed) return null;

  const install = async () => {
    setErr("");
    setState("busy");
    try {
      await api("/updates/download", { method: "POST" });
      setState("done");
    } catch (e) {
      setErr(e.message);
      setState("idle");
    }
  };

  return (
    <div className="update-banner">
      <Sparkles className="update-icon" />
      <span className="update-text">
        {state === "done"
          ? <>Instalando {info.latest}: el programa se cerrará y volverá a abrirse solo.</>
          : <>Nueva versión <b>{info.latest}</b> disponible. Instálala para recibir los últimos cambios y la nueva funcionalidad.</>}
        {err && <em className="update-err">{err}</em>}
      </span>
      <button
        className="update-btn"
        onClick={install}
        disabled={state === "busy" || state === "done" || !info.url}
        title={!info.url ? "El instalador de esta versión aún no está publicado, intenta más tarde" : "Descargar e instalar la nueva versión"}
      >
        {state === "busy" ? <><Loader2 className="icon-spin" />Descargando…</>
          : state === "done" ? <><CheckCircle2 />Instalando</>
          : <><Download />Descargar e instalar</>}
      </button>
      <button className="update-dismiss" onClick={() => setDismissed(true)} aria-label="Cerrar aviso"><X /></button>
    </div>
  );
}

function Toasts({ items }) {
  if (!items.length) return null;
  return (
    <div className="toasts">
      {items.map(t => (
        <div key={t.id} className={"toast " + t.type}>
          {t.type === "success" ? <CheckCircle2 /> : <AlertCircle />}
          <span>{t.msg}</span>
        </div>
      ))}
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);