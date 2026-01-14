from app.user.user_repository import UserRepository
from app.user.user_schema import User, UserLogin, UserUpdate

class UserService:
    def __init__(self, userRepoitory: UserRepository) -> None:
        self.repo = userRepoitory

    def login(self, user_login: UserLogin) -> User:
        '''
        유저 로그인 정보 user_login을 파라미터로 받아서,
        비밀번호가 같다면 user 접속을 허용하고 
        같지 않다면 ValueError exception을 핸들링하여
        접근을 차단합니다

        유저 로그인 정보 자체가 database에 없다면 "User not Found."를 출력하고 
        exception 핸들링 처리합니다
        '''
        user = self.repo.get_user_by_email(user_login.email)
        if user is None:
            raise ValueError("User not Found.")

        if user.password != user_login.password:
            raise ValueError("Invalid ID/PW")

        return user
        
    def register_user(self, new_user: User) -> User:
        '''
        새 유저 정보 new_user를 받아서 database에 등록합니다.

        해당 정보가 이미 database에 있다면 처리를 차단하고 exception 핸들링 합니다.
        '''
        existing_user = self.repo.get_user_by_email(new_user.email)
        if existing_user is not None:
            raise ValueError("User already Exists.")

        return self.repo.save_user(new_user)

    def delete_user(self, email: str) -> User:
        '''
        삭제 유저 정보 email를 받아서 database에서 해당 이메일을 가진 유저 정보를 삭제합니다. 

        해당 정보가 database에 없다면 처리를 차단하고 exception 핸들링 합니다.
        '''
        user = self.repo.get_user_by_email(email)
        if user is None:
            raise ValueError("User not Found.")

        return self.repo.delete_user(user)

    def update_user_pwd(self, user_update: UserUpdate) -> User:
        '''
        비밀번호 업데이트 유저 정보 user_update를 받아서, 
        database에서 해당 유저의 비밀번호를 업데이트합니다. 

        해당 정보가 database에 없다면 처리를 차단하고 exception 핸들링 합니다.
        '''
        user = self.repo.get_user_by_email(user_update.email)
        if user is None:
            raise ValueError("User not Found.")

        user.password = user_update.new_password
        return self.repo.save_user(user)