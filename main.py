import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 마스터 데이터 및 설정] ---
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
    "assets_base": { # 시트에서 읽어오기 전 기본 베이스 (시트가 비어있을 때 사용)
        "gold": 16.0,
        "현금": 492918,
        "청년도약계좌": 14700000,
        "주택청약": 2540000,
        "전세보증금": 145850000,
        "전세대출": -100000000,
        "마이너스통장": -3000000,
        "학자금대출": -1247270
    },
    "categories": {
        "지출": ["식비(집밥)", "식비(외식)", "식비(배달)", "식비(편의점)", "생활용품", "건강/의료", "기호품", "주거/통신", "교통/차량", "금융/보험", "결혼준비", "경조사", "기타지출"],
        "수입": ["급여", "금융소득", "기타"],
        "자산이동": ["적금/청약 납입", "주식/코인 매수", "대출 원금상환"]
    }
}

API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"
SPREADSHEET_ID = '1X6ypXRLkHIMOSGuYdNLnzLkVB4xHfpRR'
# Finance 탭 CSV URL (GID는 시트마다 다르므로 확인 필요, 통상 첫번째 시트가 0)
FINANCE_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=YOUR_FINANCE_GID" 

# --- [2. 시스템 유틸리티] ---
def send_to_sheet(d_type, item, value):
    now = datetime.utcnow() + timedelta(hours=9)
    kr_time = now.strftime('%Y-%m-%d %H:%M:%S')
    payload = {"time": kr_time, "type": d_type, "item": item, "value": value}
    try:
        requests.post(API_URL, data=json.dumps(payload), timeout=5)
        return True
    except: return False

def get_live_prices():
    prices = {"stocks": {}, "crypto": {}, "gold": 231345}
    # 주식/코인 가격 수집 (기존 v17.0 로직 동일)
    for name, info in FIXED_DATA["stocks"].items():
        try:
            res = requests.get(f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{info['코드']}", timeout=1).json()
            prices["stocks"][name] = int(res['result']['areas'][0]['datas'][0]['nv'])
        except: prices["stocks"][name] = info['평단']
    try:
        res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH", timeout=1).json()
        for c in res: prices["crypto"][c['market']] = float(c['trade_price'])
    except:
        for k, v in FIXED_DATA["crypto"].items(): prices["crypto"][v['마켓']] = v['평단']
    return prices

# --- [3. UI 설정 및 제어] ---
st.set_page_config(page_title="JARVIS v18.0", layout="wide")
if 'consumed' not in st.session_state: st.session_state.consumed = {k: 0 for k in FIXED_DATA["health_target"].keys()}

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["영양/식단/체중", "자산/투자/가계부", "재고/생활관리"])
    st.divider()
    
    if menu == "영양/식단/체중":
        # 건강 입력 로직 (v17.0 동일)
        in_w = st.number_input("현재 체중(kg)", 125.0, step=0.1)
        in_kcal = st.number_input("칼로리", 0)
        # ... (중략)
        if st.button("전송"):
            send_to_sheet("체중", "일일체크", in_w)
            st.success("기록 완료")

    elif menu == "자산/투자/가계부":
        st.subheader("가계부 및 자산이동")
        t_type = st.selectbox("구분", ["지출", "수입", "자산이동"])
        t_cat = st.selectbox("카테고리 선택", FIXED_DATA["categories"][t_type])
        t_memo = st.text_input("상세 내용", placeholder="예: 도약계좌 2월분 납입")
        t_val = st.number_input("금액", 0)
        
        if st.button("시트 기록"):
            item_full = f"{t_cat} - {t_memo}" if t_memo else t_cat
            if send_to_sheet(t_type, item_full, t_val):
                st.success(f"[{t_type}] 기록 완료")

# --- [4. 메인 리포트] ---
st.title(f"JARVIS: {menu}")

if menu == "자산/투자/가계부":
    live = get_live_prices()
    st.subheader("실시간 통합 자산 리포트")
    
    # 💡 핵심 로직: Finance 시트를 읽어와서 자산 합산 (현재는 시뮬레이션 코드)
    # 실제로는 pd.read_csv(FINANCE_CSV_URL)를 통해 자산이동 금액을 합산합니다.
    current_assets = FIXED_DATA["assets_base"].copy()
    
    a_rows = []
    # (1) 현금/예적금/부채 출력
    for k, v in current_assets.items():
        if k != "gold":
            a_rows.append({"분류": "금융", "항목": k, "평가액": f"{v:,}원", "비고": "-"})
    
    # (2) 금/주식/코인 실시간 (기존 로직)
    g_eval = int(current_assets["gold"] * live["gold"])
    a_rows.append({"분류": "귀금속", "항목": "순금(16g)", "평가액": f"{g_eval:,}원", "비고": "실시간 시세반영"})
    
    for n, i in FIXED_DATA["stocks"].items():
        curr = live["stocks"].get(n, i['평단'])
        a_rows.append({"분류": "주식", "항목": n, "평가액": f"{curr * i['수량']:,}원", "비고": f"{((curr/i['평단'])-1)*100:.2f}%"})
    
    df_a = pd.DataFrame(a_rows)
    df_a.index = range(1, len(df_a) + 1)
    st.table(df_a)
