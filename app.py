import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

# Mobile Optimized View
st.set_page_config(page_title="16.5T Furnace Master V31", page_icon="⚡", layout="centered")
st.title("⚡ 16.5T Furnace Master Pro V31")

# Load Rules for Different Situations
LOAD_MAP = {
    "Normal": 5600,
    "OFF": 0,
    "Water Temp Trip": 0,
    "GLD / Low KW": 1200,
    "Capacitor Fault": 4000,
    "CCM Holding": 1500,
    "Panel Tripping": 2000
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

tab1, tab2 = st.tabs(["🔥 Heat-by-Heat", "📋 15-Min Register"])

# ==========================================
# TAB 1: HEAT-BY-HEAT (Classic + Multi-Problem)
# ==========================================
with tab1:
    st.markdown("### 1️⃣ Sequential Heat Readings")
    nh = st.number_input("Total heats in shift", 1, 15, 4)
    hl = []
    if 'h_reads' not in st.session_state: st.session_state.h_reads = {}
    
    total_kwh_sum, total_kvah_sum = 0, 0
    
    for i in range(1, int(nh) + 1):
        with st.container(border=True):
            st.subheader(f"🚩 Heat #{i}")
            def_skw = st.session_state.h_reads.get(f"ekw_{i-1}", "160944480" if i==1 else "0")
            def_skv = st.session_state.h_reads.get(f"ekv_{i-1}", "169767296" if i==1 else "0")
            
            c1, c2 = st.columns(2)
            skw = gn(c1.text_input(f"Start kWh #{i}", def_skw, key=f"skw_{i}"))
            skv = gn(c1.text_input(f"Start kVAh #{i}", def_skv, key=f"skv_{i}"))
            ekw = gn(c2.text_input(f"End kWh #{i}", "160983200", key=f"ekw_{i}"))
            ekv = gn(c2.text_input(f"End kVAh #{i}", "169807360", key=f"ekv_{i}"))
            
            st.session_state.h_reads[f"ekw_{i}"] = str(ekw)
            st.session_state.h_reads[f"ekv_{i}"] = str(ekv)
            
            hk, hv = ekw-skw, ekv-skv
            total_kwh_sum += hk; total_kvah_sum += hv
            
            t1, t2, t3 = st.columns(3)
            on_t = t1.text_input(f"ON Time #{i}", "08:00 AM", key=f"on_{i}")
            tap_t = t2.text_input(f"TAP Time #{i}", "10:00 AM", key=f"tp_{i}")
            ton = t3.number_input(f"Tons #{i}", 1.0, 25.0, 16.5, key=f"tn_{i}")
            
            # Problems during heat
            with st.expander(f"⚠️ Heat #{i} Tripping Logs"):
                p_type = st.selectbox(f"Problem Type #{i}", list(LOAD_MAP.keys()), key=f"hpt_{i}")
                p_time = st.text_input(f"Problem Times (e.g. 08:10-08:20)", "", key=f"hpm_{i}")

            hl.append({"no": i, "on": on_t, "tap": tap_t, "kwh": hk, "kvah": hv, "ton": ton, "prob": p_type if p_time else "Normal"})

    if total_kwh_sum > 0:
        pf_s = total_kwh_sum/total_kvah_sum if total_kvah_sum > 0 else 0
        st.info(f"📊 **TOTAL:** kWh: `{total_kwh_sum:,}` | kVAh: `{total_kvah_sum:,}` | PF: `{round(pf_s,3)}`")

    if st.button("🔥 GENERATE HEAT REPORT", use_container_width=True, type="primary"):
        rep_r = []
        for h in hl:
            pf = h['kwh']/h['kvah'] if h['kvah'] > 0 else 0
            rep_r.append({"Heat": f"#{h['no']}", "ON": h['on'], "TAP": h['tap'], "Ton": h['ton'], "kWh": h['kwh'], "PF": f"{min(pf, 0.998):.3f}", "Status": h['prob']})
        st.dataframe(pd.DataFrame(rep_r), use_container_width=True, hide_index=True)

# ==========================================
# TAB 2: REGISTER (MULTI-RANGE FIX)
# ==========================================
with tab2:
    st.markdown("### 📋 15-Min Organic Register")
    c_m1, c_m2 = st.columns(2)
    ts4, rs4 = c_m1.text_input("Shift Start Time", "10:00 PM"), gn(c_m1.text_input("Meter Start Reading", "250513582"))
    te4, re4 = c_m2.text_input("Shift End Time", "06:00 AM"), gn(c_m2.text_input("Meter End Reading", "250534412"))
    act_diff = re4 - rs4
    
    st.markdown(f"**Total Units to Distribute:** :blue[{act_diff:,}]")
    user_verify = gn(st.text_input("📊 Cross Match - Verify Total Units", str(act_diff)))
    
    ds = pt(ts4)
    de = pt(te4, ds, True) if ds else None

    def f_ui(label, key, base_time):
        with st.container(border=True):
            st.subheader(label)
            nkw = st.number_input("Normal Panel Load (KW)", 3000, 8000, 5600, key=f"nk_{key}")
            tap = st.text_input("🚰 Tapping Times (Range)", "", key=f"tp_{key}", placeholder="10:10-10:30, 02:00-02:20")
            
            st.write("🛑 **Problem Logs (Multi-Time)**")
            p_type = st.selectbox("Select Problem Type", list(LOAD_MAP.keys()), index=0, key=f"pt_{key}")
            p_time = st.text_input("Problem Time Ranges", "", key=f"pm_{key}", placeholder="10:00-10:15, 11:30-11:45")
            
            return {"nkw": nkw, "tap": tap, "p_type": p_type, "p_time": p_time}

    if ds and de:
        fa = f_ui("Furnace A", "a", ds)
        fb = f_ui("Furnace B", "b", ds)

        if st.button("🚀 GENERATE REGISTER", type="primary", use_container_width=True, disabled=(user_verify != act_diff)):
            sl = []
            cur = ds
            while cur < de:
                nx = min(cur + timedelta(minutes=15), de)
                sl.append({"s": cur, "e": nx, "fa_kw": fa["nkw"], "fa_lab": "Normal", "fb_kw": fb["nkw"], "fb_lab": "Normal"})
                cur = nx
            
            # Range Logic
            for s in sl:
                for f_data, side in [(fa, "a"), (fb, "b")]:
                    # Check Problem
                    for r_s, r_e in parse_ranges(f_data["p_time"], ds):
                        if s["s"] < r_e and s["e"] > r_s:
                            load = LOAD_MAP.get(f_data["p_type"], 1200)
                            if side == "a": s["fa_kw"], s["fa_lab"] = load, f_data["p_type"]
                            else: s["fb_kw"], s["fb_lab"] = load, f_data["p_type"]
                    # Check Tapping (Overrides problem if load is lower)
                    for r_s, r_e in parse_ranges(f_data["tap"], ds):
                        if s["s"] < r_e and s["e"] > r_s:
                            if side == "a": s["fa_kw"], s["fa_lab"] = 1500, "Tapping"
                            else: s["fb_kw"], s["fb_lab"] = 1500, "Tapping"

            wts = [(s["fa_kw"] + s["fb_kw"]) * random.uniform(0.93, 1.07) for s in sl]
            units = [int(round((w/sum(wts))*act_diff)) for w in wts]
            
            # Cap Logic (Safety 3476)
            for _ in range(10):
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
            st.success("✅ Register Cross-Matched and Generated!")
