import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Furnace Power Master Pro", page_icon="⚡", layout="wide")
st.title("⚡ 16.5T Furnace Advanced Control System")

# Situations with Strict PF Ranges
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

tab1, tab2 = st.tabs(["🔥 1. Heat-by-Heat (With KW & Time)", "📋 2. 15-Min Register (Advanced)"])

# ==========================================
# TAB 1: HEAT-BY-HEAT (TIME & KW RESTORED)
# ==========================================
with tab1:
    st.markdown("### 1️⃣ Readings & Total")
    r1, r2 = st.columns(2)
    skw = gn(r1.text_input("Start kWh Reading", "160944480", key="h_skw"))
    skv = gn(r1.text_input("Start kVAh Reading", "169767296", key="h_skv"))
    ekw = gn(r2.text_input("End kWh Reading", "160983200", key="h_ekw"))
    ekv = gn(r2.text_input("End kVAh Reading", "169807360", key="h_ekv"))
    
    t_kwh, t_kvah = ekw - skw, ekv - skv
    if t_kwh > 0:
        st.info(f"📊 **TOTAL TO DIVIDE:** kWh = `{t_kwh:,}` | kVAh = `{t_kvah:,}` | PF = `{round(t_kwh/t_kvah,3) if t_kvah>0 else 0}`")
        nh = st.number_input("Total Heats?", 1, 20, 4)
        hl = []
        base_t = datetime.strptime("08:00 AM", "%I:%M %p")
        
        for i in range(1, int(nh) + 1):
            with st.container(border=True):
                st.markdown(f"**Heat #{i}**")
                c1, c2, c3, c4 = st.columns(4)
                
                # ON/TAP Time
                on_t = c1.text_input(f"ON Time #{i}", (base_t + timedelta(minutes=120*(i-1))).strftime("%I:%M %p"), key=f"on_{i}")
                tap_t = c2.text_input(f"TAP Time #{i}", (base_t + timedelta(minutes=115*i)).strftime("%I:%M %p"), key=f"tp_{i}")
                
                don, dtp = pt(on_t), pt(tap_t, pt(on_t), True)
                dur_m = int((dtp - don).total_seconds() / 60) if don and dtp else 115
                dur_txt = f"{dur_m//60}h {dur_m%60}m"
                
                c3.markdown(f"**⏱️ Total Time:**\n\n{dur_txt}")
                ton = c4.number_input(f"Melt Ton #{i}", 1.0, 22.0, 16.5, 0.1, key=f"tn_{i}")
                
                x1, x2, x3 = st.columns(3)
                cond = x1.selectbox(f"Situation #{i}", list(COND_RULES.keys()), key=f"cd_{i}")
                l_kw = x2.number_input(f"Low Power KW", 0, 7500, 0, key=f"lkw_{i}")
                l_min = x3.number_input(f"Low Power Min", 0, 300, 0, key=f"lmin_{i}")
                
                hl.append({
                    "no": i, "on": on_t, "tap": tap_t, "dur": dur_txt, "m": dur_m, 
                    "ton": ton, "cond": cond, "lkw": l_kw, "lmin": l_min, "pfr": COND_RULES[cond]["pf"]
                })

        if st.button("🔥 GENERATE HEAT REPORT", type="primary", use_container_width=True):
            sk = t_kwh // 8
            k_scores = []
            for h in hl:
                # Weighted logic: Tons + Situation + Time + Low Power Adjust
                low_p_units = (h["lkw"] * h["lmin"]) / 60
                sc = (h["ton"] * COND_RULES[h["cond"]]["wt"]) + (low_p_units / 8)
                k_scores.append(sc)
            
            kw_s = [int(round((s / sum(k_scores)) * sk)) for s in k_scores]
            kw_s[-1] += (sk - sum(kw_s))
            
            v_sc = [kw_s[i] / random.uniform(*hl[i]["pfr"]) for i in range(len(hl))]
            kv_s = [int(round((v / sum(v_sc)) * (t_kvah//8))) for v in v_sc]
            kv_s[-1] += ((t_kvah//8) - sum(kv_s))
            
            rep_r = []
            copy_t = ""
            for i, h in enumerate(hl):
                k, v = kw_s[i]*8, max(kw_s[i]*8+8, kv_s[i]*8)
                pf, ut = round(k/v, 3), round(k/h["ton"], 1)
                
                rep_r.append({
                    "Heat": f"#{h['no']}", "ON": h['on'], "TAP": h['tap'], "Total Time": h['dur'], 
                    "Ton": h['ton'], "Situation": h['cond'], "kWh": k, "kVAh": v, "PF": f"{pf:.3f}"
                })
                
                copy_t += (
                    f"--- Heat #{h['no']} ---\n"
                    f"Heat ON Time     : {h['on']}\n"
                    f"Heat Taping Time : {h['tap']} ({h['dur']})\n"
                    f"Melting Ton      : {h['ton']} T\n"
                    f"Kwh units        : {k}\n"
                    f"Kvah units       : {v}\n"
                    f"Pf.              : {pf:.3f}\n\n"
                )
            
            st.success("✅ Heat Report Generated with Total Time")
            st.dataframe(pd.DataFrame(rep_r), use_container_width=True, hide_index=True)
            st.code(copy_t.strip(), language=None)
    else: st.warning("End Reading Start se badi honi chahiye!")

# ==========================================
# TAB 2: 15-MIN REGISTER (ADVANCED)
# ==========================================
with tab2:
    st.markdown("### 📋 15-Min Register Settings")
    rc1, rc2, rc3 = st.columns(3)
    ts4 = rc1.text_input("Start Time", "8:00 AM", key="reg_ts")
    te4 = rc2.text_input("End Time", "10:30 AM", key="reg_te")
    rs4 = gn(rc3.text_input("Start KVAH Reading", "249983498"))
    re4 = gn(rc3.text_input("End KVAH Reading", "250011382"))
    
    act_diff = re4 - rs4
    st.info(f"**Total Meter Difference:** `{act_diff:,}` Units")
    tp_times = st.text_input("Heat Tapping Times (comma)", "8:15 AM, 10:00 AM")

    with st.expander("🛠️ Set Furnace A and B KW Timeline", expanded=True):
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            st.subheader("Furnace A (A1/A2)")
            fa_id = st.selectbox("Active A-Line", ["A1", "A2"])
            fa_off = st.checkbox("Furnace A OFF/GLD?", key="a_off_check")
            fa_kw = st.number_input("A-Line KW (0 if OFF)", 0, 7500, 7000 if not fa_off else 0)
            fa_from = st.text_input("A Status From", "8:00 AM")
            fa_to = st.text_input("A Status To", "9:45 AM")
        with f_col2:
            st.subheader("Furnace B (B1/B2)")
            fb_id = st.selectbox("Active B-Line", ["B1", "B2"], index=1)
            fb_off = st.checkbox("Furnace B OFF/GLD?", key="b_off_check")
            fb_kw = st.number_input("B-Line KW (0 if OFF)", 0, 7500, 7000 if not fb_off else 0)
            fb_from = st.text_input("B Status From", "")
            fb_to = st.text_input("B Status To", "")

    if st.button("🚀 Generate Register", type="primary", use_container_width=True):
        ds, de = pt(ts4), pt(te4, pt(ts4), True)
        if ds and de and act_diff > 0:
            sl, cur = [], ds
            while cur < de:
                nx = min(cur + timedelta(minutes=15), de)
                sl.append({"s": cur, "e": nx, "fa": fa_id, "fakw": 7000, "fb": fb_id, "fbkw": 7000, "status": "Running"})
                cur = nx
            
            as_f, as_t = pt(fa_from, ds), pt(fa_to, ds)
            bs_f, bs_t = pt(fb_from, ds), pt(fb_to, ds)
            
            for s in sl:
                if as_f and as_t and s["s"] < as_t and s["e"] > as_f:
                    s["fa"] = "OFF" if fa_kw == 0 else f"{fa_id} (Low)"
                    s["fakw"] = fa_kw
                if bs_f and bs_t and s["s"] < bs_t and s["e"] > bs_f:
                    s["fb"] = "OFF" if fb_kw == 0 else f"{fb_id} (Low)"
                    s["fbkw"] = fb_kw
                for x in tp_times.split(","):
                    if (dt := pt(x, ds)) and s["s"] <= dt < s["e"]:
                        s["status"] = "Tapping"
                        s["fakw"] *= 0.75; s["fbkw"] *= 0.75

            weights = []
            for s in sl:
                total_p = s["fakw"] + s["fbkw"]
                weights.append(total_p * random.uniform(0.95, 1.05))
            
            final_units = [int(round((w/sum(weights))*act_diff)) for w in weights]
            final_units[-1] += (act_diff - sum(final_units))
            
            curr_r, rw = rs4, [{"Time": ds.strftime('%I:%M %p'), "Furnace A": fa_id, "Furnace B": fb_id, "KVAH": str(rs4), "Unit": "-"}]
            for i, s in enumerate(sl):
                curr_r += final_units[i]
                rw.append({
                    "Time": s["e"].strftime('%I:%M %p'), "Furnace A": s["fa"], "Furnace B": s["fb"],
                    "KVAH": str(int(curr_r)), "Unit": str(int(final_units[i]))
                })
            st.dataframe(pd.DataFrame(rw), use_container_width=True, hide_index=True)
        
