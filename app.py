import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

# Layout centered for Mobile
st.set_page_config(page_title="16.5T Furnace Master V24", page_icon="⚡", layout="centered")
st.title("⚡ 16.5T Furnace Master Pro")

# MEMORY FOR SEQUENTIAL READINGS
if 'h_reads' not in st.session_state: st.session_state.h_reads = {}

# SITUATION RULES
COND_RULES = {
    "Normal Running": {"pf": (0.980, 0.998), "wt": 1.00},
    "Sintering (Lining Heat)": {"pf": (0.800, 0.880), "wt": 1.30}, 
    "GLD / Low KW Running": {"pf": (0.840, 0.890), "wt": 1.15}, 
    "Capacitor Bank Fault": {"pf": (0.750, 0.820), "wt": 1.10},
    "Panel / SCR Tripping": {"pf": (0.820, 0.880), "wt": 1.12},
    "CCM Holding / Casting": {"pf": (0.800, 0.850), "wt": 1.10},  
}

def pt(s, b=None, next_day_check=False):
    if not s: return None
    s = str(s).strip().lower().replace(".", ":").replace(" ", "")
    if "am" in s: s = s.replace("am", " am")
    if "pm" in s: s = s.replace("pm", " pm")
    formats = ["%I:%M %p", "%I:%M%p", "%H:%M", "%I %p"]
    for f in formats:
        try:
            d = datetime.strptime(s.strip(), f)
            now = datetime.now()
            base_date = b if b else now
            d = d.replace(year=base_date.year, month=base_date.month, day=base_date.day)
            if next_day_check and b and d < b: d += timedelta(days=1)
            return d
        except: pass
    return None

def gn(v):
    d = "".join(c for c in str(v) if c.isdigit())
    return int(d) if d else 0

tab1, tab2 = st.tabs(["🔥 Heat-by-Heat", "📋 15-Min Register"])

# ==========================================
# TAB 1: HEAT-BY-HEAT (EVERYTHING RESTORED)
# ==========================================
with tab1:
    st.markdown("### 1️⃣ Sequential Heat Readings")
    nh = st.number_input("Total heats in shift", 1, 20, 4)
    
    hl = [] # List initialized
    total_kwh_sum = 0
    total_kvah_sum = 0
    base_t = datetime.strptime("08:00 AM", "%I:%M %p")
    
    for i in range(1, int(nh) + 1):
        with st.container(border=True):
            st.markdown(f"🚩 **Heat #{i}**")
            
            # --- READING AUTO-FLOW ---
            def_skw = "160944480" if i == 1 else st.session_state.h_reads.get(f"ekw_{i-1}", "0")
            def_skv = "169767296" if i == 1 else st.session_state.h_reads.get(f"ekv_{i-1}", "0")
            
            c1, c2 = st.columns(2)
            skw = gn(c1.text_input(f"Start kWh #{i}", def_skw, key=f"skw_{i}"))
            skv = gn(c1.text_input(f"Start kVAh #{i}", def_skv, key=f"skv_{i}"))
            ekw = gn(c2.text_input(f"End kWh #{i}", "160983200", key=f"ekw_{i}"))
            ekv = gn(c2.text_input(f"End kVAh #{i}", "169807360", key=f"ekv_{i}"))
            
            # Save readings to memory
            st.session_state.h_reads[f"ekw_{i}"] = str(ekw)
            st.session_state.h_reads[f"ekv_{i}"] = str(ekv)
            
            hkwh = ekw - skw
            hkvah = ekv - skv
            total_kwh_sum += hkwh
            total_kvah_sum += hkvah
            
            # --- TIME & TONNAGE ---
            t1, t2, t3 = st.columns(3)
            on_t = t1.text_input(f"ON Time #{i}", (base_t + timedelta(minutes=120*(i-1))).strftime("%I:%M %p"), key=f"ont_{i}")
            tap_t = t2.text_input(f"TAP Time #{i}", (base_t + timedelta(minutes=115*i)).strftime("%I:%M %p"), key=f"tpt_{i}")
            ton = t3.number_input(f"Tons #{i}", 1.0, 25.0, 16.5, key=f"ton_{i}")
            
            don, dtp = pt(on_t), pt(tap_t, pt(on_t), True)
            dm = int((dtp-don).total_seconds()/60) if don and dtp else 0

            # --- RESTORED OPTIONS (Situation & OFF) ---
            st.markdown("---")
            cx1, cx2 = st.columns(2)
            is_off = cx1.checkbox(f"Furnace OFF in H#{i}?", key=f"hoff_{i}")
            off_m = 0
            if is_off:
                c_o1, c_o2 = st.columns(2)
                off_f = pt(c_o1.text_input(f"OFF From #{i}", "", key=f"of_{i}"), don)
                off_t = pt(c_o2.text_input(f"OFF To #{i}", "", key=f"ot_{i}"), off_f, True)
                off_m = int((off_t-off_f).total_seconds()/60) if off_f and off_t else 0

            cond = cx2.selectbox(f"Heat #{i} Situation", list(COND_RULES.keys()), key=f"hcd_{i}")
            
            with st.expander(f"⚙️ Low Power KW (if GLD/Hold)"):
                lx1, lx2 = st.columns(2)
                lkw = lx1.number_input(f"Low Load KW", 0, 7500, 1000 if "GLD" in cond else 0, key=f"hlk_{i}")
                lmin = lx2.number_input(f"Duration (min)", 0, 300, key=f"hlm_{i}")

            hl.append({
                "no": i, "on": on_t, "tap": tap_t, "kwh": hkwh, "kvah": hkvah, 
                "ton": ton, "dur": f"{dm//60}h {dm%60}m", "cond": cond, 
                "lkw": lkw, "lmin": lmin, "off_m": off_m
            })

    if total_kwh_sum > 0:
        pf_shift = total_kwh_sum/total_kvah_sum if total_kvah_sum > 0 else 0
        st.info(f"📊 **TOTAL SHIFT reading:** kWh: `{total_kwh_sum:,}` | kVAh: `{total_kvah_sum:,}` | PF: `{round(pf_shift,3)}`")

    if st.button("🔥 GENERATE HEAT REPORT", type="primary", use_container_width=True):
        rep_r = []
        copy_t = "⚡ *Furnace Heat Report*\n" + "-"*25 + "\n"
        for h in hl:
            hpf = h['kwh']/h['kvah'] if h['kvah'] > 0 else 0
            if hpf > 0.998: hpf = 0.998
            
            rep_r.append({
                "Heat": f"#{h['no']}", "TAP": h['tap'], "Time": h['dur'], 
                "Ton": h['ton'], "kWh": h['kwh'], "PF": f"{hpf:.3f}", "Status": h['cond']
            })
            copy_t += f"Heat #{h['no']} | Tap: {h['tap']} | {h['kwh']} U | {h['ton']} T | PF {hpf:.3f} | {h['cond']}\n"
        
        st.dataframe(pd.DataFrame(rep_r), use_container_width=True, hide_index=True)
        st.code(copy_t, language=None)

