import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# [데이터] 보스의 모든 정보 집대성
MY_DATA = {
    "wedding": "2026-05-30",
    "health": {"current": 125.0, "target": 90.0},
    "assets": {
        "cash": 492918,
        "savings": {"청년도약": 14700000, "주택청약": 2540000, "보증금(내돈)": 45850000},
        "liabilities": {"전세대출": 100000000, "마이너스통장": 3000000, "학자금": 1247270},
    },
    "inventory": [
        "토마토 페이스트(10캔)", "발아현미밥(1)", "삼치/닭다리살(각 4팩)", 
        "단백질쉐이크(9개)", "라면(12봉)", "치아씨드/아몬드/코코넛 등"
    ],
    "lifecycle": {
        "면도기/칫솔": {"last": "2026-02-06", "period": 21},
        "이불세탁": {"last": "2026-01-30", "period": 14},
        "로봇청소기": {"last": "2026-02-12", "period": 2}
    }
}

st.set_page_config(page_title="JARVIS Full Report", layout="wide")
st.title("🤵 JARVIS : 보스 전용 올인원 대시보드")

# --- 1. 결혼 및 건강 (최상단 고정) ---
st.subheader("🏁 결혼식 D-Day & 건강 목표")
target_dt = datetime.strptime(MY_DATA["wedding"], "%Y-%m-%d")
d_day = (target_dt - datetime.now()).days
col_h1, col_h2 = st.columns(2)
col_h1.metric("결혼식까지", f"D-{d_day}일")
col_h2.metric("목표 감량", f"{MY_DATA['health']['current'] - MY_DATA['health']['target']}kg", delta_color="inverse")
st.divider()

# --- 2. 자산 및 부채 (객관화) ---
st.subheader("💰 자산 및 부채 현황")
total_a = MY_DATA["assets"]["cash"] + sum(MY_DATA["assets"]["savings"].values())
total_l = sum(MY_DATA["assets"]["liabilities"].values())
col_a1, col_a2, col_a3 = st.columns(3)
col_a1.metric("총 자산", f"{total_a:,.0f}원")
col_a2.metric("총 부채", f"{total_l:,.0f}원")
col_a3.metric("순자산", f"{total_a - total_l:,.0f}원")
st.divider()

# --- 3. 평생 관리 (주기성 항목) ---
st.subheader("🔄 주기적 관리 리스트")
cols = st.columns(3)
for i, (item, info) in enumerate(MY_DATA["lifecycle"].items()):
    next_due = datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"])
    remain = (next_due - datetime.now()).days
    with cols[i % 3]:
        if remain <= 0: st.error(f"🚨 {item}: 관리 필요!")
        else: st.success(f"✅ {item}: {remain}일 남음")
st.divider()

# --- 4. 주방 재고 (현황 파악) ---
st.subheader("📦 주요 식재료 현황")
st.write(", ".join(MY_DATA["inventory"]))

st.markdown("---")
st.caption("🤵 보스, 모든 데이터가 객관화되었습니다. 지시하실 사항이 있으십니까?")
