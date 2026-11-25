import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="16T Furnace V53", page_icon="⚡", layout="centered")
st.title("⚡ 16T Furnace Master Pro V53")

PROB_RULES = {
    "Normal": 1.0, "Water Temp Trip": 0.1, "GLD / Low KW": 0.4,
    "Capacitor Bank Fault": 0.8, "CCM Holding": 0.5, "Panel / SCR Tripping": 0.6
}
PROB_PF = {
    "Normal": 1.00, "Water Temp Trip": 0.96, "GLD / Low KW": 0.91,
    "Capacitor Bank Fault": 0.84, "CCM Holding": 0.93, "Panel / SCR Tripping": 0.89
}

def pt(s, b=None, nd=False):
    if not s: return None
    s = str(s).strip().lower().replace(".", ":").replace(" ", "")
    s = s.replace("am", " am").replace("pm", " pm")
    for f in ["%I:%M %p", "%I:%M%p", "%H:%M", "%I %p"]:
        try:
            d = datetime.strptime(s.strip(), f)
            bd = b if b else datetime.now()
            d = d.replace(year=bd.year, month=bd.month, day=bd.day)
            if nd and b and d < b: d += timedelta(days=1)
            return d
        except: pass
    return None

def parse_ranges(inp, bt):
    res = []
    if not inp: return res
    for seg in inp.split(","):
        if "-" in seg:
            try:
                a, z = seg.split("-")
                ts = pt(a.strip(), bt, True)
                te = pt(z.strip(), ts, True)
                if ts and te: res.append((ts, te))
            except: pass
    return res

def gn(v):
    d = "".join(c for c in str(v) if c.isdigit())
    return int(d) if d else 0

def fmt_dur(m):
    m = max(0, int(m))
    return f"{m // 60}h {m % 60}m ({m} min)"

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
        hl, bt = [], pt("08:00 AM")
        for i in range(1, int(nh) + 1):
            with st.container(border=True):
                st.subheader(f"🚩 Heat #{i}")
                is_sent = st.checkbox(f"🔥 Sentring Heat (H#{i})?", key=f"cs_{i}")
                c1, c2, c3 = st.columns(3)
                on_t = c1.text_input("ON Time", "08:00 AM", key=f"on_{i}")
                tp_t = c2.text_input("TAP Time", "10:00 AM", key=f"tp_{i}")
                ton = c3.number_input("Melt Tons", 0.0, 25.0, 16.0, key=f"tn_{i}")
                don = pt(on_t, bt)
                dtp = pt(tp_t, don, True)
                dm = int((dtp - don).total_seconds() / 60) if don and dtp else 120
                is_off = st.checkbox(f"Was OFF during H#{i}?", key=f"co_{i}")
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
                    p1_min = sum([(e - s).total_seconds() / 60 for s, e in parse_ranges(p1m, don)])
                    p2_min = sum([(e - s).total_seconds() / 60 for s, e in parse_ranges(p2m, don)])
                hl.append({"no": i, "on": on_t, "tap": tp_t, "dm": dm, "net_m": net_m, "ton": ton, "sent": is_sent, "off_m": off_m, "p1_t": p1t, "p1_m": p1_min, "p1_k": p1k, "p2_t": p2t, "p2_m": p2_min, "p2_k": p2k})

        if st.button("🔥 GENERATE 8-FACTOR REPORT", type="primary", use_container_width=True):
            k_sc, kv_sc = [], []
            for h in hl:
                # 100% Per-Ton kWh (Sentring me bhi units kam nahi hongi)
                tw = max(float(h["ton"]), 0.1)
                k_sc.append(tw)
                pf_m = 0.850 if h["sent"] else 1.0
                if not h["sent"]:
                    if h["off_m"] > 0: pf_m *= 0.96
                    for pt_x, pm_x, pk_x in [(h["p1_t"], h["p1_m"], h["p1_k"]), (h["p2_t"], h["p2_m"], h["p2_k"])]:
                        if pt_x != "Normal":
                            dr = min(1.0, max(0.25, pm_x / h["net_m"])) if pm_x > 0 else 0.35
                            kr = (pk_x / 5600.0) if pk_x > 0 else 0.5
                            pf_m *= (1.0 - (1.0 - PROB_PF.get(pt_x, 0.94)) * dr * (1.2 - 0.4 * kr))
                kv_sc.append(max(tw / max(0.75, min(1.0, pf_m)), 0.1))

            kw_steps = t_kwh // 8
            kw_list = [int(round((s / sum(k_sc)) * kw_steps)) for s in k_sc]
            while sum(kw_list) < kw_steps:
                r = [kw_list[x] / k_sc[x] for x in range(len(hl))]
                kw_list[r.index(min(r))] += 1
            while sum(kw_list) > kw_steps:
                r = [kw_list[x] / k_sc[x] for x in range(len(hl))]
                kw_list[r.index(max(r))] -= 1

            kv_steps = t_kvah // 8
            kv_list = [int(round((s / sum(kv_sc)) * kv_steps)) for s in kv_sc]
            while sum(kv_list) < kv_steps:
                r = [kv_list[x] / kv_sc[x] for x in range(len(hl))]
                kv_list[r.index(min(r))] += 1
            while sum(kv_list) > kv_steps:
                r = [kv_list[x] / kv_sc[x] for x in range(len(hl))]
                kv_list[r.index(max(r))] -= 1

            if len(hl) > 1:
                for i, h in enumerate(hl):
                    if h["sent"]:
                        pf_t = (kw_list[i] / kv_list[i]) if kv_list[i] > 0 else 0
                        if pf_t > 0.895 or pf_t < 0.805:
                            tgt = max(1, int(round((kw_list[i] * 8 / 0.850) / 8)))
                            diff = tgt - kv_list[i]
                            for j in range(len(hl)):
                                if j != i and not hl[j]["sent"] and (kv_list[j] - diff) >= 1:
                                    kv_list[i] += diff; kv_list[j] -= diff; break

            txt, tbl = "", []
            for i, h in enumerate(hl):
                hk, hv = kw_list[i] * 8, kv_list[i] * 8
                if i == len(hl) - 1: hk += (t_kwh % 8); hv += (t_kvah % 8)
                pf = round(hk / hv, 3) if hv > 0 else 0
                ptn = round(hk / h["ton"], 1) if h["ton"] > 0 else 0
                pa = [p for p in [h["p1_t"], h["p2_t"]] if p != "Normal"]
                if h["off_m"] > 0: pa.append(f"OFF {h['off_m']}m")
                ps = ", ".join(pa) if pa else "Normal"
                st_tag = " (Sentring Heat)" if h["sent"] else ""
                tbl.append({"Heat": f"#{h['no']}{st_tag}", "Time": f"{h['dm']}m", "Tons": f"{h['ton']}T", "kWh": hk, "kWh/T": ptn, "kVAh": hv, "PF": f"{pf:.3f}", "Status": ps})
                txt += f"--- Heat #{h['no']}{st_tag} ---\nHeat ON: {h['on']}\nHeat TAP: {h['tap']}\nTotal Time: {fmt_dur(h['dm'])}\nMelting: {h['ton']} T\nStatus: {ps}\nKwh: {hk} ({ptn} kWh/T)\nKvah: {hv}\nPf: {pf:.3f}\n\n"
            st.success("✅ Report Generated!")
            st.dataframe(pd.DataFrame(tbl), use_container_width=True, hide_index=True)
            st.code(txt.strip(), language=None)

