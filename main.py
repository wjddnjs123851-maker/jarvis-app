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

# 2000kcal 다이어트 목표
GOALS = {"칼로리": 2000, "단백질": 150, "탄수화물": 150, "지방": 60, "당류": 30, "나트륨": 2000, "콜레스테롤": 300, "식이섬유": 25}

# --- [2. 핵심 방탄 유틸리티] ---
def to_numeric(val):
    """어떤 서식의 숫자라도 정밀하게 추출 (부채의 마이너스 유지)"""
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
        df = pd.read_csv(url).dropna(how='all')
        return df
    except: return pd.DataFrame()

def send_to_sheet(payload):
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=10)
        return res.status_code == 200
    except: return False

# --- [3. UI 설정] ---
st.set_page_config(page_title="JARVIS Prime v78.0", layout="wide")
now = datetime.utcnow() + timedelta(hours=9)
st.markdown("""<style>thead tr th:first-child, tbody th { display:none; } .metric-card { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #dee2e6; text-align: center; margin-bottom: 15px; }</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🛡️ 자비스")
    menu = st.radio("메뉴", ["💰 자산/가계부", "🥩 식단/재고", "💊 상비약 관리"])
    st.divider()

# --- [4. 로직 구현] ---

if menu == "💰 자산/가계부":
    st.header("📊 통합 자산 및 가계부")
    
    # [입력창] 지출 기록 시 자산 자동 업데이트 로직 포함
    with st.sidebar:
        st.subheader("📝 소비 기록")
        t_type = st.selectbox("구분", ["지출", "수입"])
        cats = ["식비", "주거/관리", "생활/쇼핑", "교통/차량", "의료/건강", "경조사/선물", "금융/이자", "여가/문화", "기타"]
        methods = ["현금", "계좌이체", "국민카드", "하나카드", "우리카드", "현대카드"]
        
        with st.form("log_input"):
            c_main = st.selectbox("카테고리", cats)
            item_name = st.text_input("내용")
            amount = st.number_input("금액", min_value=0, step=1000)
            pay_method = st.selectbox("결제수단", methods)
            
            if st.form_submit_button("기록 및 자산 반영"):
                # 1. 가계부 로그 전송
                payload = {"time": now.strftime('%Y-%m-%d %H시'), "corpus": "log", "type": t_type, "cat_main": c_main, "item": item_name, "value": amount, "method": pay_method, "user": "정원"}
                
                # 2. 자산 시트 자동 업데이트 로직
                df_assets = load_data(GID_MAP["assets"])
                target_asset = "가용현금" if pay_method in ["현금", "계좌이체"] else pay_method
                
                for idx, row in df_assets.iterrows():
                    if target_asset in str(row.iloc[0]):
                        current_val = to_numeric(row.iloc[1])
                        new_val = current_val - amount if t_type == "지출" else current_val + amount
                        df_assets.iloc[idx, 1] = new_val
                        break
                
                # 시트 2곳 동시 업데이트
                if send_to_sheet(payload):
                    send_to_sheet({"action": "overwrite", "gid": GID_MAP["assets"], "data": [df_assets.columns.tolist()] + df_assets.values.tolist()})
                    st.success("반영 완료!"); st.rerun()

    df_a = load_data(GID_MAP["assets"])
    if not df_a.empty:
        pos_list, neg_list = [], []
        t_pos, t_neg = 0.0, 0.0
        
        for i, r in df_a.iterrows():
            name, val, note = str(r.iloc[0]), to_numeric(r.iloc[1]), str(r.iloc[2])
            coin = re.search(r'(BTC|ETH)', name.upper())
            is_coin = False
            if coin:
                p = get_coin_price(coin.group(1))
                qty = to_numeric(note) if to_numeric(note) != 0 else val
                if p: val = p * qty; is_coin = True
            
            row = {"항목": name, "금액": val, "비고": note, "is_coin": is_coin}
            if val >= 0: pos_list.append(row); t_pos += val
            else: neg_list.append(row); t_neg += val

        # 상단 요약
        st.markdown(f"""<div style="display: flex; gap: 10px;">
            <div class="metric-card" style="flex:1;"><b>총 자산</b><br><span style="color:blue; font-size:1.5em;">{t_pos:,.0f}원</span></div>
            <div class="metric-card" style="flex:1;"><b>총 부채</b><br><span style="color:red; font-size:1.5em;">{abs(t_neg):,.0f}원</span></div>
            <div class="metric-card" style="flex:1; border-top: 4px solid #4dabf7;"><b>순자산</b><br><span style="font-size:1.8em; font-weight:bold;">{t_pos + t_neg:,.0f}원</span></div>
        </div>""", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🟢 보유 자산")
            df_pos = pd.DataFrame(pos_list)
            if not df_pos.empty:
                df_pos.insert(0, '순번', range(1, len(df_pos) + 1))
                df_pos['금액'] = df_pos.apply(lambda x: f"{x['금액']:,.8f}" if x['is_coin'] else f"{int(x['금액']):,}", axis=1)
                st.table(df_pos[['순번', '항목', '금액', '비고']])
        with col2:
            st.markdown("#### 🔴 부채 및 카드값")
            df_neg = pd.DataFrame(neg_list)
            if not df_neg.empty:
                df_neg.insert(0, '순번', range(1, len(df_neg) + 1))
                df_neg['금액'] = df_neg['금액'].apply(lambda x: f"{int(abs(x)):,}")
                st.table(df_neg[['순번', '항목', '금액', '비고']])

        st.divider()
        st.subheader("⚙️ 자산 시트 즉시 편집")
        ed_a = st.data_editor(df_a, num_rows="dynamic", use_container_width=True)
        if st.button("💾 자산 데이터 저장"):
            if send_to_sheet({"action":"overwrite", "gid":GID_MAP["assets"], "data":[ed_a.columns.tolist()]+ed_a.values.tolist()}):
                st.success("저장됨"); st.rerun()

elif menu == "🥩 식단/재고":
    st.header("🥩 식재료 재고 및 영양 관리")
    df_i = load_data(GID_MAP["inventory"])
    
    with st.sidebar:
        st.subheader("🍴 식사 기록")
        if not df_i.empty:
            f_item = st.selectbox("품목", df_i.iloc[:, 1].dropna().tolist())
            f_qty = st.number_input("섭취량(g/개)", min_value=0.0)
            if st.button("섭취 기록"):
                send_to_sheet({"action": "diet_with_inventory", "gid": GID_MAP["inventory"], "item": f_item, "weight": f_qty, "user": "정원"})
                st.success("반영됨"); st.rerun()

    st.subheader("📦 현재 재고 목록")
    if not df_i.empty:
        df_i.index = range(1, len(df_i) + 1)
        ed_i = st.data_editor(df_i, num_rows="dynamic", use_container_width=True)
        if st.button("💾 재고 저장"):
            send_to_sheet({"action":"overwrite","gid":GID_MAP["inventory"],"data":[ed_i.columns.tolist()]+ed_i.values.tolist()}); st.rerun()

elif menu == "💊 상비약 관리":
    st.header("💊 상비약 유효기한")
    df_p = load_data(GID_MAP["pharmacy"])
    if not df_p.empty:
        df_view = df_p.copy()
        if len(df_view.columns) > 1: df_view = df_view.drop(df_view.columns[1], axis=1) # 2번째 열 삭제
        df_view.iloc[:, 2] = pd.to_datetime(df_view.iloc[:, 2], errors='coerce').dt.date # 시분초 삭제
        df_view.index = range(1, len(df_view) + 1)
        st.table(df_view)
        
        st.divider()
        st.subheader("⚙️ 상비약 데이터 수정")
        ed_p = st.data_editor(df_p, num_rows="dynamic", use_container_width=True)
        if st.button("💾 상비약 저장"):
            send_to_sheet({"action":"overwrite","gid":GID_MAP["pharmacy"],"data":[ed_p.columns.tolist()]+ed_p.values.tolist()}); st.rerun()
