import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="16.5T Furnace App", page_icon="⚡")
st.title("⚡ My Load Maneger Furnace App")

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
                if d < b: d += timedelta(days=1)
            return d
        except: pass
    return None

def gn(v):
    d = "".join(c for c in str(v) if c.isdigit())
    return int(d) if d else 0

def gf(v, df=16.5):
    s = "".join(c for c in str(v) if c.isdigit() or c == ".")
    try: return float(s) if s else df
    except: return df

t1, t2 = st.tabs(["📋 15-Min Register", "🔥 16.5T Heat Report"])

with t1:
    c1, c2 = st.columns(2)
    ts, rs, fa = c1.text_input("Start Time", "8:00am"), c1.number_input("Start KVAH", value=249751728, step=1, format="%d"), c1.selectbox("A-Line", ["A1", "A2"])
    te, re, fb = c2.text_input("End Time", "10:30am"), c2.number_input("End KVAH", value=249775482, step=1, format="%d"), c2.selectbox("B-Line", ["B1", "B2"], index=1)
    uc = st.number_input("Cross-Verify Total (Optional)", value=0, step=1, format="%d")
    tp = st.text_input("Tapping Times", placeholder="8:25am, 9:45am")
    with st.expander("➕ Breakdown / Changeover / GLD"):
        b1, b2, b3 = st.columns(3)
        bf, bs, be = b1.selectbox("OFF Fur", ["None", "A", "B", "BOTH"]), b2.text_input("OFF Time"), b3.text_input("ON Time")
        k1, k2 = st.columns(2)
        ct, cm = k1.selectbox("Changeover", ["None", "A1->A2", "A2->A1", "B1->B2", "B2->B1"]), k2.text_input("Chg Time")
        g1, g2 = st.columns(2)
        gs, ge = g1.text_input("GLD Start"), g2.text_input("GLD End")

    if st.button("🚀 Register Table Banayein", type="primary", use_container_width=True):
        ds = pt(ts)
        de = pt(te, ds) if ds else None
        if not ds or not de or re < rs: st.error("Time/Reading galat hai!")
        else:
            tu, sl, cur = int(re - rs), [], ds
            while cur < de:
                nx = min(cur + timedelta(minutes=15), de)
                sl.append({"s": cur, "e": nx, "a": fa, "b": fb, "t": 0, "c": 0, "g": 0})
                cur = nx
            for x in tp.split(","):
                dt = pt(x, ds)
                if dt:
                    for s in sl:
                        if s["s"] <= dt < s["e"]: s["t"] = 1
            if bf != "None" and bs.strip():
                do, dn = pt(bs, ds), (de if be.strip().upper() in ("END", "") else pt(be, ds))
                if do and dn:
                    for s in sl:
                        if s["s"] < dn and s["e"] > do:
                            if bf in ("A", "BOTH"): s["a"] = "OFF"
                            if bf in ("B", "BOTH"): s["b"] = "OFF"
            if ct != "None" and cm.strip():
                dc = pt(cm, ds)
                if dc:
                    for s in sl:
                        if s["s"] >= dc:
                            if ct == "A1->A2" and s["a"] != "OFF": s["a"] = "A2"
                            elif ct == "A2->A1" and s["a"] != "OFF": s["a"] = "A1"
                            elif ct == "B1->B2" and s["b"] != "OFF": s["b"] = "B2"
                            elif ct == "B2->B1" and s["b"] != "OFF": s["b"] = "B1"
                        if s["s"] <= dc < s["e"]: s["c"] = 1
            if gs.strip() and ge.strip():
                d1, d2 = pt(gs, ds), pt(ge, ds)
                if d1 and d2:
                    for s in sl:
                        if s["s"] < d2 and s["e"] > d1: s["g"] = 1
            wt, pw = [], 0.0
            for i, s in enumerate(sl):
                dr = ((s["e"] - s["s"]).total_seconds() / 60.0) / 15.0
                ao, bo = s["a"] == "OFF", s["b"] == "OFF"
                if ao and bo: w = random.uniform(0.05, 0.12)
                elif ao or bo: w = random.uniform(0.32, 0.44) if s["t"] else random.uniform(0.48, 0.72)
                elif s["g"]: w = random.uniform(0.50, 0.85)
                elif s["t"]: w = random.uniform(0.62, 0.78)
                elif s["c"]: w = random.uniform(0.58, 0.76)
                else:
                    w = random.uniform(*[(0.82, 0.96), (1.04, 1.22), (1.28, 1.48)][i % 3])
                    if abs(w - pw) < 0.1: w += 0.14 if w < 1.25 else -0.15
                pw = w; wt.append(w * dr)
            tw, rd, cr = sum(wt), [int(rs)], int(rs)
            for i in range(len(sl)):
                cr = int(re) if i == len(sl) - 1 else cr + round((wt[i] / tw) * tu)
                rd.append(cr)
            rw = [{"Time": ds.strftime('%I:%M %p').lstrip('0'), "KVAH": str(int(rs)), "Unit": "-", "Status": f"{fa}+{fb}"}]
            for i, s in enumerate(sl):
                lb = f"{s['a']}+{s['b']}" + (" (GLD)" if s["g"] else (" (Tap)" if s["t"] else ""))
                rw.append({"Time": s["e"].strftime('%I:%M %p').lstrip('0'), "KVAH": str(rd[i+1]), "Unit": str(rd[i+1]-rd[i]), "Status": lb})
            st.dataframe(pd.DataFrame(rw), use_container_width=True, hide_index=True)
            st.success(f"Total Units: {tu}")
            if uc > 0: st.info("✅ MATCH!" if tu == int(uc) else f"⚠️ Farq: {tu-int(uc):+d}")

