import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
# 식단 기록용 GID (시트에 'Diet' 탭이 있다고 가정)
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532", "Diet": "0"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

FIXED_DATA = {
    "stocks": {
        "삼성전자": {"평단": 78895, "수량": 46}, "SK하이닉스": {"평단": 473521, "수량": 6},
        "삼성중공업": {"평단": 16761, "수량": 88}, "동성화인텍": {"평단": 22701, "수량": 21}
    },
    "crypto": {
        "BTC": {"평단": 137788139, "수량": 0.00181400}, "ETH": {"평단": 4243000, "수량": 0.03417393}
    }
}

DAILY_GUIDE = {
    "지방": {"val": 65.0, "unit": "g"}, "콜레스테롤": {"val": 300.0, "unit": "mg"},
    "나트륨": {"val": 2000.0, "unit": "mg"}, "탄수화물": {"val": 300.0, "unit": "g"},
    "식이섬유": {"val": 30.0, "unit": "g"}, "당": {"val": 50.0, "unit": "g"},
    "단백질": {"val": 150.0, "unit": "g"}, "칼로리": {"val": 2000.0, "unit": "kcal"}
}

# --- [2. 유틸리티] ---
def format_krw(val):
    return f"{int(val):,}"

def to_numeric(val):
    try: return int(float(str(val).replace(',', '').replace('원', '').strip()))
    except: return 0

def send_to_sheet(d_type, item, value):
    now = datetime.utcnow() + timedelta(hours=9)
    payload = {"time": now.strftime('%Y-%m-%d %H:%M:%S'), "type": d_type, "item": item, "value": value}
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=5)
        return res.status_code == 200
    except: return False

@st.cache_data(ttl=5)
def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        return df.dropna().reset_index(drop=True)
    except: return pd.DataFrame()

