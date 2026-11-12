import React, { useEffect, useState, useCallback } from "react";
import { Link, useParams, useNavigate, useSearchParams } from "react-router-dom";
import { Plus, Star, Check, X as XIcon, Printer, Bell } from "lucide-react";
import api from "./api";
import { useAuth, PageHead, Status } from "./App";

const som = (v) => Number(v || 0).toLocaleString("uz-UZ") + " so'm";
const errText = (e, d = "Xatolik yuz berdi.") => {
  const x = e?.response?.data;
  if (!x) return d;
  if (typeof x === "string") return d;
  if (x.detail) return x.detail;
  return Object.entries(x).map(([k, v]) => `${k}: ${[].concat(v).join(", ")}`).join(" | ");
};
const list = (r) => (Array.isArray(r.data) ? r.data : r.data.results || []);
const STATUSES = [["new", "Yangi"], ["diagnostics", "Diagnostika"], ["waiting_parts", "Ehtiyot qism kutilmoqda"], ["in_progress", "Ta'mirlanmoqda"], ["completed", "Yakunlandi"], ["cancelled", "Bekor qilindi"]];
export const STATUS_META = {
  new: { label: "Yangi", color: "#64748b", desc: "Qabul qilindi" },
  diagnostics: { label: "Diagnostika", color: "#2563eb", desc: "Nosozlik aniqlanmoqda" },
  waiting_parts: { label: "Ehtiyot qism kutilmoqda", color: "#d97706", desc: "Qism kelishi kutilmoqda" },
  in_progress: { label: "Ta'mirlanmoqda", color: "#7c3aed", desc: "Usta ishlayapti" },
  completed: { label: "Yakunlandi", color: "#059669", desc: "Ish tugadi" },
  cancelled: { label: "Bekor qilindi", color: "#e11d48", desc: "Buyurtma bekor qilindi" },
};
const FLOW = ["new", "diagnostics", "waiting_parts", "in_progress", "completed"];
function StatusStepper({ value }) {
  if (value === "cancelled") return <div className="stepper cancelled">Buyurtma bekor qilingan</div>;
  const at = FLOW.indexOf(value);
  return <div className="stepper">{FLOW.map((k, i) => <div key={k} className={`step ${i < at ? "done" : ""} ${i === at ? "now" : ""}`}>
    <div className="bubble">{i < at ? "✓" : i + 1}</div><span>{STATUS_META[k].label}</span></div>)}</div>;
}
const PAY = { unpaid: "To'lanmagan", partial: "Qisman to'langan", paid: "To'langan" };

function Table({ cols, rows, empty = "Hozircha ma'lumot yo'q." }) {
  return (
    <div className="table-wrap"><table>
      <thead><tr>{cols.map((c) => <th key={c}>{c.toUpperCase()}</th>)}</tr></thead>
      <tbody>{rows.length ? rows : <tr><td colSpan={cols.length} className="empty">{empty}</td></tr>}</tbody>
    </table></div>
  );
}
const Field = ({ label, children }) => <label>{label}{children}</label>;

