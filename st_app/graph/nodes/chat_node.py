from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from st_app.utils.state import GraphState
from st_app.rag.prompt import CHAT_SYSTEM_PROMPT
from st_app.rag.llm import get_llm

def chat_node(state: GraphState):
    """
    자기소개, 기능 안내, 작가 소개 및 일반 대화를 처리한다.
    """
    print("---일반 대화 및 가이드 처리 (Chat Node)---")

    llm = get_llm()
    
    # rag/prompt.py에서 정의한 시스템 메시지를 적용한다.
    prompt = ChatPromptTemplate.from_messages([
        ("system", CHAT_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ])
    
    chain = prompt | llm
    response = chain.invoke({"messages": state["messages"]})
    
    return {
        "messages": [response]
    }