# --- [3. 메인 설정] ---
st.set_page_config(page_title="JARVIS v33.5", layout="wide")
st.markdown("""
    <style>
    .stTable td { text-align: right !important; }
    .total-box { text-align: right; font-size: 1.2em; font-weight: bold; padding: 10px; border-top: 2px solid #eee; }
    .net-wealth { font-size: 2.5em !important; font-weight: bold; color: #1E90FF; text-align: left; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["식단 & 건강", "투자 & 자산", "재고 관리"])
    st.divider()
    
    if menu == "식단 & 건강":
        st.subheader("데이터 입력")
        in_w = st.number_input("체중(kg)", 0.0, 200.0, 125.0, step=0.01, format="%.2f")
        in_fat = st.number_input("지방 (g)", 0.0, format="%.2f")
        in_chol = st.number_input("콜레스테롤 (mg)", 0.0, format="%.2f")
        in_na = st.number_input("나트륨 (mg)", 0.0, format="%.2f")
        in_carb = st.number_input("탄수화물 (g)", 0.0, format="%.2f")
        in_fiber = st.number_input("식이섬유 (g)", 0.0, format="%.2f")
        in_sugar = st.number_input("당 (g)", 0.0, format="%.2f")
        in_prot = st.number_input("단백질 (g)", 0.0, format="%.2f")
        in_kcal = st.number_input("칼로리 (kcal)", 0.0, format="%.2f")
        
        input_data = {"지방": in_fat, "콜레스테롤": in_chol, "나트륨": in_na, "탄수화물": in_carb, 
                      "식이섬유": in_fiber, "당": in_sugar, "단백질": in_prot, "칼로리": in_kcal}
        
        if st.button("오늘 식단 입력 완료 및 리셋", use_container_width=True):
            # 실제 시트 전송 로직 호출
            for k, v in input_data.items():
                if v > 0: send_to_sheet("식단", k, v)
            send_to_sheet("건강", "체중", in_w)
            st.success("시트 전송 완료!")
            st.rerun()

# --- [4. 메인 화면 로직] ---
st.title(f"시스템: {menu}")

if menu == "투자 & 자산":
    df_sheet = load_sheet_data(GID_MAP["Assets"])
    df_sheet.columns = ["항목", "금액"]
    df_sheet["val"] = df_sheet["금액"].apply(to_numeric)
    
    inv_rows = []
    for cat_name, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
        for name, info in items.items():
            val = info['평단'] * info['수량']
            inv_rows.append({"항목": name, "val": val})
    
    df_total = pd.concat([df_sheet, pd.DataFrame(inv_rows)], ignore_index=True)
    assets_df = df_total[df_total["val"] >= 0].copy()
    liabs_df = df_total[df_total["val"] < 0].copy()

    col_a, col_l = st.columns(2)
    with col_a:
        st.subheader("자산 목록")
        assets_df["금액"] = assets_df["val"].apply(lambda x: f"{format_krw(x)}원")
        assets_df.index = range(1, len(assets_df) + 1)
        st.table(assets_df[["항목", "금액"]])
        st.markdown(f'<div class="total-box">자산 총계: {format_krw(assets_df["val"].sum())}원</div>', unsafe_allow_html=True)
        
    with col_l:
        st.subheader("부채 목록")
        liabs_df["금액"] = liabs_df["val"].apply(lambda x: f"{format_krw(abs(x))}원")
        liabs_df.index = range(1, len(liabs_df) + 1)
        st.table(liabs_df[["항목", "금액"]])
        st.markdown(f'<div class="total-box" style="color: #ff4b4b;">부채 총계: {format_krw(abs(liabs_df["val"].sum()))}원</div>', unsafe_allow_html=True)

    net_wealth = assets_df["val"].sum() + liabs_df["val"].sum()
    st.markdown(f'<div class="net-wealth">종합 순자산: {format_krw(net_wealth)}원</div>', unsafe_allow_html=True)

elif menu == "재고 관리":
    st.subheader("📦 식자재 통합 관리 시스템")
    if 'inventory' not in st.session_state:
        st.session_state.inventory = pd.DataFrame([
            {"항목": "닭다리살", "수량": "4팩", "보관": "냉동", "구매일": "2026-02-10", "유통기한": "2026-05-10"},
            {"항목": "냉동삼치", "수량": "4팩", "보관": "냉동", "구매일": "2026-02-12", "유통기한": "2026-04-12"}
        ])

    # data_editor 설정: 인덱스 숨기기 및 삭제 허용
    edited_df = st.data_editor(
        st.session_state.inventory, 
        num_rows="dynamic", 
        use_container_width=True, 
        hide_index=False, # 삭제를 위해선 index가 보이는게 유리(왼쪽 체크박스)
        key="inv_editor_v2"
    )
    st.session_state.inventory = edited_df
    st.caption("💡 팁: 행 왼쪽을 선택하고 'Delete'키를 누르거나 하단 행을 추가하여 편집하세요. 인덱스는 표기용일 뿐이며 관리에 영향을 주지 않습니다.")

    st.divider()
    st.subheader("⏰ 생활용품 교체주기")
    cycle_df = pd.DataFrame([
        {"품목": "칫솔", "교체주기": "1개월", "상태": "양호"},
        {"품목": "면도날", "교체주기": "2주", "상태": "교체예정"}
    ])
    cycle_df.index = range(1, len(cycle_df) + 1)
    st.table(cycle_df)

elif menu == "식단 & 건강":
    st.subheader("실시간 영양 분석 리포트")
    cols = st.columns(4)
    for idx, (k, v) in enumerate(input_data.items()):
        with cols[idx % 4]:
            guide = DAILY_GUIDE[k]
            ratio = min(v / guide["val"], 1.0) if v > 0 else 0
            st.metric(k, f"{v:.2f}{guide['unit']} / {guide['val']}{guide['unit']}", f"{int(ratio*100)}%")
            st.progress(ratio)
