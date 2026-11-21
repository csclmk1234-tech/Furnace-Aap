import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Furnace MF8 Final", page_icon="⚡", layout="wide")
st.title("⚡ 16.5T Furnace Unified System")

# Tab 1 Rules
COND_RULES = {
    "Normal Running": {"pf": (0.945, 0.982), "wt": 1.00},
    "Sintering (Lining Heat)": {"pf": (0.800, 0.880), "wt": 1.30}, 
    "GLD / Tripping Problem": {"pf": (0.850, 0.900), "wt": 1.18}, 
    "CCM Holding / Casting": {"pf": (0.800, 0.850), "wt": 1.10},  
    "Scrap / Slag Delay": {"pf": (0.820, 0.890), "wt": 1.05},     
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
    d = "".join(c for c in str(v) if c.isdigit())
    return int(d) if d else 0

t_heat, t_reg = st.tabs(["🔥 1. Heat-by-Heat Report", "📋 2. 15-Min Register"])

with t_heat:
    st.markdown("### 1️⃣ Meter Readings (Total = End - Start)")
    r1, r2 = st.columns(2)
    skw = gn(r1.text_input("Start kWh Reading", "160944480", key="h_skw"))
    skv = gn(r1.text_input("Start kVAh Reading", "169767296", key="h_skv"))
    ekw = gn(r2.text_input("End kWh Reading", "160983200", key="h_ekw"))
    ekv = gn(r2.text_input("End kVAh Reading", "169807360", key="h_ekv"))

    t_kwh, t_kvah = ekw - skw, ekv - skv
    o_pf = round(t_kwh / t_kvah, 3) if t_kvah > 0 else 0.0

    if t_kwh > 0:
        st.info(f"📊 **TOTAL TO DIVIDE:** kWh = `{t_kwh:,}` | kVAh = `{t_kvah:,}` | Overall PF = `{o_pf:.3f}`")
        nh = st.number_input("2️⃣ Total Heats?", 1, 20, 4)
        hl = []
        base_t = datetime.strptime("08:00 AM", "%I:%M %p")
        for i in range(1, int(nh) + 1):
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns(4)
                on_t = c1.text_input(f"ON Time #{i}", (base_t + timedelta(minutes=120*(i-1))).strftime("%I:%M %p"), key=f"on_{i}")
                tp_t = c2.text_input(f"TAP Time #{i}", (base_t + timedelta(minutes=115*i)).strftime("%I:%M %p"), key=f"tp_{i}")
                don, dtp = pt(on_t), pt(tp_t, pt(on_t))
                dur_m = int((dtp - don).total_seconds() / 60) if don and dtp else 115
                c3.markdown(f"**⏱️ Time:** {dur_m//60}h {dur_m%60}m")
                ton = c4.number_input(f"Ton #{i}", 1.0, 22.0, 16.5, 0.1, key=f"tn_{i}")
                cond = st.selectbox(f"Situation #{i}", list(COND_RULES.keys()), key=f"cd_{i}")
                bd = st.number_input(f"BD Min #{i}", 0, 300, 0, 5, key=f"bm_{i}")
                hl.append({"no": i, "on": on_t, "tap": tp_t, "dur": f"{dur_m//60}h {dur_m%60}m", "m": dur_m, "ton": ton, "cond": cond, "bd": bd, "pfr": COND_RULES[cond]["pf"]})

        if st.button("🔥 GENERATE 8-FACTOR REPORT", type="primary", use_container_width=True):
            sk = t_kwh // 8
            k_sc = [(h["ton"] * COND_RULES[h["cond"]]["wt"] * random.uniform(0.98, 1.02)) + (h["bd"] * 0.45) for h in hl]
            kw_s = [int(round((s / sum(k_sc)) * sk)) for s in k_sc]
            kw_s[-1] += (sk - sum(kw_s))
            v_sc = [kw_s[i] / random.uniform(*hl[i]["pfr"]) for i in range(len(hl))]
            kv_s = [int(round((v / sum(v_sc)) * (t_kvah//8))) for v in v_sc]
            kv_s[-1] += ((t_kvah//8) - sum(kv_s))
            
            rep_r = []; copy_t = ""
            for i, h in enumerate(hl):
                k, v = kw_s[i]*8, max(kw_s[i]*8+8, kv_s[i]*8)
                pf, ut = round(k/v, 3), round(k/h["ton"], 1)
                rep_r.append({"Heat": f"#{h['no']}", "ON": h['on'], "TAP": h['tap'], "Time": h['dur'], "Ton": h['ton'], "kWh": k, "kVAh": v, "PF": f"{pf:.3f}"})
                copy_t += f"--- Heat #{h['no']} ---\nHeat ON Time     : {h['on']}\nHeat Taping Time : {h['tap']} ({h['dur']})\nKwh units        : {k}\nKvah units       : {v}\nPf.              : {pf:.3f}\n\n"
            st.dataframe(pd.DataFrame(rep_r), use_container_width=True, hide_index=True)
            st.code(copy_t.strip(), language=None)
# --- END PART 1 ---
with t_reg:
    st.markdown("### 📋 15-Min Register Generator (Situation-Based)")
    rc1, rc2 = st.columns(2)
    ts4 = rc1.text_input("Start Time (Register)", "8:00 AM", key="r4_ts")
    rs4 = gn(rc1.text_input("Start KVAH (Register)", "249751728", key="r4_rs"))
    fa4 = rc1.selectbox("A-Line Active", ["A1", "A2"], key="r4_fa")
    te4 = rc2.text_input("End Time (Register)", "10:30 AM", key="r4_te")
    re4 = gn(rc2.text_input("End KVAH (Register)", "249775482", key="r4_re"))
    fb4 = rc2.selectbox("B-Line Active", ["B1", "B2"], index=1, key="r4_fb")

    tp4 = st.text_input("Tapping Times (Register)", "8:25 AM, 9:45 AM")
    
    with st.expander("➕ Register Situations (GLD, Sintering, OFF)"):
        c_b1, c_b2, c_b3 = st.columns(3)
        off_fur = c_b1.selectbox("Any Furnace OFF?", ["None", "A OFF", "B OFF", "BOTH OFF"], key="r4_off")
        off_s, off_e = c_b2.text_input("OFF From", ""), c_b3.text_input("OFF To", "")
        c_s1, c_s2, c_s3 = st.columns(3)
        sit_tp = c_s1.selectbox("Special Case?", ["None", "GLD Problem", "Sintering Heat", "Capacitor Fault"], key="r4_sit")
        sit_s, sit_e = c_s2.text_input("Sit. From", ""), c_s3.text_input("Sit. To", "")

    if st.button("🚀 Register Table Banayein", type="primary", use_container_width=True, key="r4_btn"):
        ds, de = pt(ts4), pt(te4, pt(ts4))
        if ds and de and re4 >= rs4:
            diff_total, cur, sl = re4 - rs4, ds, []
            while cur < de:
                nx = min(cur + timedelta(minutes=15), de)
                sl.append({"s": cur, "e": nx, "fa": fa4, "fb": fb4, "status": "Both Running", "wt": 1.0})
                cur = nx
            for s in sl:
                for x in tp4.split(","):
                    if (dt := pt(x, ds)) and s["s"] <= dt < s["e"]:
                        s["status"], s["wt"] = "Tapping (Dip)", 0.72
                if sit_tp != "None" and sit_s and sit_e:
                    ss, se = pt(sit_s, ds), pt(sit_e, ds)
                    if ss and se and s["s"] < se and s["e"] > ss:
                        s["status"] = sit_tp
                        s["wt"] = 0.78 if sit_tp == "GLD Problem" else 0.65
                if off_fur != "None" and off_s and off_e:
                    os, oe = pt(off_s, ds), pt(off_e, ds)
                    if os and oe and s["s"] < oe and s["e"] > os:
                        if "A OFF" in off_fur: s["fa"] = "OFF"
                        if "B OFF" in off_fur: s["fb"] = "OFF"
                        s["status"], s["wt"] = f"{off_fur}", 0.55
            wts = [s["wt"] * random.uniform(0.92, 1.15) * (((s["e"]-s["s"]).total_seconds()/60)/15) for s in sl]
            steps = [int(round((w/sum(wts))*diff_total)) for w in wts]
            steps[-1] += (diff_total - sum(steps))
            curr_r, rw = rs4, [{"Time": ds.strftime('%I:%M %p'), "Furnaces": f"{fa4}+{fb4}", "Situation": "Start", "KVAH": str(rs4), "Unit": "-"}]
            for i, s in enumerate(sl):
                curr_r += steps[i]
                rw.append({"Time": s["e"].strftime('%I:%M %p'), "Furnaces": f"{s['fa']}+{s['fb']}", "Situation": s["status"], "KVAH": str(curr_r), "Unit": str(steps[i])})
            st.dataframe(pd.DataFrame(rw), use_container_width=True, hide_index=True)
        else: st.error("Check Readings/Time!")
# --- END PART 2 ---
