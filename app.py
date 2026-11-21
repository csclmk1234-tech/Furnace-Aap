import streamlit as st, random, pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Furnace Energy App", page_icon="⚡", layout="wide")
st.title("⚡ 16.5T Furnace Heat-by-Heat Reconstructor")

# Standard Parameters
CONDITIONS = {
    "Normal Running": {"pf": 0.962, "wt": 1.00},
    "Sintering (Lining Heat)": {"pf": 0.840, "wt": 1.25},
    "GLD / Tripping Problem": {"pf": 0.880, "wt": 1.15},
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
                if d < b: d += timedelta(days=1)
            return d
        except: pass
    return None

def gn(v):
    d = "".join(c for c in str(v) if c.isdigit())
    return int(d) if d else 0

# --- STEP 1: READING & TOTAL CALCULATION ---
st.markdown("### 1️⃣ Reading Se Total Units Nikalein")
r_col1, r_col2, r_col3 = st.columns([2, 2, 1.2])

with r_col1:
    skw = gn(st.text_input("Start kWh Reading", "160944480"))
    skv = gn(st.text_input("Start kVAh Reading", "169767296"))
with r_col2:
    ekw = gn(st.text_input("End kWh Reading", "160983200"))
    ekv = gn(st.text_input("End kVAh Reading", "169807360"))
with r_col3:
    MF = st.number_input("Meter Factor (MF)", value=1.0, step=0.1)

diff_kw = ekw - skw
diff_kv = ekv - skv
tot_kwh = int(diff_kw * MF)
tot_kvah = int(diff_kv * MF)
overall_pf = round(tot_kwh / tot_kvah, 3) if tot_kvah > 0 else 0.0

if tot_kwh > 0:
    st.info(f"📊 **TOTAL UNITS TO DIVIDE:** kWh = `{tot_kwh:,}` | kVAh = `{tot_kvah:,}` | PF = `{overall_pf:.3f}`")
else:
    st.error("⚠️ End Reading check karein (Start se badi honi chahiye)")

# --- STEP 2: NUMBER OF HEATS ---
st.markdown("---")
nh = st.number_input("2️⃣ Yeh units kitni heats mein divide karni hain?", 1, 20, 4)

# --- STEP 3: HEAT DETAILS ---
st.markdown("### 3️⃣ Har Heat ki Situation Daalein")
hl = []
base_t = datetime.strptime("08:00 AM", "%I:%M %p")

for i in range(1, int(nh) + 1):
    with st.container(border=True):
        st.markdown(f"**Heat #{i}**")
        c1, c2, c3, c4, c5 = st.columns([1, 1, 1.2, 1, 1])
        ton = c1.number_input(f"Melting (Ton)", 1.0, 22.0, 16.5, 0.1, key=f"tn_{i}")
        tp_t = c2.text_input(f"Tapping Time", (base_t + timedelta(minutes=110*i)).strftime("%I:%M %p"), key=f"tt_{i}")
        cond = c3.selectbox("Situation", list(CONDITIONS.keys()), key=f"cd_{i}")
        bd_min = c4.number_input("Breakdown (min)", 0, 300, 0, 5, key=f"bm_{i}")
        target_pf = c5.number_input("Target PF", 0.600, 0.980, CONDITIONS[cond]["pf"], 0.001, format="%.3f", key=f"pf_{i}")
        hl.append({"no": i, "ton": ton, "tap": tp_t, "cond": cond, "bd": bd_min, "tpf": target_pf, "wt": CONDITIONS[cond]["wt"]})

# --- STEP 4: RECONSTRUCTION LOGIC ---
if st.button("🔥 GENERATE HEAT-BY-HEAT REPORT", type="primary", use_container_width=True):
    # Calculate Weights for kWh distribution
    # Logic: Energy = (Tons * Condition Weight) + (Breakdown mins * holding power factor)
    weights = []
    for h in hl:
        w = (h["ton"] * h["wt"] * random.uniform(0.98, 1.02)) + (h["bd"] * 0.4)
        weights.append(w)
    
    tw = sum(weights)
    
    # Split kWh Units
    kw_u = [int(round((w / tw) * tot_kwh)) for w in weights]
    # Adjustment for exact total
    kw_u[-1] += (tot_kwh - sum(kw_u))
    
    # Split kVAh Units based on individual target PFs
    kv_raw = [kw_u[i] / hl[i]["tpf"] for i in range(len(hl))]
    tkv_raw = sum(kv_raw)
    kv_u = [int(round((v / tkv_raw) * tot_kvah)) for v in kv_raw]
    # Adjustment for exact total
    kv_u[-1] += (tot_kvah - sum(kv_u))

    # Output Display
    st.success("✅ Sabhi Heats ka data situation ke hisab se divide ho gaya hai!")
    
    report_rows = []
    copy_text = ""
    
    for i, h in enumerate(hl):
        ku, vu = kw_u[i], max(kw_u[i] + 1, kv_u[i])
        actual_pf = round(ku / vu, 3)
        u_ton = round(ku / h["ton"], 1)
        
        report_rows.append({
            "Heat": f"#{h['no']}",
            "Tap Time": h["tap"],
            "Situation": h["cond"],
            "Melt Ton": h["ton"],
            "u/Ton": u_ton,
            "kWh Units": ku,
            "kVAh Units": vu,
            "PF": actual_pf
        })
        
        copy_text += (
            f"--- Heat #{h['no']} ---\n"
            f"Heat Taping Time : {h['tap']}\n"
            f"Melting Ton      : {h['ton']} T\n"
            f"Kwh units        : {ku}\n"
            f"Kvah units       : {vu}\n"
            f"Pf.              : {actual_pf:.3f}\n\n"
        )

    st.dataframe(pd.DataFrame(report_rows), use_container_width=True, hide_index=True)
    
    st.markdown("#### 📲 Copy Report (Register/WhatsApp Format):")
    st.code(copy_text.strip(), language=None)

# DONE
