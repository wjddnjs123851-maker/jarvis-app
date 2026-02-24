import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import json
import re
from datetime import datetime, timedelta

# --- [1. 시스템 기본 설정] ---
st.set_page_config(page_title="JARVIS v70.0 Next Gen", layout="wide", initial_sidebar_state="expanded")

# 가계부 2.0 시트 정보
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {
    "log": "0", 
    "assets": "1068342666", 
    "inventory": "2138778159", 
    "pharmacy": "347265850"
}
# Apps Script 배포 URL
API_URL = "https://script.google.com/macros/s/AKfycbzctUtHI2tRtNRoRRfr06xfTp0W9XkxSI1gHj8JPz_E6ftbidN8o8Lz32VbxjAfGLzj/exec"

# --- [2. 핵심 데이터 엔진] ---

@st.cache_data(ttl=300)
def fetch_global_market():
    """주식, 코인, 환율, 금 시세 통합 호출 (5분 캐시)"""
    market_data = {}
    try:
        # 환율 및 금 시세 (yfinance 기반)
        # USDKRW=X: 원달러 환율, GC=F: 금 선물 시세
        tickers_yf = yf.Tickers("USDKRW=X GC=F")
        usd_krw = tickers_yf.tickers["USDKRW=X"].fast_info['last_price']
        gold_oz = tickers_yf.tickers["GC=F"].fast_info['last_price']
        
        market_data['USD_KRW'] = usd_krw
        # 금 1g당 한화 가격: (온스당 달러 / 31.1035) * 환율
        market_data['금'] = (gold_oz / 31.1035) * usd_krw
        
        # 국내 핵심 주식 (정원님 보유 종목 기반)
        stocks = {"삼성전자": "005930.KS", "하이닉스": "000660.KS", "삼성중공업": "010140.KS", "동성화인텍": "033500.KQ"}
        for name, code in stocks.items():
            market_data[name] = yf.Ticker(code).fast_info['last_price']
            
        # 가상자산 시세 (Upbit API)
        coin_resp = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH", timeout=2).json()
        market_data['비트코인'] = coin_resp[0]['trade_price']
        market_data['이더리움'] = coin_resp[1]['trade_price']
    except Exception as e:
        st.sidebar.error(f"시세 연동 엔진 오류: {e}")
    return market_data

def load_fact_data(gid):
    """구글 시트에서 최신 팩트 데이터 로드"""
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={datetime.now().timestamp()}"
    try:
        df = pd.read_csv(url)
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

def sync_to_cloud(payload):
    """Apps Script를 통해 클라우드 데이터 업데이트"""
    try:
        response = requests.post(API_URL, data=json.dumps(payload), timeout=15)
        return response.status_code == 200
    except:
        return False

def parse_unit_value(val_str):
    """미터법 텍스트(1.2kg, 500ml 등)에서 숫자 값만 추출"""
    if pd.isna(val_str) or val_str == "": return 0.0
    # 숫자 및 소수점만 추출하여 float 변환
    found = re.findall(r"[-+]?\d*\.\d+|\d+", str(val_str))
    if found:
        # 'kg'나 'L' 단위가 포함된 경우 기본 단위(g, ml)로 변환 로직 추가 가능
        num = float(found[0])
        if any(unit in str(val_str).lower() for unit in ['kg', 'l']):
            return num * 1000
        return num
    return 0.0
# --- [3. 사이드바 및 공통 시세 표시] ---
market = fetch_global_market()

with st.sidebar:
    st.title("🛡️ JARVIS v70.0")
    st.caption("Integrated Private AI Secretary")
    user = st.radio("Access Level", ["정원", "서진"])
    st.divider()
    menu = st.selectbox("메뉴 선택", ["📊 통합 자산 현황", "🥩 식단 및 재고 차감", "💊 스마트 약 보관함", "💾 마스터 데이터 관리"])
    
    st.divider()
    # 주요 지표 실시간 브리핑
    st.metric("비트코인(BTC)", f"{market.get('비트코인', 0):,.0f}원")
    st.metric("금 시세(1g)", f"{market.get('금', 0):,.0f}원")
    st.metric("USD 환율", f"{market.get('USD_KRW', 0):,.2f}원")

# --- [4. 메뉴별 상세 기능 구현] ---

