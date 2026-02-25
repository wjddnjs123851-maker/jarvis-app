import streamlit as st
import pandas as pd
import requests
import json
import re
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {
    "log": "0", "assets": "1068342666", 
    "inventory": "2138778159", "pharmacy": "347265850"
}
API_URL = "https://script.google.com/macros/s/AKfycbxmlmMqenbvhLiLbUmI2GEd1sUMpM-NIUytaZ6jGjSL_hZ_4bk8rnDT1Td3wxbdJVBA/exec"

# --- [2. 핵심 유틸리티] ---
def to_numeric(val):
    """모든 형식의 숫자를 안전하게 추출 (부채의 마이너스 유지)"""
    if pd.isna(val) or str(val).strip() == "": return 0.0
    s = str(val).replace(',', '').replace(' ', '').strip()
    if s.startswith('(') and s.endswith(')'): s = '-' + s[1:-1]
    try:
        match = re.search(r"(-?\d*\.\d+|-?\d+)", s)
        return float(match.group(1)) if match else 0.0
    except: return 0.0

@st.cache_data(ttl=15)
def get_coin_price(ticker):
    try:
        res = requests.get(f"https://api.upbit.com/v1/ticker?markets=KRW-{ticker.upper()}", timeout=2).json()
        return float(res[0]['trade_price'])
    except: return None

@st.cache_data(ttl=5)
def load_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={datetime.now().timestamp()}"
    try:
        return pd.read_csv(url).dropna(how='all')
    except: return pd.DataFrame()

def sync_sheet(payload):
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=10)
        return res.status_code == 200
    except: return False

# --- [3. UI 설정] ---
st.set_page_config(page_title="JARVIS Prime v79.0", layout="wide")
now = datetime.utcnow() + timedelta(hours=9)

