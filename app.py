import io, random
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import database as db

st.set_page_config(page_title="16T Furnace System", page_icon="⚡", layout="wide")
db.init_db()

MF = 8
CONDITIONS = {
    "Normal Running (Optimal Melting)": {"pf": 0.940, "weight": 1.00, "cat": "Normal"},
    "CCM Casting Running (Furnace Holding)": {"pf": 0.820, "weight": 1.15, "cat": "CCM Holding"},
    "EOT Crane Breakdown (Metal Hold / Delay)": {"pf": 0.800, "weight": 1.18, "cat": "EOT Crane Breakdown"},
    "Capacitor Bank Fault / Step Trip (Low PF)": {"pf": 0.780, "weight": 1.15, "cat": "Capacitor/Panel Fault"},
    "GLD Alarm / Lining Leakage": {"pf": 0.880, "weight": 1.20, "cat": "Capacitor/Panel Fault"},
    "Panel / SCR Tripping (Frequent ON-OFF)": {"pf": 0.840, "weight": 1.20, "cat": "Capacitor/Panel Fault"},
    "Scrap / Charging / Slag Delay": {"pf": 0.860, "weight": 1.08, "cat": "Scrap/Slag Delay"},
}

def parse_time(t_str, base_dt=None, strict_after=False):
    if not t_str: return None
    clean = str(t_str).strip().upper().replace(".", ":")
    for sfx in ("AM", "PM"):
        if clean.endswith(sfx) and ":" not in clean:
            num = clean[:-2].strip()
            if num.isdigit(): clean = f"{num}:00 {sfx}"
    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
        try:
            dt = datetime.strptime(clean, fmt)
            ref = base_dt or datetime.now()
            dt = dt.replace(year=ref.year, month=ref.month, day=ref.day)
            if base_dt and ((strict_after and dt <= base_dt) or (not strict_after and dt < base_dt)):
                dt += timedelta(days=1)
            return dt
        except ValueError: pass
    return None

def fmt_ampm(dt): return dt.strftime("%I:%M %p")
def detect_shift(dt): return "Day (08:00 AM - 08:00 PM)" if 8 <= dt.hour < 20 else "Night (08:00 PM - 08:00 AM)"
def meter_card(t_str, kwh, kvah, pf): return f"Time : {t_str}\nkWh  : {int(kwh):09d}\nkVAh : {int(kvah):09d}\nPF   : {pf:.3f}"

with st.sidebar:
    st.header("⚙️ Furnace Control")
    curr_bench = float(db.get_state("benchmark_sec", "580.0"))
    new_bench = st.number_input("Benchmark SEC (kWh/T)", 450.0, 800.0, curr_bench, 5.0)
    if new_bench != curr_bench:
        db.set_state("benchmark_sec", str(new_bench)); curr_bench = new_bench
    st.divider()
    camp_no = int(db.get_state("lining_campaign", "1"))
    lining_cnt = int(db.get_state("lining_heat_count", "0"))
    st.metric("Campaign #", f"Campaign {camp_no}")
    st.metric("Lining Heat Count", f"{lining_cnt} Heats")
    if lining_cnt > 22: st.error(f"🚨 RELINING ALERT: {lining_cnt} Heats (>22)!")
    if st.button("🔄 Relining Reset", use_container_width=True):
        db.reset_lining_campaign(); st.rerun()

st.title("⚡ 16T Induction Furnace Energy & 15-Min Register")
tab1, tab2, tab3, tab4 = st.tabs(["📟 1. Heat Entry", "🛠️ 2. Missed Split", "📊 3. Analytics", "📋 4. 15-Min Register"])