if menu == "📊 통합 자산 현황":
    st.subheader(f"📊 {user}님과 서진님의 통합 자산 현황")
    df_assets = load_fact_data(GID_MAP["assets"])
    
    if not df_assets.empty:
        assets_list = []
        total_value = 0.0
        
        for _, row in df_assets.iterrows():
            name, qty_str = str(row.iloc[0]), str(row.iloc[1])
            qty = parse_unit_value(qty_str)
            price = market.get(name, 0.0)
            
            # 시세 데이터가 있는 경우 평가금액 계산, 없으면 수량(현금) 자체를 가치로 인정
            current_val = price * qty if price > 0 else qty
            assets_list.append({
                "자산항목": name, 
                "보유수량": qty, 
                "현재가/환율": price if price > 0 else 1.0, 
                "평가금액(KRW)": current_val
            })
            total_value += current_val
            
        st.metric("통합 총 자산 평가액", f"{total_value:,.0f} 원")
        st.dataframe(
            pd.DataFrame(assets_list).style.format({
                "보유수량": "{:,.2f}", 
                "현재가/환율": "{:,.2f}", 
                "평가금액(KRW)": "{:,.0f} 원"
            }), 
            use_container_width=True
        )

elif menu == "🥩 식단 및 재고 차감":
    st.subheader("🥩 118종 식재료 재고 연동 시스템")
    df_inv = load_fact_data(GID_MAP["inventory"])
    
    if not df_inv.empty:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            with st.form("diet_sync_form"):
                # 정제된 118종 리스트에서 품목 추출
                item_list = df_inv.iloc[:, 1].dropna().unique().tolist()
                selected_item = st.selectbox("사용 식재료 선택", item_list)
                use_val = st.number_input("차감량 (시트 표기 단위 기준)", min_value=0.0, step=0.1)
                
                if st.form_submit_button("차감 실행 및 식단 기록"):
                    payload = {
                        "action": "diet_with_inventory",
                        "user": user,
                        "item": selected_item,
                        "weight": use_val,
                        "gid": GID_MAP["inventory"]
                    }
                    if sync_to_cloud(payload):
                        st.success(f"✅ {selected_item} 차감 성공!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("❌ 전송 실패. 네트워크 또는 Apps Script 권한을 확인하세요.")
        
        with col2:
            st.info("💡 **재고 관리 원칙:** 고추장과 된장은 엄격히 분리됩니다. 시트의 미터법(g/ml) 표기를 준수하여 입력하세요.")
            st.write("#### 실시간 재고 모니터링")
            st.dataframe(df_inv.iloc[:, [1, 2, 4]], use_container_width=True)

elif menu == "💊 스마트 약 보관함":
    st.subheader("💊 의약품 소비기한 및 재고 현황 (37종)")
    df_pharma = load_fact_data(GID_MAP["pharmacy"])
    
    if not df_pharma.empty:
        # 데이터프레임 가공 (소비기한 날짜 형식 변환)
        df_pharma['소비기한'] = pd.to_datetime(df_pharma['소비기한'], errors='coerce')
        today = datetime.now()
        
        # 상태 진단: 만료 / 30일 이내 임박
        expired = df_pharma[df_pharma['소비기한'] < today]
        warning = df_pharma[(df_pharma['소비기한'] >= today) & (df_pharma['소비기한'] <= today + timedelta(days=30))]
        
        if not expired.empty:
            st.error(f"🚨 기한 만료 의약품 {len(expired)}건이 감지되었습니다. 폐기를 권장합니다.")
        if not warning.empty:
            st.warning(f"⚠️ {len(warning)}건의 의약품 기한이 30일 이내로 남았습니다.")
            
        st.dataframe(df_pharma, use_container_width=True)

elif menu == "💾 마스터 데이터 관리":
    st.subheader("💾 시스템 마스터 데이터 직접 편집")
    st.warning("⚠️ 주의: 여기서 변경된 사항은 구글 시트의 원본 데이터를 덮어씁니다(Overwrite).")
    
    target_sheet = st.selectbox("편집할 데이터베이스 선택", ["inventory", "pharmacy", "assets"])
    df_master = load_fact_data(GID_MAP[target_sheet])
    
    # 데이터 에디터 활성화
    edited_df = st.data_editor(df_master, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 클라우드 동기화 완료"):
        # 전체 시트 데이터를 덮어쓰는 페이로드 구성
        payload = {
            "action": "overwrite",
            "gid": GID_MAP[target_sheet],
            "data": [edited_df.columns.tolist()] + edited_df.values.tolist()
        }
        if sync_to_cloud(payload):
            st.success(f"✅ {target_sheet} 데이터베이스가 업데이트되었습니다.")
            st.cache_data.clear()
            st.rerun()
