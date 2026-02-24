import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import json
import re
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- [1. 시스템 보안 및 핵심 설정] ---
st.set_page_config(page_title="JARVIS v70.5 Pro", layout="wide", initial_sidebar_state="expanded")

SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {
    "log": "0", "assets": "1068342666", 
    "inventory": "2138778159", "pharmacy": "347265850"
}
API_URL = "https://script.google.com/macros/s/AKfycbzctUtHI2tRtNRoRRfr06xfTp0W9XkxSI1gHj8JPz_E6ftbidN8o8Lz32VbxjAfGLzj/exec"

# 영양성분 DB (정원님의 건강 관리를 위한 핵심 데이터)
NUTRITION_DB = {
    "닭가슴살": {"cal": 165, "prot": 31}, "소고기(우둔살)": {"cal": 137, "prot": 22},
    "계란": {"cal": 150, "prot": 12}, "햇반": {"cal": 145, "prot": 3},
    "돼지고기(뒷다리)": {"cal": 185, "prot": 20}, "훈제오리": {"cal": 300, "prot": 18}
}

# --- [2. 전문 데이터 엔진] ---

@st.cache_data(ttl=300)
def fetch_comprehensive_market():
    """주식, 코인, 금, 환율을 통합 조회하는 전문 엔진"""
    market = {}
    try:
        tickers = yf.Tickers("USDKRW=X GC=F 005930.KS 000660.KS 010140.KS 033500.KQ")
        rate = tickers.tickers["USDKRW=X"].fast_info['last_price']
        market['USD_KRW'] = rate
        market['금'] = (tickers.tickers["GC=F"].fast_info['last_price'] / 31.1035) * rate
        
        # 주식 종목 매핑
        stock_map = {"삼성전자": "005930.KS", "하이닉스": "000660.KS", "삼성중공업": "010140.KS", "동성화인텍": "033500.KQ"}
        for name, code in stock_map.items():
            market[name] = tickers.tickers[code].fast_info['last_price']
            
        # 코인 (업비트)
        c_res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH", timeout=5).json()
        market['비트코인'] = c_res[0]['trade_price']
        market['이더리움'] = c_res[1]['trade_price']
    except:
        st.sidebar.warning("⚠️ 실시간 시세 연동 일부 지연")
    return market

def load_fact_data(gid):
    """구글 시트 실시간 데이터 로드"""
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={datetime.now().timestamp()}"
    try:
        return pd.read_csv(url).dropna(how='all')
    except:
        return pd.DataFrame()

def parse_smart_val(v, is_inventory=False):
    """자산은 수량 그대로, 재고는 미터법 변환 적용 (천억 부자 버그 방지)"""
    if pd.isna(v) or v == "": return 0.0
    text = str(v).lower().replace(',', '')
    found = re.findall(r"[-+]?\d*\.\d+|\d+", text)
    if not found: return 0.0
    num = float(found[0])
    # 재고 관리 메뉴에서만 kg, L 단위를 1000배로 계산
    if is_inventory and ('kg' in text or ('l' in text and 'ml' not in text)):
        return num * 1000
    return num

def send_sync_request(payload):
    """Apps Script 서버 정합성 통신"""
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=15)
        return res.status_code == 200
    except:
        return False
        # --- [3. 사이드바 및 실시간 브리핑] ---
market_price = fetch_comprehensive_market()

with st.sidebar:
    st.title("🛡️ JARVIS v70.5")
    st.caption(f"접속 시간: {datetime.now().strftime('%H:%M:%S')}")
    access_user = st.radio("Access Level", ["정원", "서진"], horizontal=True)
    st.divider()
    
    # 핵심 경제 지표
    st.metric("비트코인", f"{market_price.get('비트코인', 0):,.0f}원")
    st.metric("환율(USD)", f"{market_price.get('USD_KRW', 0):,.2f}원")
    
    main_menu = st.selectbox("업무 영역 선택", 
                             ["📊 통합 자산 리포트", "🥩 식단 및 118종 재고", "💊 의약품 안전 관리", "🛠️ 마스터 데이터 편집"])

# --- [4. 영역별 비서 기능 구현] ---