with tab1:
    lh = db.get_last_heat()
    ds_t = lh["end_time"] if lh else "08:00 AM"
    ds_kw = int(lh["end_kwh"]) if lh else 160132520
    ds_kv = int(lh["end_kvah"]) if lh else 168914040
    dh_no = int(lh["heat_no"]) + 1 if lh else 1
    dl_no = int(db.get_state("lining_heat_count", "0")) + 1
    ac_cmp = int(db.get_state("lining_campaign", "1"))

    c1, c2, c3, c4 = st.columns(4)
    log_dt = c1.date_input("Log Date", value=date.today())
    heat_no = c2.number_input("Heat No.", 1, 99999, dh_no, 1)
    lining_h_no = c3.number_input("Lining Heat #", 1, 500, dl_no, 1)
    tapped_tons = c4.number_input("Tapped Tons", 1.0, 22.0, 16.0, 0.1)

    m1, m2 = st.columns(2)
    s_t_in = m1.text_input("Start Time (AM/PM)", ds_t)
    s_kw_in = m1.number_input("Start kWh", 0, 999999999, ds_kw, 1, "%d")
    s_kv_in = m1.number_input("Start kVAh", 0, 999999999, ds_kv, 1, "%d")
    s_pf_in = m1.number_input("Start PF (0.xxx)", 0.600, 0.980, 0.940, 0.001, "%.3f")

    dts0 = parse_time(s_t_in)
    e_t_in = m2.text_input("End Time (AM/PM)", fmt_ampm(dts0 + timedelta(hours=2)) if dts0 else "10:00 AM")
    e_kw_in = m2.number_input("End kWh", 0, 999999999, ds_kw + 1160, 1, "%d")
    e_kv_in = m2.number_input("End kVAh", 0, 999999999, ds_kv + 1234, 1, "%d")
    cond_sel = m2.selectbox("Heat Run Condition", list(CONDITIONS.keys()))

    d1, d2, d3 = st.columns(3)
    use_cpf = d1.checkbox("Auto-use Calculated PF", value=True)
    hold_m = d2.number_input("Holding / BD Mins", 0, 360, 0, 5)

    r_kw_d, r_kv_d = int(e_kw_in - s_kw_in), int(e_kv_in - s_kv_in)
    act_kw, act_kv = r_kw_d * MF, r_kv_d * MF
    raw_pf = round(act_kw / act_kv, 3) if act_kv > 0 else 0.0
    cap_pf = min(0.980, max(0.600, raw_pf)) if act_kv > 0 else CONDITIONS[cond_sel]["pf"]
    inst_pf = d3.number_input("End Meter PF", 0.600, 0.980, cap_pf if use_cpf else CONDITIONS[cond_sel]["pf"], 0.001, "%.3f")

    sec_v, kvt_v = round(act_kw / tapped_tons, 1), round(act_kv / tapped_tons, 1)
    eh_kw = round(hold_m * 25.0, 1)
    ex_kw = round(max(0.0, act_kw - (tapped_tons * curr_bench)), 1)
    lp_kv = round(max(0.0, act_kv - (act_kw / 0.950)), 1)

    dt_s = parse_time(s_t_in)
    dt_e = parse_time(e_t_in, dt_s, True) if dt_s else None
    shf_auto = detect_shift(dt_e) if dt_e else "Day (08:00 AM - 08:00 PM)"

    p1, p2, p3 = st.columns(3)
    p1.code(meter_card(fmt_ampm(dt_s) if dt_s else s_t_in, s_kw_in, s_kv_in, s_pf_in), language=None)
    p2.code(meter_card(fmt_ampm(dt_e) if dt_e else e_t_in, e_kw_in, e_kv_in, inst_pf), language=None)
    p3.code(f"Heat #{heat_no} | {act_kw:,} kWh ({sec_v} u/T)\nkVAh: {act_kv:,} | Calc PF: {raw_pf:.3f}\nHold: {eh_kw} kWh | Loss: {ex_kw} kWh", language=None)

    errs = list()
    if not dt_s or not dt_e: errs.append("Valid AM/PM Time daalein.")
    if r_kw_d <= 0 or r_kv_d <= 0: errs.append("End Reading Start se badi honi chahiye.")
    if not (0.600 <= raw_pf <= 0.980): errs.append(f"PF ({raw_pf:.3f}) 0.600–0.980 ke beech hona chahiye!")
    for er in errs: st.error(er)

    if st.button("💾 Save Heat Entry", type="primary", use_container_width=True, disabled=bool(errs)):
        db.insert_heat({
            "log_date": log_dt.strftime("%Y-%m-%d"), "shift": shf_auto, "lining_campaign": ac_cmp,
            "lining_heat_no": int(lining_h_no), "heat_no": int(heat_no), "start_time": fmt_ampm(dt_s),
            "end_time": fmt_ampm(dt_e), "start_kwh": int(s_kw_in), "end_kwh": int(e_kw_in),
            "start_kvah": int(s_kv_in), "end_kvah": int(e_kv_in), "actual_kwh": act_kw,
            "actual_kvah": act_kv, "calc_pf": float(cap_pf), "inst_pf": float(inst_pf),
            "tapped_tons": float(tapped_tons), "sec_kwh_ton": sec_v, "kvah_per_ton": kvt_v,
            "run_condition": cond_sel, "holding_mins": int(hold_m), "est_holding_kwh": eh_kw,
            "extra_loss_kwh": ex_kw, "low_pf_extra_kvah": lp_kv, "benchmark_sec": curr_bench, "entry_mode": "SINGLE"
        })
        st.rerun()
