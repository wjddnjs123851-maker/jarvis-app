import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. 고정 마스터 데이터 (로봇청소기 제외 및 부채 데이터 유지)
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
        "면도날": {"last": "2026-02-06", "period": 21}, 
        "칫솔": {"last": "2026-02-06", "period": 90}, 
        "이불세탁": {"last": "2026-02-04", "period": 14} 
        # 로봇청소기 삭제
    },
    "kitchen": {
        "소스/캔": "토마토페이스트, 나시고랭, S&B카레, 뚝심, 땅콩버터",
        "단백질": "냉동삼치, 냉동닭다리, 관찰레, 북어채, 단백질쉐이크",
        "곡물/면": "파스타면, 소면, 쿠스쿠스, 라면, 우동, 쌀/카무트",
        "신선/기타": "김치4종, 아사이베리, 치아씨드, 향신료, 치즈"
    }
}

# (세션 데이터 및 가격 로직 유지)
if 'cash' not in st.session_state: st.session_state.cash = 492918
if 'consumed' not in st.session_state: st.session_state.consumed = {"cal": 0, "p": 0, "f": 0, "c": 0, "fiber": 0, "water": 0}
if 'expenses' not in st.session_state: st.session_state.expenses = {cat: 0 for cat in ["식비(집밥)", "식비(배달)", "식비(외식/편의점)", "담배", "생활용품", "주거/통신/이자", "보험/청약", "주식/적금", "주유/교통", "건강/의료", "기타"]}
if 'meal_history' not in st.session_state: st.session_state.meal_history = []

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

st.set_page_config(page_title="자비스 v4.7", layout="wide")

# CSS: 정렬 및 폰트 크기 재교정
st.markdown("""
    <style>
    * { font-family: 'Arial Black', sans-serif !important; }
    
    /* 50px 특대 인덱스 숫자 */
    [data-testid="stTable"] td:nth-child(1), 
    [data-testid="stTable"] th:nth-child(1) {
        font-size: 50px !important; 
        font-weight: 900 !important;
        color: #FF4B4B !important;
        text-align: center !important;
    }

    /* 돈/숫자 우측 정렬 강제 적용 */
    [data-testid="stTable"] td:nth-child(2), 
    [data-testid="stTable"] td:nth-child(3) {
        text-align: right !important;
        font-size: 22px !important;
    }

    h2 { font-size: 30px !important; border-left: 10px solid #FF4B4B; padding-left: 15px; margin-top: 40px !important; }
    [data-testid="stMetricValue"] { text-align: right !important; font-size: 40px !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("자비스 : 통합 라이프 매니지먼트")
live = get_live_prices()

# --- 사이드바 ---
with st.sidebar:
    st.header("입력")
    with st.form("input_form"):
        exp_val = st.number_input("지출 금액", min_value=0, step=100)
        meal_in = st.text_input("음식/음료")
        if st.form_submit_button("반영"):
            st.session_state.cash -= exp_val
            st.rerun()

# --- 1. 기본 정보 (단일 열) ---
st.header("1. 기본 정보")
df_p = pd.DataFrame(FIXED_DATA["profile"])
df_p.index = range(1, len(df_p)+1)
st.table(df_p)

# --- 2. 건강 및 영양 ---
st.header("2. 건강 및 영양")
df_h = pd.DataFrame(FIXED_DATA["health"])
df_h.index = range(1, len(df_h)+1)
st.table(df_h)

n_col1, n_col2 = st.columns(2)
n_col1.metric("에너지 섭취", f"{st.session_state.consumed['cal']} / 2000")
n_col2.metric("남은 허용량", f"{2000 - st.session_state.consumed['cal']}")

# --- 3. 재무 및 자산 리포트 ---
st.header("3. 실시간 자산 및 부채")
s_cnt = {"삼성전자": 46, "SK하이닉스": 6, "삼성중공업": 88, "동성화인텍": 21}
s_val = sum(live["stocks"].get(n, 0) * s_cnt[n] for n in FIXED_DATA["assets"]["stocks"])
b_val = int(FIXED_DATA["assets"]["crypto"]["BTC"] * live["crypto"]["KRW-BTC"])
e_val = int(FIXED_DATA["assets"]["crypto"]["ETH"] * live["crypto"]["KRW-ETH"])

assets = [{"항목": "현금", "금액": st.session_state.cash}]
for k, v in FIXED_DATA["assets"]["savings"].items(): assets.append({"항목": k, "금액": v})
for n in FIXED_DATA["assets"]["stocks"]: assets.append({"항목": f"주식({n})", "금액": live["stocks"].get(n, 0) * s_cnt[n]})
assets.append({"항목": "코인 합계", "금액": b_val + e_val})
df_a = pd.DataFrame(assets)
df_a.index = range(1, len(df_a)+1)
st.table(df_a.assign(금액=lambda x: x['금액'].apply(lambda y: f"{y:,.0f}원")))

# 부채 복구
debts = [{"항목": k, "금액": v} for k, v in FIXED_DATA["assets"]["liabilities"].items()]
df_d = pd.DataFrame(debts)
df_d.index = range(1, len(df_d)+1)
st.table(df_d.assign(금액=lambda x: x['금액'].apply(lambda y: f"{y:,.0f}원")))

t_a = st.session_state.cash + 17240000 + 145850000 + s_val + b_val + e_val
t_d = 104247270
st.metric("실시간 통합 순자산", f"{t_a - t_d:,.0f}원")

# --- 4. 지출 내역 ---
st.header("4. 이번 세션 지출")
e_rows = [{"항목": k, "지출": f"{v:,.0f}원"} for k, v in st.session_state.expenses.items() if v > 0]
if e_rows:
    df_e = pd.DataFrame(e_rows)
    df_e.index = range(1, len(df_e)+1)
    st.table(df_e)
else: st.info("내역 없음")

# --- 5. 생활 주기 ---
st.header("5. 생활 주기 (로봇청소기 제외)")
l_rows = []
for item, info in FIXED_DATA["lifecycle"].items():
    rem = (datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"]) - datetime.now()).days
    l_rows.append({"항목": item, "마지막 교체일": info["last"], "상태": "🚨 점검" if rem <= 0 else "✅ 정상", "남은 일수": f"{rem}일"})
df_l = pd.DataFrame(l_rows)
df_l.index = range(1, len(df_l)+1)
st.table(df_l)

# --- 6. 주방 재고 ---
st.header("6. 주방 재고")
df_k = pd.DataFrame([{"카테고리": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()])
df_k.index = range(1, len(df_k)+1)
st.table(df_k)
