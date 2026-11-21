import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Furnace MF8 Factor App", page_icon="⚡", layout="wide")
st.title("⚡ Furnace Energy System (Units in Multiples of 8)")

# Situations with weights for distribution
CONDITIONS = {
    "Normal Running": {"pf": 0.960, "wt": 1.00},
    "Sintering (Lining Heat)": {"pf": 0.840, "wt": 1.28},
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

t_heat, t_reg = st.tabs(["🔥 1. Heat-by-Heat Report", "📋 2. 15-Min Register"])

# ==========================================
# TAB 1: HEAT-BY-HEAT (TOTAL = DIFF, HEAT = MULTIPLE OF 8)
# ==========================================
with t_heat:
    st.markdown("### 1️⃣ Meter Readings (Total = End - Start)")
    r1, r2 = st.columns(2)
    with r1:
        skw = gn(st.text_input("Start kWh Reading", "160944480"))
        skv = gn(st.text_input("Start kVAh Reading", "169767296"))
    with r2:
        ekw = gn(st.text_input("End kWh Reading", "160983200"))
        ekv = gn(st.text_input("End kVAh Reading", "169807360"))

    # Direct Difference Logic (No MF multiplication here)
    tot_kwh = ekw - skw
    tot_kvah = ekv - skv
    o_pf = round(tot_kwh / tot_kvah, 3) if tot_kvah > 0 else 0.0

    if tot_kwh > 0:
        st.info(f"📊 **TOTAL TO DIVIDE:** kWh = `{tot_kwh:,}` | kVAh = `{tot_kvah:,}` | PF = `{o_pf:.3f}`")
        nh = st.number_input("2️⃣ Yeh units kitni heats mein baantni hain?", 1, 20, 4)
        
        st.markdown("### 3️⃣ Situation & Heat Details")
        hl = []
        base_t = datetime.strptime("08:00 AM", "%I:%M %p")
        for i in range(1, int(nh) + 1):
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns(4)
                ton = c1.number_input(f"Heat #{i} Ton", 1.0, 22.0, 16.5, 0.1, key=f"h_tn_{i}")
                tp_t = c2.text_input(f"Heat #{i} Tap Time", (base_t + timedelta(minutes=110*i)).strftime("%I:%M %p"), key=f"h_tt_{i}")
                cond = c3.selectbox(f"Situation #{i}", list(CONDITIONS.keys()), key=f"h_cd_{i}")
                bd = c4.number_input(f"Breakdown Min #{i}", 0, 300, 0, 5, key=f"h_bm_{i}")
                hl.append({"no": i, "ton": ton, "tap": tp_t, "cond": cond, "bd": bd, "tpf": CONDITIONS[cond]["pf"], "wt": CONDITIONS[cond]["wt"]})

        if st.button("🔥 GENERATE HEAT REPORT", type="primary", use_container_width=True):
            # Divide 'Steps' (Total / 8) first to ensure multiples of 8
            steps_k = tot_kwh // 8
            steps_v = tot_kvah // 8
            
            scores = [(h["ton"] * h["wt"] * random.uniform(0.98, 1.02)) + (h["bd"] * 0.4) for h in hl]
            total_score = sum(scores)
            
            #kWh steps
            kw_s_alloc = [int(round((s / total_score) * steps_k)) for s in scores]
            kw_s_alloc[-1] += (steps_k - sum(kw_s_alloc))
            
            #kVAh steps based on PF
            kv_req = [kw_s_alloc[i] / hl[i]["tpf"] for i in range(len(hl))]
            kv_s_alloc = [int(round((v / sum(kv_req)) * steps_v)) for v in kv_req]
            kv_s_alloc[-1] += (steps_v - sum(kv_s_alloc))
            
            rep_rows = []
            copy_txt = ""
            for i, h in enumerate(hl):
                k_u = kw_s_alloc[i] * 8
                v_u = max(k_u + 8, kv_s_alloc[i] * 8)
                pf = round(k_u / v_u, 3)
                u_t = round(k_u / h["ton"], 1)
                
                rep_rows.append({"Heat": f"#{h['no']}", "Tap": h['tap'], "Ton": h['ton'], "u/Ton": u_t, "kWh (x8)": k_u, "kVAh (x8)": v_u, "PF": f"{pf:.3f}"})
                copy_txt += f"--- Heat #{h['no']} ---\nHeat Taping Time : {h['tap']}\nMelting Ton      : {h['ton']} T\nKwh units        : {k_u}\nKvah units       : {v_u}\nPf.              : {pf:.3f}\n\n"
            
            st.success(f"✅ Report Generated! Total Sum: {sum(x*8 for x in kw_s_alloc)} kWh (Matches {tot_kwh} if it was multiple of 8)")
            st.dataframe(pd.DataFrame(rep_rows), use_container_width=True, hide_index=True)
            st.code(copy_txt.strip(), language=None)
            
            if tot_kwh % 8 != 0:
                st.warning(f"⚠️ Note: Aapka Total KVAH Difference ({tot_kwh}) 8 ka multiple nahi hai, isliye bache hue {tot_kwh % 8} units adjust kar diye gaye hain.")

# ==========================================
# TAB 2: 15-MINUTE KVAH REGISTER
# ==========================================
with t_reg:
    st.markdown("### 📋 15-Min Register (A1/A2 & B1/B2)")
    c1, c2 = st.columns(2)
    with c1:
        ts_r = c1.text_input("Start Time", "8:00 AM")
        rs_r = gn(c1.text_input("Start KVAH Reading", "249751728"))
        fa_r = c1.selectbox("A-Line", ["A1", "A2"])
    with c2:
        te_r = c2.text_input("End Time", "10:30 AM")
        re_r = gn(c2.text_input("End KVAH Reading", "249775482"))
        fb_r = c2.selectbox("B-Line", ["B1", "B2"], index=1)
    
    tp_r = st.text_input("Tapping Times (Comma)", "8:25 AM, 9:45 AM")
    
    if st.button("🚀 Register Table Banayein", type="primary", use_container_width=True):
        ds, de = pt(ts_r), pt(te_r, pt(ts_r))
        if ds and de and re_r >= rs_r:
            diff_total = re_r - rs_r
            sl = []
            cur = ds
            while cur < de:
                nx = min(cur + timedelta(minutes=15), de)
                sl.append({"s": cur, "e": nx, "t": 0})
                cur = nx
            for x in tp_r.split(","):
                if dt := pt(x, ds):
                    for s in sl:
                        if s["s"] <= dt < s["e"]: s["t"] = 1
            
            # Natural Register fluctuation logic
            wts = [(random.uniform(0.65, 0.82) if s["t"] else random.uniform(0.85, 1.35)) * (((s["e"]-s["s"]).total_seconds()/60)/15) for s in sl]
            tw = sum(wts)
            steps = [int(round((w/tw)*diff_total)) for w in wts]
            steps[-1] += (diff_total - sum(steps))
            
            curr_read = rs_r
            rw = [{"Time": ds.strftime('%I:%M %p'), "KVAH": str(rs_r), "Unit": "-"}]
            for i, s in enumerate(sl):
                curr_read += steps[i]
                u_val = steps[i] # In register tab, units are direct difference
                rw.append({"Time": s["e"].strftime('%I:%M %p'), "KVAH": str(curr_read), "Unit": str(u_val)})
            
            st.dataframe(pd.DataFrame(rw), use_container_width=True, hide_index=True)
            st.success(f"Register Completed! Total units: {diff_total}")
        else:
            st.error("Readings check karein!")

# DONE
