from typing import Annotated, TypedDict, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class GraphState(TypedDict):
    """
    LangGraph의 노드 간에 전달되는 상태를 정의하는 클래스이다.
    """
    
    # 대화 기록을 저장하며, 새로운 메시지가 들어오면 리스트에 추가(add_messages)한다.
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Router가 판단한 사용자의 의도(intent)를 저장한다. (분기 결정용)
    # 값 예시: "chat", "info", "review"
    intent: str
    
    # 사용자가 질문에서 언급한 특정 도서명을 추적한다.
    # 예: "비행운은 어떤 내용이야?" -> "비행운" 저장
    selected_book: str
    
    # RAG 노드에서 검색된 리뷰 원문이나 도서 정보를 임시로 저장하는 공간이다.
    context: str