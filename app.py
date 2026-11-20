import streamlit as st
import random
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Furnace App", page_icon="⚡", layout="centered")
st.title("⚡ Furnace Log & Meter App")

def parse_time(t_str, base_dt=None):
    if not t_str:
        return None
    t_str = str(t_str).strip().upper().replace(".", ":")
    for sfx in ("AM", "PM"):
        if t_str.endswith(sfx) and ":" not in t_str:
            p = t_str[:-2].strip()
            if p.isdigit():
                t_str = f"{p}:00 {sfx}"
    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
        try:
            dt = datetime.strptime(t_str, fmt)
            if base_dt:
                dt = dt.replace(year=base_dt.year, month=base_dt.month, day=base_dt.day)
                if dt < base_dt:
                    dt += timedelta(days=1)
            return dt
        except ValueError:
            continue
    return None

def get_num(v):
    d = "".join(c for c in str(v) if c.isdigit())
    return int(d) if d else 0

tab1, tab2 = st.tabs(["📋 15-Min Register", "🔥 Heat-by-Heat Report"])

with tab1:
    c1, c2 = st.columns(2)
    t1_s = c1.text_input("Start Time", "8:00am")
    r1_s = c1.number_input("Start KVAH", value=249751728, step=1, format="%d")
    f_a = c1.selectbox("A-Line", ["A1", "A2"])
    t1_e = c2.text_input("End Time", "10:30am")
    r1_e = c2.number_input("End KVAH", value=249775482, step=1, format="%d")
    f_b = c2.selectbox("B-Line", ["B1", "B2"], index=1)

    u_chk = st.number_input("Cross-Verify Total (Optional)", value=0, step=1, format="%d")
    tap_in = st.text_input("Tapping Times (comma lagayein)", placeholder="8:25am, 9:45am")

    with st.expander("➕ Breakdown / Changeover / GLD"):
        bc1, bc2, bc3 = st.columns(3)
        bd_f = bc1.selectbox("OFF Fur", ["None", "A", "B", "BOTH"])
        bd_s = bc2.text_input("OFF Time")
        bd_e = bc3.text_input("ON Time")
        cc1, cc2 = st.columns(2)
        ch_t = cc1.selectbox("Changeover", ["None", "A1->A2", "A2->A1", "B1->B2", "B2->B1"])
        ch_tm = cc2.text_input("Chg Time")
        gc1, gc2 = st.columns(2)
        gld_s = gc1.text_input("GLD Start Time", placeholder="9:00am")
        gld_e = gc2.text_input("GLD End Time", placeholder="9:45am")

    if st.button("🚀 Register Table Banayein", type="primary", use_container_width=True):
        ds = parse_time(t1_s)
        de = parse_time(t1_e, ds) if ds else None
        if not ds or not de or r1_e < r1_s:
            st.error("Time ya Reading sahi daalein!")
        else:
            tot_u = int(r1_e - r1_s)
            slots, curr = [], ds
            while curr < de:
                nxt = min(curr + timedelta(minutes=15), de)
                slots.append({"s": curr, "e": nxt, "a": f_a, "b": f_b, "tap": False, "chg": False, "gld": False})
                curr = nxt
            for ti in tap_in.split(","):
                dt_t = parse_time(ti, ds)
                if dt_t:
                    for s in slots:
                        if s["s"] <= dt_t < s["e"]: s["tap"] = True
            if bd_f != "None" and bd_s.strip():
                doff = parse_time(bd_s, ds)
                don = de if bd_e.strip().upper() in ("END", "") else parse_time(bd_e, ds)
                if doff and don:
                    for s in slots:
                        if s["s"] < don and s["e"] > doff:
                            if bd_f in ("A", "BOTH"): s["a"] = "OFF"
                            if bd_f in ("B", "BOTH"): s["b"] = "OFF"
            if ch_t != "None" and ch_tm.strip():
                dc = parse_time(ch_tm, ds)
                if dc:
                    for s in slots:
                        if s["s"] >= dc:
                            if ch_t == "A1->A2" and s["a"] != "OFF": s["a"] = "A2"
                            elif ch_t == "A2->A1" and s["a"] != "OFF": s["a"] = "A1"
                            elif ch_t == "B1->B2" and s["b"] != "OFF": s["b"] = "B2"
                            elif ch_t == "B2->B1" and s["b"] != "OFF": s["b"] = "B1"
                        if s["s"] <= dc < s["e"]: s["chg"] = True
            if gld_s.strip() and gld_e.strip():
                dgs, dge = parse_time(gld_s, ds), parse_time(gld_e, ds)
                if dgs and dge:
                    for s in slots:
                        if s["s"] < dge and s["e"] > dgs: s["gld"] = True

            wts, pw = [], 0.0
            for idx, s in enumerate(slots):
                dr = ((s["e"] - s["s"]).total_seconds() / 60.0) / 15.0
                ao, bo = (s["a"] == "OFF"), (s["b"] == "OFF")
                if ao and bo: w = random.uniform(0.05, 0.12)
                elif ao or bo: w = random.uniform(0.32, 0.44) if s["tap"] else random.uniform(0.48, 0.72)
                elif s["gld"]: w = random.uniform(0.50, 0.85)
                elif s["tap"]: w = random.uniform(0.62, 0.78)
                elif s["chg"]: w = random.uniform(0.58, 0.76)
                else:
                    bnds = [(0.82, 0.96), (1.04, 1.22), (1.28, 1.48)]
                    w = random.uniform(*bnds[idx % 3])
                    if abs(w - pw) < 0.10: w += 0.14 if w < 1.25 else -0.15
                pw = w
                wts.append(w * dr)

            tw = sum(wts)
            rds, cr = [int(r1_s)], int(r1_s)
            for i in range(len(slots)):
                cr = int(r1_e) if i == len(slots) - 1 else cr + round((wts[i] / tw) * tot_u)
                rds.append(cr)

            rows = [{"Time": ds.strftime('%I:%M %p').lstrip('0'), "KVAH": str(int(r1_s)), "Unit": "-", "Status": f"{f_a}+{f_b}"}]
            for i, s in enumerate(slots):
                st_lb = f"{s['a']}+{s['b']}" + (" (GLD)" if s["gld"] else (" (Tap)" if s["tap"] else ""))
                rows.append({"Time": s["e"].strftime('%I:%M %p').lstrip('0'), "KVAH": str(rds[i+1]), "Unit": str(rds[i+1]-rds[i]), "Status": st_lb})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.success(f"Total Units: {tot_u}")
            if u_chk > 0:
                df_u = tot_u - int(u_chk)
                st.info("✅ 100% MATCH!" if df_u == 0 else f"⚠️ Farq: {df_u:+d} units")

