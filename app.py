import random
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="16T Furnace Calculator", page_icon="⚡", layout="centered")
st.title("⚡ 16T Furnace Energy & Register App")

CONDITIONS = {
    "Normal Running (Optimal Melting)": {"pf": 0.945, "wt": 1.00},
    "CCM Casting Running (Furnace Holding)": {"pf": 0.820, "wt": 1.15},
    "EOT Crane Breakdown (Metal Hold)": {"pf": 0.800, "wt": 1.18},
    "Capacitor Bank Fault / Low PF": {"pf": 0.780, "wt": 1.15},
    "GLD Alarm / Lining Leakage": {"pf": 0.880, "wt": 1.20},
    "Panel / SCR Tripping (ON-OFF)": {"pf": 0.840, "wt": 1.20},
    "Sintering / Lining Heat (Slow)": {"pf": 0.840, "wt": 1.22},
    "Scrap / Charging / Slag Delay": {"pf": 0.860, "wt": 1.08},
}

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
            if base_dt and dt <= base_dt:
                dt += timedelta(days=1)
            return dt
        except ValueError: pass
    return None

with st.sidebar:
    st.header("⚙️ Meter MF Setting")
    mf_opt = st.radio("Multiplication Factor (MF):", ["8 (Standard CT/PT)", "0.8 (9-Digit Last Decimal)", "1 (Direct Unit Meter)"], index=0)
    MF = 8.0 if mf_opt.startswith("8 ") else (0.8 if mf_opt.startswith("0.8") else 1.0)

tab1, tab2 = st.tabs(["🔥 Heat-by-Heat Report (1 to 20 Heats)", "📋 15-Min KVAH Register"])

