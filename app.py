import random
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="16T Furnace App", page_icon="⚡", layout="centered")
st.title("⚡ 16T Furnace Energy & Register App")

CONDITIONS = {
    "Normal Running (Optimal Melting)": {"pf": 0.960, "wt": 1.00},
    "CCM Casting Running (Furnace Holding)": {"pf": 0.820, "wt": 1.15},
    "EOT Crane Breakdown (Metal Hold)": {"pf": 0.800, "wt": 1.18},
    "Capacitor Bank Fault / Low PF": {"pf": 0.780, "wt": 1.15},
    "GLD Alarm / Lining Leakage": {"pf": 0.880, "wt": 1.20},
    "Panel / SCR Tripping (ON-OFF)": {"pf": 0.840, "wt": 1.20},
    "Sintering / Lining Heat (Slow)": {"pf": 0.840, "wt": 1.22},
    "Scrap / Charging / Slag Delay": {"pf": 0.860, "wt": 1.08},
}

def clean_int(val):
    if val is None: return 0
    s = str(val).strip().replace(",", "").replace(" ", "")
    digits = "".join(c for c in s if c.isdigit())
    return int(digits) if digits else 0

def parse_t(t_str, base_dt=None):
    if not t_str: return None
    s = str(t_str).strip().upper().replace(".", ":")
    for sfx in ("AM", "PM"):
        if s.endswith(sfx) and ":" not in s and s[:-2].strip().isdigit():
            s = f"{s[:-2].strip()}:00 {sfx}"
    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
        try:
            dt = datetime.strptime(s, fmt)
            ref = base_dt or datetime.now()
            dt = dt.replace(year=ref.year, month=ref.month, day=ref.day)
            if base_dt and dt <= base_dt: dt += timedelta(days=1)
            return dt
        except ValueError: pass
    return None

tab1, tab2 = st.tabs(["🔥 Heat-by-Heat Report", "📋 15-Min KVAH Register"])

