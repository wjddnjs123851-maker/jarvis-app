import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. 고정 마스터 데이터
FIXED_DATA = {
    "profile": {"항목": ["나이", "거주", "상태", "결혼예정일"], "내용": ["32세", "평택 원평동", "공무원 발령 대기 중", "2026-05-30"]},
    "health": {"항목": ["현재 체중", "목표 체중", "주요 관리", "식단 금기"], "내용": ["125.0kg", "90.0kg", "고지혈증/ADHD", "생굴/멍게"]},
    "assets": {
        "savings": {"청년도약계좌": 14700000, "주택청약": 2540000, "전세보증금": 145850000},
        "liabilities": {"전세대출": 100000000, "마이너스통장": 3000000, "학자금대출": 1247270},
        "stocks": {"삼성전자": "005930", "SK하이닉스": "000660", "삼성중공업": "010140", "동성화인텍": "033500"},
        "crypto": {"BTC": 0.00181400, "ETH": 0.03417393}
    },
    "lifecycle": {
        "면도날": {"last": "2026-02-06", "period": 21}, "칫솔": {"last": "2026-02-06", "period": 90}, "이불세탁": {"last": "2026-01-30", "period": 14}, "로봇청소기": {"last": "2026-02-12", "period": 2}
    },
    "kitchen": {
        "소스/캔": "토마토페이스트, 나시고랭, S&B카레, 뚝심, 땅콩버터",
        "단백질": "냉동삼치, 냉동닭다리, 관찰레, 북어채, 단백질쉐이크",
        "곡물/면": "파스타면, 소면, 쿠스쿠스, 라면, 우동, 쌀/카무트",
        "신선/기타": "김치4종, 아사이베리, 치아씨드, 향신료, 치즈"
    }
}

# 2. 세션 상태 초기화
if 'cash' not in st.session_state: st.session_state.cash = 492918
if 'consumed' not in st.session_state: st.session_state.consumed = {"cal": 0, "p": 0, "f": 0, "c": 0, "fiber": 0, "water": 0}
if 'expenses' not in st.session_state: st.session_state.expenses = {cat: 0 for cat in ["식비(집밥)", "식비(배달)", "식비(외식/편의점)", "담배", "생활용품", "주거/통신/이자", "보험/청약", "주식/적금", "주유/교통", "건강/의료", "기타"]}
if 'meal_history' not in st.session_state: st.session_state.meal_history = []
if 'log_history' not in st.session_state: st.session_state.log_history = []

# 실시간 시세 엔진 (에러 방지 쉴드)
def get_live_prices():
    prices = {"crypto": {"KRW-BTC": 95000000, "KRW-ETH": 3800000}, "stocks": {}}
    try:
        res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH", timeout=1).json()
        for c in res: prices["crypto"][c['market']] = int(c['trade_price'])
    except: pass
    for name, code in FIXED_DATA["assets"]["stocks"].items():
        try:
            url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{code}"
            res = requests.get(url, timeout=1).json()
            prices["stocks"][name] = int(res['result']['areas'][0]['datas'][0]['nv'])
        except: prices["stocks"][name] = 0
    return prices

st.set_page_config(page_title="자비스 v4.6", layout="wide")

