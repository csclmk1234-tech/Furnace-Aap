import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

# Mobile Optimized View
st.set_page_config(page_title="16T Furnace V53", page_icon="⚡", layout="centered")
st.title("⚡ 16T Furnace Master Pro V53")

# Default Weights
PROB_RULES = {
    "Normal": 1.0, "Water Temp Trip": 0.1, "GLD / Low KW": 0.4,
    "Capacitor Bank Fault": 0.8, "CCM Holding": 0.5, "Panel / SCR Tripping": 0.6
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

def fmt_dur(mins):
    mins = max(0, int(mins))
    return f"{mins // 60}h {mins % 60}m ({mins} min)"

tab1, tab2 = st.tabs(["🔥 8-Factor Heat Report", "📋 15-Min Register"])

# ==========================================
# TAB 1: HEAT-BY-HEAT (16 TON)
# ==========================================
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
                st.caption(f"⏱️ **Total Heat Time:** `{fmt_dur(dm)}` | **OFF:** `{off_m} min` | **Net Run Time:** `{fmt_dur(net_m)}`")
                
                with st.expander(f"⚠️ Multi-Problem Slots (H#{i})"):
                    px1, px2, px3 = st.columns(3)
                    p1t = px1.selectbox("Prob 1", list(PROB_RULES.keys()), key=f"p1t_{i}")
                    p1m = px2.text_input("Range 1", "", key=f"p1m_{i}")
                    p1k = px3.number_input("KW", 0, 7500, 1200 if "GLD" in p1t else 0, key=f"p1k_{i}")
                    
                    px4, px5, px6 = st.columns(3)
                    p2t = px4.selectbox("Prob 2", list(PROB_RULES.keys()), key=f"p2t_{i}")
                    p2m = px5.text_input("Range 2", "", key=f"p2m_{i}")
                    p2k = px6.number_input("KW ", 0, 7500, 0, key=f"p2k_{i}")
                    
                    p1_min = sum([(end_t - start_t).total_seconds() / 60 for start_t, end_t in parse_ranges(p1m, don)])
                    p2_min = sum([(end_t - start_t).total_seconds() / 60 for start_t, end_t in parse_ranges(p2m, don)])
                
                hl.append({
                    "no": i, "on": on_t, "tap": tp_t, "dm": dm, "net_m": net_m, "ton": ton, 
                    "sentring": is_sentring, "off_m": off_m, 
                    "p1_m": p1_min, "p1_k": p1k, "p2_m": p2_min, "p2_k": p2k
                })

        if st.button("🔥 GENERATE 8-FACTOR REPORT", type="primary", use_container_width=True):
            k_scores, kv_scores = [], []
            for h in hl:
                # Per-Ton + Net Running Time Weighting
                ton_base = h["ton"] if h["ton"] > 0 else 8.0
                score = (ton_base * 15.0) + (h["net_m"] * 0.6)
                
                if h["p1_m"] > 0:
                    ratio1 = min(1.0, h["p1_m"] / h["net_m"])
                    score *= (1.0 - ratio1) + (ratio1 * (h["p1_k"] / 5600.0))
                if h["p2_m"] > 0:
                    ratio2 = min(1.0, h["p2_m"] / h["net_m"])
                    score *= (1.0 - ratio2) + (ratio2 * (h["p2_k"] / 5600.0))
                
                if h["sentring"]:
                    k_scores.append(max(score * 0.45, 1.0))
                    kv_scores.append(max(score * 0.54, 1.0))
                else:
                    k_scores.append(max(score, 1.0))
                    kv_scores.append(max(score, 1.0))
            
            # 8-Factor Distribution for kWh
            w_sum = sum(k_scores)
            kw_steps = t_kwh // 8
            kw_list = [int((s / w_sum) * kw_steps) for s in k_scores]
            for _ in range(kw_steps - sum(kw_list)):
                kw_list[kw_list.index(min(kw_list))] += 1

            # 8-Factor Distribution for kVAh
            kv_sum = sum(kv_scores)
            kv_steps = t_kvah // 8
            kv_list = [int((s / kv_sum) * kv_steps) for s in kv_scores]
            for _ in range(kv_steps - sum(kv_list)):
                kv_list[kv_list.index(min(kv_list))] += 1

            # Sentring PF clamp (0.800 - 0.900)
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
                s_tag = " (Sentring Heat)" if h["sentring"] else ""
                
                rep_table.append({
                    "Heat": f"#{h['no']}{s_tag}",
                    "Time": f"{h['dm']}m",
                    "Tons": f"{h['ton']}T",
                    "kWh": hk,
                    "kWh/T": per_ton,
                    "kVAh": hv,
                    "PF": f"{pf:.3f}"
                })
                copy_txt += (
                    f"--- Heat #{h['no']}{s_tag} ---\n"
                    f"Heat ON: {h['on']}\n"
                    f"Heat TAP: {h['tap']}\n"
                    f"Total Time: {fmt_dur(h['dm'])}\n"
                    f"Melting: {h['ton']} T\n"
                    f"Kwh: {hk} ({per_ton} kWh/T)\n"
                    f"Kvah: {hv}\n"
                    f"Pf: {pf:.3f}\n\n"
                )
            
            st.success("✅ Report Generated Successfully!")
            st.dataframe(pd.DataFrame(rep_table), use_container_width=True, hide_index=True)
            st.code(copy_txt.strip(), language=None)

# ==========================================
# TAB 2: REGISTER
# ==========================================
with tab2:
    st.markdown("### 📋 15-Min Advanced Register")
    c_m1, c_m2 = st.columns(2)
    ts4, rs4 = c_m1.text_input("Reading Start Time (Reg)", "10:00 PM"), gn(c_m1.text_input("Starting kVAh Meter", "250513582"))
    te4, re4 = c_m2.text_input("Reading End Time (Reg)", "06:00 AM"), gn(c_m2.text_input("End kVAh Meter", "250534412"))
    act_diff = re4 - rs4
    st.markdown(f"**Total Units:** :blue[{act_diff:,}]")
    user_verify = gn(st.text_input("📊 Cross Match Units Box", str(act_diff)))
    
    ds, de = pt(ts4), pt(te4, pt(ts4), True)
    
    def f_ui(label, key):
        with st.container(border=True):
            st.subheader(label)
                        
