import streamlit as st
import pandas as pd
import requests
import json
import re
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {
    "log": "0",          
    "assets": "1068342666", 
    "inventory": "2138778159",
    "pharmacy": "347265850"
}
# 정원님이 제공하신 최신 Apps Script API URL
API_URL = "https://script.google.com/macros/s/AKfycbxmlmMqenbvhLiLbUmI2GEd1sUMpM-NIUytaZ6jGjSL_hZ_4bk8rnDT1Td3wxbdJVBA/exec"

# 2000kcal 기준 영양 목표 (정원님 요청 기준)
GOALS = {
    "칼로리": 2000, "단백질": 150, "탄수화물": 150, "지방": 60,
    "당류": 30, "나트륨": 2000, "콜레스테롤": 300, "식이섬유": 25
}

# --- [2. 핵심 유틸리티] ---
def to_numeric(val):
    """문자열에서 숫자만 추출하여 계산 가능하게 변환 (부채 -값 유지)"""
    if pd.isna(val) or val == "": return 0
    s = str(val).replace(',', '').strip()
    try:
        # 마이너스 기호와 숫자, 소수점만 남김
        match = re.search(r"([-+]?\d*\.\d+|\d+)", s)
        return float(match.group(1)) if match else 0
    except: return 0

def extract_quantity(text):
    """비고란에서 수량(숫자)만 추출"""
    if pd.isna(text): return None
    match = re.search(r"([0-9]*\.[0-9]+|[0-9]+)", str(text))
    return float(match.group(1)) if match else None

@st.cache_data(ttl=15)
def get_upbit_price(ticker):
    """업비트 실시간 시세 조회"""
    try:
        url = f"https://api.upbit.com/v1/ticker?markets=KRW-{ticker.upper()}"
        res = requests.get(url, timeout=2).json()
        return float(res[0]['trade_price'])
    except: return None

@st.cache_data(ttl=5)
def load_data(gid):
    """구글 시트 데이터 로드"""
    ts = datetime.now().timestamp()
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={ts}"
    try:
        df = pd.read_csv(url).dropna(how='all')
        return df
    except: return pd.DataFrame()

def sync_sheet(payload):
    """Apps Script를 통해 시트 수정사항 전송"""
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=10)
        return res.status_code == 200
    except: return False

# 영양 성분 간이 DB (재고 품목명과 매칭)
def get_nutrition_info(item_name, weight):
    db = {
        "냉동큐브닭가슴살": [165, 31, 0, 3.6, 0, 45, 85, 0], # 칼,단,탄,지,당,나,콜,식
        "계란": [150, 12, 1, 10, 1, 130, 370, 0],
        "햇반": [145, 3, 33, 0.5, 0, 5, 0, 1],
    }
    # DB에 없으면 기본값(100g당 100kcal 추정) 반환
    base = db.get(item_name, [100, 10, 10, 5, 2, 100, 20, 1])
    return [round((v * weight / 100), 2) for v in base]

# --- [3. UI 설정] ---
st.set_page_config(page_title="JARVIS Prime v77.0", layout="wide")
now = datetime.utcnow() + timedelta(hours=9)

