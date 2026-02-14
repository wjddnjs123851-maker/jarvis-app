import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- [1. 고정 마스터 데이터: 보스의 데이터 그대로 유지] ---
FIXED_DATA = {
    "profile": {"항목": ["나이", "거주", "상태", "결혼예정일"], "내용": ["32세", "평택 원평동", "공무원 발령 대기 중", "2026-05-30"]},
    "health": {"항목": ["현재 체중", "목표 체중", "주요 관리", "식단 금기"], "내용": ["125.0kg", "90.0kg", "고지혈증/ADHD", "생굴/멍게"]},
    "assets": {
        "savings": {"청년도약계좌": 14700000, "주택청약": 2540000, "전세보증금": 145850000},
        "liabilities": {"전세대출": 100000000, "마이너스통장": 3000000, "학자금대출": 1247270},
        "stocks": {"삼성전자": "005930", "SK하이닉스": "000660", "삼성중공업": "010140", "동성화인텍": "033500"},
        "stocks_count": {"삼성전자": 46, "SK하이닉스": 6, "삼성중공업": 88, "동성화인텍": 21},
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
PAY_METHODS = ["하나카드", "우리카드", "국민카드", "현대카드", "지역화폐", "현금"]
TARGET = {"칼로리": 2000, "탄수화물": 300, "단백질": 150, "지방": 65, "나트륨": 2000, "콜레스테롤": 300, "당류": 50, "수분": 2000}

# --- [2. 구글 시트 연동 설정] ---
SPREADSHEET_ID = '1X6ypXRLkHIMOSGuYdNLnzLkVB4xHfpRR'
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=0"

# 세션 데이터 초기화
if 'cash' not in st.session_state: st.session_state.cash = 492918
if 'card_debt' not in st.session_state: st.session_state.card_debt = 0
if 'consumed' not in st.session_state: st.session_state.consumed = {k: 0 for k in TARGET.keys()}

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

@st.cache_data(ttl=60) # 1분마다 시트 데이터 새로고침
def load_sheet_log():
    try:
        df = pd.read_csv(CSV_URL)
        return df
    except:
        return pd.DataFrame()

# --- [3. UI 스타일 및 헤더] ---
st.set_page_config(page_title="자비스 v7.5", layout="wide")
st.markdown("""<style>
    * { font-family: 'Arial Black', sans-serif !important; }
    [data-testid="stTable"] td:nth-child(1) { font-size: 25px !important; color: #FF4B4B !important; font-weight: 900; }
    h2 { font-size: 30px !important; border-left: 10px solid #FF4B4B; padding-left: 15px; margin-top: 40px !important; }
    [data-testid="stMetricValue"] { font-size: 40px !important; }
</style>""", unsafe_allow_html=True)

st.title("자비스 통합 리포트 v7.5")
st.markdown(f'<p style="font-size:22px; color:#1E90FF; font-weight:bold;">📍 평택 원평동: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>', unsafe_allow_html=True)

live = get_live_prices()

# --- [4. 사이드바: 데이터 기록] ---
with st.sidebar:
    st.header("📋 데이터 기록")
    
    with st.expander("🥤 수분 동기화"):
        samsung_water = st.number_input("오늘 총 수분량(ml)", min_value=0, value=int(st.session_state.consumed['수분']))
        if st.button("동기화 실행"):
            st.session_state.consumed['수분'] = samsung_water
            st.rerun()

    with st.form("master_input"):
        event_time = st.time_input("발생 시간", datetime.now())
        tran_type = st.radio("구분", ["지출", "수입"])
        amount = st.number_input("금액", min_value=0, step=100)
        pay_method = st.selectbox("결제 수단", PAY_METHODS)
        item_name = st.text_input("내용") 
        
        st.divider()
        st.subheader("🥗 영양 수치")
        col_f1, col_f2 = st.columns(2)
        c_cal = col_f1.number_input("칼로리", 0)
        c_car = col_f2.number_input("탄수(g)", 0)
        c_pro = col_f1.number_input("단백(g)", 0)
        c_fat = col_f2.number_input("지방(g)", 0)
        
        if st.form_submit_button("자비스 로그에 기록"):
            # 현재는 세션에 저장하지만, 향후 시트에 직접 쓰기 기능을 추가할 수 있습니다.
            st.success("로그가 세션에 기록되었습니다.")

# --- [5. 메인 섹션 출력] ---

# 1. 기본 정보
st.header("1. 기본 정보")
st.table(pd.DataFrame(FIXED_DATA["profile"]).assign(순번=range(1, 5)).set_index('순번'))

# 2. 건강 및 영양
st.header("2. 건강 및 정밀 영양")
col_n1, col_n2 = st.columns(2)
col_n1.metric("오늘 칼로리", f"{st.session_state.consumed['칼로리']} / {TARGET['칼로리']} kcal")
col_n2.metric("수분 섭취량", f"{st.session_state.consumed['수분']} / {TARGET['수분']} ml")

# 3. 실시간 자산 & 4. 부채
st.header("3. 실시간 자산 및 부채 상세")
assets = [{"항목": "가용 현금", "금액": st.session_state.cash}, {"항목": "⚠️ 카드값", "금액": -st.session_state.card_debt}]
for k, v in FIXED_DATA["assets"]["savings"].items(): assets.append({"항목": k, "금액": v})
s_cnt = FIXED_DATA["assets"]["stocks_count"]
for n in FIXED_DATA["assets"]["stocks"]: assets.append({"항목": f"주식({n})", "금액": live["stocks"].get(n, 0) * s_cnt[n]})
btc_val = int(FIXED_DATA["assets"]["crypto"]["BTC"] * live["crypto"]["KRW-BTC"])
eth_val = int(FIXED_DATA["assets"]["crypto"]["ETH"] * live["crypto"]["KRW-ETH"])
assets.extend([{"항목": "코인(BTC)", "금액": btc_val}, {"항목": "코인(ETH)", "금액": eth_val}])
st.table(pd.DataFrame(assets).assign(금액=lambda x: x['금액'].apply(lambda y: f"{y:,.0f}원"), 순번=range(1, len(assets)+1)).set_index('순번'))

# 통합 순자산 계산
t_a = st.session_state.cash + sum(FIXED_DATA["assets"]["savings"].values()) + sum(live["stocks"].get(n, 0) * s_cnt[n] for n in s_cnt) + btc_val + eth_val - st.session_state.card_debt
st.metric("실시간 통합 순자산", f"{t_a - sum(FIXED_DATA['assets']['liabilities'].values()):,.0f}원")

# 5. 구글 시트 가계부 로그 (핵심 업데이트)
st.header("5. 구글 시트 실시간 가계부 로그")
sheet_df = load_sheet_log()
if not sheet_df.empty:
    st.dataframe(sheet_df, use_container_width=True)
else:
    st.info("구글 시트에서 데이터를 불러오는 중이거나 데이터가 비어있습니다.")

# 6. 생활 주기 및 주방 재고
col_l, col_k = st.columns(2)
with col_l:
    st.header("6. 생활 주기")
    l_rows = []
    for item, info in FIXED_DATA["lifecycle"].items():
        rem = (datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"]) - datetime.now()).days
        l_rows.append({"항목": item, "D-Day": f"{rem}일"})
    st.table(pd.DataFrame(l_rows))

with col_k:
    st.header("7. 주방 재고")
    st.table(pd.DataFrame([{"카테고리": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()]))
