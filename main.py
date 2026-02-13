import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# [데이터] 보스의 마스터 데이터 (결혼식 목표 + 평생 관리)
MY_DATA = {
    "wedding": "2026-05-30",
    "health": {"current": 125.0, "target": 90.0},
    "lifecycle": {
        "면도기/칫솔": {"last": "2026-02-06", "period": 21}, # 1주일 전 교체 반영
        "이불세탁": {"last": "2026-01-30", "period": 14},   # 2주 전 세탁 반영
        "로봇청소기": {"last": "2026-02-12", "period": 1}    # 어제 가동 반영
    }
}

st.set_page_config(page_title="JARVIS Life Manager", layout="wide")
st.title("🤵 JARVIS : 보스 전용 라이프 관리 시스템")

# --- 섹션 1: 5월 30일 결혼식 집중 감량 ---
st.header("🎯 Wedding D-Day & Weight Loss")
target_dt = datetime.strptime(MY_DATA["wedding"], "%Y-%m-%d")
d_day = (target_dt - datetime.now()).days
remain_weight = MY_DATA["health"]["current"] - MY_DATA["health"]["target"]

col1, col2 = st.columns(2)
with col1:
    st.metric("결혼식까지", f"D-{d_day}일")
with col2:
    st.metric("최종 감량 목표", f"{remain_weight}kg", delta="남은 목표치", delta_color="inverse")

# --- 섹션 2: 평생 주기 관리 (면도기, 칫솔, 세탁 등) ---
st.header("🔄 Life Cycle Management")
st.write("주기적으로 교체하거나 관리해야 할 항목들입니다.")

cols = st.columns(3)
for i, (item, info) in enumerate(MY_DATA["lifecycle"].items()):
    last_date = datetime.strptime(info["last"], "%Y-%m-%d")
    next_date = last_date + timedelta(days=info["period"])
    remain_days = (next_date - datetime.now()).days
    
    with cols[i % 3]:
        if remain_days <= 0:
            st.error(f"🚨 {item}\n\n오늘 관리할 타이밍입니다!")
        else:
            st.success(f"✅ {item}\n\n{remain_days}일 남았습니다. (예정: {next_date.strftime('%m/%d')})")

st.markdown("---")
st.caption("🤵 보스, 로봇청소기는 주기에 맞춰 어제 잘 돌리셨더군요. 아주 훌륭합니다.")
