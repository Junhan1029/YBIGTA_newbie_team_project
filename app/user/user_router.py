from fastapi import APIRouter, HTTPException, Depends, status
from app.user.user_schema import User, UserLogin, UserUpdate, UserDeleteRequest
from app.user.user_service import UserService
from app.dependencies import get_user_service
from app.responses.base_response import BaseResponse

user = APIRouter(prefix="/api/user")


@user.post("/login", response_model=BaseResponse[User], status_code=status.HTTP_200_OK)
def login_user(user_login: UserLogin, service: UserService = Depends(get_user_service)) -> BaseResponse[User]:
    '''
    User가 로그인을 시도하면 해당 데이터를 user_login 인스턴스에 저장합니다
    이후 FastAPI가 get_user_service를 실행시킵니다

    Args:
        user_login: 로그인 정보(이메일, 비밀번호)
        service: get_user_service로 생성된 작업 객체가 담긴 변수
    '''
    try:
        user = service.login(user_login)
        return BaseResponse(status="success", data=user, message="Login Success.") 
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@user.post("/register", response_model=BaseResponse[User], status_code=status.HTTP_201_CREATED)
def register_user(user: User, service: UserService = Depends(get_user_service)) -> BaseResponse[User]:
    '''
    받은 회원가입 user 정보를 database에 등록합니다
    이미 존재하는 user 정보일 시, 400 에러로 핸들링하여 처리합니다.
    '''
    try:
        new_user: User = service.register_user(user)
        return BaseResponse(status="success", data=new_user, message="User registeration success.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    


@user.delete("/delete", response_model=BaseResponse[User], status_code=status.HTTP_200_OK)
def delete_user(user_delete_request: UserDeleteRequest, service: UserService = Depends(get_user_service)) -> BaseResponse[User]:
    '''
    받은 삭제 요청 user_delete_request 정보를 database에서 삭제합니다
    database에 존재하지 않는 user_delete_request 정보일 시, 404 에러로 핸들링하여 처리합니다.
    '''
    try:
        deleted_user: User = service.delete_user(str(user_delete_request.email))
        return BaseResponse(status="success", data=deleted_user, message="User Deletion Success.")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@user.put("/update-password", response_model=BaseResponse[User], status_code=status.HTTP_200_OK)
def update_user_password(user_update: UserUpdate, service: UserService = Depends(get_user_service)) -> BaseResponse[User]:
    '''
    받은 비밀번호 변경 요청 user_update 정보를 통해 database에 있는 원본 비밀번호를 업데이트합니다
    원본 user_update 정보가 database에 존재하지 않을 시, 404 에러로 핸들링하여 처리합니다.
    '''
    try:
        updated_user: User = service.update_user_pwd(user_update)
        return BaseResponse(status="success", data=updated_user, message="User password update success.")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