with tab2:
    MF = 8
    hc1, hc2 = st.columns(2)
    kws_t = hc1.text_input("Start kWh", "160132528")
    kvahs_t = hc1.text_input("Start kVAh", "168914048")
    kwe_t = hc2.text_input("End kWh", "160177232")
    kvahe_t = hc2.text_input("End kVAh", "168962656")
    n_h = st.selectbox("Kitni Heats hain?", list(range(1, 16)), index=2)

    st.button("🔥 GENERATE / REFRESH HEAT REPORT", type="primary", use_container_width=True)
    rep_spot = st.container()
    st.markdown("---")

    h_list = []
    for i in range(1, int(n_h) + 1):
        st.markdown(f"**Heat #{i}**")
        gld_chk = st.checkbox(f"⚡ Is Heat #{i} mein GLD / Tripping problem aayi?", key=f"gld_{i}")
        x1, x2, x3, x4 = st.columns([1.2, 1, 1, 0.8])
        ht = x1.selectbox("Type", ["Normal", "Sintering"], key=f"t_{i}")
        ton = x2.text_input("ON", "8:00am", key=f"o_{i}")
        ttap = x3.text_input("TAP", "10:00am", key=f"p_{i}")
        bd = x4.text_input("BD(m)", "0", key=f"b_{i}")
        final_type = "GLD" if gld_chk else ht
        h_list.append((i, final_type, ton, ttap, bd))

    kws, kwe = get_num(kws_t), get_num(kwe_t)
    kvs, kve = get_num(kvahs_t), get_num(kvahe_t)
    with rep_spot:
        if kwe <= kws or kve <= kvs:
            st.error("End Reading badi honi chahiye!")
        else:
            tkw = round(((kwe - kws) / 10.0) * MF)
            tkv = round(((kve - kvs) / 10.0) * MF)
            ph, fdt, ok = [], None, True
            for i, ht, ton, ttap, bd in h_list:
                don = parse_time(ton, fdt)
                if i == 1: fdt = don
                dtp = parse_time(ttap, don) if don else None
                if not don or not dtp:
                    st.warning(f"Heat #{i} ka time sahi daalein!")
                    ok = False
                    break
                bdm = float(get_num(bd))
                dur = 60.0 if (dtp - don).total_seconds() <= 0 else (dtp - don).total_seconds() / 60.0
                mult = 0.72 if ht == "Sintering" else (0.78 if ht == "GLD" else 1.0)
                var = random.uniform(0.88, 1.08) if ht == "GLD" else random.uniform(0.96, 1.04)
                w = ((max(5.0, dur - bdm) * mult) + (bdm * 0.5)) * var
                ph.append({"no": i, "ht": ht, "tap": dtp, "w": w})

            if ok and ph:
                tw, rkv = sum(x["w"] for x in ph), tkv
                for idx, x in enumerate(ph):
                    x["kvu"] = rkv if idx == len(ph) - 1 else round((x["w"] / tw) * tkv)
                    if idx < len(ph) - 1: rkv -= x["kvu"]
                rkw, nidx = tkw, []
                for idx, x in enumerate(ph):
                    if x["ht"] == "Sintering":
                        x["kwu"] = round(x["kvu"] * random.uniform(0.800, 0.900))
                        rkw -= x["kwu"]
                    elif x["ht"] == "GLD":
                        x["kwu"] = round(x["kvu"] * random.uniform(0.860, 0.925))
                        rkw -= x["kwu"]
                    else:
                        nidx.append(idx)
                if not nidx: ph[-1]["kwu"] += rkw
                else:
                    nw = [ph[j]["kvu"] * random.uniform(0.985, 1.015) for j in nidx]
                    tnw = sum(nw)
                    for k, j in enumerate(nidx):
                        v = rkw if k == len(nidx) - 1 else min(ph[j]["kvu"], round((nw[k] / tnw) * rkw))
                        ph[j]["kwu"] = v
                        if k < len(nidx) - 1: rkw -= v

                st.success(f"✅ Total Kwh: {tkw} | Kvah: {tkv} | Pf: {(tkw/tkv):.3f}")
                h_rows = []
                for x in ph:
                    pf = x["kwu"] / x["kvu"] if x["kvu"] > 0 else 0.0
                    tc = x["tap"].strftime('%I:%M %p').lstrip('0')
        