# =========================================================
# TAB 1: SINGLE UNIFIED HEAT-BY-HEAT CALCULATOR
# =========================================================
with tab1:
    st.markdown("### Step 1: Start & End Meter Reading Daalein")
    c1, c2 = st.columns(2)
    s_kwh = c1.number_input("Start kWh Reading", min_value=0.0, value=124560.0, step=1.0, format="%.2f")
    e_kwh = c2.number_input("End kWh Reading", min_value=0.0, value=128160.0, step=1.0, format="%.2f")
    s_kvah = c1.number_input("Start kVAh Reading", min_value=0.0, value=132510.0, step=1.0, format="%.2f")
    e_kvah = c2.number_input("End kVAh Reading", min_value=0.0, value=136380.0, step=1.0, format="%.2f")

    tot_kwh = round((e_kwh - s_kwh) * MF)
    tot_kvah = round((e_kvah - s_kvah) * MF)
    tot_pf = round(tot_kwh / tot_kvah, 3) if tot_kvah > 0 else 0.0

    # Instant Total Summary Banner
    if tot_kwh > 0 and tot_kvah > 0:
        st.info(f"📊 **Total kWh Units:** `{tot_kwh:,}`  |  **Total kVAh Units:** `{tot_kvah:,}`  |  **Overall PF:** `{tot_pf:.3f}`  *(MF = {MF:g})*")
    else:
        st.warning("⚠️ End Reading Start Reading se badi honi chahiye!")

    st.markdown("### Step 2: Yeh Total Units Kitni Heats Ka Hai?")
    n_heats = st.number_input("Total Heats (1 se 25 tak chunein)", min_value=1, max_value=25, value=3, step=1)

    if tot_kwh > 0 and (tot_kwh / int(n_heats)) > 15000:
        st.warning("⚠️ Dhyan dein: Ek heat ki average unit 15,000 kWh se upar jaa rahi hai! Decimal check karein ya Sidebar se MF badlein.")

    st.markdown("### Step 3: Har Heat Ka Time & Situation Daalein")
    heats_data = list()
    prev_tap = datetime.strptime("08:00 AM", "%I:%M %p")

    for i in range(1, int(n_heats) + 1):
        with st.container(border=True):
            def_on = prev_tap.strftime("%I:%M %p").lstrip("0")
            def_tap = (prev_tap + timedelta(hours=2)).strftime("%I:%M %p").lstrip("0")

            r1, r2, r3 = st.columns([1, 1, 1.2])
            on_str = r1.text_input(f"Heat #{i} ON Time", value=def_on, key=f"on_{i}")
            tap_str = r2.text_input(f"Heat #{i} TAP Time", value=def_tap, key=f"tap_{i}")

            d_on = parse_t(on_str)
            d_tap = parse_t(tap_str, d_on) if d_on else None
            if d_on and d_tap:
                dur_m = int((d_tap - d_on).total_seconds() // 60)
                dur_txt = f"{dur_m // 60}h {dur_m % 60}m ({dur_m} min)"
                prev_tap = d_tap
            else:
                dur_m, dur_txt = 120, "Invalid Time!"

            r3.text_input("Total Time (Auto)", value=dur_txt, disabled=True, key=f"dur_{i}")

            b1, b2, b3 = st.columns([2, 0.8, 0.8])
            cond = b1.selectbox("Running Condition / Problem", list(CONDITIONS.keys()), key=f"cnd_{i}")
            tons = b2.number_input("Melt (Ton)", 1.0, 22.0, 16.0, 0.5, key=f"ton_{i}")
            hold_m = b3.number_input("Hold(m)", 0, 300, 0, 5, key=f"hld_{i}")

            heats_data.append({
                "no": i, "on": on_str, "tap_dt": d_tap, "tap_str": d_tap.strftime("%I:%M %p").lstrip("0") if d_tap else tap_str,
                "dur_m": max(15, dur_m), "dur_txt": dur_txt, "cond": cond, "tons": tons, "hold_m": hold_m,
                "wt": CONDITIONS[cond]["wt"], "pf": CONDITIONS[cond]["pf"]
            })

    if st.button("🔥 GENERATE REPORT", type="primary", use_container_width=True):
        if tot_kwh <= 0 or tot_kvah <= 0 or not (0.600 <= tot_pf <= 0.985):
            st.error(f"⚠️ Meter Readings check karein! Overall PF ({tot_pf:.3f}) 0.600 se 0.980 ke beech hona chahiye.")
        elif int(n_heats) == 1:
            h = heats_data[0]
            pf1 = min(0.980, tot_pf)
            st.success(f"✅ Single Heat Report Generated! ({round(tot_kwh/h['tons'], 1)} kWh/Ton)")
            st.code(f"--- Heat #1 ---\nHeat ON Time     : {h['on']}\nHeat Taping Time : {h['tap_str']} ({h['dur_txt']})\nKwh units        : {tot_kwh}\nKvah units       : {tot_kvah}\nPf.              : {pf1:.3f}", language=None)
        else:
            # Score based on Tons + Total Time + Condition Weight + Hold Mins
            k_sc = [((h["tons"] * 0.65 + (h["dur_m"] / 7.5) * 0.35) * h["wt"] * random.uniform(0.975, 1.025)) + (h["hold_m"] * 0.25) for h in heats_data]
            t_sc = sum(k_sc)
            kw_u = [max(50, round((s / t_sc) * tot_kwh)) for s in k_sc]
            kw_u[-1] += (tot_kwh - sum(kw_u))

            v_sc = [kw_u[idx] / min(0.978, max(0.605, heats_data[idx]["pf"] + random.uniform(-0.012, 0.012))) for idx in range(len(heats_data))]
            tv_sc = sum(v_sc)
            kv_u = [max(60, round((s / tv_sc) * tot_kvah)) for s in v_sc]
            kv_u[-1] += (tot_kvah - sum(kv_u))

            # Enforce strict 0.600 <= PF <= 0.980 on every heat
            for _ in range(15000):
                bad = False
                for idx in range(len(heats_data)):
                    mn_v, mx_v = int(kw_u[idx] / 0.980) + 1, int(kw_u[idx] / 0.600)
                    if kv_u[idx] < mn_v:
                        for j in range(len(heats_data)):
                            if idx != j and kv_u[j] - 1 >= int(kw_u[j] / 0.980) + 1:
                                kv_u[idx] += 1; kv_u[j] -= 1; bad = True; break
                    elif kv_u[idx] > mx_v:
                        for j in range(len(heats_data)):
                            if idx != j and kv_u[j] + 1 <= int(kw_u[j] / 0.600):
                                kv_u[idx] -= 1; kv_u[j] += 1; bad = True; break
                if not bad: break

            rows, copy_txt = list(), ""
            for idx, h in enumerate(heats_data):
                ku, vu = kw_u[idx], kv_u[idx]
                pf_i = min(0.980, max(0.600, round(ku / vu, 3)))
                rows.append({
                    "Heat #": f"Heat #{h['no']}", "ON - TAP": f"{h['on']} - {h['tap_str']}",
                    "Total Time": h["dur_txt"].split("(")[0].strip(), "Condition": h["cond"].split("(")[0].strip(),
                    "Tons": h["tons"], "u/Ton": round(ku / h["tons"], 1), "Kwh Units": ku, "Kvah Units": vu, "PF": f"{pf_i:.3f}"
                })
                copy_txt += (
                    f"--- Heat #{h['no']} ---\n"
                    f"Heat Taping Time : {h['tap_str']} (Time: {h['dur_txt'].split('(')[0].strip()})\n"
                    f"Kwh units        : {ku}\n"
                    f"Kvah units       : {vu}\n"
                    f"Pf.              : {pf_i:.3f}\n\n"
                )

            st.success(f"✅ {len(heats_data)} Heats Report Ready! | Total Kwh: {sum(kw_u):,} | Total Kvah: {sum(kv_u):,} | Overall PF: {tot_pf:.3f}")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.markdown("#### 📲 Copy Clean Report:")
            st.code(copy_txt.strip(), language=None)

# =========================================================
# TAB 2: MANDATORY 15-MIN KVAH REGISTER
# =========================================================
with tab2:
    rc1, rc2 = st.columns(2)
    ts4 = rc1.text_input("Start Time", "8:00am")
    rs4 = rc1.number_input("Start KVAH", 0, 999999999, 249751728, 1, "%d")
    fa4 = rc1.selectbox("A-Line", ["A1", "A2"])
    te4 = rc2.text_input("End Time", "10:30am")
    re4 = rc2.number_input("End KVAH", 0, 999999999, 249775482, 1, "%d")
    fb4 = rc2.selectbox("B-Line", ["B1", "B2"], index=1)
    uc4 = st.number_input("Cross-Verify Total (Optional)", 0, 99999999, 0, 1, "%d")
    tp4 = st.text_input("Tapping Times", placeholder="8:25am, 9:45am")

    if st.button("🚀 Register Table Banayein", type="primary", use_container_width=True):
        ds4 = parse_t(ts4)
        de4 = parse_t(te4, ds4) if ds4 else None
        if ds4 and de4 and re4 >= rs4:
            tu4, sl4, cur4 = int(re4 - rs4), list(), ds4
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
