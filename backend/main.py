from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional

SECRET_KEY = "your-very-strong-secret-key-change-this-2026"  # حتماً به چیزی امن تغییر بده
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI(title="DentiFlow AI - Auth Module")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class User(BaseModel):
    username: str
    role: str
    disabled: bool = False

class UserInDB(User):
    hashed_password: str

# لیست کاربران موقت - hash را در زمان اجرا می‌سازیم تا خطا نده
fake_users_db = {
    "mostafa": {
        "username": "mostafa",
        "hashed_password": pwd_context.hash("securepass"),
        "role": "dentist",
        "disabled": False,
    },
    "assistant1": {
        "username": "assistant1",
        "hashed_password": pwd_context.hash("assistantpass"),
        "role": "assistant",
        "disabled": False,
    },
    "patient123": {
        "username": "patient123",
        "hashed_password": pwd_context.hash("patientpass"),
        "role": "patient",
        "disabled": False,
    },
}

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)

def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, token_data.username)
    if user is None:
        raise credentials_exception
    return user

def role_required(allowed_roles: list[str]):
    async def check_role(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"Insufficient permissions. Required roles: {allowed_roles}")
        return current_user
    return check_role

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/dentist-only")
async def dentist_dashboard(current_user: User = Depends(role_required(["dentist"]))):
    return {"message": f"Welcome to Dentist Dashboard, {current_user.username}!"}

@app.get("/staff")
async def staff_area(current_user: User = Depends(role_required(["dentist", "assistant"]))):
    return {"message": f"Staff area access granted for {current_user.role}: {current_user.username}"}

@app.get("/patient-portal")
async def patient_portal(current_user: User = Depends(role_required(["patient"]))):
    return {"message": f"Patient portal for {current_user.username}"}