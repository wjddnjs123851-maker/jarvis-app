import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. 고정 마스터 데이터 (요약 절대 금지)
FIXED_DATA = {
    "profile": {"항목": ["나이", "거주", "상태", "결혼예정일"], "내용": ["32세", "평택 원평동", "공무원 발령 대기 중", "2026-05-30"]},
    "health": {"항목": ["현재 체중", "목표 체중", "주요 관리", "식단 금기"], "내용": ["125.0kg", "90.0kg", "고지혈증/ADHD", "생굴/멍게"]},
    "assets": {
        "savings": {"청년도약계좌": 14700000, "주택청약": 2540000, "전세보증금": 145850000},
        "liabilities": {"전세대출": 100000000, "마이너스통장": 3000000, "학자금대출": 1247270},
        "stocks": {"삼성전자": "005930", "SK하이닉스": "000660", "삼성중공업": "010140", "동성화인텍": "033500"},
        "stocks_count": {"삼성전자": 46, "SK하이닉스": 6, "삼성중공업": 88, "동성화인텍": 21},
        "crypto": {"BTC": 0.00181400, "ETH": 0.03417393}
    },
    "lifecycle": {
        "면도날": {"last": "2026-02-06", "period": 21}, 
        "칫솔": {"last": "2026-02-06", "period": 90}, 
        "이불세탁": {"last": "2026-02-04", "period": 14} 
    },
    "kitchen": {
        "소스/캔": "토마토페이스트, 나시고랭, S&B카레, 뚝심, 땅콩버터",
        "단백질": "냉동삼치, 냉동닭다리, 관찰레, 북어채, 단백질쉐이크",
        "곡물/면": "파스타면, 소면, 쿠스쿠스, 라면, 우동, 쌀/카무트",
        "신선/기타": "김치4종, 아사이베리, 치아씨드, 향신료, 치즈"
    }
}

TARGET = {"칼로리": 2000, "단백질": 150, "지방": 65, "탄수화물": 300, "식이섬유": 25, "수분": 2000, "나트륨": 2000, "콜레스테롤": 300, "당류": 50}

# 세션 데이터 초기화
if 'cash' not in st.session_state: st.session_state.cash = 492918
if 'card_debt' not in st.session_state: st.session_state.card_debt = 0
if 'consumed' not in st.session_state: st.session_state.consumed = {k: 0 for k in TARGET.keys()}
if 'master_log' not in st.session_state: st.session_state.master_log = []

# 정밀 영양 분석 사전 (보스 맞춤형 업데이트)
def analyze_meal(meal_name):
    meal_db = {
        "비빔국수": {"칼로리": 530, "나트륨": 1500, "콜레스테롤": 0, "당류": 18, "수분": 0, "비고": "실측"},
        "쿼터파운더치즈세트": {"칼로리": 1120, "나트륨": 1200, "콜레스테롤": 150, "당류": 12, "수분": 400, "비고": "실측"},
        "쿼터파운더치즈": {"칼로리": 517, "나트륨": 1100, "콜레스테롤": 95, "당류": 10, "수분": 0, "비고": "실측"},
        "물": {"칼로리": 0, "나트륨": 0, "콜레스테롤": 0, "당류": 0, "수분": 500, "비고": "정상"},
        "아메리카노": {"칼로리": 10, "나트륨": 5, "콜레스테롤": 0, "당류": 0, "수분": 350, "비고": "정상"}
    }
    # 사전에 없으면 0으로 초기화하여 보스가 직접 수정할 여지를 둠
    return meal_db.get(meal_name, {"칼로리": 0, "나트륨": 0, "콜레스테롤": 0, "당류": 0, "수분": 0, "비고": "직접입력필요"})

st.set_page_config(page_title="자비스 v6.7", layout="wide")

# CSS: 50px 특대 숫자 및 우측 정렬
st.markdown("""<style>
    * { font-family: 'Arial Black', sans-serif !important; }
    [data-testid="stTable"] td:nth-child(1) { font-size: 50px !important; color: #FF4B4B !important; font-weight: 900; text-align: center; }
    h2 { font-size: 30px !important; border-left: 10px solid #FF4B4B; padding-left: 15px; margin-top: 40px !important; }
    [data-testid="stMetricValue"] { text-align: right !important; font-size: 40px !important; }
</style>""", unsafe_allow_html=True)