/* ---------- Buyurtmalar ro'yxati + yaratish + filtrlar ---------- */
export function OrdersPage() {
  const { user } = useAuth();
  const staff = ["admin", "manager"].includes(user.role);
  const [rows, setRows] = useState([]), [err, setErr] = useState("");
  const [sp] = useSearchParams();
  const [f, setF] = useState({ q: "", status: sp.get("status") || "", mechanic: "", client: "", date_from: "", date_to: "" });
  const [vehicles, setVehicles] = useState([]), [mechanics, setMechanics] = useState([]), [clients, setClients] = useState([]);
  const [open, setOpen] = useState(false), [form, setForm] = useState({ vehicle: "", complaint: "" });

  const load = useCallback(() => {
    const params = Object.fromEntries(Object.entries(f).filter(([k, v]) => v && k !== "status"));
    api.get("/orders/", { params }).then((r) => setRows(list(r))).catch((e) => setErr(errText(e)));
  }, [f.q, f.mechanic, f.client, f.date_from, f.date_to]);
  const shown = f.status ? rows.filter((o) => o.status === f.status) : rows;
  const counts = rows.reduce((a, o) => ({ ...a, [o.status]: (a[o.status] || 0) + 1 }), {});
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (user.role !== "mechanic") api.get("/vehicles/").then((r) => setVehicles(list(r))).catch(() => {});
    if (staff) {
      api.get("/staff/").then((r) => setMechanics(list(r).filter((u) => u.role === "mechanic"))).catch(() => {});
      api.get("/clients/").then((r) => setClients(list(r))).catch(() => {});
    }
  }, []);

  const create = async (e) => {
    e.preventDefault(); setErr("");
    try { await api.post("/orders/", { vehicle: Number(form.vehicle), complaint: form.complaint }); setOpen(false); setForm({ vehicle: "", complaint: "" }); load(); }
    catch (ex) { setErr(errText(ex)); }
  };
  const canCreate = user.role !== "mechanic";
  return <>
    <PageHead eyebrow="BOSHQARUV / BUYURTMALAR" title={user.role === "client" ? "Mening buyurtmalarim" : "Buyurtmalar"} desc="Ta'mirlash buyurtmalari, holati va to'lovlari."
      action={canCreate && <button className="btn-primary" onClick={() => setOpen((v) => !v)}><Plus size={17} /> {user.role === "client" ? "Ta'mirlash so'rovi" : "Yangi buyurtma"}</button>} />
    {err && <div className="alert">{err}</div>}
    {open && <section className="panel edit-panel"><div className="panel-head"><div><h3>{user.role === "client" ? "Servisga so'rov yuborish" : "Yangi buyurtma"}</h3><p>Avtomobil va muammoni kiriting.</p></div></div>
      <form className="manage-form" onSubmit={create}>
        <Field label="Avtomobil"><select required value={form.vehicle} onChange={(e) => setForm({ ...form, vehicle: e.target.value })}><option value="">Tanlang</option>{vehicles.map((v) => <option key={v.id} value={v.id}>{v.make} {v.model} — {v.plate_number}{staff ? ` (${v.owner_name || "mijoz"})` : ""}</option>)}</select></Field>
        <Field label="Muammo tavsifi"><input required value={form.complaint} onChange={(e) => setForm({ ...form, complaint: e.target.value })} /></Field>
        <button className="btn-primary">Yuborish</button>
      </form></section>}
    <div className="status-tabs">
      <button className={`status-chip ${!f.status ? "on" : ""}`} style={{ "--c": "#0f9d8a" }} onClick={() => setF({ ...f, status: "" })}>Hammasi <b>{rows.length}</b></button>
      {Object.entries(STATUS_META).map(([k, m]) => <button key={k} className={`status-chip ${f.status === k ? "on" : ""}`} style={{ "--c": m.color }} onClick={() => setF({ ...f, status: f.status === k ? "" : k })}><span className="dot" style={{ background: m.color }} />{m.label} <b>{counts[k] || 0}</b></button>)}
    </div>
    <section className="panel"><div className="panel-head"><div><h3>Qidirish va filtr</h3><p>Sana, status, mijoz va usta bo'yicha</p></div></div>
      <div className="manage-form">
        <Field label="Qidiruv (raqam, ism, muammo)"><input value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} /></Field>
        {staff && <Field label="Mijoz"><select value={f.client} onChange={(e) => setF({ ...f, client: e.target.value })}><option value="">Hammasi</option>{clients.map((c) => <option key={c.id} value={c.id}>{c.full_name}</option>)}</select></Field>}
        {staff && <Field label="Usta"><select value={f.mechanic} onChange={(e) => setF({ ...f, mechanic: e.target.value })}><option value="">Hammasi</option>{mechanics.map((m) => <option key={m.id} value={m.id}>{m.full_name}</option>)}</select></Field>}
        <Field label="Sanadan"><input type="date" value={f.date_from} onChange={(e) => setF({ ...f, date_from: e.target.value })} /></Field>
        <Field label="Sanagacha"><input type="date" value={f.date_to} onChange={(e) => setF({ ...f, date_to: e.target.value })} /></Field>
      </div></section>
    <section className="panel data-panel"><div className="panel-head"><div><h3>Ro'yxat</h3><p>{shown.length} ta buyurtma</p></div></div>
      <Table cols={["ID", "Avtomobil", "Mijoz", "Usta", "Status", "To'lov", "Jami"]} rows={shown.map((o) => <tr key={o.id}>
        <td><Link to={`/orders/${o.id}`}><b className="order-id">AS-{String(o.id).padStart(4, "0")}</b></Link></td>
        <td>{o.vehicle_label}</td><td>{o.client_name || "—"}</td><td>{o.mechanic_name || "—"}</td>
        <td><Status value={o.status} /></td><td>{PAY[o.payment_status]}</td><td className="amount">{som(o.total_amount)}</td></tr>)} />
    </section>
  </>;
}