if main_menu == "📊 통합 자산 리포트":
    st.header(f"📊 {access_user}님 통합 자산 분석")
    df_assets = load_fact_data(GID_MAP["assets"])
    
    if not df_assets.empty:
        summary, total = [], 0.0
        for _, row in df_assets.iterrows():
            name, qty_raw = str(row.iloc[0]), row.iloc[1]
            qty = parse_smart_val(qty_raw, is_inventory=False) # 자산은 뻥튀기 금지
            price = market_price.get(name, 0.0)
            eval_val = price * qty if price > 0 else qty
            
            summary.append({"자산명": name, "수량": qty, "현재가": price if price > 0 else "현금성", "평가액": eval_val})
            total += eval_val
            
        st.metric("총 자산 합계", f"{total:,.0f} 원")
        # 자산 비중 시각화 (Plotly)
        fig = go.Figure(data=[go.Pie(labels=[x['자산명'] for x in summary], values=[x['평가액'] for x in summary], hole=.3)])
        fig.update_layout(height=400, margin=dict(l=0, r=0, b=0, t=40))
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(pd.DataFrame(summary), use_container_width=True)

elif main_menu == "🥩 식단 및 118종 재고":
    st.header("🥩 식재료 재고 및 영양 관리")
    df_inv = load_fact_data(GID_MAP["inventory"])
    
    if not df_inv.empty:
        col1, col2 = st.columns([1, 1])
        with col1:
            with st.form("diet_sync"):
                # 시트 2열(품목)에서 118종 리스트 자동 추출
                all_items = df_inv.iloc[:, 1].dropna().unique().tolist()
                sel_item = st.selectbox("사용한 재료", all_items)
                weight = st.number_input("사용량 (g/ml/개)", min_value=0.0, step=1.0)
                
                if st.form_submit_button("재고 차감 실행"):
                    # 영양소 계산 (NUTRITION_DB 연동)
                    info = NUTRITION_DB.get(sel_item, {"cal": 0, "prot": 0})
                    payload = {
                        "action": "diet_with_inventory", "user": access_user, 
                        "item": sel_item, "weight": weight, 
                        "cal": (info["cal"]/100)*weight, "prot": (info["prot"]/100)*weight,
                        "gid": GID_MAP["inventory"]
                    }
                    if send_sync_request(payload):
                        st.success(f"✅ {sel_item} 차감 및 영양소 기록 완료"); st.rerun()

        with col2:
            st.subheader("📦 현재 재고 현황")
            st.dataframe(df_inv.iloc[:, [1, 2, 4]], height=300)

elif main_menu == "💊 의약품 안전 관리":
    st.header("💊 상비약 소비기한 모니터링")
    df_ph = load_fact_data(GID_MAP["pharmacy"])
    
    if not df_ph.empty:
        df_ph['소비기한'] = pd.to_datetime(df_ph['소비기한'], errors='coerce')
        # 기한 지남 / 30일 이내 임박 항목 추출
        expired = df_ph[df_ph['소비기한'] <= datetime.now()]
        imminent = df_ph[(df_ph['소비기한'] > datetime.now()) & (df_ph['소비기한'] <= datetime.now() + timedelta(days=30))]
        
        if not expired.empty: st.error(f"🚨 유통기한 만료 품목 {len(expired)}건 발견! 즉시 폐기하세요.")
        if not imminent.empty: st.warning(f"⚠️ 30일 이내 만료 예정 품목 {len(imminent)}건")
        st.dataframe(df_ph, use_container_width=True)

elif main_menu == "🛠️ 마스터 데이터 편집":
    st.header("🛠️ 시스템 데이터베이스 제어")
    db_choice = st.selectbox("편집할 시트", ["inventory", "pharmacy", "assets"])
    df_edit = load_fact_data(GID_MAP[db_choice])
    
    edited = st.data_editor(df_edit, num_rows="dynamic", use_container_width=True)
    if st.button("💾 변경사항 최종 저장"):
        payload = {"action": "overwrite", "gid": GID_MAP[db_choice], 
                   "data": [edited.columns.tolist()] + edited.values.tolist()}
        if send_sync_request(payload):
            st.success("✅ 클라우드 동기화 완료"); st.rerun()