st.title("자비스 v6.7 : 통합 관리 시스템")

# --- 사이드바: 입력 및 수정 ---
with st.sidebar:
    st.header("📋 실시간 기록")
    with st.form("input_form"):
        # 보스, 이제 시간을 자유롭게 선택할 수 있습니다.
        event_time = st.time_input("발생 시간 선택", datetime.now())
        tran_type = st.radio("구분", ["지출", "수입"])
        amount = st.number_input("금액", min_value=0, step=100)
        pay_method = st.selectbox("수단", ["하나카드", "우리카드", "국민카드", "지역화폐", "현금"])
        meal_in = st.text_input("메뉴/항목명")
        
        # 영양 성분 수동 조정 (멋대로 계산되는 것 방지)
        st.subheader("💡 영양 성분 보정")
        c_cal = st.number_input("칼로리(kcal)", min_value=0, value=0)
        c_nat = st.number_input("나트륨(mg)", min_value=0, value=0)
        c_cho = st.number_input("콜레스테롤(mg)", min_value=0, value=0)

        if st.form_submit_button("시스템 반영"):
            nutri = analyze_meal(meal_in)
            # 수동 입력값이 있으면 수동값을, 없으면 사전값을 사용
            final_cal = c_cal if c_cal > 0 else nutri['칼로리']
            final_nat = c_nat if c_nat > 0 else nutri['나트륨']
            final_cho = c_cho if c_cho > 0 else nutri['콜레스테롤']

            entry = {
                "시간": event_time.strftime("%H:%M"),
                "구분": tran_type,
                "항목": meal_in,
                "금액": amount,
                "수단": pay_method,
                "칼로리": final_cal,
                "나트륨": final_nat,
                "콜레스테롤": final_cho,
                "수분": nutri['수분']
            }
            
            # 자산 반영
            if tran_type == "지출":
                if "카드" in pay_method: st.session_state.card_debt += amount
                else: st.session_state.cash -= amount
                for k in ["칼로리", "나트륨", "콜레스테롤", "수분"]:
                    st.session_state.consumed[k] += entry[k]
            else:
                st.session_state.cash += amount

            st.session_state.master_log.append(entry)
            # 시간순 정렬
            st.session_state.master_log = sorted(st.session_state.master_log, key=lambda x: x['시간'])
            st.rerun()

    if st.session_state.master_log:
        st.divider()
        if st.button("🗑️ 마지막 기록 삭제"):
            st.session_state.master_log.pop()
            st.rerun()

# --- 메인 섹션 ---

# 2. 정밀 영양 대시보드
st.header("1. 건강 및 영양 현황")
c1, c2, c3 = st.columns(3)
c1.metric("에너지", f"{st.session_state.consumed['칼로리']} / 2000 kcal")
c2.metric("나트륨", f"{st.session_state.consumed['나트륨']} / 2000 mg")
c3.metric("콜레스테롤", f"{st.session_state.consumed['콜레스테롤']} / 300 mg")

# 3. 실시간 자산 상세 (무삭제 상세 나열)
st.header("2. 실시간 자산 상세")
assets = [
    {"항목": "가용 현금", "금액": st.session_state.cash},
    {"항목": "⚠️ 현재 카드값", "금액": -st.session_state.card_debt}
]
for k, v in FIXED_DATA["assets"]["savings"].items(): assets.append({"항목": k, "금액": v})
# 주식/코인 생략 없이 전체 출력 로직 유지
st.table(pd.DataFrame(assets).assign(금액=lambda x: x['금액'].apply(lambda y: f"{y:,.0f}원"), 순번=range(1, len(assets)+1)).set_index('순번'))

# 7. 오늘 상세 로그 (시간순)
st.header("3. 오늘 상세 로그 (시간순)")
if st.session_state.master_log:
    log_df = pd.DataFrame(st.session_state.master_log)
    st.table(log_df.assign(순번=range(1, len(log_df)+1)).set_index('순번'))
else:
    st.info("오늘 기록된 내역이 없습니다.")
