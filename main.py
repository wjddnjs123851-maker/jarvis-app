import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. 고정 마스터 데이터
FIXED_DATA = {
    "profile": {"항목": ["나이", "거주", "상태", "결혼예정일"], "내용": ["32세", "평택 원평동", "공무원 발령 대기 중", "2026-05-30"]},
    "health": {"항목": ["현재 체중", "목표 체중", "주요 관리", "식단 금기"], "내용": ["125.0kg", "90.0kg", "고지혈증/ADHD", "생굴/멍게"]},
    "assets": {
        "savings": {"청년도약계좌": 14700000, "주택청약": 2540000, "전세보증금(총액)": 145850000},
        "liabilities": {"전세대출": 100000000, "마이너스통장": 3000000, "학자금대출": 1247270},
        "stocks": {
            "삼성전자": {"code": "005930", "count": 46},
            "SK하이닉스": {"code": "000660", "count": 6},
            "삼성중공업": {"code": "010140", "count": 88},
            "동성화인텍": {"code": "033500", "count": 21}
        },
        "crypto": {"BTC": 0.00181400, "ETH": 0.03417393}
    },
    "lifecycle": {
        "면도날": {"last": "2026-02-06", "period": 21},
        "칫솔": {"last": "2026-02-06", "period": 90},
        "이불세탁": {"last": "2026-01-30", "period": 14},
        "로봇청소기": {"last": "2026-02-12", "period": 2}
    },
    "kitchen": {
        "소스/캔": "토마토페이스트(10), 나시고랭(1), S&B카레, 뚝심(2), 땅콩버터(4/5)",
        "단백질": "냉동삼치(4), 냉동닭다리(4), 관찰레, 북어채, 단백질쉐이크(9)",
        "곡물/면": "파스타면(다수), 소면(1), 쿠스쿠스(1), 라면(12), 우동/소바, 쌀/카무트",
        "신선/기타": "김치4종, 아사이베리, 치아씨드, 각종향신료, 치즈류"
    }
}

# 2. 실시간 세션 데이터
if 'cash' not in st.session_state: st.session_state.cash = 492918
if 'consumed_cal' not in st.session_state: st.session_state.consumed_cal = 0
if 'last_meal' not in st.session_state: st.session_state.last_meal = "미입력"

def get_live_prices():
    prices = {"crypto": {"KRW-BTC": 95000000, "KRW-ETH": 3800000}, "stocks": {}}
    try:
        res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH", timeout=2).json()
        for c in res: prices["crypto"][c['market']] = int(c['trade_price'])
    except: pass
    for name, info in FIXED_DATA["assets"]["stocks"].items():
        try:
            url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{info['code']}"
            res = requests.get(url, timeout=2).json()
            prices["stocks"][name] = int(res['result']['areas'][0]['datas'][0]['nv'])
        except: prices["stocks"][name] = 0
    return prices

st.set_page_config(page_title="자비스 v3.0", layout="wide")
st.title("자비스 : 5대 핵심 지표 대시보드")

# CSS: 표 정렬 최적화
st.markdown("""<style>td:nth-child(2), td:nth-child(3), td:nth-child(4) {text-align: right !important;}</style>""", unsafe_allow_html=True)

live = get_live_prices()

# 사이드바: 입력 패널
with st.sidebar.form("데일리 입력"):
    st.header("실시간 기록")
    expense = st.number_input("지출(원)", min_value=0, step=100)
    cal = st.number_input("칼로리(kcal)", min_value=0, step=50)
    meal = st.text_input("메뉴 이름")
    if st.form_submit_button("시스템 반영"):
        st.session_state.cash -= expense
        st.session_state.consumed_cal += cal
        st.session_state.last_meal = meal

# --- 1. 기본정보 ---
st.header("1. 기본정보")
col_p1, col_p2 = st.columns(2)
with col_p1:
    st.table(pd.DataFrame(FIXED_DATA["profile"]).assign(index=range(1, 5)).set_index('index'))
with col_p2:
    st.table(pd.DataFrame(FIXED_DATA["health"]).assign(index=range(1, 5)).set_index('index'))
st.divider()

# --- 2. 영양상태 ---
st.header("2. 영양상태")
n1, n2 = st.columns(2)
with n1:
    st.subheader(f"에너지 잔량: {st.session_state.consumed_cal} / 2000 kcal")
    rem_cal = 2000 - st.session_state.consumed_cal
    st.metric("오늘 남은 칼로리", f"{rem_cal} kcal")
with n2:
    st.info(f"최근 식사 메뉴: {st.session_state.last_meal}")
    st.write("권장 저녁 식단: 인벤토리의 '삼치'와 '백김치' 추천")
st.divider()

# --- 3. 재무관리 ---
st.header("3. 재무관리")
btc_v = int(FIXED_DATA["assets"]["crypto"]["BTC"] * live["crypto"]["KRW-BTC"])
eth_v = int(FIXED_DATA["assets"]["crypto"]["ETH"] * live["crypto"]["KRW-ETH"])
stock_total = sum(live["stocks"].get(n, 0) * i["count"] for n, i in FIXED_DATA["assets"]["stocks"].items())

a1, a2 = st.columns(2)
with a1:
    st.write("**자산 목록**")
    assets = [{"항목": "가용 현금", "금액": st.session_state.cash}]
    for k, v in FIXED_DATA["assets"]["savings"].items(): assets.append({"항목": k, "금액": v})
    assets.append({"항목": "주식 평가액", "금액": stock_total})
    assets.append({"항목": "코인 환산액", "금액": btc_v + eth_v})
    df_a = pd.DataFrame(assets)
    total_a = df_a['금액'].sum()
    df_a_disp = df_a.copy()
    df_a_disp['금액'] = df_a_disp['금액'].apply(lambda x: f"{x:,.0f}원")
    df_a_disp = pd.concat([df_a_disp, pd.DataFrame([{"항목": "총 자산 합계", "금액": f"{total_a:,.0f}원"}])], ignore_index=True)
    df_a_disp.index += 1
    st.table(df_a_disp)
with a2:
    st.write("**부채 목록**")
    debts = [{"항목": k, "금액": v} for k, v in FIXED_DATA["assets"]["liabilities"].items()]
    df_d = pd.DataFrame(debts)
    total_d = df_d['금액'].sum()
    df_d_disp = df_d.copy()
    df_d_disp['금액'] = df_d_disp['금액'].apply(lambda x: f"{x:,.0f}원")
    df_d_disp = pd.concat([df_d_disp, pd.DataFrame([{"항목": "총 부채 합계", "금액": f"{total_d:,.0f}원"}])], ignore_index=True)
    df_d_disp.index += 1
    st.table(df_d_disp)
    st.metric("실시간 순자산", f"{total_a - total_d:,.0f}원")
st.divider()

# --- 4. 생활주기 ---
st.header("4. 생활주기")
life_rows = []
for item, info in FIXED_DATA["lifecycle"].items():
    next_d = datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"])
    rem_d = (next_d - datetime.now()).days
    life_rows.append({"항목": item, "상태": "🚨 점검" if rem_d <= 0 else "✅ 정상", "남은일수": f"{rem_d}일"})
st.table(pd.DataFrame(life_rows).assign(index=range(1, 5)).set_index('index'))
st.divider()

# --- 5. 주방재고 ---
st.header("5. 주방재고")
k_rows = [{"카테고리": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()]
st.table(pd.DataFrame(k_rows).assign(index=range(1, 5)).set_index('index'))

st.caption(f"동기화 완료: {datetime.now().strftime('%H:%M:%S')}")
