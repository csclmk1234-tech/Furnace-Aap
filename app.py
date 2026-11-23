import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="16.5T Furnace Master Pro", page_icon="⚡", layout="wide")
st.title("⚡ 16.5T Furnace Advanced Control System")

# Tab 1 Rules (Strict PF & Weightage)
COND_RULES = {
    "Normal Running": {"pf": (0.945, 0.982), "wt": 1.00},
    "Sintering (Lining Heat)": {"pf": (0.800, 0.880), "wt": 1.30}, 
    "GLD / Low KW Running": {"pf": (0.840, 0.890), "wt": 1.15}, 
    "Capacitor Bank Fault": {"pf": (0.750, 0.820), "wt": 1.10},
    "Furnace Breakdown": {"pf": (0.700, 0.800), "wt": 0.45},
}

def pt(s, b=None, next_day_check=False):
    if not s: return None
    s = str(s).strip().upper().replace(".", ":")
    for x in ("AM", "PM"):
        if s.endswith(x) and ":" not in s and s[:-2].strip().isdigit():
            s = f"{s[:-2].strip()}:00 {x}"
    for f in ("%I:%M %p", "%I:%M%p", "%H:%M"):
        try:
            d = datetime.strptime(s, f)
            if b:
                d = d.replace(year=b.year, month=b.month, day=b.day)
                if next_day_check and d <= b: d += timedelta(days=1)
            return d
        except: pass
    return None

def gn(v):
    d = "".join(c for c in str(v) if c.isdigit())
    return int(d) if d else 0

tab1, tab2 = st.tabs(["🔥 1. Heat-by-Heat Report", "📋 2. 15-Min Register (Multi-Status)"])

