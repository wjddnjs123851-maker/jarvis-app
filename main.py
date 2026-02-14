import streamlit as st
import pandas as pd
from google.oauth2 import service_account
import googleapiclient.discovery
import datetime

# 1. 인증 정보 및 설정 (보스의 JSON 키 정보 유지)
CREDENTIALS_INFO = {
  "type": "service_account",
  "project_id": "driven-rider-487400-u1",
  "private_key_id": "501e1c047e08c7c40231328c3768c35c59e8ddc7",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCun2N8gKF+DwaQ\n/LwRFyzwHlY8L925hj9qHEjdNzWuUl6YNMIYK3QaiXPMprtpIITI7HUeHIrkq93m\n5QsLknpE4/5nduwYyWjU2d5WgRlUg3S8h2e1dALANT/1+U2AJ8rYBvjAYM2JCN+K\n3C/3J/oWbJCcyrGqltpqmMijX6caDqy8LVUd5GINqMMD6EE+mZnBc6spL8BD2Qn9\niJZ9hKMzupBe+XmDfIOppVH0pv1O0m4HKiW0NFh08xF8iwD3QCiqgLIDc5xa6Mq6\nzDVhONfyTvGoJ9s+BfFHZ3iKoyv/fih7KswXuCPpMLrnYm5ygl836Ap/PRkRs0We\n7BSJlB1FAgMBAAECggEAJAdPRb4dc86iVnJK1EThmPZNaRQgLXnZJinJT9knCn1E\ntqc1/7ohdaM0AP7Krp1OwEznOiv97UHXoh7SSVQyxXl8ATlsa43MwxPjl5oB0ang\nwVA3sdzKf4FNHdFO7/jl1W4Uz055wcMSqkoVXGuDYjKKoMsCXrXKwVEeHnUrG0ki\nEGuGLcd4RmlohNzUC5Higi6Nah/RjCNji4bJBFvbjdbiiuVIFmiCWXRFHad8CvU+\nqng6OQ9cwfNyHisuK5aeLFAT6X0dQJG1KtCKnTIbePXACCuk5TZnMZdYYGk8Thm9\nryZwB5sHQ0rXZax3Du4rhLHi1m8DKq0mZSNLeKW1oQKBgQDXHQnadIq7Z6xe1ndX\nf8v9is+XWkB0vfb9FgInTKhGF2Aff+xJXF4X1zWjFNUOgcuD8g4s8qBuDEjYK6zM\nUP9MVHRS/9zqDTrbXmO99H1ndYcneBvMwOAythLW5uQMyz65443n704jyz5/hb+y\nrLXHc1iAVDpWoXhZNCx1Y13rZQKBgQDP0Ccu7QpXhIYnmRRpKt3CE7zfUclposjc\ridNeWJLKLejX4CLPO6S7+qktErcNJ/tzakBY379QUIF5xKOlT8eYiHHjZY80Igq\nPZFgTIm/e1n+8coCbBCQw/SLh/h0at8twCi97rKGE7YUdyZ5sN1yzM2Ij+oG7+xy\ndUV43AV8YQKBgQDMebXcCdu1uB6JJ6PZcIkfQMuDOy75yXj1qe3yHVP3DFE6oAai\n1UI7tz4s/qhnWclyaqw+3YLSGKtFkH542KVUkRLhsoTzlg/UZiy5a6WoqncGdY03\nXD/A9IGD9YXhA3FkkYFabocATznhTemilblVFbeShH3Pyzzyzj1UeFfWYQKBgCQx\nZoGfuwtfA1ZmLM3cL18bvOtP/Toupbj5g9LUbzAT2VfUzDhz1kE1E7K3y8nqSGhM\nR0D8qSNGeE863VqD18hc4vE0UZQp5W0l5+nTqrH0s8nZJouhcokj97VNaxIrgs8f\nBnl91w3O5QlPbx4GlarmzG0aU3H92zpb/kt8VmBBAoGBAMRePTGdDIZh5F07EBy2\nH/qA69P00KXZCQk/w/y5LkfNgYDdZGO/0pEpZ0UfLcykuUtnnE/ORw+rL6he9q5Z\nI8wRFrrV03miNIxL/M4BjgFo/vG0ALBhI6boSEQkRJ7sVOv0enBaycwMLDX/CEEG\n6aOlaWMCMm4jDqC2Kesqws3C\n-----END PRIVATE KEY-----\n",
  "client_email": "jarvis-bot@driven-rider-487400-u1.iam.gserviceaccount.com",
}