st.markdown("""
<style>
    thead tr th:first-child, tbody th { display:none; }
    .metric-card { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e9ecef; text-align: center; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🛡️ 자비스")
    menu = st.radio("메뉴", ["💰 자산/가계부", "🥩 식단/재고", "💊 상비약 관리"])
    st.divider()

# --- [4. 메뉴별 기능 구현] ---

if menu == "💰 자산/가계부":
    st.header("📊 실시간 통합 자산 현황")
    
    # [입력창] 가계부 카테고리 슬림화 및 연동 로직
    with st.sidebar:
        st.subheader("💸 가계부 입력")
        t_type = st.selectbox("구분", ["지출", "수입"])
        # 정원 님 이미지 기반 슬림화 카테고리
        cats = ["식비(배달/집밥)", "생활/미용", "주거/통신", "관리/공과금", "의료/건강", "교통/차량", "보험/이자", "경조사/선물", "여가/문화", "주식/적금"]
        methods = ["현금", "계좌이체", "국민카드", "하나카드", "우리카드", "현대카드"]
        
        with st.form("log_form"):
            c_main = st.selectbox("카테고리", cats)
            item_name = st.text_input("내용")
            amount = st.number_input("금액", min_value=0, step=1000)
            pay_method = st.selectbox("결제수단", methods)
            
            if st.form_submit_button("기록 및 자산 연동"):
                df_assets = load_data(GID_MAP["assets"])
                target = "가용현금" if pay_method in ["현금", "계좌이체"] else pay_method
                
                # 자산/부채 실시간 차감 로직
                for idx, row in df_assets.iterrows():
                    if target in str(row.iloc[0]):
                        curr = to_numeric(row.iloc[1])
                        # 지출이면 자산은 줄고 부채(카드값)는 더 마이너스가 됨
                        df_assets.iloc[idx, 1] = curr - amount if t_type == "지출" else curr + amount
                        break
                
                payload = {"time": now.strftime('%Y-%m-%d %H시'), "corpus": "log", "type": t_type, "cat_main": c_main, "item": item_name, "value": amount, "method": pay_method, "user": "정원"}
                if sync_sheet(payload):
                    sync_sheet({"action": "overwrite", "gid": GID_MAP["assets"], "data": [df_assets.columns.tolist()] + df_assets.values.tolist()})
                    st.success("반영 완료"); st.rerun()

    df_a = load_data(GID_MAP["assets"])
    if not df_a.empty:
        a_rows, d_rows = [], []
        t_a, t_d = 0.0, 0.0
        
        for i, r in df_a.iterrows():
            name, qty = str(r.iloc[0]), to_numeric(r.iloc[1])
            unit, note = str(r.iloc[2]) if not pd.isna(r.iloc[2]) else "", str(r.iloc[3]) if not pd.isna(r.iloc[3]) else ""
            
            coin = re.search(r'(BTC|ETH)', name.upper())
            is_coin = False
            eval_val = qty
            
            if coin:
                p = get_coin_price(coin.group(1))
                if p: eval_val = qty * p; is_coin = True
            
            # 카드값 및 대출은 무조건 부채로 분류
            is_debt = False
            if any(kw in name for kw in ["카드", "대출", "마이너스", "빌린"]) or eval_val < 0:
                is_debt = True
                if eval_val > 0: eval_val = -eval_amount 

            row = {"항목": name, "수량": qty, "단위": unit, "평가액": eval_val, "is_coin": is_coin, "원본인덱스": i}
            if not is_debt:
                a_rows.append(row); t_a += eval_val
            else:
                d_rows.append(row); t_d += eval_val

        # 상단 요약 지표
        st.markdown(f"""<div style="display: flex; gap: 10px;">
            <div class="metric-card" style="flex:1;"><b>총 자산</b><br><span style="color:blue; font-size:1.5em;">{t_a:,.0f}원</span></div>
            <div class="metric-card" style="flex:1;"><b>총 부채</b><br><span style="color:red; font-size:1.5em;">{abs(t_d):,.0f}원</span></div>
            <div class="metric-card" style="flex:1; border-top: 4px solid #4dabf7;"><b>순자산</b><br><span style="font-size:1.8em; font-weight:bold;">{t_a + t_d:,.0f}원</span></div>
        </div>""", unsafe_allow_html=True)

        # 직접 편집 가능한 자산/부채 표
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🟢 보유 자산")
            df_pos = pd.DataFrame(a_rows)
            if not df_pos.empty:
                df_pos.insert(0, '순번', range(1, len(df_pos) + 1))
                st.data_editor(
                    df_pos[['순번', '항목', '수량', '단위', '평가액']],
                    use_container_width=True,
                    column_config={
                        "수량": st.column_config.NumberColumn(format="%.2f", alignment="right"),
                        "평가액": st.column_config.NumberColumn(format="%d", alignment="right")
                    },
                    key="edit_assets_top", disabled=["평가액", "순번"]
                )
        
        with col2:
            st.markdown("#### 🔴 부채 및 카드값")
            df_neg = pd.DataFrame(d_rows)
            if not df_neg.empty:
                df_neg.insert(0, '순번', range(1, len(df_neg) + 1))
                st.data_editor(
                    df_neg[['순번', '항목', '수량', '단위', '평가액']],
                    use_container_width=True,
                    column_config={
                        "수량": st.column_config.NumberColumn(format="%d", alignment="right"),
                        "평가액": st.column_config.NumberColumn(format="%d", alignment="right")
                    },
                    key="edit_debt_top", disabled=["평가액", "순번"]
                )

        st.divider()
        st.subheader("⚙️ 전체 시트 편집 및 저장")
        ed_a = st.data_editor(df_a, num_rows="dynamic", use_container_width=True, key="main_asset_editor")
        if st.button("💾 모든 변경사항 시트로 저장"):
            if sync_sheet({"action":"overwrite", "gid":GID_MAP["assets"], "data":[ed_a.columns.tolist()]+ed_a.values.tolist()}):
                st.success("시트 동기화 완료"); st.rerun()

elif menu == "🥩 식단/재고":
    st.header("🥩 식재료 재고 및 다이어트 관리")
    df_i = load_data(GID_MAP["inventory"])
    if not df_i.empty:
        df_i.insert(0, '순번', range(1, len(df_i) + 1))
        st.subheader("📦 현재 재고 목록")
        ed_i = st.data_editor(df_i, num_rows="dynamic", use_container_width=True)
        if st.button("💾 재고 저장"):
            sync_sheet({"action":"overwrite","gid":GID_MAP["inventory"],"data":[ed_i.columns.tolist()]+ed_i.values.tolist()}); st.rerun()

elif menu == "💊 상비약 관리":
    st.header("💊 상비약 보관함")
    df_p = load_data(GID_MAP["pharmacy"])
    if not df_p.empty:
        df_p_view = df_p.copy()
        if len(df_p_view.columns) > 1: df_p_view = df_p_view.drop(df_p_view.columns[1], axis=1)
        df_p_view.iloc[:, 2] = pd.to_datetime(df_p_view.iloc[:, 2], errors='coerce').dt.date
        df_p_view.insert(0, '순번', range(1, len(df_p_view) + 1))
        st.subheader("📅 유효기한 현황")
        st.data_editor(df_p_view, use_container_width=True, disabled=True)
        
        st.divider()
        st.subheader("⚙️ 상비약 데이터 수정")
        ed_p = st.data_editor(df_p, num_rows="dynamic", use_container_width=True)
        if st.button("💾 상비약 저장"):
            sync_sheet({"action":"overwrite","gid":GID_MAP["pharmacy"],"data":[ed_p.columns.tolist()]+ed_p.values.tolist()}); st.rerun()
