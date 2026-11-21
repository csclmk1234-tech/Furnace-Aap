import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Furnace Master 16.5T", page_icon="⚡", layout="wide")
st.title("⚡ 16.5T Furnace Unified System")

# Configuration for Situation Weights
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
# TAB 1: HEAT-BY-HEAT (PRESERVED PERFECT LOGIC)
# ==========================================
with tab1:
    st.markdown("### 1️⃣ Meter Readings (Direct x8 Division)")
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
                x1, x2 = st.columns(2); cond = x1.selectbox(f"Situation #{i}", list(COND_RULES.keys()), key=f"cd_{i}")
                bd = x2.number_input(f"BD Min #{i}", 0, 300, 0, 5, key=f"bm_{i}")
                hl.append({"no": i, "on": on_t, "tap": tp_t, "dur": f"{dur_m//60}h {dur_m%60}m", "m": dur_m, "ton": ton, "cond": cond, "bd": bd, "pfr": COND_RULES[cond]["pf"]})
        if st.button("🔥 GENERATE 8-FACTOR REPORT", type="primary", use_container_width=True):
            sk = t_kwh // 8; k_sc = [(h["ton"] * COND_RULES[h["cond"]]["wt"] * random.uniform(0.98, 1.02)) + (h["bd"] * 0.45) for h in hl]
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
# TAB 2: 15-MIN REGISTER (ORGANIC VARIATION)
# ==========================================
with tab2:
    st.markdown("### 1️⃣ Meter Readings & Cross-Verify")
    c1, c2, c3 = st.columns(3)
    with c1:
        ts4 = st.text_input("Shift Start Time", "8:00 AM", key="r4_ts")
        rs4 = gn(st.text_input("Start KVAH (Register)", "249983498", key="r4_rs"))
    with c2:
        te4 = st.text_input("Shift End Time", "10:30 AM", key="r4_te")
        re4 = gn(st.text_input("End KVAH (Register)", "250011382", key="r4_re"))
    
    actual_diff = re4 - rs4
    with c3:
        st.markdown("**Meter Total:**")
        st.subheader(f"{actual_diff:,}")
        expected_val = gn(st.text_input("Confirm Total Units", str(actual_diff)))

    if expected_val > 0 and expected_val != actual_diff:
        st.error(f"❌ Mismatch! Meter: {actual_diff:,} vs Aapka: {expected_val:,}")

    st.markdown("---")
    st.markdown("### 2️⃣ Situations & Furnaces")
    rc1, rc2 = st.columns(2)
    fa4, fb4 = rc1.selectbox("A-Line", ["A1", "A2"]), rc2.selectbox("B-Line", ["B1", "B2"], index=1)
    tp4 = st.text_input("Tapping Times (Register)", "8:15 AM, 10:00 AM")
    
    with st.expander("➕ OFF Time / Special Case (GLD / Sintering)"):
        sc1, sc2, sc3 = st.columns(3)
        off_fur = sc1.selectbox("Any Furnace OFF?", ["None", "A OFF", "B OFF", "BOTH OFF"])
        off_s, off_e = sc2.text_input("OFF From", ""), sc3.text_input("OFF To", "")
        sit_tp = st.selectbox("Special Condition?", ["None", "GLD Problem", "Sintering Heat"])
        sit_s, sit_e = st.text_input("Sit. From", ""), st.text_input("Sit. To", "")

    if st.button("🚀 Register Table Banayein", type="primary", use_container_width=True):
        ds, de = pt(ts4), pt(te4, pt(ts4), True)
        if ds and de and actual_diff > 0:
            sl, cur = [], ds
            while cur < de:
                nx = min(cur + timedelta(minutes=15), de)
                sl.append({"s": cur, "e": nx, "fa": fa4, "fb": fb4, "status": "Both Running", "wt": 1.0})
                cur = nx
            
            oss, oee = pt(off_s, ds), pt(off_e, ds)
            sss, see = pt(sit_s, ds), pt(sit_e, ds)

            for s in sl:
                # Tapping check (Matches your manual 2426/2333 dip)
                for x in tp4.split(","):
                    if (dt := pt(x, ds)) and s["s"] <= dt < s["e"]:
                        s["status"], s["wt"] = "Tapping (Dip)", 0.78
                
                # OFF Furnace check (Matches your 1350-1800 range)
                if off_fur != "None" and oss and oee and s["s"] < oee and s["e"] > oss:
                    if "A OFF" in off_fur: s["fa"] = "OFF"
                    if "B OFF" in off_fur: s["fb"] = "OFF"
                    if "BOTH" in off_fur: s["fa"], s["fb"] = "OFF", "OFF"
                    s["status"], s["wt"] = off_fur, 0.52
                
                # Situation check
                if sit_tp != "None" and sss and see and s["s"] < see and s["e"] > sss:
                    if s["status"] == "Both Running":
                        s["status"], s["wt"] = sit_tp, 0.68

            # --- NEW ORGANIC SCALING LOGIC (No Fixed Caps) ---
            # Step 1: Assign dynamic weights with natural jitter
            dynamic_weights = [s["wt"] * random.uniform(0.85, 1.15) for s in sl]
            total_wt = sum(dynamic_weights)
            
            # Step 2: Proportional distribution based on total difference
            final_units = [int(round((w / total_wt) * actual_diff)) for w in dynamic_weights]
            
            # Step 3: Exact total match adjustment
            diff_sum = actual_diff - sum(final_units)
            final_units[-1] += diff_sum 
            
            # Step 4: No-Duplicate Polish (Ensure values vary)
            for i in range(len(final_units)-1):
                if final_units[i] == final_units[i+1]:
                    adjust = random.choice([-8, -4, 4, 8, 12, -12])
                    final_units[i] += adjust
                    final_units[i+1] -= adjust

            curr_r, rw = rs4, [{"Time": ds.strftime('%I:%M %p'), "Furnaces": f"{fa4}+{fb4}", "Situation": "Start", "KVAH": str(rs4), "Unit": "-"}]
            for i, s in enumerate(sl):
                curr_r += final_units[i]
                rw.append({"Time": s["e"].strftime('%I:%M %p'), "Furnaces": f"{s['fa']}+{s['fb']}", "Situation": s["status"], "KVAH": str(int(curr_r)), "Unit": str(int(final_units[i]))})
            
            st.dataframe(pd.DataFrame(rw), use_container_width=True, hide_index=True)
            st.success(f"Register Generated! Total: {actual_diff:,}")
        else: st.error("Check Readings/Time!")
                
