import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="16T Furnace V53", page_icon="⚡", layout="centered")
st.title("⚡ 16T Furnace Master Pro V53")

PROB_RULES = {
    "Normal": 1.0,
    "Water Temp Trip": 0.1,
    "GLD / Low KW": 0.4,
    "Capacitor Bank Fault": 0.8,
    "CCM Holding": 0.5,
    "Panel / SCR Tripping": 0.6
}

PROB_PF_FACTOR = {
    "Normal": 1.00,
    "Water Temp Trip": 0.96,
    "GLD / Low KW": 0.91,
    "Capacitor Bank Fault": 0.84,
    "CCM Holding": 0.93,
    "Panel / SCR Tripping": 0.89
}

def pt(s, b=None, next_day_check=False):
    if not s: return None
    s = str(s).strip().lower().replace(".", ":").replace(" ", "")
    if "am" in s: s = s.replace("am", " am")
    if "pm" in s: s = s.replace("pm", " pm")
    for f in ["%I:%M %p", "%I:%M%p", "%H:%M", "%I %p"]:
        try:
            d = datetime.strptime(s.strip(), f)
            base_date = b if b else datetime.now()
            d = d.replace(year=base_date.year, month=base_date.month, day=base_date.day)
            if next_day_check and b and d < b: d += timedelta(days=1)
            return d
        except: pass
    return None

def parse_ranges(input_str, base_time):
    ranges = []
    if not input_str: return ranges
    for seg in input_str.split(","):
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

def fmt_dur(mins):
    mins = max(0, int(mins))
    return f"{mins // 60}h {mins % 60}m ({mins} min)"

tab1, tab2 = st.tabs(["🔥 8-Factor Heat Report", "📋 15-Min Register"])