with tab1:
    st.markdown("### 1️⃣ Meter Factor Aur Reading Daalein")
    # MF box se aap khud tay karein ki kis se guna karna hai
    MF = st.number_input("Multiplication Factor (MF) - [Diff x MF]", value=1.0, step=0.1, format="%.1f")
    
    c1, c2 = st.columns(2)
    s_kwh_txt = c1.text_input("Start kWh Reading", value="160944480")
    e_kwh_txt = c2.text_input("End kWh Reading", value="160983200")
    s_kvah_txt = c1.text_input("Start kVAh Reading", value="169767296")
    e_kvah_txt = c2.text_input("End kVAh Reading", value="169807360")

    s_kwh, e_kwh = clean_int(s_kwh_txt), clean_int(e_kwh_txt)
    s_kvah, e_kvah = clean_int(s_kvah_txt), clean_int(e_kvah_txt)

    diff_kwh = e_kwh - s_kwh
    diff_kvah = e_kvah - s_kvah
    
    # Final Units Calculation
    tot_kwh = int(diff_kwh * MF)
    tot_kvah = int(diff_kvah * MF)
    tot_pf = round(tot_kwh / tot_kvah, 3) if tot_kvah > 0 else 0.0

    st.info(
        f"📊 **Calculation Result (MF={MF:g}):**\n\n"
        f"kWh: `{e_kwh}` - `{s_kwh}` = `{diff_kwh:,}` ➔ **Total Units: {tot_kwh:,}**\n\n"
        f"kVAh: `{e_kvah}` - `{s_kvah}` = `{diff_kvah:,}` ➔ **Total Units: {tot_kvah:,}**\n\n"
        f"Overall PF: `{tot_pf:.3f}`"
    )

    if diff_kwh <= 0: st.error("⚠️ End Reading Start se badi honi chahiye!")

    st.markdown("### 2️⃣ Yeh Total Units Kitni Heats Ka Hai?")
    n_heats = st.number_input("Total Heats", 1, 25, 4)

    st.markdown("### 3️⃣ Har Heat Ka Time & Situation Chunein")
    heats_data = []
    prev_tap = datetime.strptime("02:00 AM", "%I:%M %p")

    for i in range(1, int(n_heats) + 1):
        with st.container(border=True):
            def_on = prev_tap.strftime("%I:%M %p").lstrip("0")
            def_tap = (prev_tap + timedelta(hours=2)).strftime("%I:%M %p").lstrip("0")
            r1, r2, r3 = st.columns(3)
            on_str = r1.text_input(f"Heat #{i} ON Time", value=def_on, key=f"on_{i}")
            tap_str = r2.text_input(f"Heat #{i} TAP Time", value=def_tap, key=f"tap_{i}")
            d_on, d_tap = parse_t(on_str), parse_t(tap_str, parse_t(on_str))
            if d_on and d_tap:
                dur_m = int((d_tap - d_on).total_seconds() // 60)
                dur_txt = f"{dur_m // 60} hr {dur_m % 60} min"
                prev_tap = d_tap
                r3.markdown(f"**⏱️ Total Time**<br><span style='color:#16a34a; font-weight:700;'>{dur_txt}</span>", unsafe_allow_html=True)
            else:
                dur_m, dur_txt = 120, "2 hr 0 min"
                r3.markdown("**⏱️ Total Time**<br><span>--</span>", unsafe_allow_html=True)

            b1, b2, b3 = st.columns(3)
            cond = b1.selectbox("Situation", list(CONDITIONS.keys()), key=f"cnd_{i}")
            tons = b2.number_input("Ton", 1.0, 22.0, 16.0, 0.1, key=f"ton_{i}")
            hold_m = b3.number_input("Hold(m)", 0, 300, 0, 5, key=f"hld_{i}")
            heats_data.append({"no": i, "on": on_str, "tap_str": d_tap.strftime("%I:%M %p").lstrip("0") if d_tap else tap_str, "dur_m": max(15, dur_m), "dur_txt": dur_txt, "cond": cond, "tons": tons, "hold_m": hold_m, "wt": CONDITIONS[cond]["wt"], "pf": CONDITIONS[cond]["pf"]})

    if st.button("🔥 GENERATE REPORT", type="primary", use_container_width=True):
        if tot_kwh <= 0: st.error("⚠️ Readings check karein!")
        else:
            k_sc = [((h["tons"] * 0.6 + (h["dur_m"]/7.5) * 0.4) * h["wt"] * random.uniform(0.98, 1.02)) + (h["hold_m"] * 0.3) for h in heats_data]
            ts = sum(k_sc)
            kw_u = [int(round((s / ts) * tot_kwh)) for s in k_sc]
            kw_u[-1] += (tot_kwh - sum(kw_u))
            v_sc = [kw_u[idx] / min(0.988, max(0.605, heats_data[idx]["pf"] + random.uniform(-0.01, 0.01))) for idx in range(len(heats_data))]
            tv = sum(v_sc)
            kv_u = [int(round((s / tv) * tot_kvah)) for s in v_sc]
            kv_u[-1] += (tot_kvah - sum(kv_u))

            rows, copy_txt = [], ""
            for idx, h in enumerate(heats_data):
                ku, vu = kw_u[idx], max(kw_u[idx] + 1, kv_u[idx])
                pf_i = min(0.990, round(ku / vu, 3))
                rows.append({"Heat #": f"#{h['no']}", "TAP": h["tap_str"], "Time": h["dur_txt"], "Ton": h["tons"], "Kwh": ku, "Kvah": vu, "PF": f"{pf_i:.3f}"})
                copy_txt += f"--- Heat #{h['no']} ---\nHeat Taping Time : {h['tap_str']} ({h['dur_txt']})\nKwh units        : {ku}\nKvah units       : {vu}\nPf.              : {pf_i:.3f}\n\n"
            st.success(f"✅ Report Ready! Total Kwh: {tot_kwh:,}")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.markdown("#### 📲 Copy Report:")
            st.code(copy_txt.strip(), language=None)

with tab2:
    st.info("15-Min Register calculation here.")
# DONE