with t2:
    st.caption("⚡ 5800 kW Load | Melting Tonnage × Condition (593 / 698 / 768 u/T)")
    rm = st.radio("Reading Mode:", ["Direct (Diff × 8)", "Decimal ((Diff ÷ 10) × 8)"], horizontal=True)
    h1, h2 = st.columns(2)
    ks, vs = gn(h1.text_input("Start kWh", "16013252")), gn(h1.text_input("Start kVAh", "16891404"))
    ke, ve = gn(h2.text_input("End kWh", "16017723")), gn(h2.text_input("End kVAh", "16896265"))
    nh = st.selectbox("Kitni Heats hain?", list(range(1, 16)), index=3)
    hl = []
    for i in range(1, int(nh) + 1):
        st.markdown(f"**Heat #{i}**")
        r1, r2 = st.columns([1.4, 1])
        ht = r1.selectbox("Condition", ["Normal (~698 u/T)", "Fast/Hot (~593 u/T)", "Heavy/Slow (~768 u/T)", "Sintering"], key=f"t_{i}")
        gc = r2.checkbox("⚡ GLD / Trip?", key=f"g_{i}")
        x1, x2, x3, x4 = st.columns(4)
        ton_m = gf(x1.text_input("Melt (Ton)", "16.5", key=f"m_{i}"), 16.5)
        on_t = x2.text_input("ON", "8:00am", key=f"o_{i}")
        tp_t = x3.text_input("TAP", "10:00am", key=f"p_{i}")
        bd_m = gn(x4.text_input("BD(m)", "0", key=f"b_{i}"))
        hl.append((i, ht, gc, ton_m, on_t, tp_t, bd_m))

    st.button("🔥 GENERATE / REFRESH HEAT REPORT", type="primary", use_container_width=True)
    dv = 10.0 if "Decimal" in rm else 1.0
    tk, tv = round((ke - ks) / dv), round((ve - vs) / dv)
    if ke <= ks or ve <= vs or tk >= tv:
        st.error("Reading check karein! (End > Start aur kWh Diff < kVAh Diff hona chahiye)")
    else:
        ph, fd, ok = [], None, 1
        for i, ht, gc, tm_ton, on, tp2, bm in hl:
            d1 = pt(on, fd)
            if i == 1: fd = d1
            d2 = pt(tp2, d1) if d1 else None
            if not d1 or not d2: st.warning(f"Heat #{i} time galat!"); ok = 0; break
            tm = (d2 - d1).total_seconds() / 60.0
            if tm <= 0: tm = 120.0
            rm_m = max(15.0, tm - bm)
            if "593" in ht: ut = random.uniform(585, 612)
            elif "768" in ht: ut = random.uniform(748, 778)
            elif "Sintering" in ht: ut = random.uniform(785, 845)
            else: ut = random.uniform(682, 712)
            if gc: ut += random.uniform(25, 45)
            # Actual Melting Tonnage x u/T + 5800kW Running Time blend
            kw_t = (tm_ton * ut * 0.75) + (((rm_m / 60.0) * 5650.0) * 0.25) + (bm * 6.0)
            if "Sintering" in ht and gc: pfr, lb = (0.800, 0.855), "Sint+GLD"
            elif "Sintering" in ht: pfr, lb = (0.810, 0.890), "Sintering"
            elif gc: pfr, lb = (0.865, 0.915), "GLD"
            else: pfr, lb = (0.945, 0.988), ht.split()[0]
            ph.append({"n": i, "h": lb, "ton": tm_ton, "t": d2, "ekw": kw_t, "ekv": kw_t / random.uniform(*pfr), "pfr": pfr})

        if ok and ph:
            sk, sv = tk / sum(x["ekw"] for x in ph), tv / sum(x["ekv"] for x in ph)
            for x in ph:
                x["vs"] = max(10, round(x["ekv"] * sv))
                lo, hi = x["pfr"]
                x["ks"] = max(round(x["vs"] * lo), min(round(x["vs"] * hi), round(x["ekw"] * sk)))
            dvs = tv - sum(x["vs"] for x in ph)
            for _ in range(30000):
                if dvs == 0: break
                ix = random.randrange(len(ph))
                st_v = 1 if dvs > 0 else -1
                if ph[ix]["vs"] + st_v > ph[ix]["ks"] + 1: ph[ix]["vs"] += st_v; dvs -= st_v
            dks = tk - sum(x["ks"] for x in ph)
            for _ in range(40000):
                if dks == 0: break
                ix = random.randrange(len(ph))
                lo, hi = ph[ix]["pfr"]
                mn, mx = max(1, round(ph[ix]["vs"] * lo)), min(ph[ix]["vs"] - 1, round(ph[ix]["vs"] * hi))
                if dks > 0 and ph[ix]["ks"] < mx: ph[ix]["ks"] += 1; dks -= 1
                elif dks < 0 and ph[ix]["ks"] > mn: ph[ix]["ks"] -= 1; dks += 1
            for _ in range(40000):
                if dks == 0: break
                ix = random.randrange(len(ph))
                hmx, hmn = max(1, int(ph[ix]["vs"] * 0.994)), max(1, int(ph[ix]["vs"] * 0.760))
                if dks > 0 and ph[ix]["ks"] < hmx: ph[ix]["ks"] += 1; dks -= 1
                elif dks < 0 and ph[ix]["ks"] > hmn: ph[ix]["ks"] -= 1; dks += 1

            tot_ton = sum(x["ton"] for x in ph)
            st.success(f"✅ Total Melt: {tot_ton:.2f} T | Kwh: {tk*8} ({round((tk*8)/tot_ton)} u/T) | Kvah: {tv*8} | Pf: {(tk/tv):.3f}")
            hr, txt = [], ""
            for x in ph:
                ku, vu = x["ks"] * 8, x["vs"] * 8
                pf, tc = (ku / vu if vu > 0 else 0), x["t"].strftime('%I:%M %p').lstrip('0')
                hr.append({"Heat": f"#{x['n']} ({x['h']})", "Ton": x["ton"], "TAP": tc, "u/Ton": round(ku / x["ton"]), "Kwh": ku, "Kvah": vu, "PF": f"{pf:.3f}"})
                txt += f"--- Heat #{x['n']} ---\nHeat Taping Time : {tc}\nMelting Ton      : {x['ton']} T\nKwh units        : {ku}\nKvah units       : {vu}\nPf.              : {pf:.3f}\n\n"
            st.dataframe(pd.DataFrame(hr), use_container_width=True, hide_index=True)
            st.code(txt.strip(), language=None)
    st.markdown("<br><br><br>", unsafe_allow_html=True)
# DONE
