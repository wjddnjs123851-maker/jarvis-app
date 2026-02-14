import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정 및 GID 정보] ---
SPREADSHEET_ID = '1X6ypXRLkHIMOSGuYdNLnzLkVB4xHfpRR'
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532"}

FIXED_DATA = {
    "health_target": {"칼로리": 2000, "탄수": 300, "단백": 150, "지방": 65, "당": 50, "나트륨": 2000, "콜레스테롤": 300},
    "stocks": {
        "동성화인텍": {"평단": 22701, "수량": 21, "코드": "033500"},
        "삼성중공업": {"평단": 16761, "수량": 88, "코드": "010140"},
        "SK하이닉스": {"평단": 473521, "수량": 6, "코드": "000660"},
        "삼성전자": {"평단": 78895, "수량": 46, "코드": "005930"}
    },
    "crypto": {
        "BTC": {"평단": 137788139, "수량": 0.00181400, "마켓": "KRW-BTC"},
        "ETH": {"평단": 4243000, "수량": 0.03417393, "마켓": "KRW-ETH"}
    },
    "recurring": [
        {"항목": "임대료", "금액": 261620}, {"항목": "대출 이자", "금액": 263280},
        {"항목": "통신비", "금액": 136200}, {"항목": "보험료", "금액": 121780},
        {"항목": "청년도약계좌(적금)", "금액": 700000}, 
        {"항목": "구독서비스(유튜브/Gemini/쿠팡 등)", "금액": 42680}
    ],
    "categories": {
        "지출": ["식비(집밥)", "식비(외식)", "식비(배달)", "식비(편의점)", "생활용품", "건강/의료", "기호품", "주거/통신", "교통/차량", "금융/보험", "결혼준비", "경조사", "기타지출"],
        "수입": ["급여", "금융소득", "기타"],
        "자산이동": ["적금/청약 납입", "주식/코인 매수", "대출 원금상환"]
    },
    "lifecycle": {
        "면도날": {"last": "2026-02-06", "period": 21},
        "칫솔": {"last": "2026-02-06", "period": 90},
        "이불세탁": {"last": "2026-02-04", "period": 14}
    },
    "kitchen": {
        "단백질": "냉동삼치, 냉동닭다리, 관찰레, 북어채, 단백질쉐이크",
        "곡물/면": "파스타면, 소면, 쿠스쿠스, 라면, 우동, 쌀/카무트",
        "신선/기타": "김치4종, 아사이베리, 치아씨드, 향신료, 치즈"
    }
}

API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# --- [2. 유틸리티 함수] ---
def send_to_sheet(d_type, item, value):
    now = datetime.utcnow() + timedelta(hours=9)
    payload = {"time": now.strftime('%Y-%m-%d %H:%M:%S'), "type": d_type, "item": item, "value": value}
    try:
        requests.post(API_URL, data=json.dumps(payload), timeout=5)
        return True
    except: return False

