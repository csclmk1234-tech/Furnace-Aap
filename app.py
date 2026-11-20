import streamlit as st
import random
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Furnace Log & Meter App", page_icon="⚡", layout="centered")
st.title("⚡ Furnace Log & Meter App")
st.caption("15-Min KVAH Register & Heat-by-Heat Units Generator")

def parse_flexible_time(t_str, base_start=None):
    if not t_str:
        return None
    t_str = str(t_str).strip().upper().replace(".", ":")
    for suffix in ("AM", "PM"):
        if t_str.endswith(suffix) and ":" not in t_str:
            num_part = t_str[:-2].strip()
            if num_part.isdigit() and len(num_part) <= 2:
                t_str = f"{num_part}:00 {suffix}"
    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
        try:
            dt = datetime.strptime(t_str, fmt)
            if base_start:
                dt = dt.replace(year=base_start.year, month=base_start.month, day=base_start.day)
                if dt < base_start:
                    dt += timedelta(days=1)
            return dt
        except ValueError:
            continue
    return None

tab1, tab2 = st.tabs(["📋 15-Min Register", "🔥 Heat-by-Heat Report"])

with tab1:
    st.subheader("15-Min KVAH Reading & Unit")
    col1, col2 = st.columns(2)
    with col1:
        t_start_str = st.text_input("Start Time", value="8:00am", key="t1_start")
        r_start = st.number_input("Start KVAH Reading", value=249751728, step=1, format="%d", key="r1_start")
        active_A = st.selectbox("A-Line Furnace", ["A1", "A2"], key="fur_a")
    with col2:
        t_end_str = st.text_input("End Time", value="10:30am", key="t1_end")
        r_end = st.number_input("End KVAH Reading", value=249775482, step=1, format="%d", key="r1_end")
        active_B = st.selectbox("B-Line Furnace", ["B1", "B2"], index=1, key="fur_b")

    user_check = st.number_input("Cross-Verify Total Unit (Optional - 0 chhod dein)", value=0, step=1, format="%d")
    t_input = st.text_input("Tapping Times (comma lagakar daalein)", placeholder="jaise: 8:25am, 9:45am")

    with st.expander("➕ Breakdown (OFF/ON), Changeover ya Low Load Add Karein"):
        st.markdown("**1. Furnace Breakdown (OFF/ON)**")
        b_col1, b_col2, b_col3 = st.columns(3)
        with b_col1:
            bd_fur = st.selectbox("Kaun si OFF?", ["None", "A", "B", "BOTH"])
        with b_col2:
            bd_off = st.text_input("OFF Time", placeholder="9:15am")
        with b_col3:
            bd_on = st.text_input("ON Time (ya 'end')", placeholder="10:00am")

        st.markdown("**2. Furnace Changeover**")
        c_col1, c_col2 = st.columns(2)
        with c_col1:
            chg_type = st.selectbox("Changeover", ["None", "A1 -> A2", "A2 -> A1", "B1 -> B2", "B2 -> B1"])
        with c_col2:
            chg_time = st.text_input("Changeover Time", placeholder="9:30am")

    if st.button("🚀 Register Table Banayein", type="primary", use_container_width=True, key="btn_tab1"):
        dt_start = parse_flexible_time(t_start_str)
        dt_end = parse_flexible_time(t_end_str, dt_start) if dt_start else None

        if not dt_start or not dt_end:
            st.error("Time format galat hai! Kripya '8:00am' ya '10:30am' jaisa daalein.")
        elif r_end < r_start:
            st.error("End Reading Start Reading se kam nahi ho sakti!")
        else:
            total_units = int(r_end - r_start)
            slots = []
            curr = dt_start
            while curr < dt_end:
                nxt = curr + timedelta(minutes=15)
                if nxt > dt_end:
                    nxt = dt_end
                slots.append({"start": curr, "end": nxt, "fur_A": active_A, "fur_B": active_B, "is_tapping": False, "is_changeover": False})
                curr = nxt

            if t_input.strip():
                for t_item in t_input.split(","):
                    dt_t = parse_flexible_time(t_item, dt_start)
                    if dt_t:
                        for s in slots:
                            if s["start"] <= dt_t < s["end"]:
                                s["is_tapping"] = True

            if bd_fur != "None" and bd_off.strip():
                dt_off = parse_flexible_time(bd_off, dt_start)
                dt_on = dt_end if bd_on.strip().upper() == "END" or not bd_on.strip() else parse_flexible_time(bd_on, dt_start)
                if dt_off and dt_on:
                    for s in slots:
                        if s["start"] < dt_on and s["end"] > dt_off:
                            if bd_fur == "A":
                                s["fur_A"] = "OFF"
                            elif bd_fur == "B":
                                s["fur_B"] = "OFF"
                            else:
                                s["fur_A"] = "OFF"
                                s["fur_B"] = "OFF"

            if chg_type != "None" and chg_time.strip():
                dt_chg = parse_flexible_time(chg_time, dt_start)
                if dt_chg:
                    for s in slots:
                        if s["start"] >= dt_chg:
                            if chg_type == "A1 -> A2" and s["fur_A"] != "OFF":
                                s["fur_A"] = "A2"
                            elif chg_type == "A2 -> A1" and s["fur_A"] != "OFF":
                                s["fur_A"] = "A1"
                            elif chg_type == "B1 -> B2" and s["fur_B"] != "OFF":
                                s["fur_B"] = "B2"
                            elif chg_type == "B2 -> B1" and s["fur_B"] != "OFF":
                                s["fur_B"] = "B1"
                        if s["start"] <= dt_chg < s["end"]:
                            s["is_changeover"] = True

            weights = []
            prev_w = 0.0
            for idx, s in enumerate(slots):
                dur_ratio = ((s["end"] - s["start"]).total_seconds() / 60.0) / 15.0
                a_off, b_off = (s["fur_A"] == "OFF"), (s["fur_B"] == "OFF")
                if a_off and b_off:
                    w = random.uniform(0.05, 0.12)
                elif a_off or b_off:
                    w = random.uniform(0.32, 0.44) if s["is_tapping"] else random.uniform(0.48, 0.72)
                else:
                    if s["is_tapping"]:
                        w = random.uniform(0.62, 0.78)
                    elif s["is_changeover"]:
                        w = random.uniform(0.58, 0.76)
                    else:
                        bands = [(0.82, 0.96), (1.04, 1.22), (1.28, 1.48)]
                        w = random.uniform(*bands[idx % 3])
                        if abs(w - prev_w) < 0.10:
                            w += 0.14 if w < 1.25 else -0.15
                prev_w = w
                weights.append(w * dur_ratio)

            tot_w = sum(weights)
            readings = [int(r_start)]
            curr_r = int(r_start)
            for i in range(len(slots)):
                if i == len(slots) - 1:
                    next_r = int(r_end)
                else:
                    next_r = curr_r + round((weights[i] / tot_w) * total_units)
                readings.append(next_r)
                curr_r = next_r

            rows = [{"Time": dt_start.strftime('%I:%M %p').lstrip('0'), "KVAH": str(int(r_start)), "Unit": "-", "Status": f"{active_A}+{active_B} (Start)"}]
            tot_sum = 0
            for i, s in enumerate(slots):
                u_val = readings[i + 1] - readings[i]
                tot_sum += u_val
                st_txt = f"{s['fur_A']}+{s['fur_B']}"
                if s["is_tapping"]:
                    st_txt += " (Tap)"
                rows.append({"Time": s['end'].strftime('%I:%M %p').lstrip('0'), "KVAH": str(readings[i + 1]), "Unit": str(u_val), "Status": st_txt})

            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.success(f"**Total Reading Units:** {tot_sum}")
            if user_check > 0:
                diff = tot_sum - int(user_check)
                if diff == 0:
                    st.info(f"✅ **Cross-Verify:** 100% EXACT MATCH ({user_check})")
                else:
                    st.warning(f"⚠️ **Cross-Verify Mismatch:** Aapke total se {diff:+d} units ka farq hai!")

