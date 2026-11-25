import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="16T Furnace V53", page_icon="⚡", layout="centered")
st.title("⚡ 16T Furnace Master Pro V53")

PROB_RULES = {
    "Normal": 1.0, "Water Temp Trip": 0.1, "GLD / Low KW": 0.4,
    "Capacitor Bank Fault": 0.8, "CCM Holding": 0.5, "Panel / SCR Tripping": 0.6
}

def pt(s, b=None, next_day_check=False):
    if not s: return None
    raw = str(s).strip().lower().replace(".", ":").replace(" ", "")
    has_ampm = ("am" in raw) or ("pm" in raw)
    raw = raw.replace("am", " am").replace("pm", " pm")
    formats = ["%I:%M %p", "%I:%M%p", "%H:%M", "%I %p", "%I%p", "%I:%M", "%H"]
    for f in formats:
        try:
            d = datetime.strptime(raw.strip(), f)
            base_date = b if b else datetime.now()
            d = d.replace(year=base_date.year, month=base_date.month, day=base_date.day)
            # Agar user ne AM/PM nahi likha (jaise 10:30) aur base time PM me hai
            if not has_ampm and b and d.hour < 12 and b.hour >= 12:
                d_pm = d + timedelta(hours=12)
                if d_pm >= b:
                    d = d_pm
            if next_day_check and b and d < b:
                d += timedelta(days=1)
            return d
        except: pass
    return None

