import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# [수정사항] 이불세탁 날짜 반영: 2026-02-04
FIXED_DATA = {
    "lifecycle": {
        "면도날": {"last": "2026-02-06", "period": 21}, 
        "칫솔": {"last": "2026-02-06", "period": 90}, 
        "이불세탁": {"last": "2026-02-04", "period": 14} # 보스 요청대로 수정 완료
    }
}

# --- 구글 시트 연동 로직 (미래 설계) ---
# import gspread
# def sync_to_sheets(data):
#     # 이 함수가 실행되면 보스의 구글 시트에 "2026-02-13 | 쿼파치 | 1120kcal" 가 저장됩니다.
#     pass

st.set_page_config(page_title="자비스 v5.0", layout="wide")

# CSS: 보스가 좋아하시는 특대 숫자 및 우측 정렬 유지
st.markdown("""
    <style>
    * { font-family: 'Arial Black', sans-serif !important; }
    [data-testid="stTable"] td:nth-child(1) { font-size: 50px !important; color: #FF4B4B !important; font-weight: 900; text-align: center; }
    [data-testid="stTable"] td:nth-child(2) { text-align: right !important; font-size: 20px; }
    h2 { font-size: 30px !important; border-left: 10px solid #FF4B4B; padding-left: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 자동 초기화 로직 (시트 연동 시 활성화) ---
today = datetime.now().strftime('%Y-%m-%d')
this_month = datetime.now().strftime('%Y-%m')

st.title(f"자비스 v5.0 : {today} 리포트")

# 1. 생활 주기 (이불세탁 2/4 기준 D-Day 계산)
st.header("5. 생활 주기 관리")
l_rows = []
for item, info in FIXED_DATA["lifecycle"].items():
    rem = (datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"]) - datetime.now()).days
    l_rows.append({"항목": item, "최근수행": info["last"], "상태": "🚨 점검" if rem <= 0 else "✅ 정상", "D-Day": f"{rem}일"})
st.table(pd.DataFrame(l_rows).assign(순번=range(1, 4)).set_index('순번'))

# --- 보스를 위한 가이드 ---
st.info(f"💡 현재 이불세탁일이 2월 4일로 업데이트되어 D-Day가 자동 계산됩니다.")
