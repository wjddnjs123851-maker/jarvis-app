import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import json
import re
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- [1. 시스템 보안 및 핵심 설정] ---
st.set_page_config(page_title="JARVIS v70.2 Pro", layout="wide", initial_sidebar_state="expanded")

# 데이터 정합성을 위한 상수 설정
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {
    "log": "0", "assets": "1068342666", 
    "inventory": "2138778159", "pharmacy": "347265850"
}
API_URL = "https://script.google.com/macros/s/AKfycbzctUtHI2tRtNRoRRfr06xfTp0W9XkxSI1gHj8JPz_E6ftbidN8o8Lz32VbxjAfGLzj/exec"

# --- [2. 전문 데이터 파싱 및 시세 엔진] ---
@st.cache_data(ttl=300)
def fetch_comprehensive_market():
    """주식, 코인, 금, 환율을 통합 조회하는 전문 엔진"""
    market = {}
    try:
        # 야후 파이낸스 일괄 조회 (속도 최적화)
        tickers = yf.Tickers("USDKRW=X GC=F 005930.KS 000660.KS 010140.KS 033500.KQ")
        
        # 1. 외환 및 원자재
        rate = tickers.tickers["USDKRW=X"].fast_info['last_price']
        market['USD_KRW'] = rate
        market['금'] = (tickers.tickers["GC=F"].fast_info['last_price'] / 31.1035) * rate
        
        # 2. 국내 주식 (정원님 보유 종목)
        market['삼성전자'] = tickers.tickers["005930.KS"].fast_info['last_price']
        market['하이닉스'] = tickers.tickers["000660.KS"].fast_info['last_price']
        market['삼성중공업'] = tickers.tickers["010140.KS"].fast_info['last_price']
        market['동성화인텍'] = tickers.tickers["033500.KQ"].fast_info['last_price']
        
        # 3. 가상자산 (업비트 API 연동)
        c_res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH", timeout=5).json()
        market['비트코인'] = c_res[0]['trade_price']
        market['이더리움'] = c_res[1]['trade_price']
    except Exception as e:
        st.sidebar.warning(f"⚠️ 시세 연동 일부 지연: {e}")
    return market

def load_fact_data(gid):
    """구글 시트 실시간 데이터 로드 (캐시 우회 포함)"""
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={datetime.now().timestamp()}"
    try:
        return pd.read_csv(url).dropna(how='all')
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame()

def parse_professional_num(v):
    """단위(kg, g, ml, L)가 포함된 복합 텍스트에서 순수 수치(g/ml) 추출"""
    if pd.isna(v) or v == "": return 0.0
    text = str(v).lower().replace(',', '')
    found = re.findall(r"[-+]?\d*\.\d+|\d+", text)
    if not found: return 0.0
    num = float(found[0])
    # 미터법 표준화 로직: kg, l는 1000배 환산 (단, ml는 제외)
    if ('kg' in text or 'l' in text) and 'ml' not in text:
        return num * 1000
    return num

def send_sync_request(payload):
    """Apps Script 서버 정합성 통신"""
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=15)
        return res.status_code == 200
    except:
        return False
        # --- [3. 사이드바 및 통합 시세 현황] ---
market_price = fetch_comprehensive_market()

with st.sidebar:
    st.title("🛡️ JARVIS v70.2")
    st.info(f"📅 Today: {datetime.now().strftime('%Y-%m-%d')}")
    access_user = st.radio("Access Level", ["정원", "서진"], horizontal=True)
    st.divider()
    
    # 실시간 마켓 브리핑 (사이드바 고정)
    col_a, col_b = st.columns(2)
    col_a.metric("BTC", f"{market_price.get('비트코인', 0)/10000:,.1f}M")
    col_b.metric("환율", f"{market_price.get('USD_KRW', 0):,.1f}")
    
    main_menu = st.selectbox("업무 영역 선택", 
                             ["📊 통합 자산 리포트", "🥩 식재료 재고 시스템", "💊 의약품 안전 관리", "🛠️ 데이터 마스터 편집"])

