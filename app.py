import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="16.5T Furnace Unified App", page_icon="⚡", layout="wide")
st.title("⚡ 16.5T Furnace Unified System (8-Factor Logic)")

# Plant Situations
CONDITIONS = {
    "Normal Running": {"pf": 0.962, "wt": 1.00},
    "Sintering (Lining Heat)": {"pf": 0.840, "wt": 1.28},
    "GLD / Tripping Problem": {"pf": 0.880, "wt": 1.18},
    "CCM Holding / Casting": {"pf": 0.820, "wt": 1.10},
    "Scrap / Slag Delay": {"pf": 0.860, "wt": 1.05},
}

def pt(s, b=None):
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
                if d <= b: d += timedelta(days=1)
            return d
        except: pass
    return None

def gn(v):
    d = "".join(c for c in str(v) if c.isdigit())
    return int(d) if d else 0

t_heat, t_reg = st.tabs(["🔥 1. Heat-by-Heat Report", "📋 2. 15-Min Register"])

# ==========================================
# TAB 1: HEAT-BY-HEAT (ON/TAP TIME & 8-FACTOR)
# ==========================================
with t_heat:
    ### 1️⃣ Meter Readings & Total
    r1, r2 = st.columns(2)
    with r1:
        skw = gn(st.text_input("Start kWh Reading", "160944480", key="skw_h"))
        skv = gn(st.text_input("Start kVAh Reading", "169767296", key="skv_h"))
    with r2:
        ekw = gn(st.text_input("End kWh Reading", "160983200", key="ekw_h"))
        ekv = gn(st.text_input("End kVAh Reading", "169807360", key="ekv_h"))

    tot_kwh = ekw - skw
    tot_kvah = ekv - skv
    o_pf = round(tot_kwh / tot_kvah, 3) if tot_kvah > 0 else 0.0

    if tot_kwh > 0:
        st.info(f"📊 **TOTAL TO DIVIDE:** kWh = `{tot_kwh:,}` | kVAh = `{tot_kvah:,}` | PF = `{o_pf:.3f}`")
        nh = st.number_input("2️⃣ Yeh total kitni heats mein baantni hain?", 1, 20, 4)
        
        ### 3️⃣ Heat Details with ON/TAP & Duration
        hl = []
        base_t = datetime.strptime("08:00 AM", "%I:%M %p")
        for i in range(1, int(nh) + 1):
            with st.container(border=True):
                st.markdown(f"**Heat #{i}**")
                c1, c2, c3, c4 = st.columns(4)
                
                # Time Inputs
                def_on = (base_t + timedelta(minutes=120*(i-1))).strftime("%I:%M %p")
                def_tap = (base_t + timedelta(minutes=110*i)).strftime("%I:%M %p")
                on_t = c1.text_input(f"ON Time", def_on, key=f"on_{i}")
                tap_t = c2.text_input(f"TAP Time", def_tap, key=f"tap_{i}")
                
                # Duration Calculation
                d_on = pt(on_t)
                d_tap = pt(tap_t, d_on)
                if d_on and d_tap:
                    diff = d_tap - d_on
                    dur_m = int(diff.total_seconds() / 60)
                    dur_txt = f"{dur_m // 60}h {dur_m % 60}m"
                else:
                    dur_m, dur_txt = 110, "Invalid"
                
                c3.markdown(f"**Total Time:**\n\n{dur_txt}")
                ton = c4.number_input(f"Melt Ton", 1.0, 22.0, 16.5, 0.1, key=f"tn_{i}")
                
                x1, x2, x3 = st.columns(3)
                cond = x1.selectbox(f"Situation", list(CONDITIONS.keys()), key=f"cd_{i}")
                bd = x2.number_input(f"Breakdown (min)", 0, 300, 0, 5, key=f"bm_{i}")
                target_pf = x3.number_input(f"Target PF", 0.600, 0.980, CONDITIONS[cond]["pf"], 0.001, format="%.3f", key=f"pf_{i}")
                
                hl.append({
                    "no": i, "ton": ton, "on": on_t, "tap": tap_t, "dur": dur_txt, 
                    "dur_m": dur_m, "cond": cond, "bd": bd, "tpf": target_pf, "wt": CONDITIONS[cond]["wt"]
                })

        if st.button("🔥 GENERATE HEAT REPORT", type="primary", use_container_width=True):
            # 8-Factor Splitting Logic
            steps_k = tot_kwh // 8
            steps_v = tot_kvah // 8
            
            # Weight logic including Time and Tons
            scores = [(h["ton"] * h["wt"] * (h["dur_m"]/110) * random.uniform(0.98, 1.02)) + (h["bd"] * 0.4) for h in hl]
            total_score = sum(scores)
            
            k_alloc = [int(round((s / total_score) * steps_k)) for s in scores]
            k_alloc[-1] += (steps_k - sum(k_alloc))
            
            kv_req = [k_alloc[i] / hl[i]["tpf"] for i in range(len(hl))]
            v_alloc = [int(round((v / sum(kv_req)) * steps_v)) for v in kv_req]
            v_alloc[-1] += (steps_v - sum(v_alloc))
            
            rep_rows = []
            copy_txt = ""
            for i, h in enumerate(hl):
                k_u = k_alloc[i] * 8
                v_u = max(k_u + 8, v_alloc[i] * 8)
                pf = round(k_u / v_u, 3)
                
                rep_rows.append({
                    "Heat": f"#{h['no']}", "ON": h['on'], "TAP": h['tap'], "Time": h['dur'], 
                    "Ton": h['ton'], "kWh": k_u, "kVAh": v_u, "PF": f"{pf:.3f}"
                })
                copy_txt += (
                    f"--- Heat #{h['no']} ---\n"
                    f"Heat ON Time     : {h['on']}\n"
                    f"Heat Taping Time : {h['tap']} ({h['dur']})\n"
                    f"Kwh units        : {k_u}\n"
                    f"Kvah units       : {v_u}\n"
                    f"Pf.              : {pf:.3f}\n\n"
                )
            
            st.success("✅ Report Generated with ON/TAP Times")
            st.dataframe(pd.DataFrame(rep_rows), use_container_width=True, hide_index=True)
            st.code(copy_txt.strip(), language=None)
            
            if tot_kwh % 8 != 0:
                st.warning(f"Note: Total difference {tot_kwh} was adjusted to fit 8-factor multiples.")