def get_slot_range(f_str, t_str, base_time):
    ts = pt(f_str, base_time, True)
    te = pt(t_str, ts, True) if ts else None
    return [(ts, te)] if (ts and te) else []

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
                    p1t = st.selectbox("Prob 1", list(PROB_RULES.keys()), key=f"p1t_{i}")
                    px1, px2, px3 = st.columns(3)
                    p1_f = px1.text_input("From 1", "", key=f"p1f_{i}")
                    p1_to = px2.text_input("To 1", "", key=f"p1to_{i}")
                    p1k = px3.number_input("KW", 0, 7500, 1200 if "GLD" in p1t else 0, key=f"p1k_{i}")
                    
                    p2t = st.selectbox("Prob 2", list(PROB_RULES.keys()), key=f"p2t_{i}")
                    px4, px5, px6 = st.columns(3)
                    p2_f = px4.text_input("From 2", "", key=f"p2f_{i}")
                    p2_to = px5.text_input("To 2", "", key=f"p2to_{i}")
                    p2k = px6.number_input("KW ", 0, 7500, 0, key=f"p2k_{i}")
                    
                    p1_min = sum([(e_t - s_t).total_seconds()/60 for s_t, e_t in get_slot_range(p1_f, p1_to, don)])
                    p2_min = sum([(e_t - s_t).total_seconds()/60 for s_t, e_t in get_slot_range(p2_f, p2_to, don)])
                
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
                pf_factor = 0.860 if h["sentring"] else 0.990
                if not h["sentring"]:
                    if h["off_m"] > 0: pf_factor *= 0.97
                    if h["p1_m"] > 0: pf_factor *= (0.90 + 0.10 * (h["p1_k"] / 5600))
                    if h["p2_m"] > 0: pf_factor *= (0.90 + 0.10 * (h["p2_k"] / 5600))
                kv_scores.append(ton_w / max(0.80, pf_factor))
            
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

            for _ in range(50):
                changed = False
                for i in range(len(hl)):
                    if kv_list[i] > 0 and (kw_list[i] / kv_list[i]) > 0.995:
                        donors = [j for j in range(len(hl)) if j != i and (kw_list[j] / max(1, kv_list[j] - 1)) <= (0.895 if hl[j]["sentring"] else 0.992)]
                        if donors:
                            donor = donors[0]
                            kv_list[i] += 1
                            kv_list[donor] -= 1
                            changed = True
                if not changed:
                    break

            copy_txt, rep_table = "", []
            for i, h in enumerate(hl):
                hk, hv = kw_list[i] * 8, kv_list[i] * 8
                if i == len(hl) - 1: hk += (t_kwh % 8); hv += (t_kvah % 8)
                pf = round(hk/hv, 3) if hv > 0 else 0
                if pf >= 1.0: pf = 0.995
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
    def parse_tapping_list(tap_str, base_time):
        slots = []
        if not tap_str: return slots
        for item in tap_str.split(","):
            item = item.strip()
            if not item: continue
            if "-" in item:
                a, z = item.split("-", 1)
                slots.extend(get_slot_range(a.strip(), z.strip(), base_time))
            else:
                t_start = pt(item, base_time, True)
                if t_start:
                    slots.append((t_start, t_start + timedelta(minutes=8)))
        return slots

    def f_ui(label, key):
        with st.container(border=True):
            st.subheader(label)
            nkw = st.number_input("Normal Load KW", 3000, 8000, 5600, key=f"reg_nk_{key}")
            
            is_sent = st.checkbox(f"🔥 {label} Sentring Heat?", key=f"reg_sent_{key}")
            sent_mode, sent_f, sent_t = "Full Shift", "", ""
            if is_sent:
                sent_mode = st.radio("Sentring Mode", ["Full Shift", "Time Range"], horizontal=True, key=f"smode_{key}")
                if sent_mode == "Time Range":
                    sc1, sc2 = st.columns(2)
                    sent_f = sc1.text_input("Sentring From", "", key=f"sf_{key}")
                    sent_t = sc2.text_input("Sentring To", "", key=f"st_{key}")

            tap_times = st.text_input("🚰 Tapping Start Times (e.g. 1:00am, 2:45am)", "", key=f"tptimes_{key}")
            
            is_off = st.checkbox(f"🔴 {label} was OFF?", key=f"reg_off_chk_{key}")
            off_mode, off_f, off_t = "Time Range", "", ""
            if is_off:
                off_mode = st.radio("OFF Type", ["Time Range", "Regular / Full Shift OFF"], horizontal=True, key=f"omode_{key}")
                if off_mode == "Time Range":
                    oc1, oc2 = st.columns(2)
                    off_f = oc1.text_input("OFF From", "", key=f"of_{key}")
                    off_t = oc2.text_input("OFF To", "", key=f"ot_{key}")

            st.write("🛑 **Problem Slots**")
            p1t = st.selectbox("Slot 1 Problem", list(PROB_RULES.keys()), key=f"rpt1_{key}")
            px1, px2, px3 = st.columns(3)
            p1_f = px1.text_input("From 1", "", key=f"rpf1_{key}")
            p1_to = px2.text_input("To 1", "", key=f"rpto1_{key}")
            p1k = px3.number_input("KW", 0, 7500, 1200 if "GLD" in p1t else 0, key=f"rpk1_{key}")
            
            p2t = st.selectbox("Slot 2 Problem", list(PROB_RULES.keys()), key=f"rpt2_{key}")
            px4, px5, px6 = st.columns(3)
            p2_f = px4.text_input("From 2", "", key=f"rpf2_{key}")
            p2_to = px5.text_input("To 2", "", key=f"rpto2_{key}")
            p2k = px6.number_input("KW ", 0, 7500, 0, key=f"rpk2_{key}")
            
            return {
                "nkw": nkw, "is_sent": is_sent, "sent_mode": sent_mode, "sent_f": sent_f, "sent_t": sent_t,
                "tap_times": tap_times, "is_off": is_off, "off_mode": off_mode, "off_f": off_f, "off_t": off_t,
                "probs": [(p1t, p1_f, p1_to, p1k), (p2t, p2_f, p2_to, p2k)]
            }

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
                        s_ranges = get_slot_range(f_data["sent_f"], f_data["sent_t"], ds)
                        if f_data["sent_mode"] == "Full Shift" or not s_ranges:
                            if side == "a": s["fa_kw"], s["fa_lab"] = 2500, "Sentring"
                            else: s["fb_kw"], s["fb_lab"] = 2500, "Sentring"
                        else:
                            for r_s, r_e in s_ranges:
                                if s["s"] < r_e and s["e"] > r_s:
                                    if side == "a": s["fa_kw"], s["fa_lab"] = 2500, "Sentring"
                                    else: s["fb_kw"], s["fb_lab"] = 2500, "Sentring"
                    for r_s, r_e in parse_tapping_list(f_data["tap_times"], ds):
                        if s["s"] < r_e and s["e"] > r_s:
                            tap_avg = int((f_data["nkw"] * 0.24) + random.randint(9, 15))
                            if side == "a": s["fa_kw"], s["fa_lab"] = tap_avg, "Tapping"
                            else: s["fb_kw"], s["fb_lab"] = tap_avg, "Tapping"
                    for p_t, p_f, p_to, p_k in f_data["probs"]:
                        for r_s, r_e in get_slot_range(p_f, p_to, ds):
                            if s["s"] < r_e and s["e"] > r_s:
                                if side == "a" and p_k <= s["fa_kw"]: s["fa_kw"], s["fa_lab"] = p_k, p_t
                                if side == "b" and p_k <= s["fb_kw"]: s["fb_kw"], s["fb_lab"] = p_k, p_t
                    if f_data["is_off"]:
                        o_ranges = get_slot_range(f_data["off_f"], f_data["off_t"], ds)
                        if f_data["off_mode"] == "Regular / Full Shift OFF" or not o_ranges:
                            if side == "a": s["fa_kw"], s["fa_lab"] = 0, "OFF"
                            else: s["fb_kw"], s["fb_lab"] = 0, "OFF"
                        else:
                            for r_s, r_e in o_ranges:
                                if s["s"] < r_e and s["e"] > r_s:
                                    if side == "a": s["fa_kw"], s["fa_lab"] = 0, "OFF"
                                    else: s["fb_kw"], s["fb_lab"] = 0, "OFF"

            wts = [(s["fa_kw"] + s["fb_kw"]) * random.uniform(0.94, 1.06) for s in sl]
            if sum(wts) > 0:
                units = [int(round((w / sum(wts)) * act_diff)) for w in wts]
            else:
                units = [0 for _ in sl]
            for _ in range(8):
                excess = sum([max(0, u - 3476) for u in units])
                units = [min(u, 3476) for u in units]
                if excess == 0: break
                targets = [i for i, u in enumerate(units) if u < 3476]
                if targets:
                    for idx in targets: units[idx] += excess // len(targets)
            if units: units[-1] += (act_diff - sum(units))

            curr_r = rs4
            rw = [{"Time": ds.strftime('%I:%M %p'), "A": "Start", "B": "Start", "kVAh": int(curr_r), "Unit": 0}]
            for i, s in enumerate(sl):
                curr_r += units[i]
                rw.append({"Time": s["e"].strftime('%I:%M %p'), "A": s["fa_lab"], "B": s["fb_lab"], "kVAh": int(curr_r), "Unit": units[i]})
            st.dataframe(pd.DataFrame(rw), use_container_width=True, hide_index=True)
