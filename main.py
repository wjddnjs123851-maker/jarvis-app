import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 마스터 데이터: 자산, 주식, 코인, 금 상세 정보] ---
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
    "assets": {
        "gold": {"qty_gram": 16.0, "bought_price_1g": 243800}, # 4돈(15g) + 1g
        "cash_balance": 492918,
        "savings": {"청년도약계좌": 14700000, "주택청약": 2540000, "전세보증금": 145850000},
        "liabilities": {"전세대출": 100000000, "마이너스통장": 3000000, "학자금대출": 1247270}
    },
    "kitchen": {
        "단백질": "냉동삼치, 냉동닭다리, 관찰레, 북어채, 단백질쉐이크",
        "곡물/면": "파스타면, 소면, 쿠스쿠스, 라면, 우동, 쌀/카무트",
        "신선/기타": "김치4종, 아사이베리, 치아씨드, 향신료, 치즈"
    },
    "lifecycle": {
        "면도날": {"last": "2026-02-06", "period": 21},
        "칫솔": {"last": "2026-02-06", "period": 90},
        "이불세탁": {"last": "2026-02-04", "period": 14}
    }
}

API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

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
    prices = {"stocks": {}, "crypto": {}, "gold": 231345} # 금 시세는 오늘 검색된 약 23.1만원/g 반영
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

# --- [3. UI 및 사이드바 입력] ---
st.set_page_config(page_title="JARVIS v14.0", layout="wide")
if 'consumed' not in st.session_state: st.session_state.consumed = {k: 0 for k in FIXED_DATA["health_target"].keys()}

with st.sidebar:
    st.title("JARVIS 입력 센터")
    
    with st.expander("건강 및 식단 기록", expanded=True):
        in_w = st.number_input("체중(kg)", 125.0, step=0.1)
        in_kcal = st.number_input("칼로리", 0)
        in_carb = st.number_input("탄수", 0)
        in_prot = st.number_input("단백", 0)
        in_fat = st.number_input("지방", 0)
        in_sug = st.number_input("당", 0)
        in_na = st.number_input("나트륨", 0)
        in_cho = st.number_input("콜레스테롤", 0)
        if st.button("건강 데이터 전송"):
            send_to_sheet("체중", "일일체크", in_w)
            send_to_sheet("식단", "칼로리", in_kcal)
            for k, v in zip(FIXED_DATA["health_target"].keys(), [in_kcal, in_carb, in_prot, in_fat, in_sug, in_na, in_cho]):
                st.session_state.consumed[k] += v
            st.success("건강 데이터 전송 완료")

    with st.expander("가계부 기록", expanded=True):
        t_type = st.selectbox("구분", ["지출", "수입"])
        t_item = st.text_input("항목명")
        t_val = st.number_input("금액", 0)
        if st.button("가계부 전송"):
            if send_to_sheet(t_type, t_item, t_val):
                st.success(f"{t_type} 전송 완료")

# --- [4. 메인 리포트] ---
st.title("JARVIS 통합 리포트")
tabs = st.tabs(["건강/식단 리포트", "자산/가계부 리포트", "재고/생활 관리"])

# 탭 1: 건강 리포트
with tabs[0]:
    st.subheader("일일 영양 섭취 현황")
    n_rows = []
    for k, v in st.session_state.consumed.items():
        n_rows.append({"항목": k, "현재": v, "목표": FIXED_DATA["health_target"][k]})
    df_n = pd.DataFrame(n_rows)
    df_n.index = range(1, len(df_n) + 1)
    st.table(df_n)

# 탭 2: 자산 및 가계부 리포트
with tabs[1]:
    live = get_live_prices()
    st.subheader("통합 자산 현황")
    a_rows = []
    # 1. 현금 및 예적금
    a_rows.append({"분류": "현금", "항목": "가용 잔고", "평가액": f"{FIXED_DATA['assets']['cash_balance']:,}원", "수익률": "-"})
    for k, v in FIXED_DATA["assets"]["savings"].items():
        a_rows.append({"분류": "예적금", "항목": k, "평가액": f"{v:,}원", "수익률": "-"})
    
    # 2. 금 (Gold)
    g_qty = FIXED_DATA["assets"]["gold"]["qty_gram"]
    g_eval = int(g_qty * live["gold"])
    g_profit_rate = ((live["gold"] / FIXED_DATA["assets"]["gold"]["bought_price_1g"]) - 1) * 100
    a_rows.append({"분류": "귀금속", "항목": f"순금({g_qty}g)", "평가액": f"{g_eval:,}원", "수익률": f"{g_profit_rate:.2f}% (1g 구매분 기준)"})
    
    # 3. 주식 및 코인
    for n, i in FIXED_DATA["stocks"].items():
        curr = live["stocks"].get(n, i['평단'])
        a_rows.append({"분류": "주식", "항목": n, "평가액": f"{curr * i['수량']:,}원", "수익률": f"{((curr/i['평단'])-1)*100:.2f}%"})
    for n, i in FIXED_DATA["crypto"].items():
        curr = live["crypto"].get(i['마켓'], i['평단'])
        a_rows.append({"분류": "코인", "항목": n, "평가액": f"{int(curr * i['수량']):,}원", "수익률": f"{((curr/i['평단'])-1)*100:.2f}%"})
    
    # 4. 부채
    for k, v in FIXED_DATA["assets"]["liabilities"].items():
        a_rows.append({"분류": "부채", "항목": k, "평가액": f"-{v:,}원", "수익률": "-"})

    df_a = pd.DataFrame(a_rows)
    df_a.index = range(1, len(df_a) + 1)
    st.table(df_a)

# 탭 3: 재고 및 생활 관리
with tabs[2]:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("소모품 주기")
        l_rows = []
        now_kr = datetime.utcnow() + timedelta(hours=9)
        for item, info in FIXED_DATA["lifecycle"].items():
            d_day = (datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"]) - now_kr).days
            l_rows.append({"항목": item, "상태": f"{d_day}일 남음", "최근": info["last"]})
        df_l = pd.DataFrame(l_rows)
        df_l.index = range(1, len(df_l) + 1)
        st.table(df_l)
    with c2:
        st.subheader("주방 재고")
        df_k = pd.DataFrame([{"카테고리": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()])
        df_k.index = range(1, len(df_k) + 1)
        st.table(df_k)
