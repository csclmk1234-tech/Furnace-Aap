import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="16.5T Furnace App", page_icon="⚡", layout="wide")
st.title("⚡ 16.5T Induction Furnace Energy System")

# Configuration & Constants
CONDITIONS = {
    "Normal Running": {"pf": 0.962, "wt": 1.00},
    "Sintering (Lining Heat)": {"pf": 0.840, "wt": 1.25},
    "GLD / Tripping Problem": {"pf": 0.880, "wt": 1.15},
    "CCM Holding / Casting": {"pf": 0.820, "wt": 1.10},
    "Scrap / Slag Delay": {"pf": 0.860, "wt": 1.05},
}

def pt(s, b=None):
    if not s: return None
    s = str(s).strip().upper().replace(".", ":")
    for x in ("AM", "PM"):
        if s.endswith(x) and ":" not in s and s[:-2].strip().isdigit():
            s = f"{s[:-2].strip()}:00 {x}"
    for f in ("%I:%M %p", "%I:%M%p", "%H:%M"):
        try:
            d = datetime.strptime(s, f)
            if b:
                d = d.replace(year=b.year, month=b.month, day=b.day)
                if d < b: d += timedelta(days=1)
            return d
        except: pass
    return None

def gn(v):
    d = "".join(c for c in str(v) if c.isdigit())
    return int(d) if d else 0

tab1, tab2 = st.tabs(["🔥 1. Heat-by-Heat Report", "📋 2. 15-Min Register"])

# ==========================================
# TAB 1: UNIFIED HEAT-BY-HEAT CALCULATOR
# ==========================================
with tab1:
    st.markdown("### 1️⃣ Readings Se Total Units Nikalein")
    r1, r2, r3 = st.columns(3)
    with r1:
        skw = gn(st.text_input("Start kWh Reading", "160944480", key="skw1"))
        skv = gn(st.text_input("Start kVAh Reading", "169767296", key="skv1"))
    with r2:
        ekw = gn(st.text_input("End kWh Reading", "160983200", key="ekw1"))
        ekv = gn(st.text_input("End kVAh Reading", "169807360", key="ekv1"))
    with r3:
        MF = st.number_input("Meter Factor (MF)", value=1.0, step=0.1, key="mf1")

    t_kwh = int((ekw - skw) * MF)
    t_kvah = int((ekv - skv) * MF)
    o_pf = round(t_kwh / t_kvah, 3) if t_kvah > 0 else 0.0

    if t_kwh > 0:
        st.info(f"📊 **TOTAL TO DIVIDE:** kWh = `{t_kwh:,}` | kVAh = `{t_kvah:,}` | PF = `{o_pf:.3f}`")
        nh = st.number_input("2️⃣ Yeh units kitni heats mein divide karni hain?", 1, 20, 4)
        
        st.markdown("### 3️⃣ Har Heat ki Situation Daalein")
        hl = []
        base_t = datetime.strptime("08:00 AM", "%I:%M %p")
        for i in range(1, int(nh) + 1):
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([1, 1, 1.5, 1])
                ton = c1.number_input(f"Ton", 1.0, 22.0, 16.5, 0.1, key=f"tn_{i}")
                tp_t = c2.text_input(f"Tap Time", (base_t + timedelta(minutes=110*i)).strftime("%I:%M %p"), key=f"tt_{i}")
                cond = c3.selectbox("Situation", list(CONDITIONS.keys()), key=f"cd_{i}")
                bd = c4.number_input("BD(m)", 0, 300, 0, 5, key=f"bm_{i}")
                hl.append({"no": i, "ton": ton, "tap": tp_t, "cond": cond, "bd": bd, "tpf": CONDITIONS[cond]["pf"], "wt": CONDITIONS[cond]["wt"]})

        if st.button("🔥 GENERATE HEAT REPORT", type="primary", use_container_width=True):
            wts = [(h["ton"] * h["wt"] * random.uniform(0.98, 1.02)) + (h["bd"] * 0.4) for h in hl]
            tw = sum(wts)
            ku = [int(round((w / tw) * t_kwh)) for w in wts]
            ku[-1] += (t_kwh - sum(ku))
            
            kv_r = [ku[i] / hl[i]["tpf"] for i in range(len(hl))]
            vu = [int(round((v / sum(kv_r)) * t_kvah)) for v in kv_r]
            vu[-1] += (t_kvah - sum(vu))

            rep_rows, copy_txt = [], ""
            for i, h in enumerate(hl):
                k, v = ku[i], max(ku[i]+1, vu[i])
                pf, ut = round(k/v, 3), round(k/h["ton"], 1)
                rep_rows.append({"Heat": f"#{h['no']}", "Tap": h['tap'], "Ton": h['ton'], "u/Ton": ut, "kWh": k, "kVAh": v, "PF": f"{pf:.3f}"})
                copy_txt += f"--- Heat #{h['no']} ---\nHeat Taping Time : {h['tap']}\nKwh units        : {k}\nKvah units       : {v}\nPf.              : {pf:.3f}\n\n"
            st.dataframe(pd.DataFrame(rep_rows), use_container_width=True, hide_index=True)
            st.code(copy_txt.strip(), language=None)
    else: st.warning("End Reading Start se badi honi chahiye!")

