import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import json
import re
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
st.set_page_config(page_title="JARVIS v75.0 Final", layout="wide")

API_URL = "https://script.google.com/macros/s/AKfycbw93B0RE2aeYBMDKKL0kyKHKc7c1mmUAe2QkSo-rENECvGD7xHS-0uSBwaOttyFLuwy/exec"
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {"log": "0", "assets": "1068342666", "inventory": "2138778159", "pharmacy": "347265850"}

# 2000kcal 기준 정원님 맞춤 목표
GOALS = {
    "칼로리": 2000, "탄수화물": 150, "단백질": 150, "지방": 60, 
    "당류": 30, "나트륨": 2000, "콜레스테롤": 300, "식이섬유": 25
}

# --- [2. 핵심 엔진] ---
@st.cache_data(ttl=300)
def fetch_market():
    """자산 시세 호출 (오류 방지 로직 강화)"""
    data = {}
    try:
        yf_data = yf.Tickers("USDKRW=X GC=F 005930.KS 000660.KS 010140.KS 033500.KQ")
        rate = yf_data.tickers["USDKRW=X"].fast_info['last_price']
        data.update({'USD_KRW': rate, '금(16g)': (yf_data.tickers["GC=F"].fast_info['last_price'] / 31.1035) * rate})
        stocks = {"삼성전자":"005930.KS", "SK하이닉스":"000660.KS", "삼성중공업":"010140.KS", "동성화인텍":"033500.KQ"}
        for n, c in stocks.items(): data[n] = yf_data.tickers[c].fast_info['last_price']
        c_res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH", timeout=5).json()
        data.update({'비트코인(BTC)': c_res[0]['trade_price'], '이더리움(ETH)': c_res[1]['trade_price']})
    except: pass
    return data

def load_data(gid):
    """시트 로드 및 방탄 데이터 정제"""
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={datetime.now().timestamp()}"
    try:
        df = pd.read_csv(url)
        return df.dropna(how='all').reset_index(drop=True)
    except: return pd.DataFrame()

def safe_float(v):
    """ValueError 방지: 어떤 값이 들어와도 숫자로 안전하게 변환"""
    if pd.isna(v) or v == "": return 0.0
    try:
        if isinstance(v, str):
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", v.replace(',', ''))
            return float(nums[0]) if nums else 0.0
        return float(v)
    except: return 0.0

def get_smart_nutrition(food_name, weight):
    """지능형 영양 분석 (DB가 없어도 기초 수치 기반 추정 계산)"""
    db = {
        "냉동큐브닭가슴살": [165, 0, 31, 3.6, 0, 45, 85, 0],
        "계란": [150, 1, 12, 10, 1, 130, 370, 0],
        "햇반": [145, 33, 3, 0.5, 0, 5, 0, 1],
        "훈제오리": [300, 2, 18, 25, 1, 600, 80, 0]
    }
    base = db.get(food_name, [100, 10, 5, 5, 2, 100, 10, 1]) # 기본값
    return [round((v * weight / 100), 2) for v in base]
    # --- [3. 메인 인터페이스] ---
market = fetch_market()
st.sidebar.title("🛡️ JARVIS v75.0")
active_user = st.sidebar.radio("사용자", ["정원", "서진"])
menu = st.sidebar.selectbox("메뉴", ["📊 통합 자산 & 가계부", "🥩 99kg 다이어트 보드", "💊 상비약 관리", "⚙️ 시스템 관리"])

if menu == "📊 통합 자산 & 가계부":
    st.subheader(f"📊 {active_user}님 실시간 순자산 현황")
    df_a = load_data(GID_MAP["assets"])
    if not df_a.empty:
        summary, total_val = [], 0.0
        for _, r in df_a.iterrows():
            name = str(r.iloc[0])
            qty = safe_float(r.iloc[1]) # 여기서 발생하던 에러를 방어했습니다
            price = market.get(name, 0.0)
            val = price * qty if price > 0 else qty
            summary.append({"항목": name, "수량/금액": qty, "평가액": val})
            total_val += val
        st.metric("현재 총 자산", f"{total_val:,.0f} 원")
        st.dataframe(pd.DataFrame(summary), use_container_width=True)
    
    st.divider()
    st.write("💸 최근 가계부 내역")
    st.table(load_data(GID_MAP["log"]).tail(5))

elif menu == "🥩 99kg 다이어트 보드":
    st.subheader("🔥 결혼식 목표 99kg: 영양 & 재고 추적")
    df_i = load_data(GID_MAP["inventory"])
    if not df_i.empty:
        col1, col2 = st.columns([1, 1.2])
        with col1:
            with st.form("diet_form"):
                food = st.selectbox("섭취 품목", df_i.iloc[:, 1].dropna().tolist())
                gram = st.number_input("섭취량(g/개)", min_value=0.0)
                if st.form_submit_button("섭취 기록 및 차감"):
                    payload = {"action": "diet_with_inventory", "gid": GID_MAP["inventory"], "item": food, "weight": gram, "user": active_user}
                    requests.post(API_URL, data=json.dumps(payload))
                    st.success("재고가 반영되었습니다!"); st.rerun()

        with col2:
            nutri = get_smart_nutrition(food, gram)
            labels = ["칼로리", "탄수화물", "단백질", "지방", "당류", "나트륨", "콜레스테롤", "식이섬유"]
            fig = go.Figure()
            for i, label in enumerate(labels):
                pct = (nutri[i] / GOALS[label]) * 100
                fig.add_trace(go.Bar(name=label, x=[label], y=[pct], text=f"{pct:.1f}%", textposition='auto'))
            fig.update_layout(title="오늘의 영양 달성도 (2,000kcal 기준)", yaxis_range=[0, 100])
            st.plotly_chart(fig, use_container_width=True)

elif menu == "💊 상비약 관리":
    st.subheader("💊 의약품 안전 관리")
    df_p = load_data(GID_MAP["pharmacy"])
    if not df_p.empty:
        df_p['유통/소비기한'] = pd.to_datetime(df_p.iloc[:, 3], errors='coerce')
        st.dataframe(df_p.sort_values('유통/소비기한'), use_container_width=True)

elif menu == "⚙️ 시스템 관리":
    st.subheader("⚙️ 데이터베이스 통합 편집")
    st.info("여기서 행 추가(Add)나 삭제(Delete)를 한 뒤 '저장'을 누르면 구글 시트에 즉시 반영됩니다.")
    target = st.selectbox("편집 대상 시트", ["assets", "inventory", "pharmacy", "log"])
    df_m = load_data(GID_MAP[target])
    edited = st.data_editor(df_m, num_rows="dynamic", use_container_width=True)
    if st.button("💾 변경사항 클라우드 저장"):
        payload = {"action": "overwrite", "gid": GID_MAP[target], "data": [edited.columns.tolist()] + edited.values.tolist()}
        requests.post(API_URL, data=json.dumps(payload))
        st.success("동기화 완료!"); st.rerun()
