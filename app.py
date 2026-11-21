import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Furnace Master Pro", page_icon="⚡", layout="wide")
st.title("⚡ 16.5T Furnace Unified System")

# Configuration for Situation Weights & PF
COND_RULES = {
    "Normal Running": {"pf": (0.945, 0.982), "wt": 1.00},
    "Sintering (Lining Heat)": {"pf": (0.800, 0.880), "wt": 1.30}, 
    "GLD / Tripping Problem": {"pf": (0.850, 0.900), "wt": 1.18}, 
    "Capacitor Bank Fault": {"pf": (0.750, 0.820), "wt": 1.10},
    "Furnace Breakdown / Hold": {"pf": (0.700, 0.800), "wt": 0.45},
    "CCM Holding / Casting": {"pf": (0.800, 0.850), "wt": 1.10},  
    "Scrap / Slag Delay": {"pf": (0.820, 0.890), "wt": 1.05},     
}

def pt(s, b=None, next_day_check=False):
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
                if next_day_check and d <= b: d += timedelta(days=1)
            return d
        except: pass
    return None

def gn(v):
    d = "".join(c for c in str(v) if c.isdigit())
    return int(d) if d else 0

tab1, tab2 = st.tabs(["🔥 1. Heat-by-Heat Report", "📋 2. 15-Min Register"])

