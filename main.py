import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. 고정 마스터 데이터 (요약 절대 금지)
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
TARGET = {"칼로리": 2000, "단백질": 150, "지방": 65, "탄수화물": 300, "식이섬유": 25, "수분": 2000, "나트륨": 2000, "콜레스테롤": 300, "당류": 50}

# 세션 데이터 초기화
if 'cash' not in st.session_state: st.session_state.cash = 492918
if 'card_debt' not in st.session_state: st.session_state.card_debt = 0 # 실시간 카드값 추적용
if 'consumed' not in st.session_state: st.session_state.consumed = {k: 0 for k in TARGET.keys()}
if 'expenses' not in st.session_state: st.session_state.expenses = {cat: 0 for cat in EXPENSE_CATS}
if 'master_log' not in st.session_state: st.session_state.master_log = []

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

st.set_page_config(page_title="자비스 v6.3", layout="wide")

# CSS: 50px 특대 숫자 및 우측 정렬
st.markdown("""<style>
    * { font-family: 'Arial Black', sans-serif !important; }
    [data-testid="stTable"] td:nth-child(1) { font-size: 50px !important; color: #FF4B4B !important; font-weight: 900; text-align: center; }
    [data-testid="stTable"] td:nth-child(2), [data-testid="stTable"] td:nth-child(3) { text-align: right !important; font-size: 20px !important; }
    h2 { font-size: 30px !important; border-left: 10px solid #FF4B4B; padding-left: 15px; margin-top: 40px !important; }
    [data-testid="stMetricValue"] { text-align: right !important; font-size: 40px !important; }
    .weather-text { font-size: 24px; font-weight: bold; color: #1E90FF; margin-bottom: 20px; }
</style>""", unsafe_allow_html=True)

st.title("자비스 통합 리포트")
st.markdown('<p class="weather-text">📍 평택 원평동 날씨: 10°C ☀️ (맑음, 습도 77%)</p>', unsafe_allow_html=True)

live = get_live_prices()

# --- 사이드바: 입력 ---
with st.sidebar:
    st.header("실시간 기록")
    with st.form("total_input"):
        st.subheader("1. 지출 기록")
        exp_val = st.number_input("지출 금액", min_value=0, step=100)
        pay_method = st.selectbox("지출 수단", PAY_METHODS)
        exp_cat = st.selectbox("지출 카테고리", EXPENSE_CATS)
        st.divider()
        st.subheader("2. 식단 기록")
        meal_in = st.text_input("음식명/음료")
        
        if st.form_submit_button("시스템 반영"):
            entry = {"날짜": datetime.now().strftime('%Y-%m-%d'), "시간": datetime.now().strftime('%H:%M'), 
                     "항목": meal_in or exp_cat, "금액": exp_val, "지출수단": pay_method,
                     "칼로리": 0, "단백질": 0, "지방": 0, "탄수화물": 0, 
                     "식이섬유": 0, "수분": 0, "나트륨": 0, "콜레스테롤": 0, "당류": 0}
            
            if "물" in meal_in: entry["수분"] = 500
            elif "쿼파치" in meal_in: entry.update({"칼로리": 1120, "단백질": 50, "지방": 55, "탄수화물": 110, "식이섬유": 5, "나트륨": 1200, "콜레스테롤": 150, "당류": 12})
            elif meal_in: entry.update({"칼로리": 600, "단백질": 25, "지방": 20, "탄수화물": 70, "식이섬유": 3, "나트륨": 800, "당류": 5})
            
            # 카드결제 시 카드값 누적, 현금/지역화폐 시 가용현금 차감
            if "카드" in pay_method: st.session_state.card_debt += exp_val
            else: st.session_state.cash -= exp_val
            
            st.session_state.expenses[exp_cat] += exp_val
            for k in TARGET.keys(): st.session_state.consumed[k] += entry.get(k, 0)
            st.session_state.master_log.insert(0, entry) # 최신 로그가 위로 오게
            st.rerun()

    if st.session_state.master_log:
        st.divider()
        st.download_button("📂 통합 마스터 로그(CSV) 받기", 
                           pd.DataFrame(st.session_state.master_log).to_csv(index=False).encode('utf-8-sig'), 
                           f"Jarvis_Master_{datetime.now().strftime('%Y%m%d')}.csv")

# --- 메인 섹션 (1~7 무삭제 상세) ---