# --- [4. 영역별 비서 기능 구현] ---

if main_menu == "📊 통합 자산 리포트":
    st.header(f"📊 {access_user}님 자산 분석 리포트")
    df_assets = load_fact_data(GID_MAP["assets"])
    
    if not df_assets.empty:
        asset_summary, grand_total = [], 0.0
        for _, row in df_assets.iterrows():
            item_name, qty_raw = str(row.iloc[0]), row.iloc[1]
            qty = parse_professional_num(qty_raw)
            price = market_price.get(item_name, 0.0)
            eval_val = price * qty if price > 0 else qty
            
            asset_summary.append({
                "자산명": item_name, "보유수량": qty, 
                "현재가": price if price > 0 else "현금성", "평가액(KRW)": eval_val
            })
            grand_total += eval_val
            
        st.metric("실시간 총 자산 가치", f"{grand_total:,.0f} 원")
        st.dataframe(pd.DataFrame(asset_summary).style.highlight_max(axis=0, subset=['평가액(KRW)']), use_container_width=True)

elif main_menu == "🥩 식재료 재고 시스템":
    st.header("🥩 118종 식재료 재고 실시간 차감")
    df_inv = load_fact_data(GID_MAP["inventory"])
    
    if not df_inv.empty:
        # 시트의 2열(품목) 데이터 바인딩
        all_items = df_inv.iloc[:, 1].dropna().unique().tolist()
        
        with st.expander("🍽️ 오늘 사용한 식재료 입력", expanded=True):
            with st.form("diet_sync"):
                c1, c2 = st.columns(2)
                target_item = c1.selectbox("품목 선택", all_items)
                use_amount = c2.number_input("사용량 (단위 주의)", min_value=0.0, step=0.1)
                
                if st.form_submit_button("인벤토리 반영"):
                    payload = {"action": "diet_with_inventory", "user": access_user, 
                               "item": target_item, "weight": use_amount, "gid": GID_MAP["inventory"]}
                    if send_sync_request(payload):
                        st.success(f"✅ {target_item} {use_amount} 차감 기록 완료"); st.rerun()

        st.subheader("📦 현재 재고 브리핑")
        st.dataframe(df_inv.iloc[:, [1, 2, 4]], use_container_width=True)

elif main_menu == "💊 의약품 안전 관리":
    st.header("💊 의약품 소비기한 분석 (37종)")
    df_ph = load_fact_data(GID_MAP["pharmacy"])
    
    if not df_ph.empty:
        # 날짜 데이터 정제 및 분석
        df_ph['소비기한'] = pd.to_datetime(df_ph['소비기한'], errors='coerce')
        limit_date = datetime.now() + timedelta(days=30)
        
        danger = df_ph[df_ph['소비기한'] <= datetime.now()]
        warning = df_ph[(df_ph['소비기한'] > datetime.now()) & (df_ph['소비기한'] <= limit_date)]
        
        if not danger.empty: st.error(f"🚨 즉시 폐기 필요: {len(danger)}건")
        if not warning.empty: st.warning(f"⚠️ 30일 이내 만료 임박: {len(warning)}건")
        
        st.table(df_ph)

elif main_menu == "🛠️ 데이터 마스터 편집":
    st.header("🛠️ 시트 데이터 마스터 제어")
    st.warning("경고: 이곳의 수정사항은 구글 시트 원본을 직접 덮어씁니다.")
    
    db_choice = st.selectbox("수정할 데이터베이스", ["inventory", "pharmacy", "assets"])
    df_master = load_fact_data(GID_MAP[db_choice])
    
    final_edit = st.data_editor(df_master, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 클라우드 원본 강제 동기화"):
        payload = {"action": "overwrite", "gid": GID_MAP[db_choice], 
                   "data": [final_edit.columns.tolist()] + final_edit.values.tolist()}
        if send_sync_request(payload):
            st.success("✅ 모든 데이터가 시트에 안전하게 저장되었습니다."); st.rerun()
