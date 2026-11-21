import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="16.5T Furnace Pro", page_icon="⚡", layout="wide")
st.title("⚡ 16.5T Induction Furnace Accurate System")

# Condition Range for varied PF and Weightage
COND_RULES = {
    "Normal Running": {"pf": (0.942, 0.978), "wt": 1.00},
    "CCM Casting Hold": {"pf": (0.785, 0.842), "wt": 1.15},
    "Sintering (Lining)": {"pf": (0.810, 0.885), "wt": 1.25},
    "GLD / Tripping": {"pf": (0.860, 0.915), "wt": 1.18},
    "Crane / Scrap Delay": {"pf": (0.845, 0.895), "wt": 1.08},
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
                if d <= b: d += timedelta(days=1)
            return d
        except: pass
    return None

def gn(v):
    d = "".join(c for c in str(v) if c.isdigit() or c == ".")
    try: return float(d) if d else 0.0
    except: return 0.0

tab1, tab2 = st.tabs(["🔥 1. Heat-by-Heat Report", "📋 2. 15-Min Register"])

# ==========================================
# TAB 1: ACCURATE TONNAGE-BASED CALCULATOR
# ==========================================
with tab1:
    st.markdown("### 1️⃣ Meter Readings (Decimal Supported)")
    r1, r2, r3 = st.columns(3)
    with r1:
        skw = gn(st.text_input("Start kWh", "124560.50", key="sk1"))
        skv = gn(st.text_input("Start kVAh", "132510.00", key="sv1"))
    with r2:
        ekw = gn(st.text_input("End kWh", "128160.20", key="ek1"))
        ekv = gn(st.text_input("End kVAh", "136380.80", key="ev1"))
    with r3:
        MF = st.number_input("Meter Factor (MF)", value=8.0, step=0.1)

    t_kwh = round((ekw - skw) * MF)
    t_kvah = round((ekv - skv) * MF)
    o_pf = round(t_kwh / t_kvah, 3) if t_kvah > 0 else 0.0

    if t_kwh > 0:
        st.info(f"📊 **TOTAL UNITS:** kWh: `{t_kwh:,}` | kVAh: `{t_kvah:,}` | Avg PF: `{o_pf:.3f}`")
        nh = st.number_input("2️⃣ Total Heats?", 1, 20, 4)
        
        st.markdown("### 3️⃣ Heat-wise Conditions")
        hl = []
        base_t = datetime.strptime("08:00 AM", "%I:%M %p")
        for i in range(1, int(nh) + 1):
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns(4)
                on_t = c1.text_input(f"H#{i} ON Time", (base_t + timedelta(minutes=120*(i-1))).strftime("%I:%M %p"), key=f"on_{i}")
                tap_t = c2.text_input(f"H#{i} TAP Time", (base_t + timedelta(minutes=115*i)).strftime("%I:%M %p"), key=f"tp_{i}")
                
                don, dtp = pt(on_t), pt(tap_t, pt(on_t))
                dur_m = int((dtp - don).total_seconds() / 60) if don and dtp else 110
                dur_txt = f"{dur_m // 60}h {dur_m % 60}m"
                
                ton = c3.number_input(f"H#{i} Melt Ton", 1.0, 22.0, 16.0, 0.1, key=f"tn_{i}")
                cond = c4.selectbox(f"H#{i} Situation", list(COND_RULES.keys()), key=f"cd_{i}")
                
                hl.append({"no": i, "on": on_t, "tap": tap_t, "dur": dur_txt, "m": dur_m, "ton": ton, "cond": cond})

        if st.button("🔥 GENERATE ACCURATE REPORT", type="primary", use_container_width=True):
            # STEP 1: kWh Distribution using Tonnage Priority Logic
            # Score = (Tons * 0.8) + (Time_Adjustment * 0.2)
            steps_k = t_kwh // 8
            k_scores = []
            for h in hl:
                # Long duration without tons is penalized (holding power is low)
                time_weight = 1.0 + ((h["m"] - 110) / 600) if h["m"] > 110 else 1.0
                sc = (h["ton"] * COND_RULES[h["cond"]]["wt"] * time_weight * random.uniform(0.98, 1.02))
                k_scores.append(sc)
            
            kw_steps = [max(1, round((s / sum(k_scores)) * steps_k)) for s in k_scores]
            kw_steps[-1] += (steps_k - sum(kw_steps))
            
            # STEP 2: Varied kVAh based on Dynamic Random PF within situation range
            steps_v = t_kvah // 8
            v_scores = []
            for i, h in enumerate(hl):
                r_pf = random.uniform(*COND_RULES[h["cond"]]["pf"])
                v_scores.append(kw_steps[i] / r_pf)
            
            kv_steps = [max(1, round((v / sum(v_scores)) * steps_v)) for v in v_scores]
            kv_steps[-1] += (steps_v - sum(kv_steps))

            # Final Output
            rep_rows, copy_txt = [], ""
            for i, h in enumerate(hl):
                k_u = kw_steps[i] * 8
                v_u = max(k_u + 8, kv_steps[i] * 8)
                pf = round(k_u / v_u, 3)
                ut = round(k_u / h["ton"], 1)
                
                rep_rows.append({"Heat": f"#{h['no']}", "Tap": h['tap'], "Time": h['dur'], "Ton": h['ton'], "u/Ton": ut, "kWh": k_u, "kVAh": v_u, "PF": f"{pf:.3f}"})
                copy_txt += f"--- Heat #{h['no']} ---\nHeat ON Time     : {h['on']}\nHeat Taping Time : {h['tap']} ({h['dur']})\nKwh units        : {k_u}\nKvah units       : {v_u}\nPf.              : {pf:.3f}\n\n"
            
            st.success(f"✅ Report Ready (Overall PF: {o_pf:.3f})")
            st.dataframe(pd.DataFrame(rep_rows), use_container_width=True, hide_index=True)
            st.code(copy_txt.strip(), language=None)
    else: st.warning("Meter Reading Start/End sahi bharein!")

# ==========================================
# TAB 2: 15-MINUTE KVAH REGISTER
# ==========================================
with tab2:
    st.markdown("### 📋 15-Min Register")
    rc1, rc2 = st.columns(2)
    ts_r = rc1.text_input("Start Time", "8:00 AM", key="rt_s")
    rs_r = gn(rc1.text_input("Start KVAH Reading", "249751728", key="rr_s"))
    te_r = rc2.text_input("End Time", "10:30 AM", key="rt_e")
    re_r = gn(rc2.text_input("End KVAH Reading", "249775482", key="rr_e"))
    tp_r = st.text_input("Tapping Times", "8:25 AM, 9:45 AM")
    
    if st.button("🚀 Register Table Banayein", type="primary", use_container_width=True):
        ds, de = pt(ts_r), pt(te_r, pt(ts_r))
        if ds and de and re_r >= rs_r:
            diff_total = int(re_r - rs_r)
            sl, cur = [], ds
            while cur < de:
                nx = min(cur + timedelta(minutes=15), de)
                sl.append({"s": cur, "e": nx, "tap": False})
                cur = nx
            for x in tp_r.split(","):
                if dt := pt(x, ds):
                    for s in sl:
                        if s["s"] <= dt < s["e"]: s["tap"] = True
            
            wts = [(random.uniform(0.65, 0.85) if s["tap"] else random.uniform(0.90, 1.35)) * (((s["e"]-s["s"]).total_seconds()/60)/15) for s in sl]
            steps = [int(round((w/sum(wts))*diff_total)) for w in wts]
            steps[-1] += (diff_total - sum(steps))
            
            curr_read, rw = rs_r, [{"Time": ds.strftime('%I:%M %p'), "KVAH": f"{int(rs_r)}", "Unit": "-"}]
            for i, s in enumerate(sl):
                curr_read += steps[i]
                rw.append({"Time": s["e"].strftime('%I:%M %p'), "KVAH": f"{int(curr_read)}", "Unit": f"{steps[i]}"})
            st.dataframe(pd.DataFrame(rw), use_container_width=True, hide_index=True)
# DONE