# 보스의 가계부 시트 ID
SPREADSHEET_ID = '1X6ypXRLkHIMOSGuYdNLnzLkVB4xHfpRR'

# 2. 세션 상태 초기화 (식단 합산용)
if 'daily_nutrition' not in st.session_state:
    st.session_state.daily_nutrition = {'칼로리': 0.0, '탄수화물': 0.0, '단백질': 0.0, '지방': 0.0}

# 3. 함수 정의: 가계부 데이터 로드 (표준 라이브러리 방식)
def load_finance_data():
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = service_account.Credentials.from_service_account_info(CREDENTIALS_INFO, scopes=scopes)
        service = googleapiclient.discovery.build('sheets', 'v4', credentials=creds)
        
        # 첫 번째 탭의 모든 데이터를 가져옵니다.
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range="A1:Z100").execute()
        values = result.get('values', [])
        
        if not values:
            return None
        
        # 데이터프레임으로 변환 (첫 줄을 제목으로 사용)
        df = pd.DataFrame(values[1:], columns=values[0])
        return df
    except Exception as e:
        st.error(f"구글 시트 연동 중 오류 발생: {e}")
        return None

# --- UI 구성 ---
st.set_page_config(page_title="JARVIS 비서", layout="wide")
st.title("🛡️ JARVIS: 개인 비서 시스템")

st.sidebar.header("메뉴 선택")
menu = st.sidebar.radio("이동할 기능", ["🏠 데일리 리포트", "💸 실시간 가계부", "🥗 식단 매니저", "📦 재고 및 주기 관리"])

# --- 1. 데일리 리포트 ---
if menu == "🏠 데일리 리포트":
    st.header("오늘의 요약 리포트")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 영양소 섭취 현황")
        st.write(f"**현재 칼로리:** {st.session_state.daily_nutrition['칼로리']} kcal")
        st.progress(min(st.session_state.daily_nutrition['칼로리'] / 2500, 1.0)) # 2500kcal 기준 예시
    
    with col2:
        st.subheader("💡 보스를 위한 메모")
        st.info("5월 30일 결혼식까지 약 100일 남았습니다. 신체 리듬 유지에 유의하십시오.")

# --- 2. 실시간 가계부 ---
elif menu == "💸 실시간 가계부":
    st.header("가계부 실시간 연동 (Sheet: 1X6yp...)")
    with st.spinner("데이터를 동기화 중입니다..."):
        finance_df = load_finance_data()
        
        if finance_df is not None:
            st.success("보스의 데이터를 성공적으로 불러왔습니다.")
            # 이자, 정수기, 난방비 등 모든 항목을 표로 출력
            st.dataframe(finance_df, use_container_width=True)
        else:
            st.warning("시트에서 데이터를 찾을 수 없습니다.")

# --- 3. 식단 매니저 ---
elif menu == "🥗 식단 매니저":
    st.header("식단 입력 및 누적 관리")
    
    with st.form("nutrition_form"):
        col1, col2 = st.columns(2)
        with col1:
            f_cal = st.number_input("칼로리 (kcal)", min_value=0.0)
            f_carb = st.number_input("탄수화물 (g)", min_value=0.0)
        with col2:
            f_prot = st.number_input("단백질 (g)", min_value=0.0)
            f_fat = st.number_input("지방 (g)", min_value=0.0)
            
        submit_btn = st.form_submit_button("영양 데이터 합산하기")
        
        if submit_btn:
            st.session_state.daily_nutrition['칼로리'] += f_cal
            st.session_state.daily_nutrition['탄수화물'] += f_carb
            st.session_state.daily_nutrition['단백질'] += f_prot
            st.session_state.daily_nutrition['지방'] += f_fat
            st.balloons()
            st.success("데이터가 합산되었습니다.")

    st.subheader("🔥 현재까지 섭취 총량")
    st.table(pd.DataFrame([st.session_state.daily_nutrition]))

# --- 4. 재고 및 주기 관리 ---
elif menu == "📦 재고 및 주기 관리":
    st.header("생활 주기 및 주방 재고")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔄 소모품 교체 주기")
        st.table(pd.DataFrame({
            "항목": ["면도날", "칫솔", "베개커버"],
            "상태": ["교체 임박", "사용 중", "청결"]
        }))
    with c2:
        st.subheader("🍳 주방 재고")
        st.table(pd.DataFrame({
            "품목": ["닭가슴살", "계란", "프로틴"],
            "수량": ["5kg", "2판", "1.2kg"]
        }))

st.sidebar.markdown("---")
st.sidebar.write(f"최근 업데이트: {datetime.datetime.now().strftime('%H:%M:%S')}")
