import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 마스터 데이터: 보스의 자산 및 목표 지표] ---
FIXED_DATA = {
    "health": {"항목": ["목표 체중", "주요 관리", "식단 금기"], "내용": ["90.0kg", "고지혈증/ADHD", "생굴/멍게"]},
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
        "cash": {"가용 현금": 492918, "금(Gold)": 0}, # 금은 정보를 주시면 업데이트 하겠습니다.
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
TARGET = {"칼로리": 2000, "탄수": 300, "단백": 150, "지방": 65, "당": 50, "나트륨": 2000, "콜레스테롤": 300}

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
    prices = {"stocks": {}, "crypto": {}}
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

# --- [3. UI 설정 및 사이드바 입력창] ---
st.set_page_config(page_title="JARVIS v13.0", layout="wide")
if 'consumed' not in st.session_state: st.session_state.consumed = {k: 0 for k in TARGET.keys()}

with st.sidebar:
    st.title("JARVIS 입력 센터")
    
    # 1. 건강/식단/체중 통합 입력
    with st.expander("건강 및 식단 기록", expanded=True):
        in_w = st.number_input("오늘 체중(kg)", 125.0, step=0.1)
        in_kcal = st.number_input("칼로리(kcal)", 0)
        in_carb = st.number_input("탄수(g)", 0)
        in_prot = st.number_input("단백(g)", 0)
        in_fat = st.number_input("지방(g)", 0)
        in_sug = st.number_input("당(g)", 0)
        in_na = st.number_input("나트륨(mg)", 0)
        in_cho = st.number_input("콜레스테롤(mg)", 0)
        
        if st.button("건강 데이터 시트 전송"):
            send_to_sheet("체중", "일일체크", in_w)
            send_to_sheet("식단", "칼로리", in_kcal)
            # 앱 내 세션 업데이트
            update_vals = [in_kcal, in_carb, in_prot, in_fat, in_sug, in_na, in_cho]
            for k, v in zip(TARGET.keys(), update_vals):
                st.session_state.consumed[k] += v
            st.success("건강 기록 완료")

    # 2. 가계부 통합 입력
    with st.expander("가계부 기록", expanded=False):
        t_type = st.selectbox("구분", ["지출", "수입"])
        t_item = st.text_input("항목명")
        t_val = st.number_input("금액", 0)
        if st.button("가계부 시트 전송"):
            if send_to_sheet(t_type, t_item, t_val):
                st.success(f"{t_type} 내역 저장 완료")

# --- [4. 메인 대시보드 리포트] ---
st.title("JARVIS 통합 리포트")
tabs = st.tabs(["건강 리포트", "자산 리포트", "생활 관리"])

# 탭 1: 건강 리포트
with tabs[0]:
    st.subheader("오늘의 영양 섭취 현황")
    nut_rows = []
    for k, v in st.session_state.consumed.items():
        nut_rows.append({"항목": k, "현재": v, "목표": TARGET[k], "상태": "초과" if v > TARGET[k] else "정상"})
    df_nut = pd.DataFrame(nut_rows)
    df_nut.index = range(1, len(df_nut) + 1)
    st.table(df_nut)
    
    st.subheader("건강 관리 가이드")
    df_health = pd.DataFrame(FIXED_DATA["health"])
    df_health.index = range(1, len(df_health) + 1)
    st.table(df_health)

# 탭 2: 자산 리포트 (통합 자산 관리)
with tabs[1]:
    live = get_live_prices()
    st.subheader("종합 자산 상세")
    
    asset_rows = []
    # 1. 현금 및 금
    for k, v in FIXED_DATA["assets"]["cash"].items():
        asset_rows.append({"분류": "가용자산", "항목": k, "평가금액": f"{v:,}원", "비고": "-"})
    
    # 2. 예적금
    for k, v in FIXED_DATA["assets"]["savings"].items():
        asset_rows.append({"분류": "예적금", "항목": k, "평가금액": f"{v:,}원", "비고": "-"})
    
    # 3. 주식 실시간
    for n, i in FIXED_DATA["stocks"].items():
        curr = live["stocks"].get(n, i['평단'])
        eval_amt = curr * i['수량']
        rate = ((curr / i['평단']) - 1) * 100
        asset_rows.append({"분류": "주식", "항목": n, "평가금액": f"{eval_amt:,}원", "비고": f"수익률 {rate:.2f}%"})
        
    # 4. 코인 실시간
    for n, i in FIXED_DATA["crypto"].items():
        curr = live["crypto"].get(i['마켓'], i['평단'])
        eval_amt = int(curr * i['수량'])
        rate = ((curr / i['평단']) - 1) * 100
        asset_rows.append({"분류": "코인", "항목": n, "평가금액": f"{eval_amt:,}원", "비고": f"수익률 {rate:.2f}%"})
        
    # 5. 부채
    for k, v in FIXED_DATA["assets"]["liabilities"].items():
        asset_rows.append({"분류": "부채", "항목": k, "평가금액": f"-{v:,}원", "비고": "상환 필요"})

    df_asset = pd.DataFrame(asset_rows)
    df_asset.index = range(1, len(df_asset) + 1)
    st.table(df_asset)

# 탭 3: 생활 관리
with tabs[2]:
    col_l, col_k = st.columns(2)
    with col_l:
        st.subheader("교체 주기")
        l_rows = []
        for item, info in FIXED_DATA["lifecycle"].items():
            d_day = (datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"]) - (datetime.utcnow() + timedelta(hours=9))).days
            l_rows.append({"항목": item, "상태": f"{d_day}일 남음", "최근수행": info["last"]})
        df_l = pd.DataFrame(l_rows)
        df_l.index = range(1, len(df_l) + 1)
        st.table(df_l)
        
    with col_k:
        st.subheader("주방 재고")
        df_k = pd.DataFrame([{"카테고리": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()])
        df_k.index = range(1, len(df_k) + 1)
        st.table(df_k)
