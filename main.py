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
TARGET = {"cal": 2000, "p": 150, "f": 65, "c": 300, "fiber": 25, "water": 2000}

# 2. 세션 상태 초기화 (버그 방지를 위한 딕셔너리 구조 통일)
if 'cash' not in st.session_state: st.session_state.cash = 492918
if 'consumed' not in st.session_state: st.session_state.consumed = {"cal": 0, "p": 0, "f": 0, "c": 0, "fiber": 0, "water": 0}
if 'expenses' not in st.session_state: st.session_state.expenses = {cat: 0 for cat in EXPENSE_CATS}
if 'master_log' not in st.session_state: st.session_state.master_log = []

st.set_page_config(page_title="자비스 v5.6", layout="wide")

# CSS: 특대 숫자 및 정렬 유지
st.markdown("""<style>
    * { font-family: 'Arial Black', sans-serif !important; }
    [data-testid="stTable"] td:nth-child(1) { font-size: 50px !important; color: #FF4B4B !important; font-weight: 900; text-align: center; }
    [data-testid="stTable"] td:nth-child(2), [data-testid="stTable"] td:nth-child(3) { text-align: right !important; font-size: 20px !important; }
    h2 { font-size: 30px !important; border-left: 10px solid #FF4B4B; padding-left: 15px; margin-top: 40px !important; }
    [data-testid="stMetricValue"] { text-align: right !important; font-size: 40px !important; }
</style>""", unsafe_allow_html=True)

st.title(f"자비스 통합 리포트 : {datetime.now().strftime('%Y-%m-%d')} (원평동 10°C ☀️)")

# --- 사이드바: 입력 ---
with st.sidebar:
    st.header("실시간 기록")
    with st.form("clean_input"):
        exp_val = st.number_input("지출 금액", min_value=0, step=100)
        exp_cat = st.selectbox("카테고리", EXPENSE_CATS)
        st.divider()
        meal_in = st.text_input("음식명/음료")
        
        if st.form_submit_button("반영"):
            # 1. 데이터 준비
            m_entry = {"날짜": datetime.now().strftime('%Y-%m-%d'), "시간": datetime.now().strftime('%H:%M'), "항목": meal_in or exp_cat, "금액": exp_val, "cal": 0, "p": 0, "f": 0, "c": 0, "fiber": 0, "water": 0}
            
            # 2. 영양소 분석 로직
            if "물" in meal_in: m_entry["water"] = 500
            elif "쿼파치" in meal_in: m_entry.update({"cal": 1120, "p": 50, "f": 55, "c": 110, "fiber": 5})
            elif meal_in: m_entry.update({"cal": 600, "p": 25, "f": 20, "c": 70, "fiber": 3})
            
            # 3. 세션 업데이트 (버그 방지용 직접 가산)
            st.session_state.cash -= exp_val
            st.session_state.expenses[exp_cat] += exp_val
            for k in ["cal", "p", "f", "c", "fiber", "water"]:
                st.session_state.consumed[k] += m_entry[k]
            
            st.session_state.master_log.append(m_entry)
            st.rerun()

    if st.session_state.master_log:
        st.divider()
        m_df = pd.DataFrame(st.session_state.master_log)
        st.download_button("📂 통합 마스터 로그(CSV) 받기", m_df.to_csv(index=False).encode('utf-8-sig'), f"Jarvis_Master_{datetime.now().strftime('%Y%m%d')}.csv")

# --- 메인 화면 (무삭제 6개 섹션) ---
st.header("1. 기본 정보")
st.table(pd.DataFrame(FIXED_DATA["profile"]).assign(순번=range(1, 5)).set_index('순번'))

st.header("2. 건강 및 영양")
c_col1, c_col2 = st.columns(2)
c_col1.metric("에너지 섭취", f"{st.session_state.consumed['cal']} / {TARGET['cal']} kcal")
c_col2.metric("수분 섭취", f"{st.session_state.consumed['water']} / {TARGET['water']} ml")
cons_df = pd.DataFrame([{"항목": k, "현황": f"{v}g"} for k, v in st.session_state.consumed.items() if k not in ['cal', 'water']])
st.table(cons_df.assign(순번=range(1, len(cons_df)+1)).set_index('순번'))

st.header("3. 실시간 자산 리포트")
assets = [{"항목": "가용 현금", "금액": st.session_state.cash}]
for k, v in FIXED_DATA["assets"]["savings"].items(): assets.append({"항목": k, "금액": v})
# 주식은 고정수량으로 계산
s_cnt = FIXED_DATA["assets"]["stocks"]
for n, count in s_cnt.items(): assets.append({"항목": f"주식({n})", "금액": 0}) # 시세연동은 생략 가능 시 0처리
df_a = pd.DataFrame(assets)
st.table(df_a.assign(금액=lambda x: x['금액'].apply(lambda y: f"{y:,.0f}원"), 순번=range(1, len(df_a)+1)).set_index('순번'))

st.header("4. 누적 지출 현황")
e_data = [{"카테고리": k, "지출액": f"{v:,.0f}원"} for k, v in st.session_state.expenses.items() if v > 0]
if e_data: st.table(pd.DataFrame(e_data).assign(순번=range(1, len(e_data)+1)).set_index('순번'))
else: st.info("기록된 지출이 없습니다.")

st.header("5. 생활 주기 관리")
l_rows = []
for item, info in FIXED_DATA["lifecycle"].items():
    rem = (datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"]) - datetime.now()).days
    l_rows.append({"항목": item, "최근수행": info["last"], "D-Day": f"{rem}일"})
st.table(pd.DataFrame(l_rows).assign(순번=range(1, 4)).set_index('순번'))

st.header("6. 주방 재고")
st.table(pd.DataFrame([{"카테고리": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()]).assign(순번=range(1, 5)).set_index('순번'))
