import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import json
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
st.set_page_config(page_title="JARVIS v73.0 Final", layout="wide")

# 정원님이 주신 최신 API URL 적용
API_URL = "https://script.google.com/macros/s/AKfycbw93B0RE2aeYBMDKKL0kyKHKc7c1mmUAe2QkSo-rENECvGD7xHS-0uSBwaOttyFLuwy/exec"
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {
    "log": "0", "assets": "1068342666", 
    "inventory": "2138778159", "pharmacy": "347265850"
}

# 2000kcal 기준 6대 영양소 + 식이섬유 목표 (결혼식 99kg 프로젝트)
GOALS = {
    "칼로리": 2000, "탄수화물": 150, "단백질": 150, 
    "지방": 60, "당류": 30, "나트륨": 2000, "콜레스테롤": 300, "식이섬유": 25
}

# --- [2. 핵심 엔진] ---
@st.cache_data(ttl=300)
def fetch_market():
    data = {}
    try:
        yf_data = yf.Tickers("USDKRW=X GC=F 005930.KS 000660.KS 010140.KS 033500.KQ")
        rate = yf_data.tickers["USDKRW=X"].fast_info['last_price']
        data.update({'USD_KRW': rate, '금(16g)': (yf_data.tickers["GC=F"].fast_info['last_price'] / 31.1035) * rate})
        stocks = {"삼성전자":"005930.KS", "SK하이닉스":"000660.KS", "삼성중공업":"010140.KS", "동성화인텍":"033500.KQ"}
        for n, c in stocks.items(): data[n] = yf_data.tickers[c].fast_info['last_price']
        c_res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH").json()
        data.update({'비트코인(BTC)': c_res[0]['trade_price'], '이더리움(ETH)': c_res[1]['trade_price']})
    except: pass
    return data

def load_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={datetime.now().timestamp()}"
    return pd.read_csv(url).dropna(how='all')

def sync_gsheet(action, gid, data=None, item=None, weight=None, user=None):
    payload = {"action": action, "gid": gid, "data": data, "item": item, "weight": weight, "user": user}
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=15)
        return res.status_code == 200
    except: return False

def get_nutrition(food_name, weight):
    """표준 영양 성분 매핑 (100g 기준 데이터 -> 섭취량 비례 계산)"""
    # 정원님 재고 기반 간이 DB (이후 확장 가능)
    db = {
        "냉동큐브닭가슴살": [165, 0, 31, 3.6, 0, 45, 85, 0],
        "계란": [150, 1, 12, 10, 1, 130, 370, 0],
        "햇반": [145, 33, 3, 0.5, 0, 5, 0, 1],
        "훈제오리": [300, 2, 18, 25, 1, 600, 80, 0]
    }
    base = db.get(food_name, [0]*8)
    return [round((v * weight / 100), 2) for v in base]
    # --- [3. 메인 레이아웃] ---
market = fetch_market()
st.sidebar.title("🛡️ JARVIS v73.0")
active_user = st.sidebar.radio("접속자", ["정원", "서진"])
menu = st.sidebar.selectbox("메뉴", ["📊 통합 자산 & 가계부", "🥩 식단-재고 연동 (99kg)", "💊 의약품 보관함", "⚙️ 시스템 마스터"])

if menu == "📊 통합 자산 & 가계부":
    st.subheader(f"📊 {active_user}님 자산/지출 리포트")
    # 자산 섹션
    df_a = load_data(GID_MAP["assets"])
    summary, total_val = [], 0.0
    for _, r in df_a.iterrows():
        name, qty = str(r.iloc[0]), float(r.iloc[1])
        price = market.get(name, 0.0)
        val = price * qty if price > 0 else qty
        summary.append({"항목": name, "보유": qty, "단위": str(r.iloc[2]), "평가액": val})
        total_val += val
    
    st.metric("실시간 순자산", f"{total_val:,.0f} 원")
    st.dataframe(pd.DataFrame(summary), use_container_width=True)
    
    # 가계부 최근 내역
    st.divider()
    st.write("💸 최근 가계부 기록")
    st.table(load_data(GID_MAP["log"]).tail(5))

elif menu == "🥩 식단-재고 연동 (99kg)":
    st.subheader("🥩 오늘의 영양 섭취 및 재고 관리")
    df_i = load_data(GID_MAP["inventory"])
    items = df_i.iloc[:, 1].dropna().unique().tolist()
    
    col1, col2 = st.columns([1, 1.2])
    with col1:
        with st.form("diet_form"):
            food = st.selectbox("품목 선택", items)
            gram = st.number_input("섭취량 (g/개/ml)", min_value=0.0)
            if st.form_submit_button("섭취 및 재고 차감"):
                if sync_gsheet("diet_with_inventory", GID_MAP["inventory"], item=food, weight=gram, user=active_user):
                    st.success("재고가 차감되었습니다!"); st.rerun()

    with col2:
        nutri = get_nutrition(food, gram)
        labels = ["칼로리", "탄수화물", "단백질", "지방", "당류", "나트륨", "콜레스테롤", "식이섬유"]
        # 대시보드 시각화 (목표 대비 섭취량)
        fig = go.Figure()
        for i, label in enumerate(labels):
            goal = GOALS.get(label, 1)
            fig.add_trace(go.Bar(name=label, x=[label], y=[(nutri[i]/goal)*100]))
        fig.update_layout(title="오늘의 영양 달성도 (%)", ylim=[0, 100])
        st.plotly_chart(fig, use_container_width=True)

elif menu == "💊 의약품 보관함":
    st.subheader("💊 상비약 유효기한 진단")
    df_p = load_data(GID_MAP["pharmacy"])
    df_p['유통/소비기한'] = pd.to_datetime(df_p['유통/소비기한'], errors='coerce')
    st.dataframe(df_p.sort_values('유통/소비기한'), use_container_width=True)

elif menu == "⚙️ 시스템 마스터":
    st.subheader("⚙️ 전 시트 편집 및 데이터 관리")
    target = st.selectbox("편집 대상", ["assets", "inventory", "pharmacy", "log"])
    df_edit = load_data(GID_MAP[target])
    
    # 여기서 행 추가, 삭제, 수정이 모두 가능합니다.
    edited = st.data_editor(df_edit, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 클라우드 동기화 (Overwrite)"):
        data_list = [edited.columns.tolist()] + edited.values.tolist()
        if sync_gsheet("overwrite", GID_MAP[target], data=data_list):
            st.success("구글 시트에 성공적으로 저장되었습니다!"); st.rerun()