# CSS: 인덱스 숫자 강제 확대 및 두꺼운 폰트 적용
st.markdown("""
    <style>
    /* 전체 폰트를 두껍고 힘있는 폰트로 설정 */
    * { font-family: 'Arial Black', sans-serif !important; }
    
    /* 1. 표의 첫 번째 열(번호)을 제목보다 압도적으로 크게(50px) */
    [data-testid="stTable"] td:nth-child(1), 
    [data-testid="stTable"] th:nth-child(1) {
        font-size: 50px !important; 
        font-weight: 900 !important;
        color: #FF4B4B !important;
        line-height: 1 !important;
        min-width: 80px !important;
        text-align: center !important;
        vertical-align: middle !important;
    }

    /* 2. 섹션 제목 (25px) - 숫자보다 작게 설정 */
    h2 { 
        font-size: 25px !important; 
        font-weight: bold; 
        color: #333; 
        border-left: 10px solid #FF4B4B; 
        padding-left: 15px;
    }

    /* 3. 일반 데이터 텍스트 (16px) */
    [data-testid="stTable"] td { font-size: 16px !important; vertical-align: middle !important; }

    /* 4. 메트릭(순자산 등) 우측 정렬 및 확대 */
    [data-testid="stMetricValue"] { font-size: 35px !important; text-align: right !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("자비스 : 라이프 매니지먼트 시스템")
live = get_live_prices()

# --- 사이드바 ---
with st.sidebar:
    st.header("기록")
    with st.form("input_form"):
        exp_val = st.number_input("금액", min_value=0, step=100)
        meal_in = st.text_input("음식")
        if st.form_submit_button("반영"):
            # 로직 처리...
            st.session_state.cash -= exp_val
            st.rerun()

# --- 1 & 2 섹션 ---
c1, c2 = st.columns([1, 1.3])
with c1:
    st.header("1. 기본 정보")
    p_df = pd.DataFrame(FIXED_DATA["profile"])
    p_df.index = range(1, 5)
    st.table(p_df)
    
    h_df = pd.DataFrame(FIXED_DATA["health"])
    h_df.index = range(1, 5)
    st.table(h_df)

with c2:
    st.header("2. 영양 상태")
    n_col1, n_col2 = st.columns(2)
    n_col1.metric("섭취 칼로리", f"{st.session_state.consumed['cal']} / 2000")
    n_col2.metric("남은 허용량", f"{2000 - st.session_state.consumed['cal']}")
    
    cons = st.session_state.consumed
    nut_df = pd.DataFrame([
        {"항목": "단백질", "현황": f"{cons['p']} / 150g"},
        {"항목": "지방", "현황": f"{cons['f']} / 65g"},
        {"항목": "식이섬유", "현황": f"{cons['fiber']} / 25g"},
        {"항목": "수분", "현황": f"{cons['water']} / 2000ml"}
    ])
    nut_df.index = range(1, 5)
    st.table(nut_df)

# --- 3 & 4 섹션 ---
st.divider()
st.header("3 & 4. 재무 및 지출")
s_cnt = {"삼성전자": 46, "SK하이닉스": 6, "삼성중공업": 88, "동성화인텍": 21}
s_val = sum(live["stocks"].get(n, 0) * s_cnt[n] for n in FIXED_DATA["assets"]["stocks"])
b_val = int(FIXED_DATA["assets"]["crypto"]["BTC"] * live["crypto"]["KRW-BTC"])
e_val = int(FIXED_DATA["assets"]["crypto"]["ETH"] * live["crypto"]["KRW-ETH"])

f_col1, f_col2 = st.columns([1.5, 1])
with f_col1:
    st.subheader("자산 현황")
    assets = [{"항목": "현금", "금액": st.session_state.cash}]
    for k, v in FIXED_DATA["assets"]["savings"].items(): assets.append({"항목": k, "금액": v})
    for n in FIXED_DATA["assets"]["stocks"]: assets.append({"항목": f"주식({n})", "금액": live["stocks"].get(n, 0) * s_cnt[n]})
    assets.append({"항목": "코인", "금액": b_val + e_val})
    df_a = pd.DataFrame(assets)
    df_a.index = range(1, len(df_a)+1)
    st.table(df_a.assign(금액=lambda x: x['금액'].apply(lambda y: f"{y:,.0f}원")))
    
with f_col2:
    t_a = st.session_state.cash + 17240000 + 145850000 + s_val + b_val + e_val
    t_d = 104247270
    st.metric("실시간 순자산", f"{t_a - t_d:,.0f}원")

# --- 5 & 6 섹션 ---
st.divider()
st.header("5 & 6. 생활 및 주방")
l1, l2 = st.columns(2)
with l1:
    l_rows = []
    for item, info in FIXED_DATA["lifecycle"].items():
        rem = (datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"]) - datetime.now()).days
        l_rows.append({"항목": item, "D-Day": f"{rem}일"})
    df_l = pd.DataFrame(l_rows)
    df_l.index = range(1, 5)
    st.table(df_l)
with l2:
    k_df = pd.DataFrame([{"카테고리": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()])
    k_df.index = range(1, 5)
    st.table(k_df)
