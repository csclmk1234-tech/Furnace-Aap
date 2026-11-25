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

tab1, tab2 = st.tabs(["🔥 8-Factor Heat Report", "📋 15-Min Register"])

# ==========================================
# TAB 1: HEAT-BY-HEAT
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
                
                st.markdown("🔴 **Furnace Status**")
                is_off = st.checkbox(f"Was OFF during H#{i}?", key=f"chk_off_{i}")
                off_m = 0
                if is_off:
                    ox1, ox2 = st.columns(2)
                    off_f = pt(ox1.text_input("OFF From", "", key=f"of_{i}"), don)
                    off_t = pt(ox2.text_input("OFF To", "", key=f"ot_{i}"), off_f, True)
                    off_m = int((off_t-off_f).total_seconds()/60) if off_f and off_t else 0
                
                with st.expander(f"⚠️ Multi-Problem Slots (H#{i})"):
                    px1, px2, px3 = st.columns(3)
                    p1t = px1.selectbox("Prob 1", list(PROB_RULES.keys()), key=f"p1t_{i}")
                    p1m = px2.text_input("Range 1", "", key=f"p1m_{i}")
                    p1k = px3.number_input("KW", 0, 7500, 1200 if "GLD" in p1t else 0, key=f"p1k_{i}")
                    
                    px4, px5, px6 = st.columns(3)
                    p2t = px4.selectbox("Prob 2", list(PROB_RULES.keys()), key=f"p2t_{i}")
                    p2m = px5.text_input("Range 2", "", key=f"p2m_{i}")
                    p2k = px6.number_input("KW ", 0, 7500, 0, key=f"p2k_{i}")
                    
                    p1_min = sum([(e_t - s_t).total_seconds()/60 for s_t, e_t in parse_ranges(p1m, don)])
                    p2_min = sum([(e_t - s_t).total_seconds()/60 for s_t, e_t in parse_ranges(p2m, don)])
                
                don_p = pt(on_t, bt)
                dtp_p = pt(tp_t, don_p, True)
                dm = int((dtp_p - don_p).total_seconds()/60) if don_p and dtp_p else 115
                
                hl.append({
                    "no": i, "on": on_t, "tap": tp_t, "dm": dm, "ton": ton, "sentring": is_sentring,
                    "off_m": off_m, "p1_m": p1_min, "p1_k": p1k, "p2_m": p2_min, "p2_k": p2k
                })

        if st.button("🔥 GENERATE 8-FACTOR REPORT", type="primary", use_container_width=True):
            k_scores, kv_scores = [], []
            for h in hl:
                ton_w = max(float(h["ton"]), 0.1)
                k_scores.append(ton_w)
                pf_factor = 0.850 if h["sentring"] else 1.0
                if not h["sentring"]:
                    if h["off_m"] > 0: pf_factor *= 0.96
                    if h["p1_m"] > 0: pf_factor *= (0.88 + 0.12 * (h["p1_k"] / 5600))
                    if h["p2_m"] > 0: pf_factor *= (0.88 + 0.12 * (h["p2_k"] / 5600))
                kv_scores.append(ton_w / max(0.78, pf_factor))
            
            w_sum = sum(k_scores)
            kw_steps = t_kwh // 8
            kw_list = [int(round((s / w_sum) * kw_steps)) for s in k_scores]
            for _ in range(kw_steps - sum(kw_list)): kw_list[kw_list.index(min(kw_list))] += 1
            for _ in range(sum(kw_list) - kw_steps): kw_list[kw_list.index(max(kw_list))] -= 1

            kv_sum = sum(kv_scores)
            kv_steps = t_kvah // 8
            kv_list = [int(round((s / kv_sum) * kv_steps)) for s in kv_scores]
            for _ in range(kv_steps - sum(kv_list)): kv_list[kv_list.index(min(kv_list))] += 1
            for _ in range(sum(kv_list) - kv_steps): kv_list[kv_list.index(max(kv_list))] -= 1

            if len(hl) > 1:
                for i, h in enumerate(hl):
                    if h["sentring"]:
                        pf_chk = kw_list[i] / kv_list[i] if kv_list[i] > 0 else 0
                        if pf_chk > 0.895 or pf_chk < 0.805:
                            tgt = max(1, int(round((kw_list[i] * 8 / 0.850) / 8)))
                            diff = tgt - kv_list[i]
                            for j in range(len(hl)):
                                if j != i and not hl[j]["sentring"] and (kv_list[j] - diff) >= 1:
                                    kv_list[i] += diff; kv_list[j] -= diff; break

            copy_txt, rep_table = "", []
            for i, h in enumerate(hl):
                hk, hv = kw_list[i] * 8, kv_list[i] * 8
                if i == len(hl) - 1: hk += (t_kwh % 8); hv += (t_kvah % 8)
                pf = round(hk/hv, 3) if hv > 0 else 0
                s_tag = " (Sentring Heat)" if h["sentring"] else ""
                rep_table.append({"Heat": f"#{h['no']}{s_tag}", "kWh": hk, "kVAh": hv, "PF": f"{pf:.3f}"})
                copy_txt += (f"--- Heat #{h['no']}{s_tag} ---\nHeat ON: {h['on']}\nHeat TAP: {h['tap']}\nMelting: {h['ton']} T\nKwh: {hk}\nKvah: {hv}\nPf: {pf:.3f}\n\n")
            
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
            nkw = st.number_input("Normal Load KW", 3000, 8000, 5600, key=f"reg_nk_{key}")
            is_sent = st.checkbox(f"🔥 {label} Sentring Heat?", key=f"reg_sent_{key}")
            sent_r = st.text_input("Sentring Range(s) (Khali = Full Shift)", "", key=f"reg_sr_{key}") if is_sent else ""
            tap = st.text_input("🚰 Tapping Range(s)", "", key=f"reg_tp_{key}")
            is_off = st.checkbox(f"{label} was OFF?", key=f"reg_off_chk_{key}")
            off_r = st.text_input("OFF Range(s)", "", key=f"reg_off_m_{key}") if is_off else ""
            st.write("🛑 **Problem Slots**")
            px1, px2, px3 = st.columns(3)
            p1t = px1.selectbox("Slot 1", list(PROB_RULES.keys()), key=f"rpt1_{key}")
            p1m = px2.text_input("Range 1", "", key=f"rpm1_{key}")
            p1k = px3.number_input("KW", 0, 7500, 1200 if "GLD" in p1t else 0, key=f"rpk1_{key}")
            px4, px5, px6 = st.columns(3)
            p2t = px4.selectbox("Slot 2", list(PROB_RULES.keys()), key=f"rpt2_{key}")
            p2m = px5.text_input("Range 2", "", key=f"rpm2_{key}")
            p2k = px6.number_input("KW ", 0, 7500, 0, key=f"rpk2_{key}")
            return {"nkw": nkw, "is_sent": is_sent, "sent_r": sent_r, "tap": tap, "off": off_r, "probs": [(p1t, p1m, p1k), (p2t, p2m, p2k)]}

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
                    if f_data["is_sent"]:
                        if not f_data["sent_r"].strip():
                            if side == "a": s["fa_kw"], s["fa_lab"] = 2500, "Sentring"
                            else: s["fb_kw"], s["fb_lab"] = 2500, "Sentring"
                        else:
                            for r_s, r_e in parse_ranges(f_data["sent_r"], ds):
                                if s["s"] < r_e and s["e"] > r_s:
                                    if side == "a": s["fa_kw"], s["fa_lab"] = 2500, "Sentring"
                                    else: s["fb_kw"], s["fb_lab"] = 2500, "Sentring"
                    for r_s, r_e in parse_ranges(f_data["tap"], ds):
                        if s["s"] < r_e and s["e"] > r_s:
                            if side == "a": s["fa_kw"], s["fa_lab"] = 1500, "Tapping"
                            else: s["fb_kw"], s["fb_lab"] = 1500, "Tapping"
                    for p_t, p_m, p_k in f_data["probs"]:
                        for r_s, r_e in parse_ranges(p_m, ds):
                            if s["s"] < r_e and s["e"] > r_s:
                                if side == "a" and p_k <= s["fa_kw"]: s["fa_kw"], s["fa_lab"] = p_k, p_t
                                if side == "b" and p_k <= s["fb_kw"]: s["fb_kw"], s["fb_lab"] = p_k, p_t
                    for r_s, r_e in parse_ranges(f_data["off"], ds):
                        if s["s"] < r_e and s["e"] > r_s:
                            if side == "a": s["fa_kw"], s["fa_lab"] = 0, "OFF"
                            else: s["fb_kw"], s["fb_lab"] = 0, "OFF"

            wts = [(s["fa_kw"] + s["fb_kw"]) * random.uniform(0.94, 1.06) for s in sl]
            units = [int(round((w/sum(wts))*act_diff)) for w in wts]
            for _ in range(8):
                excess = sum([max(0, u - 3476) for u in units])
                units = [min(u, 3476) for u in units]
                if excess == 0: break
                targets = [i for i, u in enumerate(units) if u < 3476]
                if targets:
                    for idx in targets: units[idx] += excess // len(targets)
            units[-1] += (act_diff - sum(units))
            curr_r, rw = rs4, []
            for i, s in enumerate(sl):
                curr_r += units[i]
                rw.append({"Time": s["e"].strftime('%I:%M %p'), "A": s["fa_lab"], "B": s["fb_lab"], "kVAh": int(curr_r), "Unit": units[i]})
            st.dataframe(pd.DataFrame(rw), use_container_width=True, hide_index=True)

                