# CSS: 인덱스 숨기기 및 대시보드 스타일
st.markdown("""
<style>
    thead tr th:first-child, tbody th { display:none; }
    .metric-card { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e9ecef; text-align: center; }
    .stTable { font-size: 0.9em; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🛡️ 자비스 제어 센터")
    menu = st.radio("메뉴 이동", ["📊 자산 현황", "🥩 식단/재고 관리", "💊 상비약 보관함"])
    st.divider()

# --- [4. 메뉴별 기능 구현] ---

if menu == "📊 자산 현황":
    st.header("📊 통합 자산 및 부채 리포트")
    
    # [입력창] 사이드바 하단 배치
    with st.sidebar:
        st.subheader("📝 내역 추가")
        t_choice = st.selectbox("구분", ["지출", "수입"])
        with st.form("quick_log"):
            cat = st.selectbox("분류", ["식비", "생활", "고정비", "금융", "기타"])
            item_name = st.text_input("상세 내용")
            amount = st.number_input("금액", min_value=0, step=1000)
            if st.form_submit_button("시트로 기록"):
                payload = {"time": now.strftime('%Y-%m-%d %H시'), "corpus": "log", "type": t_choice, "cat_main": cat, "item": item_name, "value": amount, "method": "앱입력", "user": "정원"}
                if amount > 0 and sync_sheet(payload): st.success("기록 완료"); st.rerun()

    # 데이터 로드
    df_assets = load_data(GID_MAP["assets"])
    if not df_assets.empty:
        a_list, d_list = [], []
        t_a, t_d = 0.0, 0.0
        
        for i, r in df_assets.iterrows():
            name = str(r.iloc[0])
            val = to_numeric(r.iloc[1])
            note = str(r.iloc[2])
            
            # 코인 실시간 시세 반영
            coin_match = re.search(r'(BTC|ETH)', name.upper())
            is_coin = False
            if coin_match:
                qty = extract_quantity(note)
                if qty:
                    price = get_upbit_price(coin_match.group(1))
                    if price:
                        val = price * qty
                        is_coin = True
            
            row_data = {"항목": name, "금액": val, "비고": note, "is_coin": is_coin}
            if val >= 0:
                a_list.append(row_data); t_a += val
            else:
                d_list.append(row_data); t_d += val
        
        # 상단 요약 요약
        st.markdown(f"""
        <div style="display: flex; gap: 10px; margin-bottom: 20px;">
            <div class="metric-card" style="flex:1;"><b>총 자산</b><br><span style="color:blue; font-size:1.5em;">{t_a:,.0f} 원</span></div>
            <div class="metric-card" style="flex:1;"><b>총 부채</b><br><span style="color:red; font-size:1.5em;">{abs(t_d):,.0f} 원</span></div>
            <div class="metric-card" style="flex:1; border-left: 5px solid #4dabf7;"><b>순자산</b><br><span style="font-size:1.5em; font-weight:bold;">{t_a + t_d:,.0f} 원</span></div>
        </div>
        """, unsafe_allow_html=True)
        
        # 좌우 배치 출력
        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("#### 🟢 자산 상세")
            df_a_display = pd.DataFrame(a_list)
            if not df_a_display.empty:
                df_a_display.insert(0, '순번', range(1, len(df_a_display) + 1))
                df_a_display['금액'] = df_a_display.apply(lambda x: f"{x['금액']:,.8f}" if x['is_coin'] else f"{int(x['금액']):,}", axis=1)
                st.table(df_a_display[['순번', '항목', '금액', '비고']])
        
        with col_right:
            st.markdown("#### 🔴 부채 및 카드값")
            df_d_display = pd.DataFrame(d_list)
            if not df_d_display.empty:
                df_d_display.insert(0, '순번', range(1, len(df_d_display) + 1))
                df_d_display['금액'] = df_d_display['금액'].apply(lambda x: f"{int(abs(x)):,}")
                st.table(df_d_display[['순번', '항목', '금액', '비고']])

        # 데이터 편집 (별도 메뉴 없이 하단 배치)
        st.divider()
        st.subheader("⚙️ 자산 데이터 수정")
        ed_assets = st.data_editor(df_assets, num_rows="dynamic", use_container_width=True, key="edit_assets")
        if st.button("💾 자산 시트 업데이트"):
            data_to_send = [ed_assets.columns.tolist()] + ed_assets.values.tolist()
            if sync_sheet({"action": "overwrite", "gid": GID_MAP["assets"], "data": data_to_send}):
                st.success("저장되었습니다."); st.rerun()

elif menu == "🥩 식단/재고 관리":
    st.header("🥩 오늘의 식단 및 재고 현황")
    
    # 재고 데이터 로드
    df_inv = load_data(GID_MAP["inventory"])
    
    # 1. 영양 대시보드 (2000kcal 기준)
    st.subheader("⚖️ 영양 섭취 현황")
    # 임시 세션 상태 (실제 서비스 시에는 log 시트에서 오늘 분 합산 로직 필요)
    if 'daily' not in st.session_state:
        st.session_state.daily = {k: 0.0 for k in GOALS.keys()}
    
    cols = st.columns(4)
    metrics = list(GOALS.keys())
    for i, m in enumerate(metrics):
        with cols[i % 4]:
            val = st.session_state.daily[m]
            goal = GOALS[m]
            st.write(f"**{m}**")
            st.progress(min(1.0, val/goal) if goal > 0 else 0)
            st.caption(f"{val:,.1f} / {goal:,.0f}")

    # 2. 식단 입력 및 재고 차감 (사이드바)
    with st.sidebar:
        st.subheader("🍴 식단 기록")
        if not df_inv.empty:
            inv_items = df_inv.iloc[:, 1].dropna().tolist()
            f_sel = st.selectbox("품목 선택", inv_items)
            f_qty = st.number_input("섭취량(g/개)", min_value=0.0, step=10.0)
            if st.button("섭취 완료"):
                nutri = get_nutrition_info(f_sel, f_qty)
                # 세션 업데이트
                st.session_state.daily["칼로리"] += nutri[0]
                st.session_state.daily["단백질"] += nutri[1]
                st.session_state.daily["탄수화물"] += nutri[2]
                # ... (생략) 시트 차감 연동
                payload = {"action": "diet_with_inventory", "gid": GID_MAP["inventory"], "item": f_sel, "weight": f_qty, "user": "정원"}
                sync_sheet(payload)
                st.success(f"{f_sel} 반영 완료"); st.rerun()

    # 3. 재고 목록 및 편집
    st.divider()
    st.subheader("📦 현재 재고 목록 및 수정")
    if not df_inv.empty:
        df_inv.index = range(1, len(df_inv) + 1)
        ed_inv = st.data_editor(df_inv, num_rows="dynamic", use_container_width=True, key="edit_inv")
        if st.button("💾 재고 시트 업데이트"):
            data_to_send = [ed_inv.columns.tolist()] + ed_inv.values.tolist()
            sync_sheet({"action": "overwrite", "gid": GID_MAP["inventory"], "data": data_to_send})
            st.rerun()

elif menu == "💊 상비약 보관함":
    st.header("💊 상비약 유효기한 관리")
    df_ph = load_data(GID_MAP["pharmacy"])
    
    if not df_ph.empty:
        # 데이터 정제: 두 번째 열 삭제 및 날짜 포맷팅
        df_display = df_ph.copy()
        if len(df_display.columns) > 1:
            df_display = df_display.drop(df_display.columns[1], axis=1)
        
        # 유효기한 열(D열 -> 인덱스 3) 시분초 제거
        df_display.iloc[:, 2] = pd.to_datetime(df_display.iloc[:, 2], errors='coerce').dt.date
        df_display.index = range(1, len(df_display) + 1)
        
        st.subheader("📅 유통기한 현황")
        st.table(df_display)
        
        st.divider()
        st.subheader("⚙️ 상비약 데이터 수정")
        ed_ph = st.data_editor(df_ph, num_rows="dynamic", use_container_width=True, key="edit_ph")
        if st.button("💾 상비약 시트 업데이트"):
            data_to_send = [ed_ph.columns.tolist()] + ed_ph.values.tolist()
            sync_sheet({"action": "overwrite", "gid": GID_MAP["pharmacy"], "data": data_to_send})
            st.rerun()