st.header("1. 기본 정보")
st.table(pd.DataFrame(FIXED_DATA["profile"]).assign(순번=range(1, 5)).set_index('순번'))

st.header("2. 건강 및 정밀 영양")
n1, n2 = st.columns(2)
n1.metric("에너지 섭취", f"{st.session_state.consumed['칼로리']} / {TARGET['칼로리']} kcal")
n2.metric("수분 섭취량", f"{st.session_state.consumed['수분']} / {TARGET['수분']} ml")

nut_rows = []
for k in ["단백질", "지방", "탄수화물", "식이섬유", "수분", "나트륨", "콜레스테롤", "당류"]:
    v = st.session_state.consumed[k]
    unit = "mg" if k in ["나트륨", "콜레스테롤"] else ("ml" if k == "수분" else "g")
    nut_rows.append({"항목": k, "현재 섭취": f"{v}{unit}", "권장 기준": f"{TARGET[k]}{unit}"})
st.table(pd.DataFrame(nut_rows).assign(순번=range(1, len(nut_rows)+1)).set_index('순번'))

st.header("3. 실시간 자산 상세")
# 가용현금과 청년도약계좌 사이에 현재 카드값(부채성격) 기입
assets_display = [
    {"항목": "가용 현금", "금액": st.session_state.cash},
    {"항목": "⚠️ 현재 카드값(결제예정)", "금액": -st.session_state.card_debt} # 부채이므로 마이너스 표시
]
for k, v in FIXED_DATA["assets"]["savings"].items():
    assets_display.append({"항목": k, "금액": v})

# 주식/코인 상세 (무삭제)
s_cnt = FIXED_DATA["assets"]["stocks_count"]
for n in FIXED_DATA["assets"]["stocks"]:
    assets_display.append({"항목": f"주식({n})", "금액": live["stocks"].get(n, 0) * s_cnt[n]})
btc_val = int(FIXED_DATA["assets"]["crypto"]["BTC"] * live["crypto"]["KRW-BTC"])
eth_val = int(FIXED_DATA["assets"]["crypto"]["ETH"] * live["crypto"]["KRW-ETH"])
assets_display.extend([{"항목": "코인(BTC)", "금액": btc_val}, {"항목": "코인(ETH)", "금액": eth_val}])

st.table(pd.DataFrame(assets_display).assign(금액=lambda x: x['금액'].apply(lambda y: f"{y:,.0f}원"), 순번=range(1, len(assets_display)+1)).set_index('순번'))

st.header("4. 실시간 부채 상세")
debts = [{"항목": k, "금액": v} for k, v in FIXED_DATA["assets"]["liabilities"].items()]
st.table(pd.DataFrame(debts).assign(금액=lambda x: x['금액'].apply(lambda y: f"{y:,.0f}원"), 순번=range(1, len(debts)+1)).set_index('순번'))

t_a = st.session_state.cash + sum(FIXED_DATA["assets"]["savings"].values()) + sum(live["stocks"].get(n, 0) * s_cnt[n] for n in s_cnt) + btc_val + eth_val - st.session_state.card_debt
t_d = sum(FIXED_DATA["assets"]["liabilities"].values())
st.metric("실시간 통합 순자산", f"{t_a - t_d:,.0f}원")

st.header("5. 생활 주기 관리")
l_rows = []
for item, info in FIXED_DATA["lifecycle"].items():
    rem = (datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"]) - datetime.now()).days
    l_rows.append({"항목": item, "마지막 수행": info["last"], "상태": "🚨 점검" if rem <= 0 else "✅ 정상", "D-Day": f"{rem}일"})
st.table(pd.DataFrame(l_rows).assign(순번=range(1, 4)).set_index('순번'))

st.header("6. 주방 재고 현황")
st.table(pd.DataFrame([{"카테고리": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()]).assign(순번=range(1, 5)).set_index('순번'))

st.header("7. 오늘 상세 로그 (식단 및 지출)")
if st.session_state.master_log:
    log_df = pd.DataFrame(st.session_state.master_log)
    # 가독성을 위해 주요 영양소와 금액만 노출
    display_log = log_df[["시간", "항목", "금액", "지출수단", "칼로리", "나트륨", "콜레스테롤"]]
    st.table(display_log.assign(순번=range(1, len(display_log)+1)).set_index('순번'))
else:
    st.info("오늘 기록된 내역이 없습니다.")