# ==========================================
# TAB 2: REGISTER (ALL FEATURES PRESERVED)
# ==========================================
with tab2:
    st.markdown("### 📋 15-Min Register Control")
    c_m1, c_m2 = st.columns(2)
    ts4 = c_m1.text_input("Meter Start Time", "10:00 PM")
    rs4 = gn(c_m1.text_input("Start Reading (kVAh)", "250513582"))
    te4 = c_m2.text_input("Meter End Time", "12:15 AM")
    re4 = gn(c_m2.text_input("End Reading (kVAh)", "250534412"))
    
    act_diff = re4 - rs4
    st.markdown(f"**Total Units to Distribute:** :blue[{act_diff:,}]")
    
    # CROSS MATCH
    user_verify = gn(st.text_input("📊 Verify Expected Total Units", str(act_diff)))
    
    match_ready = True if user_verify == act_diff else False
    if not match_ready: st.error("❌ Total mismatch with reading difference!")
    else: st.success("✅ Difference Matched!")

    ds = pt(ts4)
    de = pt(te4, ds, True)

    def f_ui(f_name, f_key):
        with st.container(border=True):
            st.subheader(f_name)
            fid = st.selectbox("Line ID", ["A1", "A2"] if "A" in f_name else ["B1", "B2"], key=f"id_{f_key}")
            nkw = st.number_input("Normal Load KW", 3000, 8000, 5600, key=f"nk_{f_key}")
            
            st.markdown("🚰 **Tapping Range**")
            tx1, tx2 = st.columns(2)
            tf, tt = tx1.text_input("Start", "", key=f"tf_{f_key}"), tx2.text_input("End", "", key=f"tt_{f_key}")
            
            is_off = st.checkbox("Furnace OFF?", key=f"off_chk_{f_key}")
            of, ot = "", ""
            if is_off:
                ox1, ox2 = st.columns(2)
                of, ot = ox1.text_input("OFF From", "", key=f"of_{f_key}"), ox2.text_input("OFF To", "", key=f"ot_{f_key}")
            
            return {"id": fid, "nkw": nkw, "tap": (tf, tt), "off": (of, ot)}

    if ds:
        fa = f_ui("Furnace A", "a")
        fb = f_ui("Furnace B", "b")

        if st.button("🚀 GENERATE REGISTER", type="primary", disabled=not match_ready):
            sl = []
            cur = ds
            while cur < de:
                nx = min(cur + timedelta(minutes=15), de)
                sl.append({"s": cur, "e": nx, "fa": fa["id"], "fakw": fa["nkw"], "fb": fb["id"], "fbkw": fb["nkw"]})
                cur = nx
            
            for s in sl:
                for f_data, f_side in [(fa, "a"), (fb, "b")]:
                    # Priority 1: OFF
                    of, ot = f_data["off"]
                    if of:
                        d_of, d_ot = pt(of, ds, True), pt(ot, pt(of, ds, True), True)
                        if d_of and d_ot and s["s"] < d_ot and s["e"] > d_of:
                            if f_side == "a": s["fa"], s["fakw"] = "OFF", 0
                            else: s["fb"], s["fbkw"] = "OFF", 0
                    
                    # Priority 2: Tapping (Holding 1500 KW)
                    tf, tt = f_data["tap"]
                    if tf:
                        d_tf, d_tt = pt(tf, ds, True), pt(tt, pt(tf, ds, True), True)
                        if d_tf and d_tt and s["s"] < d_tt and s["e"] > d_tf:
                            if f_side == "a" and s["fakw"] > 0: s["fakw"] = 1500; s["fa"] += "(Tap)"
                            if f_side == "b" and s["fbkw"] > 0: s["fbkw"] = 1500; s["fb"] += "(Tap)"

            wts = [(s["fakw"] + s["fbkw"]) * random.uniform(0.94, 1.06) for s in sl]
            units = [int(round((w/sum(wts))*act_diff)) for w in wts]
            units[-1] += (act_diff - sum(units))
            
            curr_r, rw = rs4, []
            for i, s in enumerate(sl):
                curr_r += units[i]
                t_str = s["e"].strftime('%I:%M %p')
                rw.append({"Time": t_str, "A": s["fa"], "B": s["fb"], "kVAh": int(curr_r), "Unit": units[i]})
            
            st.dataframe(pd.DataFrame(rw), use_container_width=True, hide_index=True)
            st.success("✅ Register Done!")
            
