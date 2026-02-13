import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. 마스터 데이터
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

# 세션 데이터 (지출 및 영양)
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
        except:
            prices["stocks"][name] = 0 # 시세 못 가져와도 에러 안 나게 0 처리
    return prices

st.set_page_config(page_title="자비스 v2.9", layout="wide")
st.title("자비스 : 실시간 통합 관리 시스템")

# CSS: 정렬 및 줄바꿈
st.markdown("""<style>td:nth-child(2), td:nth-child(3), td:nth-child(4) {text-align: right !important;}</style>""", unsafe_allow_html=True)

# 실시간 시세 로드
live = get_live_prices()

# 사이드바 입력창
with st.sidebar.form("입력창"):
    st.header("실시간 기록")
    expense = st.number_input("지출(원)", min_value=0, step=100)
    cal = st.number_input("칼로리(kcal)", min_value=0, step=50)
    meal = st.text_input("메뉴")
    if st.form_submit_button("반영"):
        st.session_state.cash -= expense
        st.session_state.consumed_cal += cal
        st.session_state.last_meal = meal

# --- 섹션 1: 프로필 & 영양 ---
st.header("기본 정보 및 영양 상태")
p1, p2 = st.columns(2)
with p1:
    df_p = pd.DataFrame(FIXED_DATA["profile"])
    df_p.index += 1
    st.table(df_p)
with p2:
    st.subheader(f"에너지 잔량: {st.session_state.consumed_cal} / 2000 kcal")
    rem = 2000 - st.session_state.consumed_cal
    st.metric("오늘 남은 칼로리", f"{rem} kcal", help=f"최근 식사: {st.session_state.last_meal}")

# --- 섹션 2: 재무 관리 (복구 완료) ---
st.header("재무 관리 매트릭스")
btc_v = int(FIXED_DATA["assets"]["crypto"]["BTC"] * live["crypto"]["KRW-BTC"])
eth_v = int(FIXED_DATA["assets"]["crypto"]["ETH"] * live["crypto"]["KRW-ETH"])

stock_total = 0
for name, info in FIXED_DATA["assets"]["stocks"].items():
    stock_total += live["stocks"].get(name, 0) * info["count"]

a1, a2 = st.columns(2)
with a1:
    st.subheader("자산 목록")
    asset_list = [{"항목": "보유 현금", "금액": st.session_state.cash}]
    for k, v in FIXED_DATA["assets"]["savings"].items(): asset_list.append({"항목": k, "금액": v})
    asset_list.append({"항목": "주식 평가액", "금액": stock_total})
    asset_list.append({"항목": "코인 환산액", "금액": btc_v + eth_v})
    
    df_a = pd.DataFrame(asset_list)
    total_a = df_a['금액'].sum()
    df_a_disp = df_a.copy()
    df_a_disp['금액'] = df_a_disp['금액'].apply(lambda x: f"{x:,.0f}원")
    df_a_disp = pd.concat([df_a_disp, pd.DataFrame([{"항목": "총 자산 합계", "금액": f"{total_a:,.0f}원"}])], ignore_index=True)
    df_a_disp.index += 1
    st.table(df_a_disp)

with a2:
    st.subheader("부채 목록")
    debt_list = [{"항목": k, "금액": v} for k, v in FIXED_DATA["assets"]["liabilities"].items()]
    df_d = pd.DataFrame(debt_list)
    total_d = df_d['금액'].sum()
    df_d_disp = df_d.copy()
    df_d_disp['금액'] = df_d_disp['금액'].apply(lambda x: f"{x:,.0f}원")
    df_d_disp = pd.concat([df_d_disp, pd.DataFrame([{"항목": "총 부채 합계", "금액": f"{total_d:,.0f}원"}])], ignore_index=True)
    df_d_disp.index += 1
    st.table(df_d_disp)
    st.metric("실시간 순자산", f"{total_a - total_d:,.0f}원")

# --- 섹션 3: 주방 및 주기 ---
st.header("생활 주기 및 주방 재고")
l1, l2 = st.columns(2)
with l1:
    life_rows = []
    for item, info in FIXED_DATA["lifecycle"].items():
        next_d = datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"])
        rem_d = (next_d - datetime.now()).days
        life_rows.append({"항목": item, "상태": "🚨 점검" if rem_d <= 0 else "✅ 정상", "남은일수": f"{rem_d}일"})
    df_l = pd.DataFrame(life_rows)
    df_l.index += 1
    st.table(df_l)
with l2:
    k_rows = [{"카테고리": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()]
    df_k = pd.DataFrame(k_rows)
    df_k.index += 1
    st.table(df_k)

st.caption(f"Last Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