# ==========================================
# TAB 2: 15-MINUTE KVAH REGISTER
# ==========================================
with t_reg:
    ### Register Inputs
    rc1, rc2 = st.columns(2)
    with rc1:
        ts_r = rc1.text_input("Start Time", "8:00 AM", key="rts")
        rs_r = gn(rc1.text_input("Start KVAH Reading", "249751728", key="rrs"))
        fa_r = rc1.selectbox("A-Line", ["A1", "A2"], key="rfa")
    with rc2:
        te_r = rc2.text_input("End Time", "10:30 AM", key="rte")
        re_r = gn(rc2.text_input("End KVAH Reading", "249775482", key="rre"))
        fb_r = rc2.selectbox("B-Line", ["B1", "B2"], index=1, key="rfb")
    
    tp_r = st.text_input("Tapping Times (Comma)", "8:25 AM, 9:45 AM", key="rtp")
    
    if st.button("🚀 Register Table Banayein", type="primary", use_container_width=True):
        ds, de = pt(ts_r), pt(te_r, pt(ts_r))
        if ds and de and re_r >= rs_r:
            diff_total = re_r - rs_r
            sl = []
            cur = ds
            while cur < de:
                nx = min(cur + timedelta(minutes=15), de)
                sl.append({"s": cur, "e": nx, "t": 0})
                cur = nx
            for x in tp_r.split(","):
                if dt := pt(x, ds):
                    for s in sl:
                        if s["s"] <= dt < s["e"]: s["t"] = 1
            
            wts = [(random.uniform(0.65, 0.82) if s["t"] else random.uniform(0.85, 1.35)) * (((s["e"]-s["s"]).total_seconds()/60)/15) for s in sl]
            tw = sum(wts)
            steps = [int(round((w/tw)*diff_total)) for w in wts]
            steps[-1] += (diff_total - sum(steps))
            
            curr_read = rs_r
            rw = [{"Time": ds.strftime('%I:%M %p'), "KVAH": str(rs_r), "Unit": "-"}]
            for i, s in enumerate(sl):
                curr_read += steps[i]
                rw.append({"Time": s["e"].strftime('%I:%M %p'), "KVAH": str(curr_read), "Unit": str(steps[i])})
            
            st.dataframe(pd.DataFrame(rw), use_container_width=True, hide_index=True)
            st.success(f"Register Completed for {len(sl)} slots.")
        else:
            st.error("Readings check karein!")

# DONE