with tab2:
    st.markdown("### 📋 15-Min Advanced Register")
    c1, c2 = st.columns(2)
    ts4 = c1.text_input("Reading Start Time (Reg)", "10:00 PM")
    rs4 = gn(c1.text_input("Starting kVAh Meter", "250513582"))
    te4 = c2.text_input("Reading End Time (Reg)", "06:00 AM")
    re4 = gn(c2.text_input("End kVAh Meter", "250534412"))
    act_diff = re4 - rs4
    st.markdown(f"**Total Units:** :blue[{act_diff:,}]")
    uv = gn(st.text_input("📊 Cross Match Units Box", str(act_diff)))

    def f_ui(lbl, k):
        with st.container(border=True):
            st.subheader(lbl)
            nkw = st.number_input("Normal Load KW", 3000, 8000, 5600, key=f"nk_{k}")
            isent = st.checkbox(f"🔥 {lbl} Sentring Heat?", key=f"sc_{k}")
            sr = st.text_input("Sentring Range(s)", "", key=f"sm_{k}") if isent else ""
            tp = st.text_input("🚰 Tapping Range(s)", "", key=f"tp_{k}")
            ioff = st.checkbox(f"{lbl} was OFF?", key=f"oc_{k}")
            ofr = st.text_input("OFF Range(s)", "", key=f"om_{k}") if ioff else ""
            st.write("🛑 **Problem Slots**")
            x1, x2, x3 = st.columns(3)
            p1t = x1.selectbox("Slot 1", list(PROB_RULES.keys()), key=f"pt1_{k}")
            p1m = x2.text_input("Range 1", "", key=f"pm1_{k}")
            p1k = x3.number_input("KW", 0, 7500, 1200 if "GLD" in p1t else 0, key=f"pk1_{k}")
            x4, x5, x6 = st.columns(3)
            p2t = x4.selectbox("Slot 2", list(PROB_RULES.keys()), key=f"pt2_{k}")
            p2m = x5.text_input("Range 2", "", key=f"pm2_{k}")
            p2k = x6.number_input("KW ", 0, 7500, 0, key=f"pk2_{k}")
                                    
