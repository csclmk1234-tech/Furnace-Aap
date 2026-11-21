import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Furnace MF8 Final", page_icon="⚡", layout="wide")
st.title("⚡ 16.5T Furnace Unified System")

# Situations with Strict PF Ranges
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
    with r1:
        skw = gn(st.text_input("Start kWh Reading", "160944480", key="h_skw"))
        skv = gn(st.text_input("Start kVAh Reading", "169767296", key="h_skv"))
    with r2:
        ekw = gn(st.text_input("End kWh Reading", "160983200", key="h_ekw"))
        ekv = gn(st.text_input("End kVAh Reading", "169807360", key="h_ekv"))

    t_kwh = ekw - skw
    t_kvah = ekv - skv
    o_pf = round(t_kwh / t_kvah, 3) if t_kvah > 0 else 0.0

    if t_kwh > 0:
        st.info(f"📊 **TOTAL TO DIVIDE:** kWh = `{t_kwh:,}` | kVAh = `{t_kvah:,}` | Overall PF = `{o_pf:.3f}`")
        nh = st.number_input("2️⃣ Yeh total kitni heats mein divide karni hain?", 1, 20, 4)
        
        st.markdown("### 3️⃣ Heat-wise Details")
        hl = []
        base_t = datetime.strptime("08:00 AM", "%I:%M %p")
        for i in range(1, int(nh) + 1):
            with st.container(border=True):
                st.markdown(f"**Heat #{i}**")
                c1, c2, c3, c4 = st.columns(4)
                on_t = c1.text_input(f"ON Time", (base_t + timedelta(minutes=120*(i-1))).strftime("%I:%M %p"), key=f"on_{i}")
                tp_t = c2.text_input(f"TAP Time", (base_t + timedelta(minutes=115*i)).strftime("%I:%M %p"), key=f"tp_{i}")
                
                don, dtp = pt(on_t), pt(tp_t, pt(on_t))
                dur_m = int((dtp - don).total_seconds() / 60) if don and dtp else 115
                dur_txt = f"{dur_m // 60}h {dur_m % 60}m"
                
                c3.markdown(f"**⏱️ Total Time**\n\n{dur_txt}")
                ton = c4.number_input(f"Melt Ton", 1.0, 22.0, 16.5, 0.1, key=f"tn_{i}")
                
                x1, x2 = st.columns(2)
                cond = x1.selectbox(f"Situation", list(COND_RULES.keys()), key=f"cd_{i}")
                bd = x2.number_input(f"Breakdown Min", 0, 300, 0, 5, key=f"bm_{i}")
                
                hl.append({"no": i, "on": on_t, "tap": tp_t, "dur": dur_txt, "m": dur_m, "ton": ton, "cond": cond, "bd": bd, "pfr": COND_RULES[cond]["pf"]})

        if st.button("🔥 GENERATE 8-FACTOR REPORT", type="primary", use_container_width=True):
            steps_k = t_kwh // 8
            steps_v = t_kvah // 8
            k_scores = [(h["ton"] * COND_RULES[h["cond"]]["wt"] * random.uniform(0.98, 1.02)) + (h["bd"] * 0.45) for h in hl]
            kw_s_alloc = [int(round((s / sum(k_scores)) * steps_k)) for s in k_scores]
            kw_s_alloc[-1] += (steps_k - sum(kw_s_alloc))
            
            v_scores = [kw_s_alloc[i] / random.uniform(*hl[i]["pfr"]) for i in range(len(hl))]
            kv_s_alloc = [int(round((v / sum(v_scores)) * steps_v)) for v in v_scores]
            kv_s_alloc[-1] += (steps_v - sum(kv_s_alloc))
            
            rep_rows, copy_txt = [], ""
            for i, h in enumerate(hl):
                k_u, v_u = kw_s_alloc[i] * 8, max(kw_s_alloc[i] * 8 + 8, kv_s_alloc[i] * 8)
                pf, ut = round(k_u / v_u, 3), round(k_u / h["ton"], 1)
                
                rep_rows.append({"Heat": f"#{h['no']}", "ON": h['on'], "TAP": h['tap'], "Time": h['dur'], "Ton": h['ton'], "kWh": k_u, "kVAh": v_u, "PF": f"{pf:.3f}"})
                copy_txt += (
                    f"--- Heat #{h['no']} ---\n"
                    f"Heat ON Time     : {h['on']}\n"
                    f"Heat Taping Time : {h['tap']} ({h['dur']})\n"
                    f"Kwh units        : {k_u}\n"
                    f"Kvah units       : {v_u}\n"
                    f"Pf.              : {pf:.3f}\n\n"
                )
            st.success("✅ Report Ready (Strict 8-Factor)")
            st.dataframe(pd.DataFrame(rep_rows), use_container_width=True, hide_index=True)
            st.code(copy_txt.strip(), language=None)
    else: st.warning("Start/End Readings sahi se daalein.")

with t_reg:
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
