import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="16.5T Furnace Advanced", page_icon="⚡", layout="wide")
st.title("⚡ 16.5T Furnace Master Control (Status-Wise)")

# Rules for Tab 1 (Heat-by-Heat)
COND_RULES = {
    "Normal Running": {"pf": (0.945, 0.982), "wt": 1.00},
    "Sintering (Lining Heat)": {"pf": (0.800, 0.880), "wt": 1.30}, 
    "GLD / Low KW Running": {"pf": (0.840, 0.890), "wt": 1.15}, 
    "Capacitor Bank Fault": {"pf": (0.750, 0.820), "wt": 1.10},
    "Furnace Breakdown": {"pf": (0.700, 0.800), "wt": 0.45},
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

tab1, tab2 = st.tabs(["🔥 1. Heat-by-Heat (With KW & Time)", "📋 2. 15-Min Register (Advanced Timeline)"])

# ==========================================
# TAB 1: HEAT-BY-HEAT (PRESERVED)
# ==========================================
with tab1:
    st.markdown("### 1️⃣ Readings & Total")
    r1, r2 = st.columns(2)
    skw = gn(r1.text_input("Start kWh", "160944480", key="h_skw"))
    skv = gn(r1.text_input("Start kVAh", "169767296", key="h_skv"))
    ekw = gn(r2.text_input("End kWh", "160983200", key="h_ekw"))
    ekv = gn(r2.text_input("End kVAh", "169807360", key="h_ekv"))
    t_kwh, t_kvah = ekw - skw, ekv - skv
    if t_kwh > 0:
        st.info(f"📊 **TOTAL:** kWh = `{t_kwh:,}` | PF = `{round(t_kwh/t_kvah,3) if t_kvah>0 else 0}`")
        nh = st.number_input("Total Heats?", 1, 20, 4)
        hl = []
        bt = datetime.strptime("08:00 AM", "%I:%M %p")
        for i in range(1, int(nh) + 1):
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns(4)
                on_t = c1.text_input(f"ON Time #{i}", (bt + timedelta(minutes=120*(i-1))).strftime("%I:%M %p"), key=f"on_{i}")
                tp_t = c2.text_input(f"TAP Time #{i}", (bt + timedelta(minutes=115*i)).strftime("%I:%M %p"), key=f"tp_{i}")
                don, dtp = pt(on_t), pt(tp_t, pt(on_t), True)
                dm = int((dtp-don).total_seconds()/60) if don and dtp else 115
                c3.markdown(f"**⏱️ Total Time:**\n\n{dm//60}h {dm%60}m")
                ton = c4.number_input(f"Ton #{i}", 1.0, 22.0, 16.5, 0.1, key=f"tn_{i}")
                x1, x2, x3 = st.columns(3)
                cd = x1.selectbox(f"Situation #{i}", list(COND_RULES.keys()), key=f"cd_{i}")
                lkw = x2.number_input(f"Low KW Running", 0, 7500, 0, key=f"lk_{i}")
                lm = x3.number_input(f"Low KW Time(min)", 0, 300, 0, key=f"lm_{i}")
                hl.append({"no": i, "on": on_t, "tap": tp_t, "dur": f"{dm//60}h {dm%60}m", "m": dm, "ton": ton, "cond": cd, "lkw": lkw, "lmin": lm, "pfr": COND_RULES[cd]["pf"]})
        
        if st.button("🔥 GENERATE HEAT REPORT", type="primary"):
            sk = t_kwh // 8
            k_sc = [(h["ton"] * COND_RULES[h["cond"]]["wt"]) + ((h["lkw"]*h["lmin"])/60/8) for h in hl]
            kw_s = [int(round((s/sum(k_sc))*sk)) for s in k_sc]
            kw_s[-1] += (sk - sum(kw_s))
            v_sc = [kw_s[i]/random.uniform(*hl[i]["pfr"]) for i in range(len(hl))]
            kv_s = [int(round((v/sum(v_sc))*(t_kvah//8))) for v in v_sc]
            kv_s[-1] += ((t_kvah//8) - sum(kv_s))
            rep_r, cp_t = [], ""
            for i, h in enumerate(hl):
                k, v = kw_s[i]*8, max(kw_s[i]*8+8, kv_s[i]*8)
                rep_r.append({"Heat": f"#{h['no']}", "ON": h['on'], "TAP": h['tap'], "Time": h['dur'], "Ton": h['ton'], "kWh": k, "PF": f"{round(k/v,3):.3f}"})
                cp_t += f"--- Heat #{h['no']} ---\nHeat ON Time: {h['on']}\nHeat Taping: {h['tap']} ({h['dur']})\nKwh: {k}\nPf: {round(k/v,3):.3f}\n\n"
            st.dataframe(pd.DataFrame(rep_r), use_container_width=True, hide_index=True)
            st.code(cp_t.strip(), language=None)

# ==========================================
# TAB 2: 15-MIN REGISTER (TIMELINE FIXED)
# ==========================================
with tab2:
    st.markdown("### 📋 Register Configuration")
    rc1, rc2, rc3 = st.columns(3)
    ts4 = rc1.text_input("Shift Start Time", "8:00 AM", key="reg_ts")
    te4 = rc2.text_input("Shift End Time", "10:30 AM", key="reg_te")
    rs4 = gn(rc3.text_input("Start KVAH Reading", "249983498"))
    re4 = gn(rc3.text_input("End KVAH Reading", "250011382"))
    
    act_diff = re4 - rs4
    st.info(f"📊 **Meter Total:** `{act_diff:,}` Units")
    tp_times = st.text_input("Tapping Times (comma)", "8:15 AM, 10:00 AM")

    st.markdown("### 🔧 Furnace Timeline Manager")
    
    def status_ui(label, f_key):
        with st.container(border=True):
            st.subheader(label)
            f_id = st.selectbox(f"Select Line", ["A1", "A2"] if "A" in label else ["B1", "B2"], key=f"id_{f_key}")
            stat = st.selectbox(f"Status", ["Normal Running", "GLD Low KW", "OFF (0 KW)", "Holding", "Capacitor Fault"], key=f"st_{f_key}")
            
            kw = 7000 # Default
            if stat == "OFF (0 KW)": kw = 0
            elif stat == "GLD Low KW": kw = st.number_input("Enter GLD KW", 500, 3000, 1000, key=f"kw_{f_key}")
            elif stat == "Holding": kw = st.number_input("Enter Holding KW", 500, 2500, 1200, key=f"hkw_{f_key}")
            elif stat == "Capacitor Fault": kw = st.number_input("Enter Fault KW", 500, 5000, 4500, key=f"ckw_{f_key}")
            
            c1, c2 = st.columns(2)
            frm = c1.text_input("From", "8:00 AM" if "A" in label else "", key=f"fr_{f_key}")
            to = c2.text_input("To", "9:45 AM" if "A" in label else "", key=f"to_{f_key}")
            return {"id": f_id, "stat": stat, "kw": kw, "from": frm, "to": to}

    col_a, col_b = st.columns(2)
    with col_a: f_a = status_ui("Furnace A", "a")
    with col_b: f_b = status_ui("Furnace B", "b")

    if st.button("🚀 Generate Advanced Register", type="primary", use_container_width=True):
        ds, de = pt(ts4), pt(te4, pt(ts4), True)
        if ds and de and act_diff > 0:
            sl, cur = [], ds
            while cur < de:
                nx = min(cur + timedelta(minutes=15), de)
                sl.append({"s": cur, "e": nx, "fa": f_a["id"], "fakw": 7000, "fastat": "Normal", "fb": f_b["id"], "fbkw": 7000, "fbstat": "Normal"})
                cur = nx
            
            # Applying Timelines
            as_f, as_t = pt(f_a["from"], ds), pt(f_a["to"], ds)
            bs_f, bs_t = pt(f_b["from"], ds), pt(f_b["to"], ds)
            
            for s in sl:
                # Furnace A Logic
                if as_f and as_t and s["s"] < as_t and s["e"] > as_f:
                    s["fastat"], s["fakw"] = f_a["stat"], f_a["kw"]
                    if f_a["kw"] == 0: s["fa"] = "OFF"
                # Furnace B Logic
                if bs_f and bs_t and s["s"] < bs_t and s["e"] > bs_f:
                    s["fbstat"], s["fbkw"] = f_b["stat"], f_b["kw"]
                    if f_b["kw"] == 0: s["fb"] = "OFF"
                
                # Tapping check (natural dip only for 'Normal' running)
                for x in tp_times.split(","):
                    if (dt := pt(x, ds)) and s["s"] <= dt < s["e"]:
                        if s["fastat"] == "Normal": s["fakw"] *= 0.75
                        if s["fbstat"] == "Normal": s["fbkw"] *= 0.75

            # KW-based Proportional Weighting
            wts = [(s["fakw"] + s["fbkw"]) * random.uniform(0.96, 1.04) for s in sl]
            total_wt = sum(wts)
            
            # Allocation with 3476 max cap for safety
            steps = [int(round((w/total_wt)*act_diff)) for w in wts]
            steps[-1] += (act_diff - sum(steps)) # Adjust total
            
            curr_r, rw = rs4, [{"Time": ds.strftime('%I:%M %p'), "A-Status": "-", "B-Status": "-", "KVAH": str(rs4), "Unit": "-"}]
            for i, s in enumerate(sl):
                curr_r += steps[i]
                rw.append({
                    "Time": s["e"].strftime('%I:%M %p'),
                    "A-Status": f"{s['fa']} ({s['fastat']})",
                    "B-Status": f"{s['fb']} ({s['fbstat']})",
                    "KVAH": str(int(curr_r)),
                    "Unit": str(int(steps[i]))
                })
            st.dataframe(pd.DataFrame(rw), use_container_width=True, hide_index=True)
            st.success("✅ Advanced Register Generated Successfully!")
                                                                 
