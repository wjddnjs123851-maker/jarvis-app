import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# 고정 자산 데이터 (보스 포트폴리오)
FIXED_DATA = {
    "stocks": {
        "삼성전자": {"평단": 78895, "수량": 46},
        "SK하이닉스": {"평단": 473521, "수량": 6},
        "삼성중공업": {"평단": 16761, "수량": 88},
        "동성화인텍": {"평단": 22701, "수량": 21}
    },
    "crypto": {
        "BTC": {"평단": 137788139, "수량": 0.00181400},
        "ETH": {"평단": 4243000, "수량": 0.03417393}
    }
}

# 영양소 권장량
DAILY_GUIDE = {"지방": 65, "콜레스테롤": 300, "나트륨": 2000, "탄수화물": 300, "식이섬유": 30, "당": 50, "단백질": 150, "칼로리": 2000}

# --- [2. 유틸리티] ---
def format_krw(val):
    return f"{int(val):,}"

def to_numeric(val):
    try: return int(float(str(val).replace(',', '').replace('원', '').strip()))
    except: return 0

@st.cache_data(ttl=5)
def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        return df.dropna().reset_index(drop=True)
    except: return pd.DataFrame()

def send_to_sheet(d_type, item, value):
    now = datetime.utcnow() + timedelta(hours=9)
    payload = {"time": now.strftime('%Y-%m-%d %H:%M:%S'), "type": d_type, "item": item, "value": value}
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=5)
        return res.status_code == 200
    except: return False

# --- [3. 메인 설정] ---
st.set_page_config(page_title="JARVIS v33.0", layout="wide")
st.markdown("<style>.stTable td { text-align: right !important; }</style>", unsafe_allow_html=True)

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["식단 & 건강", "투자 & 자산", "재고 관리"])
    st.divider()
    
    # 사이드바 입력창 (식단 & 건강)
    if menu == "식단 & 건강":
        st.subheader("데이터 입력")
        in_w = st.number_input("체중(kg)", 0.0, 150.0, 125.0)
        in_fat = st.number_input("지방 (g)", 0)
        in_chol = st.number_input("콜레스테롤 (mg)", 0)
        in_na = st.number_input("나트륨 (mg)", 0)
        in_carb = st.number_input("탄수화물 (g)", 0)
        in_fiber = st.number_input("식이섬유 (g)", 0)
        in_sugar = st.number_input("당 (g)", 0)
        in_prot = st.number_input("단백질 (g)", 0)
        in_kcal = st.number_input("칼로리 (kcal)", 0)
        
        input_data = {"지방": in_fat, "콜레스테롤": in_chol, "나트륨": in_na, "탄수화물": in_carb, 
                      "식이섬유": in_fiber, "당": in_sugar, "단백질": in_prot, "칼로리": in_kcal}
        
        if st.button("시트로 전송", use_container_width=True):
            send_to_sheet("건강", "체중", in_w)
            for k, v in input_data.items():
                if v > 0: send_to_sheet("식단", k, v)
            st.success("전송 완료")

# --- [4. 메인 화면 로직] ---
st.title(f"시스템: {menu}")

if menu == "식단 & 건강":
    st.subheader("실시간 영양 분석 리포트")
    cols = st.columns(4)
    for idx, (k, v) in enumerate(input_data.items()):
        with cols[idx % 4]:
            ratio = min(v / DAILY_GUIDE[k], 1.0) if v > 0 else 0
            st.metric(k, f"{v} / {DAILY_GUIDE[k]}", f"{int(ratio*100)}%")
            st.progress(ratio)
    st.divider()
    st.warning("목표: 5월 30일 결혼식 전 체중 감량")

elif menu == "투자 & 자산":
    # 1. 시트 데이터 (현금, 금, 부채 등)
    df_sheet = load_sheet_data(GID_MAP["Assets"])
    df_sheet.columns = ["항목", "금액"]
    df_sheet["val"] = df_sheet["금액"].apply(to_numeric)
    
    # 2. 고정 자산 (주식, 코인) 합치기
    inv_rows = []
    for cat, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
        for name, info in items.items():
            total_val = info['평단'] * info['수량']
            inv_rows.append({"항목": name, "금액": format_krw(total_val), "val": total_val})
    
    df_inv = pd.DataFrame(inv_rows)
    
    # 전체 통합 데이터프레임
    df_total = pd.concat([df_sheet, df_inv], ignore_index=True)
    
    # 총계 계산
    total_a = df_total[df_total["val"] > 0]["val"].sum()
    total_l = df_total[df_total["val"] < 0]["val"].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("총 자산", f"{format_krw(total_a)}원")
    c2.metric("총 부채", f"{format_krw(total_l)}원")
    c3.metric("순자산", f"{format_krw(total_a + total_l)}원")
    
    st.subheader("전체 자산 목록")
    display_df = df_total[["항목", "금액"]].copy()
    display_df.index = range(1, len(display_df) + 1)
    st.table(display_df)

elif menu == "재고 관리":
    # 생활용품 및 식자재 섹션 (보스 맞춤 데이터)
    col_h, col_f = st.columns(2)
    
    with col_h:
        st.subheader("생활용품 관리주기")
        # 실제 관리 주기에 기반한 데이터 구성
        h_df = pd.DataFrame([
            {"품목": "칫솔", "주기": "1개월", "상태": "교체필요"},
            {"품목": "면도날", "주기": "2주", "상태": "양호"},
            {"품목": "영양제", "주기": "매일", "상태": "복용중"}
        ])
        h_df.index = range(1, len(h_df) + 1)
        st.table(h_df)

    with col_f:
        st.subheader("식자재 재고 관리")
        # 보스 식단(해산물 선호, 멍게/굴 제외) 반영 샘플
        f_df = pd.DataFrame([
            {"품목": "냉동 새우", "잔량": "여유", "보관": "냉동"},
            {"품목": "고등어", "잔량": "부족", "보관": "냉동"},
            {"품목": "닭가슴살", "잔량": "보통", "보관": "냉동"}
        ])
        f_df.index = range(1, len(f_df) + 1)
        st.table(f_df)
