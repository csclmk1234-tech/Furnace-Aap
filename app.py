import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="16.5T Furnace Ultimate V4", page_icon="⚡", layout="wide")
st.title("⚡ 16.5T Furnace Advanced Master Control")

# --- RULES & CONFIGURATION ---
COND_RULES = {
    "Normal Running": {"pf": (0.945, 0.982), "wt": 1.00},
    "Sintering (Lining Heat)": {"pf": (0.800, 0.880), "wt": 1.30}, 
    "GLD / Low KW Running": {"pf": (0.840, 0.890), "wt": 1.15}, 
    "Capacitor Bank Fault": {"pf": (0.750, 0.820), "wt": 1.10},
    "Panel / SCR Tripping": {"pf": (0.820, 0.880), "wt": 1.12},
    "CCM Holding / Casting": {"pf": (0.800, 0.850), "wt": 1.10},  
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

tab1, tab2 = st.tabs(["🔥 1. Heat-by-Heat (Checkbox Added)", "📋 2. 15-Min Register (Checkbox Added)"])

# ==========================================
# TAB 1: HEAT-BY-HEAT (OFF CHECKBOX LOGIC)
# ==========================================
with tab1:
    st.markdown("### 1️⃣ Meter Readings")
    r1, r2 = st.columns(2)
    skw = gn(r1.text_input("Start kWh Reading", "160944480", key="h_skw"))
    skv = gn(r1.text_input("Start kVAh Reading", "169767296", key="h_skv"))
    ekw = gn(r2.text_input("End kWh Reading", "160983200", key="h_ekw"))
    ekv = gn(r2.text_input("End kVAh Reading", "169807360", key="h_ekv"))
    
    t_kwh, t_kvah = ekw - skw, ekv - skv
    
    if t_kwh > 0:
        st.info(f"📊 **METER TOTAL:** kWh = `{t_kwh:,}` | kVAh = `{t_kvah:,}` | PF = `{round(t_kwh/t_kvah,3) if t_kvah>0 else 0}`")
        
        nh = st.number_input("Total Heats?", 1, 20, 4)
        hl =
        bt = datetime.strptime("08:00 AM", "%I:%M %p")
        
        for i in range(1, int(nh) + 1):
            with st.container(border=True):
                st.markdown(f"**Heat #{i}**")
                c1, c2, c3, c4 = st.columns(4)
                on_t = c1.text_input(f"H#{i} ON Time", (bt + timedelta(minutes=120*(i-1))).strftime("%I:%M %p"), key=f"on_{i}")
                tp_t = c2.text_input(f"H#{i} TAP Time", (bt + timedelta(minutes=115*i)).strftime("%I:%M %p"), key=f"tp_{i}")
                don, dtp = pt(on_t), pt(tp_t, pt(on_t), True)
                dm = int((dtp-don).total_seconds()/60) if don and dtp else 115
                c3.markdown(f"**⏱️ Total Time:**\n\n{dm//60}h {dm%60}m")
                ton = c4.number_input(f"Melt Ton #{i}", 1.0, 22.0, 16.5, 0.1, key=f"tn_{i}")

                # OFF & PROBLEM SECTIONS
                col_off, col_prob = st.columns(2)
                with col_off:
                    st.markdown("🔴 **Furnace OFF / Breakdown**")
                    # CHECKBOX ADDED HERE
                    is_off = st.checkbox("Was Furnace OFF?", key=f"chk_off_{i}")
                    if is_off:
                        off_f = st.text_input(f"OFF From", "", key=f"of_{i}")
                        off_t = st.text_input(f"OFF To", "", key=f"ot_{i}")
                    else:
                        off_f, off_t = "", ""

                    doff_f, doff_t = pt(off_f, don), pt(off_t, don)
                    off_min = int((doff_t - doff_f).total_seconds()/60) if doff_f and doff_t else 0
                
                with col_prob:
                    st.markdown("🟡 **Problem / Low Power**")
                    cond = st.selectbox(f"Select Problem", list(COND_RULES.keys()), key=f"cd_{i}")
                    lkw = st.number_input(f"Low KW Load", 0, 7500, 1000 if "GLD" in cond else 0, key=f"lk_{i}")
                    lmin = st.number_input(f"Duration (min)", 0, 300, key=f"lm_{i}")
                
                hl.append({"no": i, "on": on_t, "tap": tp_t, "dur": f"{dm//60}h {dm%60}m", "ton": ton, "cond": cond, "lkw": lkw, "lmin": lmin, "off_m": off_min, "pfr": COND_RULES[cond]["pf"]})

        if st.button("🔥 GENERATE REPORT", type="primary", use_container_width=True):
            sk = t_kwh // 8
            k_sc =
            for h in hl:
                sc = (h["ton"] * COND_RULES[h["cond"]]["wt"]) + ((h["lkw"]*h["lmin"])/60/8)
                if h["off_m"] > 0: sc *= 0.8
                k_sc.append(sc)
            
            kw_s = [int(round((s / sum(k_sc)) * sk)) for s in k_sc]
            kw_s[-1] += (sk - sum(kw_s))
            
            v_sc = [kw_s[i] / random.uniform(*hl[i]["pfr"]) for i in range(len(hl))]
            kv_s = [int(round((v / sum(v_sc)) * (t_kvah//8))) for v in v_sc]
            kv_s[-1] += ((t_kvah//8) - sum(kv_s))
            
            rep_r, cp_t =, ""
            for i, h in enumerate(hl):
                k, v = kw_s[i]*8, max(kw_s[i]*8+8, kv_s[i]*8)
                pf = round(k/v, 3)
                rep_r.append({
                    "Heat": f"#{h['no']}", "ON": h['on'], "TAP": h['tap'], "Time": h['dur'], 
                    "Ton": h['ton'], "OFF Time": f"{h['off_m']} min", 
                    "kWh": k, "kVAh": v, "PF": f"{pf:.3f}"
                })
                cp_t += (
                    f"--- Heat #{h['no']} ---\n"
                    f"Heat ON Time     : {h['on']}\n"
                    f"Heat Taping Time : {h['tap']} ({h['dur']})\n"
                    f"OFF Time         : {h['off_m']}m\n"
                    f"Kwh units        : {k}\n"
                    f"Kvah units       : {v}\n"
                    f"Pf.              : {pf:.3f}\n\n"
                )
            
            st.dataframe(pd.DataFrame(rep_r), use_container_width=True, hide_index=True)
            st.code(cp_t.strip(), language=None)

# ==========================================
# TAB 2: 15-MIN REGISTER (CHECKBOX LOGIC)
# ==========================================
with tab2:
    st.markdown("### 📋 Register Readings")
    c1, c2, c3 = st.columns(3)
    ts4, rs4 = c1.text_input("Shift Start Time", "8:00 AM"), gn(c1.text_input("Start KVAH", "249983498"))
    te4, re4 = c2.text_input("Shift End Time", "10:30 AM"), gn(c2.text_input("End KVAH", "250011382"))
    
    act_diff = re4 - rs4
    c3.subheader(f"Meter: {act_diff:,} Units")
    exp_total = gn(c3.text_input("Verify Total Units", str(act_diff)))
    
    tp_list = st.text_input("Heat Tapping Times", "8:15 AM, 10:00 AM")

    def f_control_ui(f_name, f_key):
        with st.container(border=True):
            st.subheader(f_name)
            fid = st.selectbox(f"Select Line", ["A1", "A2"] if "A" in f_name else ["B1", "B2"], key=f"id_{f_key}")
            
            st.error(f"🔴 **Furnace {f_name} OFF**")
            # CHECKBOX ADDED HERE
            is_off = st.checkbox(f"Tick if {f_name} was OFF", key=f"off_chk_{f_key}")
            
            if is_off:
                c_o1, c_o2 = st.columns(2)
                o_f = c_o1.text_input("OFF From", "", key=f"of_{f_key}")
                o_t = c_o2.text_input("OFF To", "", key=f"ot_{f_key}")
            else:
                o_f, o_t = "", ""
            
            st.warning(f"🟡 **Problem Running (Low KW)**")
            c_p1, c_p2, c_p3 = st.columns(3)
            p_st = c_p1.selectbox("Problem", ["None", "GLD", "Holding", "Sintering", "Capacitor"], key=f"ps_{f_key}")
            p_kw = c_p2.number_input("Problem KW", 0, 3000, 1000, key=f"pk_{f_key}")
            p_f = c_p3.text_input("From", "", key=f"pf_{f_key}")
            p_t = st.text_input("To", "", key=f"pt_{f_key}")
            
            return {"id": fid, "off": (o_f, o_t), "prob": (p_st, p_kw, p_f, p_t)}

    ca, cb = st.columns(2)
    with ca: fa_d = f_control_ui("Furnace A", "a")
    with cb: fb_d = f_control_ui("Furnace B", "b")

    if st.button("🚀 GENERATE REGISTER TABLE", type="primary", use_container_width=True):
        ds, de = pt(ts4), pt(te4, pt(ts4), True)
        if ds and de and act_diff > 0:
            sl, cur =, ds
            while cur < de:
                nx = min(cur + timedelta(minutes=15), de)
                sl.append({"s": cur, "e": nx, "fa": fa_d["id"], "fakw": 7000, "fastat": "Normal", "fb": fb_d["id"], "fbkw": 7000, "fbstat": "Normal"})
                cur = nx
            
            for s in sl:
                # Apply OFF Times (Priority 1)
                for f_data, f_side in [(fa_d, "a"), (fb_d, "b")]:
                    off_from, off_to = pt(f_data["off"][0], ds), pt(f_data["off"][1], ds)
                    if off_from and off_to and s["s"] < off_to and s["e"] > off_from:
                        if f_side == "a": s["fa"], s["fastat"], s["fakw"] = "OFF", "OFF", 0
                        else: s["fb"], s["fbstat"], s["fbkw"] = "OFF", "OFF", 0
                
                # Apply Problems (Priority 2)
                for f_data, f_side in [(fa_d, "a"), (fb_d, "b")]:
                    p_st, p_kw, p_f, p_t = f_data["prob"]
                    prob_f, prob_t = pt(p_f, ds), pt(p_t, ds)
                    if p_st != "None" and prob_f and prob_t and s["s"] < prob_t and s["e"] > prob_f:
                        if f_side == "a" and s["fastat"] != "OFF":
                            s["fastat"], s["fakw"] = p_st, p_kw
                        if f_side == "b" and s["fbstat"] != "OFF":
                            s["fbstat"], s["fbkw"] = p_st, p_kw

                for x in tp_list.split(","):
                    if (dt := pt(x, ds)) and s["s"] <= dt < s["e"]:
                        if s["fastat"] == "Normal": s["fakw"] *= 0.78
                        if s["fbstat"] == "Normal": s["fbkw"] *= 0.78

            wts = [(s["fakw"] + s["fbkw"]) * random.uniform(0.90, 1.10) for s in sl]
            final_units = [int(round((w/sum(wts))*act_diff)) for w in wts]
            final_units[-1] += (act_diff - sum(final_units))
            
            for i in range(len(final_units)-1):
                if final_units[i] == final_units[i+1]: final_units[i] += random.choice([-8, 8])

            curr_r, rw = rs4, [{"Time": ds.strftime('%I:%M %p'), "A-Line": "-", "B-Line": "-", "KVAH": str(rs4), "Unit": "-"}]
            for i, s in enumerate(sl):
                curr_r += final_units[i]
                rw.append({"Time": s["e"].strftime('%I:%M %p'), "A-Line": f"{s['fa']} ({s['fastat']})", "B-Line": f"{s['fb']} ({s['fbstat']})", "KVAH": str(int(curr_r)), "Unit": str(int(final_units[i]))})
            st.dataframe(pd.DataFrame(rw), use_container_width=True, hide_index=True)
            st.success(f"Register Generated Successfully! Sum: {sum(final_units):,}")
            