@st.cache_data(ttl=60)
def load_csv(sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={GID_MAP[sheet_name]}"
    try:
        df = pd.read_csv(url)
        return df
    except:
        return pd.DataFrame()

def get_live_prices():
    prices = {"stocks": {}, "crypto": {}, "gold": 231345}
    for n, i in FIXED_DATA["stocks"].items():
        try:
            res = requests.get(f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{i['코드']}", timeout=1).json()
            prices["stocks"][n] = int(res['result']['areas'][0]['datas'][0]['nv'])
        except: prices["stocks"][n] = i['평단']
    try:
        res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH", timeout=1).json()
        for c in res: prices["crypto"][c['market']] = float(c['trade_price'])
    except:
        for k, v in FIXED_DATA["crypto"].items(): prices["crypto"][v['마켓']] = v['평단']
    return prices

# --- [3. 메인 인터페이스] ---
st.set_page_config(page_title="JARVIS v21.0", layout="wide")
if 'consumed' not in st.session_state: st.session_state.consumed = {k: 0 for k in FIXED_DATA["health_target"].keys()}

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["영양/식단/체중", "자산/투자/가계부", "재고/생활관리"])
    st.divider()
    
    if menu == "영양/식단/체중":
        st.subheader("건강/영양 입력")
        in_w = st.number_input("현재 체중(kg)", 125.0, step=0.1)
        in_kcal = st.number_input("칼로리", 0)
        in_carb = st.number_input("탄수", 0)
        in_prot = st.number_input("단백", 0)
        in_fat = st.number_input("지방", 0)
        in_sug = st.number_input("당", 0)
        in_na = st.number_input("나트륨", 0)
        in_cho = st.number_input("콜레스테롤", 0)
        if st.button("데이터 시트 전송"):
            send_to_sheet("체중", "일일체크", in_w)
            send_to_sheet("식단", "칼로리", in_kcal)
            for k, v in zip(FIXED_DATA["health_target"].keys(), [in_kcal, in_carb, in_prot, in_fat, in_sug, in_na, in_cho]):
                st.session_state.consumed[k] += v
            st.success("Log 전송 완료")

    elif menu == "자산/투자/가계부":
        st.subheader("가계부 기록")
        t_type = st.selectbox("구분", ["지출", "수입", "자산이동"])
        t_cat = st.selectbox("카테고리", FIXED_DATA["categories"][t_type])
        t_memo = st.text_input("상세 메모")
        t_val = st.number_input("금액", 0)
        if st.button("시트 기록"):
            if send_to_sheet(t_type, f"{t_cat} - {t_memo}", t_val):
                st.success("Finance 전송 완료")

# --- [4. 메뉴별 리포트 화면] ---
st.title(f"자비스 리포트: {menu}")

if menu == "영양/식단/체중":
    st.subheader("일일 영양 섭취 현황")
    n_rows = []
    for k, v in st.session_state.consumed.items():
        n_rows.append({"항목": k, "현재": v, "목표": FIXED_DATA["health_target"][k]})
    df_n = pd.DataFrame(n_rows)
    df_n.index = range(1, len(df_n) + 1)
    st.table(df_n)

elif menu == "자산/투자/가계부":
    live = get_live_prices()
    
    # (1) 고정 지출 리포트
    st.subheader("매달 고정 지출 현황")
    df_recur = pd.DataFrame(FIXED_DATA["recurring"])
    df_recur.index = range(1, len(df_recur) + 1)
    st.table(df_recur)
    
    # (2) 실시간 자산 현황
    st.subheader("통합 자산 관리")
    df_assets = load_csv("Assets")
    a_rows = []
    
    # 시트 데이터 안전하게 로드
    if not df_assets.empty and "항목" in df_assets.columns:
        for _, row in df_assets.iterrows():
            a_rows.append({"분류": "금융", "항목": row['항목'], "평가액": f"{row['금액']:,}원", "비고": "기초잔액"})
    else:
        st.warning("Assets 탭의 데이터를 읽을 수 없습니다. (항목, 금액 컬럼 확인 필요)")

    # 금/주식/코인 데이터 추가
    g_qty = 16.0
    a_rows.append({"분류": "귀금속", "항목": "순금(16g)", "평가액": f"{int(g_qty * live['gold']):,}원", "비고": "시세반영"})
    for n, i in FIXED_DATA["stocks"].items():
        curr = live["stocks"].get(n, i['평단'])
        a_rows.append({"분류": "주식", "항목": n, "평가액": f"{curr * i['수량']:,}원", "비고": f"{((curr/i['평단'])-1)*100:.2f}%"})
    for n, i in FIXED_DATA["crypto"].items():
        curr = live["crypto"].get(i['마켓'], i['평단'])
        a_rows.append({"분류": "코인", "항목": n, "평가액": f"{int(curr * i['수량']):,}원", "비고": f"{((curr/i['평단'])-1)*100:.2f}%"})
    
    df_report = pd.DataFrame(a_rows)
    df_report.index = range(1, len(df_report) + 1)
    st.table(df_report)

elif menu == "재고/생활관리":
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("소모품 교체 주기")
        l_rows = []
        now_kr = datetime.utcnow() + timedelta(hours=9)
        for item, info in FIXED_DATA["lifecycle"].items():
            d_day = (datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"]) - now_kr).days
            l_rows.append({"항목": item, "상태": f"{d_day}일 남음", "최근수행": info["last"]})
        df_l = pd.DataFrame(l_rows)
        df_l.index = range(1, len(df_l) + 1)
        st.table(df_l)
    with c2:
        st.subheader("주방 재고 리스트")
        df_k = pd.DataFrame([{"구분": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()])
        df_k.index = range(1, len(df_k) + 1)
        st.table(df_k)