# ==========================================
# TAB 1: HEAT-BY-HEAT (PREVIOUS PERFECT LOGIC)
# ==========================================
with tab1:
    st.markdown("### 1️⃣ Reading Se Total Nikalein")
    r1, r2 = st.columns(2)
    skw = gn(r1.text_input("Start kWh Reading", "160944480", key="h_skw"))
    skv = gn(r1.text_input("Start kVAh Reading", "169767296", key="h_skv"))
    ekw = gn(r2.text_input("End kWh Reading", "160983200", key="h_ekw"))
    ekv = gn(r2.text_input("End kVAh Reading", "169807360", key="h_ekv"))
    t_kwh, t_kvah = ekw - skw, ekv - skv
    o_pf = round(t_kwh / t_kvah, 3) if t_kvah > 0 else 0.0
    if t_kwh > 0:
        st.info(f"📊 **METER TOTAL:** kWh = `{t_kwh:,}` | kVAh = `{t_kvah:,}` | PF = `{o_pf:.3f}`")
        nh = st.number_input("2️⃣ Total Heats?", 1, 20, 4)
        hl = []
        base_t = datetime.strptime("08:00 AM", "%I:%M %p")
        for i in range(1, int(nh) + 1):
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns(4)
                on_t = c1.text_input(f"ON Time #{i}", (base_t + timedelta(minutes=120*(i-1))).strftime("%I:%M %p"), key=f"on_{i}")
                tp_t = c2.text_input(f"TAP Time #{i}", (base_t + timedelta(minutes=115*i)).strftime("%I:%M %p"), key=f"tp_{i}")
                don, dtp = pt(on_t), pt(tp_t, pt(on_t), True)
                dur_m = int((dtp - don).total_seconds() / 60) if don and dtp else 115
                c3.markdown(f"**⏱️ Time:** {dur_m//60}h {dur_m%60}m"); ton = c4.number_input(f"Ton #{i}", 1.0, 22.0, 16.5, 0.1, key=f"tn_{i}")
                cond = st.selectbox(f"Situation #{i}", list(COND_RULES.keys()), key=f"cd_{i}")
                bd = st.number_input(f"BD Min #{i}", 0, 300, 0, 5, key=f"bm_{i}")
                hl.append({"no": i, "on": on_t, "tap": tp_t, "dur": f"{dur_m//60}h {dur_m%60}m", "m": dur_m, "ton": ton, "cond": cond, "bd": bd, "pfr": COND_RULES[cond]["pf"]})
        if st.button("🔥 GENERATE 8-FACTOR REPORT", type="primary", use_container_width=True):
            sk = t_kwh // 8
            k_sc = [(h["ton"] * COND_RULES[h["cond"]]["wt"] * random.uniform(0.98, 1.02)) + (h["bd"] * 0.45) for h in hl]
            kw_s = [int(round((s / sum(k_sc)) * sk)) for s in k_sc]; kw_s[-1] += (sk - sum(kw_s))
            v_sc = [kw_s[i] / random.uniform(*hl[i]["pfr"]) for i in range(len(hl))]
            kv_s = [int(round((v / sum(v_sc)) * (t_kvah//8))) for v in v_sc]; kv_s[-1] += ((t_kvah//8) - sum(kv_s))
            rep_r = []; copy_t = ""
            for i, h in enumerate(hl):
                k, v = kw_s[i]*8, max(kw_s[i]*8+8, kv_s[i]*8); pf, ut = round(k/v, 3), round(k/h["ton"], 1)
                rep_r.append({"Heat": f"#{h['no']}", "ON": h['on'], "TAP": h['tap'], "Time": h['dur'], "Ton": h['ton'], "kWh": k, "kVAh": v, "PF": f"{pf:.3f}"})
                copy_t += f"--- Heat #{h['no']} ---\nHeat ON Time     : {h['on']}\nHeat Taping Time : {h['tap']} ({h['dur']})\nKwh units        : {k}\nKvah units       : {v}\nPf.              : {pf:.3f}\n\n"
            st.dataframe(pd.DataFrame(rep_r), use_container_width=True, hide_index=True); st.code(copy_t.strip(), language=None)

# ==========================================
# TAB 2: 15-MIN REGISTER (WITH CROSS-MATCH)
# ==========================================
with tab2:
    st.markdown("### 1️⃣ Meter Readings & Cross-Verify")
    c1, c2, c3 = st.columns(3)
    with c1:
        ts4 = st.text_input("Start Time (Reg)", "8:00 AM")
        rs4 = gn(st.text_input("Start KVAH (Reg)", "249751728"))
    with c2:
        te4 = st.text_input("End Time (Reg)", "10:30 AM")
        re4 = gn(st.text_input("End KVAH (Reg)", "249775482"))
    
    # SYSTEM CALCULATION
    actual_diff = re4 - rs4
    
    with c3:
        st.markdown(f"**Meter Total:**")
        st.subheader(f"{actual_diff:,}")
        expected_val = gn(st.text_input("Aapka Expected Total Units?", "0"))

    # VERIFICATION BANNER
    if expected_val > 0:
        if expected_val == actual_diff:
            st.success(f"✅ **CROSS-MATCH OK!** Reading aur aapka total dono `{actual_diff:,}` hain.")
        else:
            st.error(f"❌ **MISMATCH!** Meter: `{actual_diff:,}` vs Aapka: `{expected_val:,}` (Farq: {actual_diff-expected_val})")

    st.markdown("---")
    st.markdown("### 2️⃣ Select Situations")
    rc1, rc2 = st.columns(2)
    fa4 = rc1.selectbox("A-Line Furnace", ["A1", "A2"])
    fb4 = rc2.selectbox("B-Line Furnace", ["B1", "B2"], index=1)
    tp4 = st.text_input("Tapping Times (Comma)", "8:25 AM, 9:45 AM")
    
    with st.expander("➕ OFF Time / Special Situations", expanded=True):
        sc1, sc2, sc3 = st.columns(3)
        off_fur = sc1.selectbox("Any Furnace OFF?", ["None", "A OFF", "B OFF", "BOTH OFF"])
        off_s = sc2.text_input("OFF From", "8:00 AM")
        off_e = sc3.text_input("OFF To", "9:45 AM")
        sc4, sc5, sc6 = st.columns(3)
        sit_tp = sc4.selectbox("Special Condition", ["None", "GLD Problem", "Sintering Heat"])
        sit_s = sc5.text_input("Sit. From", "")
        sit_e = sc6.text_input("Sit. To", "")

    if st.button("🚀 Register Table Banayein", type="primary", use_container_width=True):
        ds, de = pt(ts4), pt(te4, pt(ts4), True)
        if ds and de and actual_diff > 0:
            sl, cur = [], ds
            while cur < de:
                nx = min(cur + timedelta(minutes=15), de)
                sl.append({"s": cur, "e": nx, "fa": fa4, "fb": fb4, "status": "Both Running", "wt": 1.0, "min": 2850, "max": 3476})
                cur = nx
            
            oss, oee = pt(off_s, ds), pt(off_e, ds)
            sss, see = pt(sit_s, ds), pt(sit_e, ds)

            for s in sl:
                if off_fur != "None" and oss and oee and s["s"] < oee and s["e"] > oss:
                    if "A OFF" in off_fur: s["fa"] = "OFF"
                    if "B OFF" in off_fur: s["fb"] = "OFF"
                    if "BOTH" in off_fur: s["fa"], s["fb"] = "OFF", "OFF"
                    s["status"], s["wt"], s["min"], s["max"] = off_fur, 0.48, 825, 1831
                if sit_tp != "None" and sss and see and s["s"] < see and s["e"] > sss:
                    if "Both" in s["status"]:
                        s["status"], s["wt"], s["min"], s["max"] = sit_tp, 0.65, 1550, 2150
                for x in tp4.split(","):
                    if (dt := pt(x, ds)) and s["s"] <= dt < s["e"]:
                        if "Both" in s["status"]:
                            s["status"], s["wt"], s["min"], s["max"] = "Tapping (Dip)", 0.72, 2150, 2840

            # --- DYNAMIC RANDOM ALLOCATION WITH STRICT TOTAL ---
            final_units = [random.randint(s["min"], s["max"]) for s in sl]
            diff_sum = actual_diff - sum(final_units)
            
            attempts = 0
            while diff_sum != 0 and attempts < 10000:
                idx = random.randrange(len(final_units))
                step = 1 if diff_sum > 0 else -1
                if sl[idx]["min"] <= final_units[idx] + step <= sl[idx]["max"]:
                    final_units[idx] += step
                    diff_sum -= step
                attempts += 1
            if diff_sum != 0: final_units[-1] += diff_sum # Force last fix

            curr_r, rw = rs4, [{"Time": ds.strftime('%I:%M %p'), "Furnaces": f"{fa4}+{fb4}", "Situation": "Start", "KVAH": str(rs4), "Unit": "-"}]
            for i, s in enumerate(sl):
                curr_r += final_units[i]
                rw.append({"Time": s["e"].strftime('%I:%M %p'), "Furnaces": f"{s['fa']}+{s['fb']}", "Situation": s["status"], "KVAH": str(int(curr_r)), "Unit": str(int(final_units[i]))})
            
            st.dataframe(pd.DataFrame(rw), use_container_width=True, hide_index=True)
            st.success(f"Register Table Generated! Total: {actual_diff:,}")
        else:
            st.error("Readings ya Time check karein!")
                                                             