# --- END PART 1 ---
       with tab2:
    st.subheader("🔥 Multi-Heat (e.g. 10 Heats) Situation-Wise Units & PF Report")
    lh2 = db.get_last_heat()
    bst_d = lh2["end_time"] if lh2 else "08:00 AM"
    bskw_d = int(lh2["end_kwh"]) if lh2 else 160132520
    bskv_d = int(lh2["end_kvah"]) if lh2 else 168914040
    nh_no = int(lh2["heat_no"]) + 1 if lh2 else 1
    nl_no = int(db.get_state("lining_heat_count", "0")) + 1

    st1, st2, st3 = st.columns(3)
    sp_dt = st1.date_input("Report Date", value=date.today(), key="sp_d")
    n_miss = st2.number_input("Kitni Heats ki Report nikalni hai? (e.g. 10)", 1, 25, 10, 1)
    rm_mode = st3.selectbox("Meter Mode", ["Direct ((End-Start) × 8)", "Decimal (((End-Start)÷10) × 8)"])

    bc1, bc2 = st.columns(2)
    bst = bc1.text_input("Shift / Block Start Time", bst_d, key="bst")
    bskw = bc1.number_input("Start kWh Reading", 0, 999999999, bskw_d, 1, "%d", key="bsk")
    bskv = bc1.number_input("Start kVAh Reading", 0, 999999999, bskv_d, 1, "%d", key="bsv")

    div_m = 10 if "Decimal" in rm_mode else 1
    bet = bc2.text_input("Last Heat Tapping / End Time", "08:00 PM", key="bet")
    bekw = bc2.number_input("End kWh Reading", 0, 999999999, bskw_d + (1180 * int(n_miss) * div_m), 1, "%d", key="bek")
    bekv = bc2.number_input("End kVAh Reading", 0, 999999999, bskv_d + (1295 * int(n_miss) * div_m), 1, "%d", key="bev")

    ALL_SITUATIONS = dict(CONDITIONS)
    ALL_SITUATIONS["Sintering / Lining Heat (Low Power)"] = {"pf": 0.840, "weight": 1.25, "cat": "Sintering"}

    st.markdown(f"#### 📋 Sabhi {int(n_miss)} Heats ki Situation & Tapping Details Bharein")
    m_rows = list()
    bds_base = parse_time(bst) or datetime.strptime("08:00 AM", "%I:%M %p")

    for i in range(int(n_miss)):
        sug_tap = fmt_ampm(bds_base + timedelta(minutes=72 * (i + 1)))
        x1, x2, x3, x4, x5, x6 = st.columns([0.8, 1.2, 1.0, 2.3, 0.9, 1.0])
        mh = x1.number_input("Heat#", 1, 99999, nh_no + i, 1, key=f"mh_{i}")
        mtap = x2.text_input("Tap Time", sug_tap, key=f"mtp_{i}")
        mt = x3.number_input("Tons", 1.0, 22.0, 16.0, 0.1, key=f"mt_{i}")
        mc = x4.selectbox("Situation / Condition", list(ALL_SITUATIONS.keys()), key=f"mc_{i}")
        md = x5.number_input("Hold(m)", 0, 300, 0, 5, key=f"md_{i}")
        mp = x6.number_input("Base PF", 0.600, 0.980, ALL_SITUATIONS[mc]["pf"], 0.001, "%.3f", key=f"mp_{i}")
        m_rows.append({
            "hno": int(mh), "lno": nl_no + i, "tap_in": mtap, "tons": float(mt),
            "cond": mc, "hm": int(md), "tpf": float(mp), "wt": ALL_SITUATIONS[mc]["weight"]
        })

    st.button("🔥 GENERATE COMPLETE MULTI-HEAT REPORT", type="primary", use_container_width=True)

    tkw_r = round((bekw - bskw) / div_m)
    tkv_r = round((bekv - bskv) / div_m)
    bpf = round(tkw_r / tkv_r, 3) if tkv_r > 0 else 0.0

    if tkw_r <= int(n_miss) * 5 or not (0.600 <= bpf <= 0.980):
        st.error(f"⚠️ Meter Reading check karein! Overall PF ({bpf:.3f}) 0.600 se 0.980 ke beech hona chahiye.")
    else:
        # 1. Situation + Tonnage + Holding + Natural Jitter se kWh steps (x8) nikalna
        k_sc = list()
        for r in m_rows:
            jitter = random.uniform(0.975, 1.025)
            hold_steps = (r["hm"] * 25.0) / MF
            sc = ((r["tons"] * r["wt"]) * jitter) + (hold_steps * 0.03)
            k_sc.append(sc)
        t_sc = sum(k_sc)
        kw_al = [max(5, round((s / t_sc) * tkw_r)) for s in k_sc]
        kw_al[-1] += (tkw_r - sum(kw_al))

        # 2. Har heat ki situation PF + slight variation se kVAh steps (x8) nikalna
        v_sc = [kw_al[i] / min(0.978, max(0.605, m_rows[i]["tpf"] + random.uniform(-0.012, 0.012))) for i in range(len(m_rows))]
        tv_sc = sum(v_sc)
        kv_al = [max(6, round((s / tv_sc) * tkv_r)) for s in v_sc]
        kv_al[-1] += (tkv_r - sum(kv_al))

        # 3. Strict 0.600 <= PF <= 0.980 lock on all 10+ heats
        for _ in range(20000):
            bad = False
            for i in range(len(m_rows)):
                mn_v, mx_v = int((kw_al[i] / 0.980) + 0.9999), int(kw_al[i] / 0.600)
                if kv_al[i] < mn_v:
                    for j in range(len(m_rows)):
                        if i != j and kv_al[j] - 1 >= int((kw_al[j] / 0.980) + 0.9999):
                            kv_al[i] += 1; kv_al[j] -= 1; bad = True; break
                elif kv_al[i] > mx_v:
                    for j in range(len(m_rows)):
                        if i != j and kv_al[j] + 1 <= int(kw_al[j] / 0.600):
                            kv_al[i] -= 1; kv_al[j] += 1; bad = True; break
            if not bad: break

        recs = list()
        c_dt = bds_base
        c_kw, c_kv = int(bskw), int(bskv)
        ac_c2 = int(db.get_state("lining_campaign", "1"))

        for i, r in enumerate(m_rows):
            ndt = parse_time(r["tap_in"], c_dt, True) or (c_dt + timedelta(minutes=70))
            if i == len(m_rows) - 1:
                nkw, nkv = int(bekw), int(bekv)
            else:
                nkw = c_kw + (kw_al[i] * div_m)
                nkv = c_kv + (kv_al[i] * div_m)

            akw, akv = kw_al[i] * MF, kv_al[i] * MF
            cpf = min(0.980, max(0.600, round(akw / akv, 3)))
            recs.append({
                "log_date": sp_dt.strftime("%Y-%m-%d"), "shift": detect_shift(ndt),
                "lining_campaign": ac_c2, "lining_heat_no": r["lno"], "heat_no": r["hno"],
                "start_time": fmt_ampm(c_dt), "end_time": fmt_ampm(ndt),
                "start_kwh": c_kw, "end_kwh": nkw, "start_kvah": c_kv, "end_kvah": nkv,
                "actual_kwh": akw, "actual_kvah": akv, "calc_pf": cpf, "inst_pf": cpf,
                "tapped_tons": r["tons"], "sec_kwh_ton": round(akw / r["tons"], 1),
                "kvah_per_ton": round(akv / r["tons"], 1), "run_condition": r["cond"],
                "holding_mins": r["hm"], "est_holding_kwh": round(r["hm"] * 25.0, 1),
                "extra_loss_kwh": round(max(0.0, akw - r["tons"] * curr_bench), 1),
                "low_pf_extra_kvah": round(max(0.0, akv - akw / 0.950), 1),
                "benchmark_sec": curr_bench, "entry_mode": "MULTI_HEAT"
            })
            c_dt, c_kw, c_kv = ndt, nkw, nkv

        tot_t = sum(x["tapped_tons"] for x in recs)
        st.success(f"✅ {len(recs)} Heats Report Ready | Total Tons: {tot_t:.1f} T | Total Kwh: {tkw_r*MF:,} | Total Kvah: {tkv_r*MF:,} | Overall Pf: {bpf:.3f}")

        tbl_r, rep_txt = list(), ""
        for rc in recs:
            tbl_r.append({
                "Heat #": rc["heat_no"], "Tap Time": rc["end_time"], "Situation": rc["run_condition"].split("(")[0].strip(),
                "Tons": rc["tapped_tons"], "u/Ton": rc["sec_kwh_ton"], "Kwh Units": rc["actual_kwh"],
                "Kvah Units": rc["actual_kvah"], "PF": f"{rc['calc_pf']:.3f}", "End kWh": rc["end_kwh"], "End kVAh": rc["end_kvah"]
            })
            rep_txt += (
                f"--- Heat #{rc['heat_no']} ---\n"
                f"Heat Taping Time : {rc['end_time']}\n"
                f"Kwh units        : {rc['actual_kwh']}\n"
                f"Kvah units       : {rc['actual_kvah']}\n"
                f"Pf.              : {rc['calc_pf']:.3f}\n\n"
            )
        st.dataframe(pd.DataFrame(tbl_r), use_container_width=True, hide_index=True)
        st.markdown("#### 📲 Copy Full Report (All Heats):")
        st.code(rep_txt.strip(), language=None)

        if st.button("💾 Save All Heats to Database", type="primary", use_container_width=True):
            db.insert_bulk_heats(recs); st.rerun()