with tab2:
    st.subheader("Heat-Wise kWh, kVAh (MF=8) & PF")
    MF = 8
    h_col1, h_col2 = st.columns(2)
    with h_col1:
        kw_s_txt = st.text_input("Start kWh Reading", value="160132528", key="kws_t")
        kvah_s_txt = st.text_input("Start kVAh Reading", value="168914048", key="kvahs_t")
    with h_col2:
        kw_e_txt = st.text_input("End kWh Reading", value="160177232", key="kwe_t")
        kvah_e_txt = st.text_input("End kVAh Reading", value="168962656", key="kvahe_t")

    num_heats = st.selectbox("Kitni Heats hain?", list(range(1, 16)), index=2, key="nh_sel")

    heat_inputs = []
    for i in range(1, int(num_heats) + 1):
        st.markdown(f"**Heat #{i}**")
        c1, c2, c3, c4 = st.columns([1.2, 1, 1, 0.8])
        with c1:
            ht = st.selectbox("Type", ["Normal", "Sintering"], key=f"ht_{i}")
        with c2:
            ton = st.text_input("ON Time", value="8:00am", key=f"ton_{i}")
        with c3:
            ttap = st.text_input("TAP Time", value="10:00am", key=f"ttap_{i}")
        with c4:
            bd_txt = st.text_input("BD(m)", value="0", key=f"bd_{i}")
        heat_inputs.append((i, ht, ton, ttap, bd_txt))

    st.markdown("---")
    if st.button("🔥 GENERATE HEAT REPORT", type="primary", use_container_width=True, key="gen_h_btn"):
        kw_s = int(float(kw_s_txt.strip() or 0))
        kw_e = int(float(kw_e_txt.strip() or 0))
        kvah_s = int(float(kvah_s_txt.strip() or 0))
        kvah_e = int(float(kvah_e_txt.strip() or 0))

        if kw_e <= kw_s or kvah_e <= kvah_s:
            st.error("⚠️ End Reading hamesha Start Reading se badi honi chahiye!")
        else:
            tot_kw_u = round(((kw_e - kw_s) / 10.0) * MF)
            tot_kvah_u = round(((kvah_e - kvah_s) / 10.0) * MF)
            parsed_heats = []
                                
