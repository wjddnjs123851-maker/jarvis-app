import streamlit as st
import pandas as pd
import requests
import json
import plotly.express as px
from datetime import datetime, timedelta

# --- [1. 시스템 설정 및 상수] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

FIXED_DATA = {
    "health_target": {"칼로리": 2000, "지방": 65, "탄수화물": 300, "단백질": 150},
    "stocks": {
        "동성화인텍": {"평단": 22701, "수량": 21},
        "삼성중공업": {"평단": 16761, "수량": 88},
        "SK하이닉스": {"평단": 473521, "수량": 6},
        "삼성전자": {"평단": 78895, "수량": 46}
    },
    "crypto": {
        "BTC": {"평단": 137788139, "수량": 0.00181400},
        "ETH": {"평단": 4243000, "수량": 0.03417393}
    },
    "recurring": [
        {"항목": "임대료/대출이자", "금액": 524900},
        {"항목": "고정비(통신/보험/구독)", "금액": 300660},
        {"항목": "청년도약계좌", "금액": 700000}
    ]
}

# --- [2. 핵심 유틸리티] ---
def to_numeric(val):
    """문자열 숫자를 정수로 변환 (쉼표, 단위 제거)"""
    try:
        return int(float(str(val).replace(',', '').replace('원', '').strip()))
    except: return 0

def format_krw(val):
    return f"{int(val):,}"

def send_to_sheet(d_type, item, value):
    now = datetime.utcnow() + timedelta(hours=9)
    payload = {"time": now.strftime('%Y-%m-%d %H:%M:%S'), "type": d_type, "item": item, "value": value}
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=5)
        return res.status_code == 200
    except: return False

@st.cache_data(ttl=60)
def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        return df.dropna(subset=[df.columns[0]])
    except: return pd.DataFrame()

# --- [3. 메인 레이아웃 및 스타일] ---
st.set_page_config(page_title="JARVIS v32.5", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
</style>""", unsafe_allow_html=True)

# --- [4. 사이드바 제어판] ---
with st.sidebar:
    st.title("🤖 JARVIS OS")
    menu = st.radio("모듈 선택", ["📊 투자 & 자산", "🥗 식단 & 건강", "📦 재고 관리"])
    st.divider()
    
    if menu == "🥗 식단 & 건강":
        st.subheader("Daily 로그 입력")
        w_col, k_col = st.columns(2)
        in_w = w_col.number_input("체중(kg)", 0.0, 150.0, 125.0, step=0.1)
        in_kcal = k_col.number_input("칼로리", 0, 5000, 0)
        
        with st.expander("세부 영양소 입력"):
            c1, c2 = st.columns(2)
            in_fat = c1.number_input("지방(g)", 0)
            in_na = c1.number_input("나트륨(mg)", 0)
            in_fiber = c1.number_input("식이섬유(g)", 0)
            in_prot = c2.number_input("단백질(g)", 0)
            in_carb = c2.number_input("탄수화물(g)", 0)
            in_sugar = c2.number_input("당(g)", 0)
        
        if st.button("데이터 동기화", use_container_width=True, type="primary"):
            with st.spinner("전송 중..."):
                success = True
                success &= send_to_sheet("건강", "체중", in_w)
                inputs = {"칼로리": in_kcal, "지방": in_fat, "나트륨": in_na, "단백질": in_prot, "탄수화물": in_carb}
                for k, v in inputs.items():
                    if v > 0: success &= send_to_sheet("식단", k, v)
                if success: st.success("시트 업데이트 완료!")

# --- [5. 메인 대시보드] ---
st.title(f"Core System: {menu}")

if menu == "📊 투자 & 자산":
    # 상단 요약 지표
    asset_df = load_sheet_data(GID_MAP["Assets"])
    cash_total = sum(asset_df.iloc[:, 1].apply(to_numeric)) if not asset_df.empty else 0
    
    # 투자 자산 계산
    inv_rows = []
    for name, info in {**FIXED_DATA["stocks"], **FIXED_DATA["crypto"]}.items():
        val = info['평단'] * info['수량']
        inv_rows.append({"항목": name, "평가액": val, "유형": "투자"})
    
    inv_total = sum(row['평가액'] for row in inv_rows)
    
    m1, m2, m3 = st.columns(3)
    m1.metric("총 자산(추정)", f"{format_krw(cash_total + inv_total)}원")
    m2.metric("보유 현금", f"{format_krw(cash_total)}원")
    m3.metric("투자 비중", f"{(inv_total/(cash_total+inv_total+1)*100):.1f}%")

    

    # 자산 구성 차트 및 상세 표
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.subheader("자산 포트폴리오")
        plot_data = pd.DataFrame([{"유형": "현금/금융", "금액": cash_total}, {"유형": "투자자산", "금액": inv_total}])
        fig = px.pie(plot_data, values='금액', names='유형', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("상세 보유 내역")
        # 가독성을 위해 데이터프레임 정리
        display_inv = pd.DataFrame(inv_rows)
        display_inv['평가액'] = display_inv['평가액'].apply(format_krw)
        st.dataframe(display_inv, use_container_width=True, hide_index=True)

elif menu == "🥗 식단 & 건강":
    st.info("오늘의 권장 섭취량 대비 달성률을 시각화할 예정입니다. (데이터 로딩 중)")
    # (여기에 식단 로그 시트 데이터를 가져와서 시각화하는 로직 추가 가능)