# ==========================================
# TAB 2: 15-MINUTE KVAH REGISTER
# ==========================================
with tab2:
    st.markdown("### 📋 15-Min KVAH Register Generator")
    c1, c2 = st.columns(2)
    with c1:
        ts4 = c1.text_input("Start Time", "8:00 AM", key="rts")
        rs4 = gn(c1.text_input("Start KVAH Reading", "249751728", key="rrs"))
        fa4 = c1.selectbox("A-Line Furnace", ["A1", "A2"], key="rfa")
    with c2:
        te4 = c2.text_input("End Time", "10:30 AM", key="rte")
        re4 = gn(c2.text_input("End KVAH Reading", "249775482", key="rre"))
        fb4 = c2.selectbox("B-Line Furnace", ["B1", "B2"], index=1, key="rfb")
    
    uc4 = st.number_input("Cross-Verify Total (Optional)", 0, 999999, 0, 1, key="ruc")
    tp4 = st.text_input("Tapping Times (comma lagayein)", "8:25 AM, 9:45 AM", key="rtp")

    with st.expander("➕ BD / GLD / Changeover (15-Min)"):
        x1, x2, x3 = st.columns(3)
        bf4 = x1.selectbox("OFF Fur", ["None", "A", "B", "BOTH"], key="rbf")
        bs4, be4 = x2.text_input("OFF Time", key="rbs"), x3.text_input("ON Time", key="rbe")
        g1, g2 = st.columns(2)
        gs4, ge4 = g1.text_input("GLD Start", key="rgs"), g2.text_input("GLD End", key="rge")

    if st.button("🚀 Register Table Banayein", type="primary", use_container_width=True):
        ds, de = pt(ts4), pt(te4, pt(ts4))
        if ds and de and re4 >= rs4:
            tu, sl, cur = int(re4 - rs4), [], ds
            while cur < de:
                nx = min(cur + timedelta(minutes=15), de)
                sl.append({"s": cur, "e": nx, "a": fa4, "b": fb4, "t": 0, "g": 0})
                cur = nx
            for x in tp4.split(","):
                if dt := pt(x, ds):
                    for s in sl:
                        if s["s"] <= dt < s["e"]: s["t"] = 1
            if bf4 != "None" and bs4:
                do, dn = pt(bs4, ds), (de if be4.upper() == "END" or not be4 else pt(be4, ds))
                for s in sl:
                    if s["s"] < dn and s["e"] > do:
                        if bf4 in ("A", "BOTH"): s["a"] = "OFF"
                        if bf4 in ("B", "BOTH"): s["b"] = "OFF"
            if gs4 and ge4:
                g1, g2 = pt(gs4, ds), pt(ge4, ds)
                for s in sl:
                    if s["s"] < g2 and s["e"] > g1: s["g"] = 1
            
            wts, pw = [], 0.0
            for i, s in enumerate(sl):
                ao, bo = s["a"] == "OFF", s["b"] == "OFF"
                if ao and bo: w = random.uniform(0.05, 0.12)
                elif ao or bo: w = random.uniform(0.32, 0.44) if s["t"] else random.uniform(0.48, 0.72)
                elif s["g"]: w = random.uniform(0.50, 0.85)
                elif s["t"]: w = random.uniform(0.62, 0.78)
                else:
                    w = random.uniform(*[(0.82, 0.96), (1.04, 1.22), (1.28, 1.48)][i % 3])
                    if abs(w - pw) < 0.1: w += 0.14 if w < 1.25 else -0.15
                pw = w; wts.append(w * (((s["e"] - s["s"]).total_seconds() / 60.0) / 15.0))
            
            tw, rd, cr = sum(wts), [int(rs4)], int(rs4)
            for i in range(len(sl)):
                cr = int(re4) if i == len(sl)-1 else cr + round((wts[i]/tw)*tu)
                rd.append(cr)
            
            rw = [{"Time": ds.strftime('%I:%M %p'), "KVAH": str(int(rs4)), "Unit": "-", "Status": "Start"}]
            for i, s in enumerate(sl):
                lb = f"{s['a']}+{s['b']}" + (" (GLD)" if s["g"] else (" (Tap)" if s["t"] else ""))
                rw.append({"Time": s["e"].strftime('%I:%M %p'), "KVAH": str(rd[i+1]), "Unit": str(rd[i+1]-rd[i]), "Status": lb})
            st.dataframe(pd.DataFrame(rw), use_container_width=True, hide_index=True)
            st.success(f"Total Shift Units: {tu}")
            if uc4 > 0: st.info("✅ MATCH!" if tu == int(uc4) else f"⚠️ Difference: {tu-int(uc4):+d}")
        else: st.error("Check Readings/Time!")

# DONE