with tab3:
    dfa = db.fetch_heats_df()
    if dfa.empty: st.info("Abhi koi heat save nahi hui hai.")
    else:
        tkw_s, tkv_s, ttn_s = int(dfa["actual_kwh"].sum()), int(dfa["actual_kvah"].sum()), dfa["tapped_tons"].sum()
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Heats / Tons", f"{len(dfa)} / {ttn_s:,.1f} T")
        k2.metric("Total Kwh / Kvah", f"{tkw_s:,} / {tkv_s:,}")
        k3.metric("Avg SEC / PF", f"{(tkw_s/ttn_s):,.1f} u/T | {min(0.98, tkw_s/tkv_s):.3f}")
        k4.metric("Hold Loss / Low-PF", f"{dfa['est_holding_kwh'].sum():,.0f} kWh | {dfa['low_pf_extra_kvah'].sum():,.0f}")
        st.dataframe(dfa, use_container_width=True, hide_index=True)
        dc1, dc2 = st.columns(2)
        dc1.download_button("⬇️ CSV", dfa.to_csv(index=False).encode("utf-8"), "Heats.csv", "text/csv", use_container_width=True)
        ebuf = io.BytesIO()
        with pd.ExcelWriter(ebuf, engine="openpyxl") as wr: dfa.to_excel(wr, index=False)
        dc2.download_button("📗 Excel (.xlsx)", ebuf.getvalue(), "Heats.xlsx", use_container_width=True)