/* ---------- Buyurtma tafsilotlari ---------- */
export function OrderDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const role = user.role, staff = ["admin", "manager"].includes(role);
  const [o, setO] = useState(null), [err, setErr] = useState(""), [msg, setMsg] = useState("");
  const [services, setServices] = useState([]), [parts, setParts] = useState([]), [mechanics, setMechanics] = useState([]), [history, setHistory] = useState([]);
  const [sel, setSel] = useState({ service: "", part: "", qty: 1, mechanic: "", pay: "", method: "cash", reqPart: "", reqQty: 1, reqNote: "" });
  const [work, setWork] = useState({ diagnosis: "", extra_issues: "", work_notes: "", add_minutes: 0 });
  const [review, setReview] = useState({ rating: 5, comment: "" }), [invoice, setInvoice] = useState(null);

  const apply = (data) => { setO(data); setWork((w) => ({ ...w, diagnosis: data.diagnosis || "", extra_issues: data.extra_issues || "", work_notes: data.work_notes || "", add_minutes: 0 })); };
  const load = useCallback(() => {
    api.get(`/orders/${id}/`).then((r) => apply(r.data)).catch((e) => setErr(errText(e, "Buyurtma topilmadi.")));
    api.get(`/orders/${id}/history/`).then((r) => setHistory(list(r))).catch(() => {});
  }, [id]);
  useEffect(() => {
    load();
    api.get("/services/").then((r) => setServices(list(r).filter((s) => s.is_active))).catch(() => {});
    api.get("/parts/").then((r) => setParts(list(r))).catch(() => {});
    if (staff) api.get("/staff/").then((r) => setMechanics(list(r).filter((u) => u.role === "mechanic"))).catch(() => {});
  }, [load]);

  const call = async (fn, ok) => { setErr(""); setMsg(""); try { const r = await fn(); if (r?.data?.id && r.data.vehicle) apply(r.data); else load(); if (ok) setMsg(ok); } catch (e) { setErr(errText(e)); } };
  if (!o) return <>{err ? <div className="alert">{err}</div> : <div className="loading">Yuklanmoqda...</div>}</>;
  const mine = role !== "mechanic" || o.mechanic === user.id;
  const staffOrMine = staff || (role === "mechanic" && mine);

  return <>
    <PageHead eyebrow={`BUYURTMA / AS-${String(o.id).padStart(4, "0")}`} title={o.vehicle_label} desc={`Mijoz: ${o.client_name || "—"} · Usta: ${o.mechanic_name || "biriktirilmagan"}`} action={<Status value={o.status} />} />
    <StatusStepper value={o.status} />
    {err && <div className="alert">{err}</div>}{msg && <div className="alert" style={{ background: "#e8f7ee", color: "#146c43", borderColor: "#b7ebcd" }}>{msg}</div>}

    <section className="panel"><div className="panel-head"><div><h3>Ma'lumot</h3><p>Muammo, diagnostika va hisob</p></div></div>
      <div style={{ padding: "0 23px 22px", lineHeight: 1.8 }}>
        <div><b>Muammo:</b> {o.complaint}</div><div><b>Diagnostika:</b> {o.diagnosis || "—"}</div>
        {o.extra_issues && <div><b>Qo'shimcha nosozliklar:</b> {o.extra_issues}</div>}
        {o.work_notes && <div><b>Bajarilgan ishlar:</b> {o.work_notes}</div>}
        <div><b>Sarflangan vaqt:</b> {o.spent_minutes} daqiqa</div>
        {role !== "mechanic" && <><div><b>Jami narx:</b> {som(o.total_amount)} · <b>To'langan:</b> {som(o.paid_amount)} · <b>Qoldiq:</b> {som(o.balance)}</div><div><b>To'lov holati:</b> {PAY[o.payment_status]}</div></>}
      </div></section>

    <section className="panel"><div className="panel-head"><div><h3>Xizmatlar va ehtiyot qismlar</h3><p>Narx xizmatlar, qismlar va ish haqi asosida hisoblanadi</p></div></div>
      <Table cols={["Nomi", "Turi", "Miqdor", "Narx", ...(staff ? ["Amal"] : [])]} rows={[
        ...o.services.map((s) => <tr key={"s" + s.id}><td>{s.name}</td><td>Xizmat</td><td>1</td><td>{role === "mechanic" ? "—" : som(s.price)}</td>{staff && <td><button className="btn-danger" onClick={() => call(() => api.post(`/orders/${id}/remove_service/`, { service_id: s.id }))}><XIcon size={14} /></button></td>}</tr>),
        ...o.parts.map((p) => <tr key={"p" + p.id}><td>{p.name}</td><td>Qism</td><td>{p.quantity}</td><td>{role === "mechanic" ? "—" : som(p.unit_price * p.quantity)}</td>{staff && <td><button className="btn-danger" onClick={() => call(() => api.post(`/orders/${id}/remove_part/`, { part_id: p.id }))}><XIcon size={14} /></button></td>}</tr>),
      ]} />
      {staff && <div className="manage-form" style={{ padding: "0 23px 22px" }}>
        <Field label="Xizmat qo'shish"><select value={sel.service} onChange={(e) => setSel({ ...sel, service: e.target.value })}><option value="">Tanlang</option>{services.map((s) => <option key={s.id} value={s.id}>{s.name} — {som(s.price)}</option>)}</select></Field>
        <button className="btn-secondary" disabled={!sel.service} onClick={() => call(() => api.post(`/orders/${id}/add_service/`, { service_id: sel.service }))}>Qo'shish</button>
        <Field label="Ehtiyot qism"><select value={sel.part} onChange={(e) => setSel({ ...sel, part: e.target.value })}><option value="">Tanlang</option>{parts.map((p) => <option key={p.id} value={p.id}>{p.name} (qoldiq {p.stock}) — {som(p.sale_price)}</option>)}</select></Field>
        <Field label="Miqdor"><input type="number" min="1" value={sel.qty} onChange={(e) => setSel({ ...sel, qty: e.target.value })} /></Field>
        <button className="btn-secondary" disabled={!sel.part} onClick={() => call(() => api.post(`/orders/${id}/add_part/`, { part_id: sel.part, quantity: Number(sel.qty) }))}>Qism qo'shish</button>
        <Field label="Ish haqi (so'm)"><input type="number" min="0" defaultValue={o.labor_cost} onBlur={(e) => call(() => api.patch(`/orders/${id}/`, { labor_cost: e.target.value }), "Ish haqi saqlandi.")} /></Field>
      </div>}
    </section>

    {staff && <section className="panel"><div className="panel-head"><div><h3>Ustani biriktirish</h3></div></div>
      <div className="manage-form" style={{ padding: "0 23px 22px" }}>
        <Field label="Usta"><select value={sel.mechanic || o.mechanic || ""} onChange={(e) => setSel({ ...sel, mechanic: e.target.value })}><option value="">Tanlang</option>{mechanics.map((m) => <option key={m.id} value={m.id}>{m.full_name}</option>)}</select></Field>
        <button className="btn-primary" disabled={!(sel.mechanic || o.mechanic)} onClick={() => call(() => api.post(`/orders/${id}/assign_mechanic/`, { mechanic_id: sel.mechanic || o.mechanic }), "Usta biriktirildi.")}>Biriktirish</button>
      </div></section>}

    {staffOrMine && <section className="panel"><div className="panel-head"><div><h3>Ta'mirlash jarayoni</h3><p>Status, diagnostika, izoh va vaqt</p></div></div>
      <div className="manage-form" style={{ padding: "0 23px 22px" }}>
        <Field label="Status"><select value={o.status} onChange={(e) => call(() => api.post(`/orders/${id}/set_status/`, { status: e.target.value }), "Status yangilandi.")}>{STATUSES.filter(([k]) => role !== "mechanic" || !["new", "cancelled"].includes(k) || k === o.status).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
        <Field label="Diagnostika natijasi"><input value={work.diagnosis} onChange={(e) => setWork({ ...work, diagnosis: e.target.value })} /></Field>
        <Field label="Qo'shimcha nosozliklar"><input value={work.extra_issues} onChange={(e) => setWork({ ...work, extra_issues: e.target.value })} /></Field>
        <Field label="Bajarilgan ishlar izohi"><input value={work.work_notes} onChange={(e) => setWork({ ...work, work_notes: e.target.value })} /></Field>
        <Field label="Qo'shiladigan vaqt (daq.)"><input type="number" min="0" value={work.add_minutes} onChange={(e) => setWork({ ...work, add_minutes: e.target.value })} /></Field>
        <button className="btn-primary" onClick={() => call(() => api.post(`/orders/${id}/work_update/`, { ...work, add_minutes: Number(work.add_minutes) || 0 }), "Saqlandi.")}>Saqlash</button>
      </div></section>}

    {role === "mechanic" && mine && <section className="panel"><div className="panel-head"><div><h3>Ehtiyot qism so'rash</h3><p>So'rov menejerga yuboriladi</p></div></div>
      <div className="manage-form" style={{ padding: "0 23px 22px" }}>
        <Field label="Qism"><select value={sel.reqPart} onChange={(e) => setSel({ ...sel, reqPart: e.target.value })}><option value="">Tanlang</option>{parts.map((p) => <option key={p.id} value={p.id}>{p.name} (qoldiq {p.stock})</option>)}</select></Field>
        <Field label="Miqdor"><input type="number" min="1" value={sel.reqQty} onChange={(e) => setSel({ ...sel, reqQty: e.target.value })} /></Field>
        <Field label="Izoh"><input value={sel.reqNote} onChange={(e) => setSel({ ...sel, reqNote: e.target.value })} /></Field>
        <button className="btn-primary" disabled={!sel.reqPart} onClick={() => call(() => api.post(`/orders/${id}/request_part/`, { part_id: sel.reqPart, quantity: Number(sel.reqQty), note: sel.reqNote }), "So'rov yuborildi.")}>So'rov yuborish</button>
      </div></section>}

    {staff && <section className="panel"><div className="panel-head"><div><h3>To'lovni qayd etish</h3></div></div>
      <div className="manage-form" style={{ padding: "0 23px 22px" }}>
        <Field label="Summa"><input type="number" min="1" value={sel.pay} onChange={(e) => setSel({ ...sel, pay: e.target.value })} /></Field>
        <Field label="Usul"><select value={sel.method} onChange={(e) => setSel({ ...sel, method: e.target.value })}><option value="cash">Naqd</option><option value="card">Karta</option><option value="transfer">O'tkazma</option></select></Field>
        <button className="btn-primary" disabled={!sel.pay} onClick={() => call(() => api.post(`/orders/${id}/payments/`, { amount: sel.pay, method: sel.method }), "To'lov qayd etildi.").then(() => setSel((s) => ({ ...s, pay: "" })))}>Qayd etish</button>
      </div></section>}

    {role !== "mechanic" && o.status === "completed" && <section className="panel"><div className="panel-head"><div><h3>Hisob-faktura</h3></div>
      <button className="btn-secondary" onClick={() => api.get(`/orders/${id}/invoice/`).then((r) => setInvoice(r.data)).catch((e) => setErr(errText(e)))}>Ko'rish</button></div>
      {invoice && <div id="invoice" style={{ padding: "0 23px 22px", lineHeight: 1.8 }}>
        <b>{invoice.number}</b> · {invoice.date ? new Date(invoice.date).toLocaleDateString("uz-UZ") : ""}<br />
        Mijoz: {invoice.client} · Avtomobil: {invoice.vehicle}<br />
        {invoice.services.map((s) => <div key={"s" + s.id}>{s.name}: {som(s.price)}</div>)}
        {invoice.parts.map((p) => <div key={"p" + p.id}>{p.name} × {p.quantity}: {som(p.unit_price * p.quantity)}</div>)}
        <div>Ish haqi: {som(invoice.labor_cost)}</div>
        <b>Jami: {som(invoice.total)}</b> · To'langan: {som(invoice.paid)} · Qoldiq: {som(invoice.balance)} ({PAY[invoice.payment_status]})<br />
        <button className="btn-secondary" onClick={() => window.print()}><Printer size={14} /> Chop etish</button>
      </div>}</section>}

    {role === "client" && o.status === "completed" && <section className="panel"><div className="panel-head"><div><h3>Fikr va baho</h3></div></div>
      <div className="manage-form" style={{ padding: "0 23px 22px" }}>
        {o.review ? <div>Sizning bahoyingiz: {"★".repeat(o.review.rating)} — {o.review.comment}</div> : <>
          <Field label="Baho (1–5)"><select value={review.rating} onChange={(e) => setReview({ ...review, rating: Number(e.target.value) })}>{[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{n} ★</option>)}</select></Field>
          <Field label="Fikr"><input value={review.comment} onChange={(e) => setReview({ ...review, comment: e.target.value })} /></Field>
          <button className="btn-primary" onClick={() => call(() => api.post(`/orders/${id}/review/`, review), "Fikringiz uchun rahmat!")}>Yuborish</button></>}
      </div></section>}

    <section className="panel"><div className="panel-head"><div><h3>Status tarixi</h3></div></div>
      <Table cols={["Sana", "Kim", "O'zgarish", "Izoh"]} rows={history.map((h) => <tr key={h.id}><td>{new Date(h.created_at).toLocaleString("uz-UZ")}</td><td>{h.actor_name || "—"}</td><td>{h.from_status || "—"} → {h.to_status}</td><td>{h.note || "—"}</td></tr>)} />
    </section>
  </>;
}

/* ---------- Avtomobillar ---------- */
export function VehiclesPage() {
  const { user } = useAuth();
  const staff = ["admin", "manager"].includes(user.role);
  const [rows, setRows] = useState([]), [clients, setClients] = useState([]), [err, setErr] = useState(""), [open, setOpen] = useState(false);
  const empty = { owner: "", make: "", model: "", plate_number: "", year: "", vin: "", color: "" };
  const [form, setForm] = useState(empty), [history, setHistory] = useState(null);
  const load = () => api.get("/vehicles/").then((r) => setRows(list(r))).catch((e) => setErr(errText(e)));
  useEffect(() => { load(); if (staff) api.get("/clients/").then((r) => setClients(list(r))).catch(() => {}); }, []);
  const save = async (e) => {
    e.preventDefault(); setErr("");
    const body = { ...form, year: form.year ? Number(form.year) : null }; if (!staff) delete body.owner;
    try { await api.post("/vehicles/", body); setOpen(false); setForm(empty); load(); } catch (ex) { setErr(errText(ex)); }
  };
  const remove = async (id) => { if (!confirm("O'chirishni tasdiqlaysizmi?")) return; try { await api.delete(`/vehicles/${id}/`); load(); } catch (ex) { setErr(errText(ex, "O'chirib bo'lmadi (buyurtmalari bor bo'lishi mumkin).")); } };
  const showHistory = (v) => api.get("/orders/", { params: { q: v.plate_number } }).then((r) => setHistory({ v, orders: list(r) }));
  return <>
    <PageHead eyebrow="BOSHQARUV / AVTOMOBILLAR" title="Avtomobillar" desc="Avtomobillar ro'yxati va ta'mirlash tarixi." action={<button className="btn-primary" onClick={() => setOpen((v) => !v)}><Plus size={17} /> Avtomobil qo'shish</button>} />
    {err && <div className="alert">{err}</div>}
    {open && <section className="panel edit-panel"><form className="manage-form" onSubmit={save}>
      {staff && <Field label="Mijoz"><select required value={form.owner} onChange={(e) => setForm({ ...form, owner: e.target.value })}><option value="">Tanlang</option>{clients.map((c) => <option key={c.id} value={c.id}>{c.full_name}</option>)}</select></Field>}
      {[["make", "Rusumi"], ["model", "Modeli"], ["plate_number", "Davlat raqami"], ["year", "Ishlab chiqarilgan yil"], ["vin", "VIN"], ["color", "Rang"]].map(([k, l]) => <Field key={k} label={l}><input required={["make", "model", "plate_number"].includes(k)} type={k === "year" ? "number" : "text"} value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} /></Field>)}
      <button className="btn-primary">Saqlash</button></form></section>}
    <section className="panel data-panel"><div className="panel-head"><div><h3>Ro'yxat</h3><p>{rows.length} ta avtomobil</p></div></div>
      <Table cols={["Rusum / model", "Raqam", "Yil", "Rang", ...(staff ? ["Egasi"] : []), "Amallar"]} rows={rows.map((v) => <tr key={v.id}><td>{v.make} {v.model}</td><td>{v.plate_number}</td><td>{v.year || "—"}</td><td>{v.color || "—"}</td>{staff && <td>{v.owner_name || "—"}</td>}
        <td><div className="row-actions"><button className="btn-secondary" onClick={() => showHistory(v)}>Tarix</button>{staff && <button className="btn-danger" onClick={() => remove(v.id)}>O'chirish</button>}</div></td></tr>)} /></section>
    {history && <section className="panel"><div className="panel-head"><div><h3>{history.v.make} {history.v.model} — ta'mirlash tarixi</h3></div><button className="btn-secondary" onClick={() => setHistory(null)}>Yopish</button></div>
      <Table cols={["ID", "Muammo", "Status", "Jami"]} rows={history.orders.map((o) => <tr key={o.id}><td><Link to={`/orders/${o.id}`}>AS-{String(o.id).padStart(4, "0")}</Link></td><td>{o.complaint}</td><td><Status value={o.status} /></td><td>{som(o.total_amount)}</td></tr>)} /></section>}
  </>;
}

/* ---------- Mijozlar (admin/manager) ---------- */
export function ClientsPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]), [err, setErr] = useState(""), [open, setOpen] = useState(null);
  const blank = { username: "", first_name: "", last_name: "", email: "", phone: "", password: "" };
  const [form, setForm] = useState(blank);
  const load = () => api.get("/clients/").then((r) => setRows(list(r))).catch((e) => setErr(errText(e)));
  useEffect(() => { load(); }, []);
  const save = async (e) => {
    e.preventDefault(); setErr("");
    try { if (open === "new") await api.post("/clients/", form); else { const { password, username, ...rest } = form; await api.patch(`/clients/${open}/`, rest); } setOpen(null); load(); }
    catch (ex) { setErr(errText(ex)); }
  };
  return <>
    <PageHead eyebrow="BOSHQARUV / MIJOZLAR" title="Mijozlar" desc="Mijozlarni ro'yxatdan o'tkazish va ma'lumotlarini tahrirlash." action={<button className="btn-primary" onClick={() => { setForm(blank); setOpen("new"); }}><Plus size={17} /> Mijoz qo'shish</button>} />
    {err && <div className="alert">{err}</div>}
    {open !== null && <section className="panel edit-panel"><form className="manage-form" onSubmit={save}>
      {[["username", "Login"], ["first_name", "Ism"], ["last_name", "Familiya"], ["email", "Email"], ["phone", "Telefon"], ["password", "Parol (kamida 8 belgi)"]].filter(([k]) => open === "new" || !["username", "password"].includes(k)).map(([k, l]) => <Field key={k} label={l}><input required={["username", "first_name"].includes(k) || (k === "password" && open === "new")} type={k === "password" ? "password" : "text"} value={form[k] ?? ""} onChange={(e) => setForm({ ...form, [k]: e.target.value })} /></Field>)}
      <button className="btn-primary">Saqlash</button><button type="button" className="btn-secondary" onClick={() => setOpen(null)}>Yopish</button></form></section>}
    <section className="panel data-panel"><Table cols={["Ism", "Login", "Telefon", "Avtomobillar", "Holat", "Amallar"]} rows={rows.map((c) => <tr key={c.id}><td>{c.full_name}</td><td>{c.username}</td><td>{c.phone || "—"}</td><td>{c.vehicles_count}</td><td>{c.is_active ? "Faol" : "Bloklangan"}</td>
      <td><div className="row-actions"><button className="btn-secondary" onClick={() => { setForm(c); setOpen(c.id); }}>Tahrir</button>
        {user.role === "admin" && <button className="btn-secondary" onClick={() => api.patch(`/clients/${c.id}/`, { is_active: !c.is_active }).then(load).catch((e) => setErr(errText(e)))}>{c.is_active ? "Bloklash" : "Faollashtirish"}</button>}</div></td></tr>)} /></section>
  </>;
}

/* ---------- Ehtiyot qism so'rovlari ---------- */
export function PartRequestsPage() {
  const { user } = useAuth();
  const staff = ["admin", "manager"].includes(user.role);
  const [rows, setRows] = useState([]), [err, setErr] = useState("");
  const load = () => api.get("/part-requests/").then((r) => setRows(list(r))).catch((e) => setErr(errText(e)));
  useEffect(() => { load(); }, []);
  const decide = (id, decision) => api.post(`/part-requests/${id}/decide/`, { decision }).then(load).catch((e) => setErr(errText(e)));
  const L = { pending: "Kutilmoqda", approved: "Tasdiqlandi", rejected: "Rad etildi" };
  return <>
    <PageHead eyebrow="OMBOR / SO'ROVLAR" title="Ehtiyot qism so'rovlari" desc={staff ? "Ustalar so'ragan qismlarni tasdiqlang yoki rad eting." : "O'zingiz yuborgan so'rovlar."} />
    {err && <div className="alert">{err}</div>}
    <section className="panel data-panel"><Table cols={["Buyurtma", "Qism", "Miqdor", "Usta", "Izoh", "Holat", ...(staff ? ["Amal"] : [])]} rows={rows.map((r) => <tr key={r.id}>
      <td><Link to={`/orders/${r.order}`}>AS-{String(r.order).padStart(4, "0")}</Link></td><td>{r.part_name}</td><td>{r.quantity}</td><td>{r.mechanic_name || "—"}</td><td>{r.note || "—"}</td><td>{L[r.status]}</td>
      {staff && <td>{r.status === "pending" ? <div className="row-actions"><button className="btn-primary" onClick={() => decide(r.id, "approve")}><Check size={14} /></button><button className="btn-danger" onClick={() => decide(r.id, "reject")}><XIcon size={14} /></button></div> : "—"}</td>}</tr>)} /></section>
  </>;
}

/* ---------- Fikrlar (admin/manager) ---------- */
export function ReviewsPage() {
  const [rows, setRows] = useState([]), [err, setErr] = useState("");
  useEffect(() => { api.get("/reviews/").then((r) => setRows(list(r))).catch((e) => setErr(errText(e))); }, []);
  return <>
    <PageHead eyebrow="TAHLIL / FIKRLAR" title="Mijozlar fikri" desc="Servis faoliyatiga qoldirilgan baholar." />
    {err && <div className="alert">{err}</div>}
    <section className="panel data-panel"><Table cols={["Buyurtma", "Mijoz", "Baho", "Fikr", "Sana"]} rows={rows.map((r) => <tr key={r.id}><td><Link to={`/orders/${r.order}`}>AS-{String(r.order).padStart(4, "0")}</Link></td><td>{r.client_name}</td><td><Star size={14} /> {r.rating}/5</td><td>{r.comment || "—"}</td><td>{new Date(r.created_at).toLocaleDateString("uz-UZ")}</td></tr>)} /></section>
  </>;
}

/* ---------- Foydalanuvchilar va jarayonlar tarixi (admin) ---------- */
export function UsersPage() {
  const [rows, setRows] = useState([]), [log, setLog] = useState([]), [err, setErr] = useState("");
  const load = () => { api.get("/users/").then((r) => setRows(list(r))).catch((e) => setErr(errText(e))); api.get("/activity/").then((r) => setLog(list(r))).catch(() => {}); };
  useEffect(() => { load(); }, []);
  const patch = (id, body) => api.patch(`/users/${id}/`, body).then(load).catch((e) => setErr(errText(e)));
  return <>
    <PageHead eyebrow="ADMIN / FOYDALANUVCHILAR" title="Foydalanuvchilar" desc="Barcha hisoblar: bloklash, faollashtirish va rolni o'zgartirish." />
    {err && <div className="alert">{err}</div>}
    <section className="panel data-panel"><Table cols={["Ism", "Login", "Rol", "Holat", "Amallar"]} rows={rows.map((u) => <tr key={u.id}><td>{u.full_name}</td><td>{u.username}</td>
      <td>{u.role === "admin" ? "Admin" : <select value={u.role} onChange={(e) => patch(u.id, { role: e.target.value })}><option value="manager">Menejer</option><option value="mechanic">Mexanik</option><option value="client">Mijoz</option></select>}</td>
      <td>{u.is_active ? "Faol" : "Bloklangan"}</td><td>{u.role !== "admin" && <button className="btn-secondary" onClick={() => patch(u.id, { is_active: !u.is_active })}>{u.is_active ? "Bloklash" : "Faollashtirish"}</button>}</td></tr>)} /></section>
    <section className="panel data-panel"><div className="panel-head"><div><h3>Jarayonlar tarixi</h3><p>Oxirgi status o'zgarishlari</p></div></div>
      <Table cols={["Sana", "Buyurtma", "Kim", "O'zgarish", "Izoh"]} rows={log.map((h) => <tr key={h.id}><td>{new Date(h.created_at).toLocaleString("uz-UZ")}</td><td><Link to={`/orders/${h.order}`}>AS-{String(h.order).padStart(4, "0")}</Link></td><td>{h.actor}</td><td>{h.from_status || "—"} → {h.to_status}</td><td>{h.note || "—"}</td></tr>)} /></section>
  </>;
}

/* ---------- Dashboardga qo'shimcha rol ko'rsatkichlari ---------- */
export function RoleStats({ role, data }) {
  if (!data) return null;
  const sets = {
    admin: [["Jami mijozlar", data.clients_count], ["Jami avtomobillar", data.vehicles_count], ["Ombordagi mahsulot turlari", data.parts_count], ["Ombor birliklari", data.parts_stock_total], ["Kutilayotgan qism so'rovlari", data.pending_part_requests]],
    manager: [["Bugungi buyurtmalar", data.today_orders], ["Yangi buyurtmalar", data.new_orders], ["Ta'mirlanayotgan", data.in_progress_orders], ["Ta'mirlashni kutayotgan", data.waiting_orders], ["To'lov kutilayotgan", data.awaiting_payment], ["Qism so'rovlari", data.pending_part_requests]],
    mechanic: [["Yangi buyurtmalar", data.new_orders], ["Jarayondagi ta'mirlar", data.in_progress_orders], ["Ehtiyot qism so'rovlari", data.part_requests]],
    client: [["Mening avtomobillarim", data.vehicles_count], ["Jarayondagi ta'mirlar", data.in_progress_orders], ["To'lov kutilayotgan hisoblar", data.awaiting_payment]],
  }[role] || [];
  return <>
    {data.status_counts && <section className="panel"><div className="panel-head"><div><h3>Buyurtma statuslari</h3><p>Statusga bosib buyurtmalarni ko'ring</p></div></div>
      <div className="pipeline">{Object.entries(STATUS_META).map(([k, m]) => <Link key={k} className="pipe-tile" style={{ "--c": m.color }} to={`/orders?status=${k}`}><strong>{data.status_counts[k] || 0}</strong><span>{m.label}</span></Link>)}</div></section>}
    <div className="stats-grid">{sets.map(([l, v]) => <div className="stat-card" key={l}><span className="stat-label">{l}</span><strong>{v ?? "—"}</strong></div>)}</div>
    {role === "admin" && data.top_mechanics?.length > 0 && <section className="panel data-panel"><div className="panel-head"><div><h3>Eng ko'p buyurtma bajargan ustalar</h3></div></div>
      <Table cols={["Usta", "Yakunlangan"]} rows={data.top_mechanics.map((m) => <tr key={m.name}><td>{m.name}</td><td>{m.completed}</td></tr>)} /></section>}
  </>;
}


/* ---------- Profil (barcha rollar) ---------- */
export function ProfilePage() {
  const { user } = useAuth();
  const [form, setForm] = useState({ first_name: user.first_name || "", last_name: user.last_name || "", email: user.email || "", phone: user.phone || "", old_password: "", new_password: "" });
  const [err, setErr] = useState(""), [msg, setMsg] = useState("");
  const save = async (e) => {
    e.preventDefault(); setErr(""); setMsg("");
    const body = { ...form }; if (!body.new_password) { delete body.new_password; delete body.old_password; }
    try { await api.patch("/auth/me/", body); setMsg("Ma'lumotlar saqlandi."); setForm({ ...form, old_password: "", new_password: "" }); }
    catch (ex) { setErr(errText(ex)); }
  };
  return <>
    <PageHead eyebrow="SHAXSIY KABINET" title="Mening profilim" desc={`Login: ${user.username}`} />
    {err && <div className="alert">{err}</div>}{msg && <div className="alert" style={{ background: "#e8f7ee", color: "#146c43" }}>{msg}</div>}
    <section className="panel edit-panel"><form className="manage-form" onSubmit={save}>
      {[["first_name", "Ism"], ["last_name", "Familiya"], ["email", "Email"], ["phone", "Telefon"]].map(([k, l]) => <Field key={k} label={l}><input value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} /></Field>)}
      <Field label="Eski parol (parolni almashtirish uchun)"><input type="password" value={form.old_password} onChange={(e) => setForm({ ...form, old_password: e.target.value })} /></Field>
      <Field label="Yangi parol"><input type="password" value={form.new_password} onChange={(e) => setForm({ ...form, new_password: e.target.value })} /></Field>
      <button className="btn-primary">Saqlash</button></form></section>
  </>;
}

/* ---------- Ombor harakatlari tarixi (admin/manager) ---------- */
export function StockHistoryPage() {
  const [rows, setRows] = useState([]), [err, setErr] = useState("");
  useEffect(() => { api.get("/stock/movements/").then((r) => setRows(list(r))).catch((e) => setErr(errText(e))); }, []);
  const K = { in: "Kirim", out: "Chiqim", adjust: "Tuzatish" };
  return <>
    <PageHead eyebrow="OMBOR / TARIX" title="Ombor harakatlari" desc="Kirim, chiqim va qoldiq tuzatishlari tarixi." />
    {err && <div className="alert">{err}</div>}
    <section className="panel data-panel"><Table cols={["Sana", "Mahsulot", "Turi", "Miqdor", "Kim", "Izoh"]} rows={rows.map((m) => <tr key={m.id}><td>{new Date(m.created_at).toLocaleString("uz-UZ")}</td><td>{m.part_name}</td><td>{K[m.kind]}</td><td>{m.quantity}</td><td>{m.created_by_name}</td><td>{m.note || "—"}</td></tr>)} /></section>
  </>;
}


/* ---------- Bildirishnomalar qo'ng'irog'i ---------- */
export function NotificationBell() {
  const [data, setData] = useState({ unread: 0, items: [] }), [open, setOpen] = useState(false);
  const go = useNavigate();
  const load = () => api.get("/notifications/").then((r) => setData(r.data)).catch(() => {});
  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t); }, []);
  const read = async (n) => { await api.post("/notifications/read/", n ? { id: n.id } : {}).catch(() => {}); load(); if (n?.order) { setOpen(false); go(`/orders/${n.order}`); } };
  return <div style={{ position: "relative" }}>
    <button className="icon-btn" title="Bildirishnomalar" onClick={() => setOpen((v) => !v)}><Bell size={18} />{data.unread > 0 && <i />}</button>
    {open && <div className="panel" style={{ position: "absolute", right: 0, top: 46, width: 320, maxHeight: 380, overflow: "auto", zIndex: 50 }}>
      <div className="panel-head"><div><h3>Bildirishnomalar ({data.unread})</h3></div>{data.unread > 0 && <button className="btn-secondary" onClick={() => read(null)}>Hammasini o'qildi</button>}</div>
      {data.items.length ? data.items.map((n) => <div key={n.id} onClick={() => read(n)} style={{ padding: "10px 18px", cursor: "pointer", borderTop: "1px solid rgba(128,128,128,.2)", fontWeight: n.is_read ? 400 : 700 }}>
        {n.message}<br /><small>{new Date(n.created_at).toLocaleString("uz-UZ")}</small></div>) : <div className="empty">Bildirishnoma yo'q.</div>}
    </div>}
  </div>;
}

/* ---------- Hisobotlar (har bir rol uchun, sana filtri bilan) ---------- */
export function ReportsView() {
  const { user } = useAuth();
  const role = user.role;
  const [d, setD] = useState(null), [err, setErr] = useState(""), [f, setF] = useState({ date_from: "", date_to: "" });
  useEffect(() => {
    const params = Object.fromEntries(Object.entries(f).filter(([, v]) => v));
    api.get("/reports/", { params }).then((r) => setD(r.data)).catch((e) => setErr(errText(e)));
  }, [f]);
  const title = { admin: "Moliyaviy hisobot", manager: "Moliyaviy hisobot", mechanic: "Mening ishlarim hisoboti", client: "Mening buyurtmalarim hisoboti" }[role];
  const cards = d ? [["Jami buyurtmalar", d.orders_count], ["Yakunlangan", d.completed_count], ["Faol", d.active_count], ["Bekor qilingan", d.cancelled_count], ["Sarflangan vaqt (daq.)", d.spent_minutes],
    ...(d.revenue !== undefined ? [[role === "client" ? "To'langan summa" : "Tushum", som(d.revenue)], ["Buyurtmalar summasi", som(d.orders_total)]] : []),
    ...(d.reviews_count !== undefined ? [["Fikrlar soni", d.reviews_count], ["O'rtacha baho", d.reviews_avg ?? "—"]] : [])] : [];
  return <>
    <PageHead eyebrow="TAHLIL / HISOBOTLAR" title={title} desc="Sana oralig'ini tanlab hisobotni filtrlang." />
    {err && <div className="alert">{err}</div>}
    <section className="panel edit-panel"><div className="manage-form">
      <Field label="Sanadan"><input type="date" value={f.date_from} onChange={(e) => setF({ ...f, date_from: e.target.value })} /></Field>
      <Field label="Sanagacha"><input type="date" value={f.date_to} onChange={(e) => setF({ ...f, date_to: e.target.value })} /></Field>
      <button className="btn-secondary" onClick={() => setF({ date_from: "", date_to: "" })}>Tozalash</button></div></section>
    <div className="stats-grid">{cards.map(([l, v]) => <div className="stat-card" key={l}><span className="stat-label">{l}</span><strong>{v ?? "—"}</strong></div>)}</div>
    {d?.monthly_revenue && <section className="panel data-panel"><div className="panel-head"><div><h3>Oylik {role === "client" ? "to'lovlar" : "tushum"}</h3></div></div>
      <Table cols={["Oy", "Summa"]} rows={d.monthly_revenue.map((x) => <tr key={x.month}><td>{x.month}</td><td>{som(x.amount)}</td></tr>)} empty="Bu davrda to'lovlar yo'q." /></section>}
    {d?.by_mechanic && <section className="panel data-panel"><div className="panel-head"><div><h3>Ustalar bo'yicha</h3></div></div>
      <Table cols={["Usta", "Buyurtmalar", "Yakunlangan", "Sarflangan vaqt (daq.)"]} rows={d.by_mechanic.map((m) => <tr key={m.name}><td>{m.name}</td><td>{m.orders}</td><td>{m.completed}</td><td>{m.minutes}</td></tr>)} /></section>}
  </>;
}


/* ---------- Buyurtmalar taxtasi (Kanban) ---------- */
export function BoardPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]), [err, setErr] = useState("");
  const load = () => api.get("/orders/").then((r) => setRows(list(r))).catch((e) => setErr(errText(e)));
  useEffect(() => { load(); }, []);
  const move = (id, status) => api.post(`/orders/${id}/set_status/`, { status }).then(load).catch((e) => setErr(errText(e)));
  const opts = (cur) => Object.entries(STATUS_META).filter(([k]) => user.role !== "mechanic" || !["new", "cancelled"].includes(k) || k === cur);
  return <>
    <PageHead eyebrow="BOSHQARUV / TAXTA" title="Buyurtmalar taxtasi" desc="Har bir buyurtma o'z statusi ustunida. Statusni kartadan o'zgartiring." />
    {err && <div className="alert">{err}</div>}
    <div className="board">{Object.entries(STATUS_META).map(([k, m]) => {
      const items = rows.filter((o) => o.status === k);
      return <div className="board-col" key={k}><h3><span className="dot" style={{ background: m.color }} />{m.label}<b>{items.length}</b></h3>
        {items.map((o) => <div className="board-card" key={o.id} style={{ "--c": m.color }}>
          <Link to={`/orders/${o.id}`}>AS-{String(o.id).padStart(4, "0")}</Link><span>{o.vehicle_label}</span>
          <small>{o.client_name || "—"} · {o.mechanic_name || "usta yo'q"}</small>
          {user.role !== "mechanic" && <b>{som(o.total_amount)}</b>}
          <select value={o.status} onChange={(e) => move(o.id, e.target.value)}>{opts(o.status).map(([sk, sm]) => <option key={sk} value={sk}>{sm.label}</option>)}</select>
        </div>)}
        {!items.length && <small style={{ color: "#667085", padding: 8 }}>Bo'sh</small>}
      </div>;
    })}</div>
  </>;
}