# ==========================================
# TAB 1: HEAT-BY-HEAT (PRESERVED)
# ==========================================
with tab1:
    st.markdown("### 1️⃣ Meter Readings & Total")
    r1, r2 = st.columns(2)
    skw = gn(r1.text_input("Start kWh Reading", "160944480", key="h_skw"))
    skv = gn(r1.text_input("Start kVAh Reading", "169767296", key="h_skv"))
    ekw = gn(r2.text_input("End kWh Reading", "160983200", key="h_ekw"))
    ekv = gn(r2.text_input("End kVAh Reading", "169807360", key="h_ekv"))
    t_kwh, t_kvah = ekw - skw, ekv - skv
    if t_kwh > 0:
        st.info(f"📊 **TOTAL TO DIVIDE:** kWh = `{t_kwh:,}` | PF = `{round(t_kwh/t_kvah,3) if t_kvah>0 else 0}`")
        nh = st.number_input("Total Heats?", 1, 20, 4)
        hl = []
        base_t = datetime.strptime("08:00 AM", "%I:%M %p")
        for i in range(1, int(nh) + 1):
            with st.container(border=True):
                st.markdown(f"**Heat #{i}**")
                c1, c2, c3, c4 = st.columns(4)
                on_t = c1.text_input(f"ON Time #{i}", (base_t + timedelta(minutes=120*(i-1))).strftime("%I:%M %p"), key=f"on_{i}")
                tap_t = c2.text_input(f"TAP Time #{i}", (base_t + timedelta(minutes=115*i)).strftime("%I:%M %p"), key=f"tp_{i}")
                don, dtp = pt(on_t), pt(tap_t, pt(on_t), True)
                dur_m = int((dtp - don).total_seconds() / 60) if don and dtp else 115
                c3.markdown(f"**⏱️ Total Time:**\n\n{dur_m//60}h {dur_m%60}m")
                ton = c4.number_input(f"Melt Ton #{i}", 1.0, 22.0, 16.5, 0.1, key=f"tn_{i}")
                x1, x2, x3 = st.columns(3)
                cond = x1.selectbox(f"Situation #{i}", list(COND_RULES.keys()), key=f"cd_{i}")
                l_kw = x2.number_input(f"Low KW Power", 0, 7500, 0, key=f"lkw_{i}")
                l_min = x3.number_input(f"Low KW Duration(m)", 0, 300, 0, key=f"lmin_{i}")
                hl.append({"no": i, "on": on_t, "tap": tap_t, "dur": f"{dur_m//60}h {dur_m%60}m", "m": dur_m, "ton": ton, "cond": cond, "lkw": l_kw, "lmin": l_min, "pfr": COND_RULES[cond]["pf"]})

        if st.button("🔥 GENERATE HEAT REPORT", type="primary"):
            sk = t_kwh // 8
            k_scores = [(h["ton"] * COND_RULES[h["cond"]]["wt"]) + ((h["lkw"]*h["lmin"])/60/8) for h in hl]
            kw_s = [int(round((s / sum(k_scores)) * sk)) for s in k_scores]
            kw_s[-1] += (sk - sum(kw_s))
            v_sc = [kw_s[i] / random.uniform(*hl[i]["pfr"]) for i in range(len(hl))]
            kv_s = [int(round((v / sum(v_sc)) * (t_kvah//8))) for v in v_sc]
            kv_s[-1] += ((t_kvah//8) - sum(kv_s))
            rep_r, copy_t = [], ""
            for i, h in enumerate(hl):
                k, v = kw_s[i]*8, max(kw_s[i]*8+8, kv_s[i]*8)
                rep_r.append({"Heat": f"#{h['no']}", "ON": h['on'], "TAP": h['tap'], "Total Time": h['dur'], "Ton": h['ton'], "kWh": k, "PF": f"{round(k/v,3):.3f}"})
                copy_t += f"--- Heat #{h['no']} ---\nHeat ON Time     : {h['on']}\nHeat Taping Time : {h['tap']} ({h['dur']})\nMelting Ton      : {h['ton']} T\nKwh units        : {k}\nPf.              : {round(k/v,3):.3f}\n\n"
            st.dataframe(pd.DataFrame(rep_r), use_container_width=True, hide_index=True)
            st.code(copy_t.strip(), language=None)

# ==========================================
# TAB 2: 15-MIN REGISTER (MULTI-STATUS ENABLED)
# ==========================================
with tab2:
    st.markdown("### 📋 Advanced Register (GLD and OFF Separated)")
    rc1, rc2, rc3 = st.columns(3)
    ts4 = rc1.text_input("Shift Start Time", "8:00 AM", key="reg_ts")
    te4 = rc2.text_input("Shift End Time", "10:30 AM", key="reg_te")
    rs4 = gn(rc3.text_input("Start KVAH (Reg)", "249983498"))
    re4 = gn(rc3.text_input("End KVAH (Reg)", "250011382"))
    
    total_diff = re4 - rs4
    st.info(f"📊 **Meter Total:** `{total_diff:,}` Units")
    tp_list = st.text_input("Heat Tapping Times", "8:15 AM, 10:00 AM")

    def furnace_timeline_ui(f_name, f_key):
        with st.container(border=True):
            st.subheader(f_name)
            fid = st.selectbox(f"Select Line", ["A1", "A2"] if "A" in f_name else ["B1", "B2"], key=f"id_{f_key}")
            
            st.markdown("**1. GLD / Low KW Period**")
            g_c1, g_c2, g_c3 = st.columns(3)
            g_kw = g_c1.number_input("GLD KW", 500, 3000, 1000, key=f"gkw_{f_key}")
            g_f = g_c2.text_input("GLD From", "", key=f"gf_{f_key}")
            g_t = g_c3.text_input("GLD To", "", key=f"gt_{f_key}")
            
            st.markdown("**2. OFF / Patching Period**")
            o_c1, o_c2 = st.columns(2)
            o_f = o_c1.text_input("OFF From", "", key=f"of_{f_key}")
            o_t = o_c2.text_input("OFF To", "", key=f"ot_{f_key}")
            
            return {"id": fid, "gkw": g_kw, "gf": g_f, "gt": g_t, "of": o_f, "ot": o_t}

    col_a, col_b = st.columns(2)
    with col_a: fa_data = furnace_timeline_ui("Furnace A", "a")
    with col_b: fb_data = furnace_timeline_ui("Furnace B", "b")

    if st.button("🚀 Generate Register", type="primary", use_container_width=True):
        ds, de = pt(ts4), pt(te4, pt(ts4), True)
        if ds and de and total_diff > 0:
            sl, cur = [], ds
            while cur < de:
                nx = min(cur + timedelta(minutes=15), de)
                sl.append({"s": cur, "e": nx, "fa": fa_data["id"], "fakw": 7000, "fastat": "Normal", "fb": fb_data["id"], "fbkw": 7000, "fbstat": "Normal"})
                cur = nx
            
            # Times Mapping
            agf, agt = pt(fa_data["gf"], ds), pt(fa_data["gt"], ds)
            aof, aot = pt(fa_data["of"], ds), pt(fa_data["ot"], ds)
            bgf, bgt = pt(fb_data["gf"], ds), pt(fb_data["gt"], ds)
            bof, bot = pt(fb_data["of"], ds), pt(fb_data["ot"], ds)

            for s in sl:
                # Apply Furnace A
                if agf and agt and s["s"] < agt and s["e"] > agf:
                    s["fastat"], s["fakw"] = "GLD", fa_data["gkw"]
                if aof and aot and s["s"] < aot and s["e"] > aof:
                    s["fastat"], s["fakw"] = "OFF", 0
                    s["fa"] = "OFF"
                # Apply Furnace B
                if bgf and bgt and s["s"] < bgt and s["e"] > bgf:
                    s["fbstat"], s["fbkw"] = "GLD", fb_data["gkw"]
                if bof and bot and s["s"] < bot and s["e"] > bof:
                    s["fbstat"], s["fbkw"] = "OFF", 0
                    s["fb"] = "OFF"
                # Tapping check
                for x in tp_list.split(","):
                    if (dt := pt(x, ds)) and s["s"] <= dt < s["e"]:
                        if s["fastat"] == "Normal": s["fakw"] *= 0.75
                        if s["fbstat"] == "Normal": s["fbkw"] *= 0.75

            # Weight Distribution
            weights = [(s["fakw"] + s["fbkw"]) * random.uniform(0.96, 1.04) for s in sl]
            steps = [int(round((w/sum(weights))*total_diff)) for w in weights]
            steps[-1] += (total_diff - sum(steps))
            
            curr_r, rw = rs4, [{"Time": ds.strftime('%I:%M %p'), "A-Line": "-", "B-Line": "-", "KVAH": str(rs4), "Unit": "-"}]
            for i, s in enumerate(sl):
                curr_r += steps[i]
                rw.append({
                    "Time": s["e"].strftime('%I:%M %p'),
                    "A-Line": f"{s['fa']} ({s['fastat']})",
                    "B-Line": f"{s['fb']} ({s['fbstat']})",
                    "KVAH": str(int(curr_r)),
                    "Unit": str(int(steps[i]))
                })
            st.dataframe(pd.DataFrame(rw), use_container_width=True, hide_index=True)
            st.success("✅ Multi-Status Register Generated!")
            
