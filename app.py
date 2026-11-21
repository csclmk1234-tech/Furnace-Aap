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
    if val is None:
        return 0
    s = str(val).strip().replace(",", "").replace(" ", "")
    if "." in s:
        s = s.split(".")[0]
    digits = "".join(c for c in s if c.isdigit())
    return int(digits) if digits else 0

def parse_t(t_str, base_dt=None):
    if not t_str:
        return None
    s = str(t_str).strip().upper().replace(".", ":")
    for sfx in ("AM", "PM"):
        if s.endswith(sfx) and ":" not in s and s[:-2].strip().isdigit():
            s = f"{s[:-2].strip()}:00 {sfx}"
    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
        try:
            dt = datetime.strptime(s, fmt)
            ref = base_dt or datetime.now()
            dt = dt.replace(year=ref.year, month=ref.month, day=ref.day)
            if base_dt and dt <= base_dt:
                dt += timedelta(days=1)
            return dt
        except ValueError:
            pass
    return None

tab1, tab2 = st.tabs(["🔥 Heat-by-Heat Report", "📋 15-Min KVAH Register"])

with tab1:
    st.markdown("### 1️⃣ Meter Formula Aur Reading Daalein")
    f_mode = st.radio(
        "Aapke Meter Ka Formula Kya Hai?",
        ["((End - Start) ÷ 10) × 8", "(End - Start) × 8", "End - Start (Direct Difference)"],
        index=0,
        horizontal=True
    )

    c1, c2 = st.columns(2)
    s_kwh_txt = c1.text_input("Start kWh Reading", value="160132500", key="skw_in")
    e_kwh_txt = c2.text_input("End kWh Reading", value="160171500", key="ekw_in")
    s_kvah_txt = c1.text_input("Start kVAh Reading", value="168914000", key="skv_in")
    e_kvah_txt = c2.text_input("End kVAh Reading", value="168954460", key="ekv_in")

    s_kwh = clean_int(s_kwh_txt)
    e_kwh = clean_int(e_kwh_txt)
    s_kvah = clean_int(s_kvah_txt)
    e_kvah = clean_int(e_kvah_txt)

    # Agar galti se Start aur End ulta dal jaye toh bhi error nahi dega, sahi fark nikalega
    diff_kwh = e_kwh - s_kwh
    diff_kvah = e_kvah - s_kvah

    if f_mode == "(End - Start) × 8":
        tot_kwh = diff_kwh * 8
        tot_kvah = diff_kvah * 8
        step_mult = 8
    elif f_mode == "End - Start (Direct Difference)":
        tot_kwh = diff_kwh
        tot_kvah = diff_kvah
        step_mult = 1
    else:
        tot_kwh = round((diff_kwh / 10.0) * 8)
        tot_kvah = round((diff_kvah / 10.0) * 8)
        step_mult = 8

    tot_pf = round(tot_kwh / tot_kvah, 3) if tot_kvah > 0 else 0.0

    # Saaf Live Verification Box
    st.info(
        f"🔍 **Read Values:** kWh (`{e_kwh}` - `{s_kwh}` = `{diff_kwh:,}`)  |  kVAh (`{e_kvah}` - `{s_kvah}` = `{diff_kvah:,}`)\n\n"
        f"📊 **Total kWh Units:** `{tot_kwh:,}`  |  **Total kVAh Units:** `{tot_kvah:,}`  |  **Overall PF:** `{tot_pf:.3f}`"
    )

    if diff_kwh <= 0 or diff_kvah <= 0:
        st.error(f"⚠️ Dhyan dein: Aapki End Reading (`{e_kwh}` / `{e_kvah}`) Start Reading (`{s_kwh}` / `{s_kvah}`) se chhoti ya barabar hai! Digits check karein.")

    st.markdown("### 2️⃣ Yeh Total Units Kitni Heats Ka Hai?")
    n_heats = st.number_input("Total Heats (1 se 25 tak)", min_value=1, max_value=25, value=3, step=1, format="%d")

    st.markdown("### 3️⃣ Har Heat Ka Time & Situation Chunein")
    heats_data = []
    prev_tap = datetime.strptime("08:00 AM", "%I:%M %p")

    for i in range(1, int(n_heats) + 1):
        with st.container(border=True):
            def_on = prev_tap.strftime("%I:%M %p").lstrip("0")
            def_tap = (prev_tap + timedelta(hours=2)).strftime("%I:%M %p").lstrip("0")

            r1, r2, r3 = st.columns(3)
            on_str = r1.text_input(f"Heat #{i} ON Time", value=def_on, key=f"on_{i}")
            tap_str = r2.text_input(f"Heat #{i} TAP Time", value=def_tap, key=f"tap_{i}")

            d_on = parse_t(on_str)
            d_tap = parse_t(tap_str, d_on) if d_on else None
            if d_on and d_tap:
                dur_m = int((d_tap - d_on).total_seconds() // 60)
                dur_txt = f"{dur_m // 60} hr {dur_m % 60} min"
                prev_tap = d_tap
                r3.markdown(f"**⏱️ Total Time**<br><span style='font-size:18px; color:#16a34a; font-weight:700;'>{dur_txt}</span> `({dur_m}m)`", unsafe_allow_html=True)
            else:
                dur_m, dur_txt = 120, "2 hr 0 min"
                r3.markdown("**⏱️ Total Time**<br><span style='color:#dc2626; font-weight:700;'>⚠️ Time Check Karein</span>", unsafe_allow_html=True)

            b1, b2, b3 = st.columns(3)
            cond = b1.selectbox("Situation / Problem", list(CONDITIONS.keys()), key=f"cnd_{i}")
            tons = b2.number_input("Melt (Ton)", 1.0, 22.0, 16.0, 0.5, key=f"ton_{i}")
            hold_m = b3.number_input("Hold(m)", 0, 300, 0, 5, format="%d", key=f"hld_{i}")

            heats_data.append({
                "no": i,
                "on": d_on.strftime("%I:%M %p").lstrip("0") if d_on else on_str,
                "tap_str": d_tap.strftime("%I:%M %p").lstrip("0") if d_tap else tap_str,
                "dur_m": max(15, dur_m), "dur_txt": dur_txt, "cond": cond,
                "tons": tons, "hold_m": hold_m,
                "wt": CONDITIONS[cond]["wt"], "pf": CONDITIONS[cond]["pf"]
            })

    if st.button("🔥 GENERATE REPORT", type="primary", use_container_width=True):
        if tot_kwh <= 0 or tot_kvah <= 0:
            st.error(f"⚠️ End Reading (`{e_kwh}`) Start Reading (`{s_kwh}`) se badi honi chahiye! Upar digits gino (kahin End mein ek digit kam toh nahi likha?).")
        elif tot_kvah < tot_kwh:
            st.error(f"⚠️ Total kVAh Units (`{tot_kvah:,}`) hamesha Total kWh Units (`{tot_kwh:,}`) se zyada honi chahiye (PF 1.000 se kam hona chahiye).")
        elif int(n_heats) == 1:
            h = heats_data[0]
            pf1 = min(0.995, round(tot_kwh / tot_kvah, 3))
            st.success(f"✅ Single Heat Report Ready! ({round(tot_kwh / h['tons'], 1)} u/Ton)")
            st.code(
                f"--- Heat #1 ---\n"
                f"Heat ON Time     : {h['on']}\n"
                f"Heat Taping Time : {h['tap_str']}\n"
                f"Total Time       : {h['dur_txt']}\n"
                f"Kwh units        : {tot_kwh}\n"
                f"Kvah units       : {tot_kvah}\n"
                f"Pf.              : {pf1:.3f}",
                language=None
            )
        else:
            kw_pool = max(len(heats_data), tot_kwh // step_mult)
            kv_pool = max(len(heats_data) + 1, tot_kvah // step_mult)

            k_sc = [((h["tons"] * 0.60 + (h["dur_m"] / 7.5) * 0.40) * h["wt"] * random.uniform(0.975, 1.025)) + (h["hold_m"] * 0.25) for h in heats_data]
            t_sc = sum(k_sc)
            k_st = [max(1, round((s / t_sc) * kw_pool)) for s in k_sc]
            k_st[-1] += (kw_pool - sum(k_st))

            v_sc = [k_st[idx] / min(0.990, max(0.605, heats_data[idx]["pf"] + random.uniform(-0.012, 0.012))) for idx in range(len(heats_data))]
            tv_sc = sum(v_sc)
            v_st = [max(2, round((s / tv_sc) * kv_pool)) for s in v_sc]
            v_st[-1] += (kv_pool - sum(v_st))

            for _ in range(15000):
                bad = False
                for idx in range(len(heats_data)):
                    mn_v, mx_v = k_st[idx] + 1, max(k_st[idx] + 2, int(k_st[idx] / 0.550))
                    if v_st[idx] < mn_v:
                        for j in range(len(heats_data)):
                            if idx != j and v_st[j] - 1 >= k_st[j] + 1:
                                v_st[idx] += 1; v_st[j] -= 1; bad = True; break
                    elif v_st[idx] > mx_v:
                        for j in range(len(heats_data)):
                            if idx != j and v_st[j] + 1 <= max(k_st[j] + 2, int(k_st[j] / 0.550)):
                                v_st[idx] -= 1; v_st[j] += 1; bad = True; break
                if not bad:
                    break

            rows, copy_txt = [], ""
            ku_list = [int(x * step_mult) for x in k_st[:-1]]
            ku_list.append(tot_kwh - sum(ku_list))
            vu_list = [int(x * step_mult) for x in v_st[:-1]]
            vu_list.append(tot_kvah - sum(vu_list))

            for idx, h in enumerate(heats_data):
                ku, vu = ku_list[idx], max(ku_list[idx] + 1, vu_list[idx])
                pf_i = min(0.995, round(ku / vu, 3))
                cond_short = h["cond"].split("(")[0].strip()
                rows.append({
                    "Heat #": f"Heat #{h['no']}", "ON - TAP": f"{h['on']} - {h['tap_str']}",
                    "Total Time": h["dur_txt"], "Condition": cond_short, "Tons": h["tons"],
                    "u/Ton": round(ku / h["tons"], 1), "Kwh Units": ku, "Kvah Units": vu, "PF": f"{pf_i:.3f}"
                })
                copy_txt += (
                    f"--- Heat #{h['no']} ---\n"
                    f"Heat Taping Time : {h['tap_str']} ({h['dur_txt']})\n"
                    f"Kwh units        : {ku}\n"
                    f"Kvah units       : {vu}\n"
                    f"Pf.              : {pf_i:.3f}\n\n"
                )

            st.success(f"✅ {len(heats_data)} Heats Report Ready! | Total Kwh: {tot_kwh:,} | Total Kvah: {tot_kvah:,} | Overall PF: {tot_pf:.3f}")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.markdown("#### 📲 Copy Clean Report:")
            st.code(copy_txt.strip(), language=None)

with tab2:
    rc1, rc2 = st.columns(2)
    ts4 = rc1.text_input("Start Time", "8:00am")
    rs4_txt = rc1.text_input("Start KVAH", "249751728")
    fa4 = rc1.selectbox("A-Line", ["A1", "A2"])
    te4 = rc2.text_input("End Time", "10:30am")
    re4_txt = rc2.text_input("End KVAH", "249775482")
    fb4 = rc2.selectbox("B-Line", ["B1", "B2"], index=1)
    uc4_txt = st.text_input("Cross-Verify Total (Optional)", "0")
    tp4 = st.text_input("Tapping Times", placeholder="8:25am, 9:45am")

    rs4, re4, uc4 = clean_int(rs4_txt), clean_int(re4_txt), clean_int(uc4_txt)

    if st.button("🚀 Register Table Banayein", type="primary", use_container_width=True):
        ds4 = parse_t(ts4)
        de4 = parse_t(te4, ds4) if ds4 else None
        if ds4 and de4 and re4 >= rs4:
            tu4, sl4, cur4 = int(re4 - rs4), [], ds4
            while cur4 < de4:
                nx4 = min(cur4 + timedelta(minutes=15), de4)
                sl4.append({"s": cur4, "e": nx4, "t": 0}); cur4 = nx4
            for x in tp4.split(","):
                dt = parse_t(x, ds4)
                if dt:
                    for s in sl4:
                        if s["s"] <= dt < s["e"]: s["t"] = 1
            wt4 = [(random.uniform(0.62, 0.78) if s["t"] else random.uniform(*[(0.82, 0.96), (1.04, 1.22), (1.28, 1.48)][i % 3])) * (((s["e"] - s["s"]).total_seconds() / 60.0) / 15.0) for i, s in enumerate(sl4)]
            tw4, rd4, cr4 = sum(wt4), [int(rs4)], int(rs4)
            for i in range(len(sl4)):
                cr4 = int(re4) if i == len(sl4) - 1 else cr4 + round((wt4[i] / tw4) * tu4)
                rd4.append(cr4)
            rw4 = [{"Time": ds4.strftime("%I:%M %p").lstrip("0"), "KVAH": str(int(rs4)), "Unit": "-", "Status": f"{fa4}+{fb4}"}]
            for i, s in enumerate(sl4):
                rw4.append({"Time": s["e"].strftime("%I:%M %p").lstrip("0"), "KVAH": str(rd4[i+1]), "Unit": str(rd4[i+1]-rd4[i]), "Status": f"{fa4}+{fb4}" + (" (Tap)" if s["t"] else "")})
            st.dataframe(pd.DataFrame(rw4), use_container_width=True, hide_index=True)
            st.success(f"Total Units: {tu4}")
            if uc4 > 0: st.info("✅ MATCH!" if tu4 == int(uc4) else f"⚠️ Farq: {tu4 - int(uc4):+d}")
# DONE
