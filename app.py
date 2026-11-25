import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

# Mobile Optimized
st.set_page_config(page_title="16.5T Furnace V41", page_icon="⚡", layout="centered")
st.title("⚡ 16.5T Furnace Master Pro V41")

# Load Rules
LOAD_RULES = {
    "Normal": 1.0, "OFF": 0.0, "Water Temp Trip": 0.1,
    "GLD / Low KW": 0.4, "Capacitor Bank Fault": 0.8,
    "CCM Holding": 0.5, "Panel / SCR Tripping": 0.6
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

tab1, tab2 = st.tabs(["🔥 8-Factor Heat Report", "📋 15-Min Register"])

# ==========================================
# TAB 1: HEAT-BY-HEAT (TRUE 8-FACTOR)
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
        st.info(f"📊 **TOTAL:** kWh: `{t_kwh:,}` | kVAh: `{t_kvah:,}` | PF: `{round(t_kwh/t_kvah,3) if t_kvah>0 else 0}`")
        nh = st.number_input("Total Heats in Shift", 1, 20, 4)
        hl = []
        bt = pt("08:00 AM")
        for i in range(1, int(nh) + 1):
            with st.container(border=True):
                st.subheader(f"🚩 Heat #{i}")
                c1, c2, c3 = st.columns(3)
                on_t = c1.text_input(f"ON Time", "08:00 AM", key=f"hon_{i}")
                tp_t = c2.text_input(f"TAP Time", "10:00 AM", key=f"htp_{i}")
                ton = c3.number_input(f"Melt Tons", 1.0, 25.0, 16.5, key=f"htn_{i}")
                don = pt(on_t, bt)
                dtp = pt(tp_t, don, True)
                dm = int((dtp-don).total_seconds()/60) if don and dtp else 115
                is_off = st.checkbox(f"Furnace OFF in H#{i}?", key=f"chk_off_{i}")
                off_min = 0
                if is_off:
                    o1, o2 = st.columns(2)
                    off_f = pt(o1.text_input("OFF From", "", key=f"of_{i}"), don)
                    off_t = pt(o2.text_input("OFF To", "", key=f"ot_{i}"), off_f, True)
                    off_min = int((off_t - off_f).total_seconds()/60) if off_f and off_t else 0
                with st.expander(f"⚠️ Tripping/Problems (H#{i})"):
                    p1_t = st.selectbox("Problem Type", list(LOAD_RULES.keys()), key=f"p1t_{i}")
                    p1_m = st.text_input("Ranges (e.g. 08:10-08:20)", "", key=f"p1m_{i}")
                    p1_min = sum([(r[1]-r[0]).total_seconds()/60 for r in parse_ranges(p1_m, don)])
                hl.append({"no": i, "on": on_t, "tap": tp_t, "dm": dm, "ton": ton, "off_min": off_min, "p1_min": p1_min, "p1_type": p1_t})

        if st.button("🔥 GENERATE 8-FACTOR REPORT", type="primary", use_container_width=True):
            # 1. Weights with Jitter
            k_scores = []
            for h in hl:
                score = ((h["ton"] * 12) + (h["dm"] * 0.6)) * random.uniform(0.92, 1.08)
                if h["off_min"] > 0: score *= 0.05
                if h["p1_min"] > 0: score *= LOAD_RULES[h["p1_type"]]
                k_scores.append(max(score, 1.0))
            
            # 2. STRICT 8-FACTOR STEP DISTRIBUTION
            total_steps = t_kwh // 8
            steps_per_heat = [int((s / sum(k_scores)) * total_steps) for s in k_scores]
            
            # Balance missing steps randomly
            missing = total_steps - sum(steps_per_heat)
            for _ in range(missing):
                steps_per_heat[random.randint(0, len(steps_per_heat)-1)] += 1
            
            copy_txt, rep_table = "", []
            for i, h in enumerate(hl):
                hk = steps_per_heat[i] * 8
                # Last heat takes the small remainder from meter (0-7 units)
                if i == len(hl) - 1: hk += (t_kwh % 8)
                
                hv = int(hk / random.uniform(0.985, 0.998))
                pf = round(hk/hv, 3)
                dur = f"{h['dm']//60}h {h['dm']%60}m"
                
                rep_table.append({"Heat": f"#{h['no']}", "kWh": hk, "kVAh": hv, "PF": f"{pf:.3f}"})
                copy_txt += (f"--- Heat #{h['no']} ---\nHeat ON Time     : {h['on']}\nHeat Taping Time : {h['tap']}\nTotal Time       : {dur}\nMelting Ton      : {h['ton']} T\nKwh units        : {hk}\nKvah units       : {hv}\nPf.              : {pf:.3f}\n\n")
            
            st.success("✅ 8-Factor Distribution Applied with Organic Variation!")
            st.dataframe(pd.DataFrame(rep_table), use_container_width=True, hide_index=True)
            st.code(copy_txt.strip(), language=None)

# ==========================================
# TAB 2: REGISTER
# ==========================================
with tab2:
    st.markdown("### 📋 15-Min Advanced Register")
    c_m1, c_m2 = st.columns(2)
    ts4, rs4 = c_m1.text_input("Start Time", "10:00 PM"), gn(c_m1.text_input("Start kVAh", "250513582"))
    te4, re4 = c_m2.text_input("End Time", "06:00 AM"), gn(c_m2.text_input("End kVAh", "250534412"))
    act_diff = re4 - rs4
    st.markdown(f"**Total Units:** :blue[{act_diff:,}]")
    user_verify = gn(st.text_input("📊 Verify Total Units", str(act_diff)))
    ds, de = pt(ts4), pt(te4, pt(ts4), True)
    
    def f_ui(label, key):
        with st.container(border=True):
            st.subheader(label)
            nkw = st.number_input("Normal Load KW", 3000, 8000, 5600, key=f"reg_nk_{key}")
            tap = st.text_input("🚰 Tapping Range(s)", "", key=f"reg_tp_{key}", placeholder="10:10-10:30")
            p_t = st.selectbox("Select Problem", ["None", "OFF", "Water Temp Trip", "GLD", "CCM Holding"], key=f"reg_pt_{key}")
            p_m = st.text_input("Problem Range(s)", "", key=f"reg_pm_{key}")
            return {"nkw": nkw, "tap": tap, "p_type": p_t, "p_time": p_m}

    if ds and de:
        fa, fb = f_ui("Furnace A", "a"), f_ui("Furnace B", "b")
        if st.button("🚀 GENERATE REGISTER", type="primary", use_container_width=True, disabled=(user_verify != act_diff)):
            sl, cur = [], ds
            while cur < de:
                nx = min(cur + timedelta(minutes=15), de)
                sl.append({"s": cur, "e": nx, "fa_kw": fa["nkw"], "fa_lab": "Normal", "fb_kw": fb["nkw"], "fb_lab": "Normal"})
                cur = nx
            for s in sl:
                for f_data, side in [(fa, "a"), (fb, "b")]:
                    for r_s, r_e in parse_ranges(f_data["tap"], ds):
                        if s["s"] < r_e and s["e"] > r_s:
                            if side == "a": s["fa_kw"], s["fa_lab"] = 1500, "Tapping"
                            else: s["fb_kw"], s["fb_lab"] = 1500, "Tapping"
                    for r_s, r_e in parse_ranges(f_data["p_time"], ds):
                        if s["s"] < r_e and s["e"] > r_s:
                            ld = 0 if f_data["p_type"] in ["OFF", "Water Temp Trip"] else 1200
                            if side == "a": s["fa_kw"], s["fa_lab"] = ld, f_data["p_type"]
                            else: s["fb_kw"], s["fb_lab"] = ld, f_data["p_type"]
            wts = [(s["fa_kw"] + s["fb_kw"]) * random.uniform(0.94, 1.06) for s in sl]
            units = [int(round((w/sum(wts))*act_diff)) for w in wts]
            for _ in range(8):
                ex = 0
                for i in range(len(units)):
                    if units[i] > 3476: ex += (units[i] - 3476); units[i] = 3476
                if ex == 0: break
                targets = [i for i, x in enumerate(sl) if units[i] < 3476]
                if targets:
                    add = ex // len(targets)
                    for idx in targets: units[idx] += add
            units[-1] += (act_diff - sum(units))
            curr_r, rw = rs4, []
            for i, s in enumerate(sl):
                curr_r += units[i]
                rw.append({"Time": s["e"].strftime('%I:%M %p'), "A": s["fa_lab"], "B": s["fb_lab"], "kVAh": int(curr_r), "Unit": units[i]})
            st.dataframe(pd.DataFrame(rw), use_container_width=True, hide_index=True)
                        