with tab4:
    rc1, rc2 = st.columns(2)
    ts4, rs4, fa4 = rc1.text_input("Start Time", "8:00am"), rc1.number_input("Start KVAH", 0, 999999999, 249751728, 1, "%d"), rc1.selectbox("A-Line", ["A1", "A2"])
    te4, re4, fb4 = rc2.text_input("End Time", "10:30am"), rc2.number_input("End KVAH", 0, 999999999, 249775482, 1, "%d"), rc2.selectbox("B-Line", ["B1", "B2"], index=1)
    uc4 = st.number_input("Cross-Verify Total (Optional)", 0, 99999999, 0, 1, "%d")
    tp4 = st.text_input("Tapping Times", placeholder="8:25am, 9:45am")
    if st.button("🚀 Register Table Banayein", type="primary", use_container_width=True):
        ds4 = parse_time(ts4)
        de4 = parse_time(te4, ds4, True) if ds4 else None
        if ds4 and de4 and re4 >= rs4:
            tu4, sl4, cur4 = int(re4 - rs4), list(), ds4
            while cur4 < de4:
                nx4 = min(cur4 + timedelta(minutes=15), de4)
                sl4.append({"s": cur4, "e": nx4, "t": 0}); cur4 = nx4
            for x in tp4.split(","):
                dt = parse_time(x, ds4)
                if dt:
                    for s in sl4:
                        if s["s"] <= dt < s["e"]: s["t"] = 1
            wt4 = [(random.uniform(0.62, 0.78) if s["t"] else random.uniform(*[(0.82, 0.96), (1.04, 1.22), (1.28, 1.48)][i % 3])) * (((s["e"] - s["s"]).total_seconds() / 60.0) / 15.0) for i, s in enumerate(sl4)]
            tw4, rd4, cr4 = sum(wt4), [int(rs4)], int(rs4)
            for i in range(len(sl4)):
                cr4 = int(re4) if i == len(sl4) - 1 else cr4 + round((wt4[i] / tw4) * tu4)
                rd4.append(cr4)
            rw4 = [{"Time": ds4.strftime('%I:%M %p').lstrip('0'), "KVAH": str(int(rs4)), "Unit": "-", "Status": f"{fa4}+{fb4}"}]
            for i, s in enumerate(sl4):
                rw4.append({"Time": s["e"].strftime('%I:%M %p').lstrip('0'), "KVAH": str(rd4[i+1]), "Unit": str(rd4[i+1]-rd4[i]), "Status": f"{fa4}+{fb4}" + (" (Tap)" if s["t"] else "")})
            st.dataframe(pd.DataFrame(rw4), use_container_width=True, hide_index=True)
            st.success(f"Total Units: {tu4}")
            if uc4 > 0: st.info("✅ MATCH!" if tu4 == int(uc4) else f"⚠️ Farq: {tu4 - int(uc4):+d}")
# --- END PART 2 ---
