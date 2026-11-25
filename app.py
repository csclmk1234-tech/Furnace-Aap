import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

# Mobile Optimized
st.set_page_config(page_title="16.5T Furnace V33", page_icon="⚡", layout="centered")
st.title("⚡ 16.5T Furnace Master Pro V33")

# Situation Load/Weight Rules
LOAD_MAP = {
    "Normal": {"kw": 5600, "wt": 1.0},
    "OFF": {"kw": 0, "wt": 0.0},
    "Water Temp Trip": {"kw": 0, "wt": 0.2},
    "GLD / Low KW": {"kw": 1200, "wt": 0.4},
    "Capacitor Fault": {"kw": 4000, "wt": 0.8},
    "CCM Holding": {"kw": 1500, "wt": 0.5},
    "Panel Tripping": {"kw": 2000, "wt": 0.6}
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

def parse_ranges(input_str, base_time):
    ranges = []
    if not input_str: return ranges
    segments = input_str.split(",")
    for seg in segments:
        if "-" in seg:
            try:
                start_s, end_s = seg.split("-")
                t_start = pt(start_s.strip(), base_time, True)
                t_end = pt(end_s.strip(), t_start, True)
                if t_start and t_end: ranges.append((t_start, t_end))
            except: pass
    return ranges

def gn(v):
    d = "".join(c for c in str(v) if c.isdigit())
    return int(d) if d else 0

tab1, tab2 = st.tabs(["🔥 Classic Heat Report", "📋 15-Min Register"])

# ==========================================
# TAB 1: HEAT-BY-HEAT (CLASSIC LOGIC FIXED)
# ==========================================
with tab1:
    st.markdown("### 1️⃣ Shift Meter Readings")
    r1, r2 = st.columns(2)
    skw = gn(r1.text_input("Shift Start kWh", "160944480"))
    skv = gn(r1.text_input("Shift Start kVAh", "169767296"))
    ekw = gn(r2.text_input("Shift End kWh", "160983200"))
    ekv = gn(r2.text_input("Shift End kVAh", "169807360"))
    
    t_kwh, t_kvah = ekw - skw, ekv - skv
    
    if t_kwh > 0:
        pf_avg = t_kwh/t_kvah if t_kvah > 0 else 0
        st.info(f"📊 **TOTAL SHIFT:** kWh: `{t_kwh:,}` | kVAh: `{t_kvah:,}` | PF: `{round(pf_avg,3)}`")
        
        nh = st.number_input("Total Heats in Shift", 1, 20, 4)
        hl = []
        bt = pt("08:00 AM")
        
        for i in range(1, int(nh) + 1):
            with st.container(border=True):
                st.markdown(f"🚩 **Heat #{i}**")
                c1, c2, c3 = st.columns(3)
                on_t = c1.text_input(f"ON Time", "08:00 AM", key=f"hon_{i}")
                tp_t = c2.text_input(f"TAP Time", "10:00 AM", key=f"htp_{i}")
                ton = c3.number_input(f"Melt Tons", 1.0, 25.0, 16.5, key=f"htn_{i}")
                
                don = pt(on_t, bt)
                dtp = pt(tp_t, don, True)
                dm = int((dtp-don).total_seconds()/60) if don and dtp else 115
                
                with st.expander(f"⚠️ Tripping/Problems for Heat #{i}"):
                    p_type = st.selectbox("Situation", list(LOAD_MAP.keys()), key=f"hcd_{i}")
                    p_time = st.text_input("Problem Ranges (e.g. 08:10-08:20)", "", key=f"hpm_{i}")
                    p_ranges = parse_ranges(p_time, don)
                    p_min = sum([(r[1]-r[0]).total_seconds()/60 for r in p_ranges])
                
                # FIXED: tap_t was NameError, changed to tp_t
                hl.append({
                    "no": i, "on": on_t, "tap": tp_t, "dm": dm, "ton": ton, 
                    "cond": p_type, "p_min": p_min, "p_time": p_time
                })

        if st.button("🔥 GENERATE 8-FACTOR REPORT", type="primary", use_container_width=True):
            k_scores = []
            for h in hl:
                base_score = (h["ton"] * 10) + (h["dm"] * 0.5)
                if h["p_min"] > 0:
                    base_score *= LOAD_MAP[h["cond"]]["wt"]
                k_scores.append(base_score)
            
            total_steps = t_kwh // 8
            steps_per_heat = [int(round((s / sum(k_scores)) * total_steps)) for s in k_scores]
            steps_per_heat[-1] += (total_steps - sum(steps_per_heat))
            
            rep_data = []
            copy_txt = f"⚡ *Heat Report* (Total: {t_kwh} U)\n" + "-"*25 + "\n"
            
            for i, h in enumerate(hl):
                hk = steps_per_heat[i] * 8
                hv = int(hk / random.uniform(0.985, 0.998))
                pf = hk/hv
                
                rep_data.append({
                    "Heat": f"#{h['no']}", "ON": h['on'], "TAP": h['tap'], 
                    "Ton": h['ton'], "kWh": hk, "PF": f"{pf:.3f}", "Status": h['cond'] if h['p_min']>0 else "Normal"
                })
                copy_txt += f"H#{h['no']} | {h['ton']}T | {hk} U | PF {pf:.3f} | {h['cond'] if h['p_min']>0 else ''}\n"
            
            st.dataframe(pd.DataFrame(rep_data), use_container_width=True, hide_index=True)
            st.code(copy_txt, language=None)
            st.success(f"Units distributed in multiples of 8. Total: {sum(steps_per_heat)*8}")

# ==========================================
# TAB 2: REGISTER (STABLE)
# ==========================================
with tab2:
    st.markdown("### 📋 15-Min Organic Register")
    c_m1, c_m2 = st.columns(2)
    ts4, rs4 = c_m1.text_input("Reading Start Time", "10:00 PM"), gn(c_m1.text_input("Start kVAh", "250513582"))
    te4, re4 = c_m2.text_input("Reading End Time", "06:00 AM"), gn(c_m2.text_input("End kVAh", "250534412"))
    act_diff = re4 - rs4
    
    st.markdown(f"**Units to Distribute:** :blue[{act_diff:,}]")
    user_verify = gn(st.text_input("📊 Verify Total Units (Cross Match)", str(act_diff)))
    
    ds = pt(ts4)
    de = pt(te4, ds, True) if ds else None

    def f_ui(label, key):
        with st.container(border=True):
            st.subheader(label)
            nkw = st.number_input("Normal Running KW", 3000, 8000, 5600, key=f"reg_nk_{key}")
            tap = st.text_input("🚰 Tapping Ranges", "", key=f"reg_tp_{key}", placeholder="10:10-10:30")
            p_type = st.selectbox("Problem Type", list(LOAD_MAP.keys()), key=f"reg_pt_{key}")
            p_time = st.text_input("Problem Ranges", "", key=f"reg_pm_{key}", placeholder="10:00-10:15")
            return {"nkw": nkw, "tap": tap, "p_type": p_type, "p_time": p_time}

    if ds and de:
        fa = f_ui("Furnace A", "a")
        fb = f_ui("Furnace B", "b")

        if st.button("🚀 GENERATE REGISTER", type="primary", use_container_width=True, disabled=(user_verify != act_diff)):
            sl = []
            cur = ds
            while cur < de:
                nx = min(cur + timedelta(minutes=15), de)
                sl.append({"s": cur, "e": nx, "fa_kw": fa["nkw"], "fa_lab": "Normal", "fb_kw": fb["nkw"], "fb_lab": "Normal"})
                cur = nx
            
            for s in sl:
                for f_data, side in [(fa, "a"), (fb, "b")]:
                    for r_s, r_e in parse_ranges(f_data["p_time"], ds):
                        if s["s"] < r_e and s["e"] > r_s:
                            load = LOAD_MAP[f_data["p_type"]]["kw"]
                            if side == "a": s["fa_kw"], s["fa_lab"] = load, f_data["p_type"]
                            else: s["fb_kw"], s["fb_lab"] = load, f_data["p_type"]
                    for r_s, r_e in parse_ranges(f_data["tap"], ds):
                        if s["s"] < r_e and s["e"] > r_s:
                            if side == "a": s["fa_kw"], s["fa_lab"] = 1500, "Tapping"
                            else: s["fb_kw"], s["fb_lab"] = 1500, "Tapping"

            wts = [(s["fa_kw"] + s["fb_kw"]) * random.uniform(0.93, 1.07) for s in sl]
            units = [int(round((w/sum(wts))*act_diff)) for w in wts]
            
            for _ in range(5):
                ex = 0
                for i in range(len(units)):
                    if units[i] > 3476: ex += (units[i] - 3476); units[i] = 3476
                if ex == 0: break
                targets = [i for i, x in enumerate(sl) if units[i] < 3476 and (x["fa_kw"]+x["fb_kw"]) > 4000]
                if targets:
                    add = ex // len(targets)
                    for idx in targets: units[idx] += add
            
            units[-1] += (act_diff - sum(units))
            curr_r, rw = rs4, []
            for i, s in enumerate(sl):
                curr_r += units[i]
                rw.append({"Time": s["e"].strftime('%I:%M %p'), "A": s["fa_lab"], "B": s["fb_lab"], "kVAh": int(curr_r), "Unit": units[i]})
            
            st.dataframe(pd.DataFrame(rw), use_container_width=True, hide_index=True)
            st.success("✅ Register Generated Successfully!")
                
