import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

# Layout centered for Mobile
st.set_page_config(page_title="16.5T Furnace Master V23", page_icon="⚡", layout="centered")
st.title("⚡ 16.5T Furnace Advanced Control")

# memory across reruns
if 'h_reads' not in st.session_state: st.session_state.h_reads = {}

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
# TAB 1: HEAT-BY-HEAT (AUTO-FLOW)
# ==========================================
with tab1:
    st.markdown("### 1️⃣ Sequential Heat Readings")
    nh = st.number_input("Total Heats", 1, 20, 4)
    
    hl = []
    total_kwh_sum = 0
    total_kvah_sum = 0
    
    base_t = datetime.strptime("08:00 AM", "%I:%M %p")
    
    for i in range(1, int(nh) + 1):
        with st.container(border=True):
            st.markdown(f"**Heat #{i}**")
            
            # --- AUTO-FLOW LOGIC ---
            # If Heat 2, Start = End of Heat 1
            def_start_kwh = "160944480" if i == 1 else st.session_state.h_reads.get(f"ekw_{i-1}", "0")
            def_start_kvah = "169767296" if i == 1 else st.session_state.h_reads.get(f"ekv_{i-1}", "0")
            
            c1, c2 = st.columns(2)
            skw = gn(c1.text_input(f"Start kWh #{i}", def_start_kwh, key=f"skw_{i}"))
            skv = gn(c1.text_input(f"Start kVAh #{i}", def_start_kvah, key=f"skv_{i}"))
            
            ekw = gn(c2.text_input(f"End kWh #{i}", "160983200", key=f"ekw_{i}"))
            ekv = gn(c2.text_input(f"End kVAh #{i}", "169807360", key=f"ekv_{i}"))
            
            # Save for next heat
            st.session_state.h_reads[f"ekw_{i}"] = str(ekw)
            st.session_state.h_reads[f"ekv_{i}"] = str(ekv)
            
            hkwh = ekw - skw
            hkvah = ekv - skv
            total_kwh_sum += hkwh
            total_kvah_sum += hkvah
            
            t1, t2, t3 = st.columns(3)
            on_t = t1.text_input(f"ON Time #{i}", (base_t + timedelta(minutes=120*(i-1))).strftime("%I:%M %p"), key=f"ont_{i}")
            tap_t = t2.text_input(f"TAP Time #{i}", (base_t + timedelta(minutes=115*i)).strftime("%I:%M %p"), key=f"tpt_{i}")
            ton = t3.number_input(f"Tons #{i}", 1.0, 25.0, 16.5, key=f"ton_{i}")
            
            don, dtp = pt(on_t), pt(tap_t, pt(on_t), True)
            dm = int((dtp-don).total_seconds()/60) if don and dtp else 0
            
            if hkwh > 0:
                hpf = hkwh/hkvah if hkvah > 0 else 0
                st.caption(f"✅ Units: {hkwh:,} | PF: {round(hpf,3)} | Time: {dm//60}h {dm%60}m")
            
            hl.append({"no": i, "on": on_t, "tap": tap_t, "kwh": hkwh, "kvah": hkvah, "ton": ton, "dur": f"{dm//60}h {dm%60}m"})

    if total_kwh_sum > 0:
        st.info(f"📊 **TOTAL SHIFT:** kWh: `{total_kwh_sum:,}` | kVAh: `{total_kvah_sum:,}` | PF: `{round(total_kwh_sum/total_kvah_sum,3)}`")

    if st.button("🔥 GENERATE CONSOLIDATED REPORT", type="primary", use_container_width=True):
        rep_r = []
        copy_t = "⚡ *Heat Report*\n" + "-"*20 + "\n"
        for h in hl:
            pf = h['kwh']/h['kvah'] if h['kvah'] > 0 else 0
            rep_r.append({
                "Heat": f"#{h['no']}", "ON": h['on'], "TAP": h['tap'], "Time": h['dur'], 
                "Ton": h['ton'], "kWh": h['kwh'], "PF": f"{pf:.3f}"
            })
            copy_t += f"Heat #{h['no']} | {h['tap']} | {h['kwh']} U | {h['ton']} T | PF {pf:.3f}\n"
        
        st.dataframe(pd.DataFrame(rep_r), use_container_width=True, hide_index=True)
        st.code(copy_t, language=None)

