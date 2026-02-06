from langchain_upstage import ChatUpstage
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from st_app.utils.state import GraphState

def route_question(state: GraphState):
    """
    사용자의 질문 의도를 분류하여 다음으로 이동할 노드를 결정한다.
    """
    print("---의도 분류 시작 (LLM Router)---")
    
    # 1. 의도 분류를 위한 LLM 설정 (Solar-1-Mini 사용)
    llm = ChatUpstage(model="solar-1-mini-chat")
    
    # 2. 의도 분류 프롬프트 작성 (김애란 작가 저서 컨텍스트 반영)
    prompt = PromptTemplate(
        template="""당신은 사용자의 질문 의도를 파악하여 적절한 노드로 연결해주는 라우터입니다.
        사용자의 질문을 분석하여 아래 세 가지 카테고리 중 하나로만 답변하세요.
        
        1. 'info': 김애란 작가의 책에 대한 객관적인 정보(출판사, 출판년도, 줄거리, 저자 정보 등)를 묻는 경우
        2. 'review': 책에 대한 독자들의 반응, 분위기, 서평, 감상평 등을 궁금해하는 경우
        3. 'chat': 단순한 인사, 잡담, 또는 도서 정보/리뷰와 관련 없는 일반적인 대화인 경우
        
        질문: {question}
        
        형식: {{"intent": "카테고리명"}}
        """,
        input_variables=["question"],
    )
    
    # 3. 체인 구성 및 실행
    chain = prompt | llm | JsonOutputParser()
    
    # 마지막 메시지를 기준으로 의도 파악
    user_message = state["messages"][-1].content
    result = chain.invoke({"question": user_message})
    
    intent = result.get("intent", "chat")
    print(f"---분류된 의도: {intent}---")
    
    # 4. 분류된 의도에 따라 다음 노드 이름 반환
    if intent == "info":
        return "subject_info"
    elif intent == "review":
        return "rag_review"
    else:
        return "chat"