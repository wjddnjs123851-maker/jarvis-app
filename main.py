import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. 고정 마스터 데이터 (이불세탁 2/4, 로봇청소기 제외)
FIXED_DATA = {
    "profile": {"항목": ["나이", "거주", "상태", "결혼예정일"], "내용": ["32세", "평택 원평동", "공무원 발령 대기 중", "2026-05-30"]},
    "health": {"항목": ["현재 체중", "목표 체중", "주요 관리", "식단 금기"], "내용": ["125.0kg", "90.0kg", "고지혈증/ADHD", "생굴/멍게"]},
    "assets": {
        "savings": {"청년도약계좌": 14700000, "주택청약": 2540000, "전세보증금": 145850000},
        "liabilities": {"전세대출": 100000000, "마이너스통장": 3000000, "학자금대출": 1247270},
        "stocks": {"삼성전자": 46, "SK하이닉스": 6, "삼성중공업": 88, "동성화인텍": 21},
        "crypto": {"BTC": 0.00181400, "ETH": 0.03417393}
    },
    "lifecycle": {
        "면도날": {"last": "2026-02-06", "period": 21}, 
        "칫솔": {"last": "2026-02-06", "period": 90}, 
        "이불세탁": {"last": "2026-02-04", "period": 14} 
    },
    "kitchen": {
        "소스/캔": "토마토페이스트, 나시고랭, S&B카레, 뚝심, 땅콩버터",
        "단백질": "냉동삼치, 냉동닭다리, 관찰레, 북어채, 단백질쉐이크",
        "곡물/면": "파스타면, 소면, 쿠스쿠스, 라면, 우동, 쌀/카무트",
        "신선/기타": "김치4종, 아사이베리, 치아씨드, 향신료, 치즈"
    }
}

EXPENSE_CATS = ["식비(집밥)", "식비(배달)", "식비(외식/편의점)", "담배", "생활용품", "주거/통신/이자", "보험/청약", "주식/적금", "주유/교통", "건강/의료", "기타"]
TARGET = {"칼로리": 2000, "단백질": 150, "지방": 65, "탄수화물": 300, "식이섬유": 25, "수분": 2000}

# 2. 세션 상태 초기화 (한글 키값 적용)
if 'cash' not in st.session_state: st.session_state.cash = 492918
if 'consumed' not in st.session_state: st.session_state.consumed = {"칼로리": 0, "단백질": 0, "지방": 0, "탄수화물": 0, "식이섬유": 0, "수분": 0}
if 'expenses' not in st.session_state: st.session_state.expenses = {cat: 0 for cat in EXPENSE_CATS}
if 'master_log' not in st.session_state: st.session_state.master_log = []

st.set_page_config(page_title="자비스 v5.7", layout="wide")

# CSS: 특대 숫자 및 우측 정렬 유지
st.markdown("""<style>
    * { font-family: 'Arial Black', sans-serif !important; }
    [data-testid="stTable"] td:nth-child(1) { font-size: 50px !important; color: #FF4B4B !important; font-weight: 900; text-align: center; }
    [data-testid="stTable"] td:nth-child(2), [data-testid="stTable"] td:nth-child(3) { text-align: right !important; font-size: 20px !important; }
    h2 { font-size: 30px !important; border-left: 10px solid #FF4B4B; padding-left: 15px; margin-top: 40px !important; }
    [data-testid="stMetricValue"] { text-align: right !important; font-size: 40px !important; }
</style>""", unsafe_allow_html=True)

st.title(f"자비스 통합 리포트 : {datetime.now().strftime('%Y-%m-%d')} (원평동 10°C ☀️)")

# --- 사이드바 ---
with st.sidebar:
    st.header("실시간 기록")
    with st.form("hangle_input"):
        exp_val = st.number_input("지출 금액", min_value=0, step=100)
        exp_cat = st.selectbox("카테고리", EXPENSE_CATS)
        st.divider()
        meal_in = st.text_input("음식명/음료")
        
        if st.form_submit_button("반영"):
            # 로그 데이터 생성 (전체 한글화)
            entry = {"날짜": datetime.now().strftime('%Y-%m-%d'), "시간": datetime.now().strftime('%H:%M'), 
                     "항목": meal_in or exp_cat, "금액": exp_val, 
                     "칼로리": 0, "단백질": 0, "지방": 0, "탄수화물": 0, "식이섬유": 0, "수분": 0}
            
            if "물" in meal_in: entry["수분"] = 500
            elif "쿼파치" in meal_in: entry.update({"칼로리": 1120, "단백질": 50, "지방": 55, "탄수화물": 110, "식이섬유": 5})
            elif meal_in: entry.update({"칼로리": 600, "단백질": 25, "지방": 20, "탄수화물": 70, "식이섬유": 3})
            
            st.session_state.cash -= exp_val
            st.session_state.expenses[exp_cat] += exp_val
            for k in ["칼로리", "단백질", "지방", "탄수화물", "식이섬유", "수분"]:
                st.session_state.consumed[k] += entry[k]
            
            st.session_state.master_log.append(entry)
            st.rerun()

    if st.session_state.master_log:
        st.divider()
        st.download_button("📂 통합 마스터 로그(CSV) 받기", 
                           pd.DataFrame(st.session_state.master_log).to_csv(index=False).encode('utf-8-sig'), 
                           f"Jarvis_Master_{datetime.now().strftime('%Y%m%d')}.csv")

# --- 메인 화면 (6개 섹션 무삭제) ---
st.header("1. 기본 정보")
st.table(pd.DataFrame(FIXED_DATA["profile"]).assign(순번=range(1, 5)).set_index('순번'))

st.header("2. 건강 및 영양")
n_col1, n_col2 = st.columns(2)
n_col1.metric("에너지 섭취", f"{st.session_state.consumed['칼로리']} / {TARGET['칼로리']} kcal")
n_col2.metric("수분 섭취", f"{st.session_state.consumed['수분']} / {TARGET['수분']} ml")

nut_rows = [{"항목": k, "현황": f"{v}g", "잔여": f"{max(0, TARGET[k]-v)}g"} 
            for k, v in st.session_state.consumed.items() if k not in ["칼로리", "수분"]]
st.table(pd.DataFrame(nut_rows).assign(순번=range(1, 5)).set_index('순번'))

st.header("3. 실시간 자산 리포트")
assets = [{"항목": "가용 현금", "금액": st.session_state.cash}]
for k, v in FIXED_DATA["assets"]["savings"].items(): assets.append({"항목": k, "금액": v})
# (주식 등 데이터 나열...)
st.table(pd.DataFrame(assets).assign(금액=lambda x: x['금액'].apply(lambda y: f"{y:,.0f}원"), 순번=range(1, len(assets)+1)).set_index('순번'))

st.header("4. 이번 달 누적 지출")
e_rows = [{"항목": k, "지출": f"{v:,.0f}원"} for k, v in st.session_state.expenses.items() if v > 0]
if e_rows: st.table(pd.DataFrame(e_rows).assign(순번=range(1, len(e_rows)+1)).set_index('순번'))
else: st.info("내역 없음")

st.header("5. 생활 주기 관리")
l_rows = []
for item, info in FIXED_DATA["lifecycle"].items():
    rem = (datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"]) - datetime.now()).days
    l_rows.append({"항목": item, "마지막교체": info["last"], "D-Day": f"{rem}일"})
st.table(pd.DataFrame(l_rows).assign(순번=range(1, 4)).set_index('순번'))

st.header("6. 주방 재고 현황")
st.table(pd.DataFrame([{"카테고리": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()]).assign(순번=range(1, 5)).set_index('순번'))