# ==========================================
# TAB 2: REGISTER (CROSS-MATCH CHECK)
# ==========================================
with tab2:
    st.markdown("### 📋 Register & Meter Verification")
    
    c_m1, c_m2 = st.columns(2)
    ts4 = c_m1.text_input("Meter Start Time", "10:00 PM")
    rs4 = gn(c_m1.text_input("Start Reading (kVAh)", "250513582"))
    te4 = c_m2.text_input("Meter End Time", "12:15 AM")
    re4 = gn(c_m2.text_input("End Reading (kVAh)", "250534412"))
    
    act_diff = re4 - rs4
    st.markdown(f"**Difference to Distribute:** :blue[{act_diff:,}]")
    
    # CROSS MATCH FEATURE
    user_verify = gn(st.text_input("📊 Verify Expected Total Units (Cross Match)", str(act_diff)))
    
    if user_verify != act_diff:
        st.error(f"❌ Mismatch! Meter Diff is {act_diff}, but you entered {user_verify}. Please check readings.")
        match_ready = False
    else:
        st.success("✅ Meter Difference Matched!")
        match_ready = True

    ds = pt(ts4)
    de = pt(te4, ds, True) if ds else None

    def f_ui(f_name, f_key, base_time):
        with st.container(border=True):
            st.subheader(f_name)
            fid = st.selectbox("Line ID", ["A1", "A2"] if "A" in f_name else ["B1", "B2"], key=f"id_{f_key}")
            nkw = st.number_input("Normal KW", 3000, 8000, 5600, key=f"nk_{f_key}")
            
            st.markdown("🚰 **Tapping Period**")
            c_t1, c_t2 = st.columns(2)
            tf, tt = c_t1.text_input("Start", "", key=f"tf_{f_key}"), c_t2.text_input("End", "", key=f"tt_{f_key}")
            
            is_off = st.checkbox("Furnace OFF?", key=f"off_chk_{f_key}")
            of, ot = "", ""
            if is_off:
                c_o1, c_o2 = st.columns(2)
                of, ot = c_o1.text_input("OFF From", "", key=f"of_{f_key}"), c_o2.text_input("OFF To", "", key=f"ot_{f_key}")
            
            return {"id": fid, "nkw": nkw, "tap": (tf, tt), "off": (of, ot)}

    if ds:
        fa = f_ui("Furnace A", "a", ds)
        fb = f_ui("Furnace B", "b", ds)

        if st.button("🚀 GENERATE 15-MIN REGISTER", type="primary", disabled=not match_ready):
            sl = []
            cur = ds
            while cur < de:
                nx = min(cur + timedelta(minutes=15), de)
                sl.append({"s": cur, "e": nx, "fa": fa["id"], "fakw": fa["nkw"], "fb": fb["id"], "fbkw": fb["nkw"], "st": "Normal"})
                cur = nx
            
            for s in sl:
                for f_data, f_side in [(fa, "a"), (fb, "b")]:
                    # 1. Check OFF
                    of, ot = f_data["off"]
                    if of:
                        d_of, d_ot = pt(of, ds, True), pt(ot, pt(of, ds, True), True)
                        if d_of and d_ot and s["s"] < d_ot and s["e"] > d_of:
                            if f_side == "a": s["fa"], s["fakw"] = "OFF", 0
                            else: s["fb"], s["fbkw"] = "OFF", 0
                    
                    # 2. Check Tap
                    tf, tt = f_data["tap"]
                    if tf:
                        d_tf, d_tt = pt(tf, ds, True), pt(tt, pt(tf, ds, True), True)
                        if d_tf and d_tt and s["s"] < d_tt and s["e"] > d_tf:
                            if f_side == "a" and s["fakw"] > 0: s["fakw"] = 1500; s["fa"] += "(Tap)"
                            if f_side == "b" and s["fbkw"] > 0: s["fbkw"] = 1500; s["fb"] += "(Tap)"

            wts = [(s["fakw"] + s["fbkw"]) * random.uniform(0.92, 1.08) for s in sl]
            units = [int(round((w/sum(wts))*act_diff)) for w in wts]
            units[-1] += (act_diff - sum(units))
            
            curr_r, rw = rs4, []
            copy_reg = f"⚡ *Register* ({ts4}-{te4})\nTime | A | B | Units\n" + "-"*20 + "\n"
            for i, s in enumerate(sl):
                curr_r += units[i]
                t_str = s["e"].strftime('%I:%M %p')
                rw.append({"Time": t_str, "A": s["fa"], "B": s["fb"], "kVAh": int(curr_r), "Unit": units[i]})
                copy_reg += f"{t_str} | {s['fa']} | {s['fb']} | {units[i]}\n"
            
            st.dataframe(pd.DataFrame(rw), use_container_width=True, hide_index=True)
            st.code(copy_reg, language=None)
            st.success(f"Register Generated! Sum: {sum(units):,}")
                