with tab1:
    st.markdown("### 1️⃣ Meter Readings Entry")
    r1, r2 = st.columns(2)
    skw = gn(r1.text_input("Starting Reading kWh", "160944480"))
    skv = gn(r1.text_input("Starting Reading kVAh", "169767296"))
    ekw = gn(r2.text_input("End Reading kWh", "160983200"))
    ekv = gn(r2.text_input("End Reading kVAh", "169807360"))
    
    t_kwh, t_kvah = ekw - skw, ekv - skv
    if t_kwh > 0:
        st.info(f"📊 **TOTAL:** kWh: `{t_kwh:,}` | kVAh: `{t_kvah:,}` | PF: `{round(t_kwh/t_kvah,3) if t_kvah>0 else 0}`")
        nh = st.number_input("Total Heats in shift", 1, 20, 4)
        hl = []
        bt = pt("08:00 AM")
        
        for i in range(1, int(nh) + 1):
            with st.container(border=True):
                st.subheader(f"🚩 Heat #{i}")
                is_sentring = st.checkbox(f"🔥 Sentring Heat (H#{i})?", key=f"chk_sent_{i}")
                c1, c2, c3 = st.columns(3)
                on_t = c1.text_input("ON Time", "08:00 AM", key=f"hon_{i}")
                tp_t = c2.text_input("TAP Time", "10:00 AM", key=f"tp_t_{i}")
                ton = c3.number_input("Melt Tons", 0.0, 25.0, 16.0, key=f"htn_{i}")
                don = pt(on_t, bt)
                
                don_p = pt(on_t, bt)
                dtp_p = pt(tp_t, don_p, True)
                dm = int((dtp_p - don_p).total_seconds() / 60) if don_p and dtp_p else 120
                
                st.markdown("🔴 **Furnace Status**")
                is_off = st.checkbox(f"Was OFF during H#{i}?", key=f"chk_off_{i}")
                off_m = 0
                if is_off:
                    ox1, ox2 = st.columns(2)
                    off_f = pt(ox1.text_input("OFF From", "", key=f"of_{i}"), don)
                    off_t = pt(ox2.text_input("OFF To", "", key=f"ot_{i}"), off_f, True)
                    off_m = int((off_t - off_f).total_seconds() / 60) if off_f and off_t else 0
                
                net_m = max(1, dm - off_m)
                st.caption(f"⏱️ **Total Time:** `{fmt_dur(dm)}` | **OFF:** `{off_m}m` | **Run:** `{fmt_dur(net_m)}`")
                
                with st.expander(f"⚠️ Multi-Problem Slots (H#{i})"):
                    px1, px2, px3 = st.columns(3)
                    p1t = px1.selectbox("Prob 1", list(PROB_RULES.keys()), key=f"p1t_{i}")
                    p1m = px2.text_input("Range 1", "", key=f"p1m_{i}")
                    p1k = px3.number_input("KW", 0, 7500, 1200 if "GLD" in p1t else 0, key=f"p1k_{i}")
                    
                    px4, px5, px6 = st.columns(3)
                    p2t = px4.selectbox("Prob 2", list(PROB_RULES.keys()), key=f"p2t_{i}")
                    p2m = px5.text_input("Range 2", "", key=f"p2m_{i}")
                    p2k = px6.number_input("KW ", 0, 7500, 0, key=f"p2k_{i}")
                    
                    p1_min = sum([(e_t - s_t).total_seconds() / 60 for s_t, e_t in parse_ranges(p1m, don)])
                    p2_min = sum([(e_t - s_t).total_seconds() / 60 for s_t, e_t in parse_ranges(p2m, don)])
                
                hl.append({
                    "no": i, "on": on_t, "tap": tp_t, "dm": dm, "net_m": net_m, "ton": ton,
                    "sentring": is_sentring, "off_m": off_m,
                    "p1_t": p1t, "p1_m": p1_min, "p1_k": p1k,
                    "p2_t": p2t, "p2_m": p2_min, "p2_k": p2k
                })

        if st.button("🔥 GENERATE 8-FACTOR REPORT", type="primary", use_container_width=True):
            k_scores, kv_scores = [], []
            for h in hl:
                ton_weight = float(h["ton"]) if h["ton"] > 0 else 8.0
                kw_score = ton_weight * 0.50 if h["sentring"] else ton_weight
                k_scores.append(max(kw_score, 0.1))

                pf_mult = 1.0
                if h["sentring"]:
                    pf_mult = 0.850
                else:
                    if h["off_m"] > 0:
                        pf_mult *= 0.96
                    if h["p1_t"] != "Normal":
                        dur1 = min(1.0, max(0.25, h["p1_m"] / h["net_m"])) if h["p1_m"] > 0 else 0.35
                        kwr1 = (h["p1_k"] / 5600.0) if h["p1_k"] > 0 else 0.5
                        pf_mult *= (1.0 - (1.0 - PROB_PF_FACTOR.get(h["p1_t"], 0.94)) * dur1 * (1.2 - 0.4 * kwr1))
                    if h["p2_t"] != "Normal":
                        dur2 = min(1.0, max(0.25, h["p2_m"] / h["net_m"])) if h["p2_m"] > 0 else 0.35
                        kwr2 = (h["p2_k"] / 5600.0) if h["p2_k"] > 0 else 0.5
                        pf_mult *= (1.0 - (1.0 - PROB_PF_FACTOR.get(h["p2_t"], 0.94)) * dur2 * (1.2 - 0.4 * kwr2))

                pf_mult = max(0.75, min(1.0, pf_mult))
                kv_scores.append(max(kw_score / pf_mult, 0.1))
            
            w_sum = sum(k_scores)
            kw_steps = t_kwh // 8
            kw_list = [int(round((s / w_sum) * kw_steps)) for s in k_scores]
            while sum(kw_list) < kw_steps:
                ratios = [kw_list[idx] / k_scores[idx] for idx in range(len(hl))]
                kw_list[ratios.index(min(ratios))] += 1
            while sum(kw_list) > kw_steps:
                ratios = [kw_list[idx] / k_scores[idx] for idx in range(len(hl))]
                kw_list[ratios.index(max(ratios))] -= 1

            kv_sum = sum(kv_scores)
            kv_steps = t_kvah // 8
            kv_list = [int(round((s / kv_sum) * kv_steps)) for s in kv_scores]
            while sum(kv_list) < kv_steps:
                ratios = [kv_list[idx] / kv_scores[idx] for idx in range(len(hl))]
                kv_list[ratios.index(min(ratios))] += 1
            while sum(kv_list) > kv_steps:
                ratios = [kv_list[idx] / kv_scores[idx] for idx in range(len(hl))]
                kv_list[ratios.index(max(ratios))] -= 1

            if len(hl) > 1:
                for i, h in enumerate(hl):
                    if h["sentring"]:
                        hk_t, hv_t = kw_list[i] * 8, kv_list[i] * 8
                        pf_t = (hk_t / hv_t) if hv_t > 0 else 0
                        if pf_t > 0.895 or pf_t < 0.805:
                            tgt = max(1, int(round((hk_t / 0.850) / 8)))
                            diff = tgt - kv_list[i]
                            for j in range(len(hl)):
                                if j != i and not hl[j]["sentring"] and (kv_list[j] - diff) >= 1:
                                    kv_list[i] += diff
                                    kv_list[j] -= diff
                                    break

            copy_txt, rep_table = "", []
            for i, h in enumerate(hl):
                hk, hv = kw_list[i] * 8, kv_list[i] * 8
                if i == len(hl) - 1:
                    hk += (t_kwh % 8)
                    hv += (t_kvah % 8)
                pf = round(hk / hv, 3) if hv > 0 else 0
                per_ton = round(hk / h["ton"], 1) if h["ton"] > 0 else 0
                probs_active = [p for p in [h["p1_t"], h["p2_t"]] if p != "Normal"]
                if h["off_m"] > 0: probs_active.append(f"OFF {h['off_m']}m")
                prob_str = ", ".join(probs_active) if probs_active else "Normal"
                s_tag = " (Sentring Heat)" if h["sentring"] else ""
                
                rep_table.append({"Heat": f"#{h['no']}{s_tag}", "Time": f"{h['dm']}m", "Tons": f"{h['ton']}T", "kWh": hk, "kWh/T": per_ton, "kVAh": hv, "PF": f"{pf:.3f}", "Status": prob_str})
                copy_txt += f"--- Heat #{h['no']}{s_tag} ---\nHeat ON: {h['on']}\nHeat TAP: {h['tap']}\nTotal Time: {fmt_dur(h['dm'])}\nMelting: {h['ton']} T\nStatus: {prob_str}\nKwh: {hk} ({per_ton} kWh/T)\nKvah: {hv}\nPf: {pf:.3f}\n\n"
            
            st.success("✅ Report Generated Successfully!")
            st.dataframe(pd.DataFrame(rep_table), use_container_width=True, hide_index=True)
            st.code(copy_txt.strip(), language=None)

with tab2:
    st.markdown("### 📋 15-Min Advanced Register")
    c_m1, c_m2 = st.columns(2)
    ts4 = c_m1.text_input("Reading Start Time (Reg)", "10:00 PM")
    rs4 = gn(c_m1.text_input("Starting kVAh Meter", "250513582"))
        
