import streamlit as st
import os
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END

# --- [핵심 수정] 정석적인 패키지 호출 방식 ---
# st_app 폴더 안에 __init__.py가 있어야 작동합니다.
try:
    from st_app.utils.state import GraphState
    from st_app.graph.nodes.chat_node import chat_node
    from st_app.graph.nodes.subject_info_node import info_node
    from st_app.graph.nodes.rag_review_node import review_node
    from st_app.graph.router import route_question
except ModuleNotFoundError as e:
    st.error(f"⚠️ 모듈 로드 오류: {e}")
    st.warning("팁: 'st_app' 폴더 안에 '__init__.py' 파일이 있는지 반드시 확인해주세요!")
    st.stop()

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="김애란 저서 안내 챗봇",
    page_icon="📚",
    layout="centered"
)

st.title("📚 김애란 저서 안내 AI")
st.markdown("김애란 작가의 작품 세계(정보)와 독자들의 생생한 리뷰(RAG)를 알려드립니다.")

# 2. 사이드바 설정 (API Key)
with st.sidebar:
    st.header("설정")
    
    # API Key 로드 상태 추적 변수
    is_key_loaded = False

    # (1) Secrets에서 키 로드 시도
    try:
        # st.secrets 접근 시 파일이 없으면 에러가 발생하므로 try-except로 감쌈
        if "UPSTAGE_API_KEY" in st.secrets:
            os.environ["UPSTAGE_API_KEY"] = st.secrets["UPSTAGE_API_KEY"]
            st.success("Secrets에서 API Key 로드됨")
            is_key_loaded = True
    except Exception:
        # secrets.toml 파일이 없거나 설정되지 않은 경우 에러 무시 (패스)
        pass

    # (2) Secrets에 키가 없는 경우 직접 입력 받기
    if not is_key_loaded:
        api_key = st.text_input("Upstage API Key", type="password")
        if api_key:
            os.environ["UPSTAGE_API_KEY"] = api_key
            st.success("API Key 입력 완료")
        else:
            st.warning("API Key를 입력해주세요.")
            
    st.divider()
    if st.button("대화 초기화"):
        st.session_state.messages = []
        st.rerun()

# 3. LangGraph 구축 로직
@st.cache_resource
def build_graph_app():
    """
    LangGraph의 노드와 엣지를 정의하고 컴파일된 앱을 반환한다.
    """
    workflow = StateGraph(GraphState)

    workflow.add_node("chat_node", chat_node)
    workflow.add_node("subject_info_node", info_node)
    workflow.add_node("rag_review_node", review_node)

    # 조건부 엣지 설정
    workflow.set_conditional_entry_point(
        route_question,
        {
            "chat": "chat_node",
            "subject_info": "subject_info_node",
            "rag_review": "rag_review_node",
        },
    )

    # 종료 엣지 설정
    # Chat Node는 최종 응답이므로 END로 이동
    workflow.add_edge("chat_node", END)
    # Subject Info / RAG Review 처리 후 Chat Node로 복귀
    workflow.add_edge("subject_info_node", "chat_node")
    workflow.add_edge("rag_review_node", "chat_node")

    return workflow.compile()

app = build_graph_app()

# 4. 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 5. 대화 기록 표시
for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.markdown(msg.content)
    elif isinstance(msg, AIMessage):
        with st.chat_message("assistant"):
            st.markdown(msg.content)

# 6. 사용자 입력 처리
if prompt := st.chat_input("질문을 입력하세요 (예: 비행운 줄거리 알려줘)"):
    if "UPSTAGE_API_KEY" not in os.environ:
        st.error("왼쪽 사이드바에서 Upstage API Key를 먼저 입력해주세요.")
        st.stop()

    # (1) 사용자 메시지 표시
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append(HumanMessage(content=prompt))

    # (2) 챗봇 응답 생성
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Thinking...")
        
        try:
            inputs = {"messages": st.session_state.messages}
            result = app.invoke(inputs)
            
            last_message = result["messages"][-1]
            response_text = last_message.content
            
            # 결과 화면 출력
            message_placeholder.markdown(response_text)
            
            # (3) RAG 참조 문서가 있다면 아코디언으로 표시
            if "context" in result and result["context"]:
                with st.expander("참조한 정보/리뷰 확인"):
                    st.write(result["context"])
            
            # 대화 기록 저장
            st.session_state.messages.append(AIMessage(content=response_text))
            
        except Exception as e:
            message_placeholder.error(f"오류 발생: {e}")