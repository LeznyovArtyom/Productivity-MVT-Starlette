from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
from starlette.responses import JSONResponse, RedirectResponse
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.authentication import (
    AuthCredentials, AuthenticationBackend, SimpleUser, UnauthenticatedUser, requires
)
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from databases import Database
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
from models import User, Task, Role
from starlette.middleware.cors import CORSMiddleware
import base64
from starlette.datastructures import UploadFile
import re


DATABASE_URL = "mysql+aiomysql://root:TikTakfoke86!@localhost:3306/Productivity"
# DATABASE_URL = f"mysql+aiomysql://root:PApMPOEEpPmxXCRtXpGgzCErCNIjihtJ@roundhouse.proxy.rlwy.net:45012/Productivity"

# Создание асинхронного двигателя и базы данных
database = Database(DATABASE_URL)
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

templates = Jinja2Templates(directory="templates")


SECRET_KEY = "MenedgerZadach"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Сверить введенный пароль с хешированным 
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Получить захешированный пароль
def get_password_hash(password):
    return pwd_context.hash(password)

# Создать токен доступа
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Извлечь информацию из токена
def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# Проверка отправленного токена
class JWTAuthanticationBackend(AuthenticationBackend):
    async def authenticate(self, request):
        token = request.cookies.get("access_token")
        if not token:
            return None

        payload = decode_access_token(token)
        if payload is None:
            return None

        return AuthCredentials(["authenticated"]), SimpleUser(payload["sub"])


# Получить страницу index
async def homepage(request):
    return templates.TemplateResponse(request, "index.html")


# Получить страницу авторизации
async def authorization_page(request):
    return templates.TemplateResponse(request, "Authorization.html")


# Получить страницу регистрации
async def registration_page(request):
    return templates.TemplateResponse(request, "Registration.html")


# Получить страницу задач пользователя
@requires("authenticated", redirect="homepage")
async def my_tasks_page(request):
    user_login = request.user.username
    async with SessionLocal() as session:
        async with session.begin():
            result1 = await session.execute(select(User).options(joinedload(User.role)).filter(User.login == user_login))
            user = result1.scalar_one_or_none()
            result2 = await session.execute(select(Task).options(joinedload(Task.importance), joinedload(Task.status)).filter(Task.user_id == user.id, Task.status_id.notin_([3, 4])))
            tasks = result2.scalars().all()

            # Получить параметры фильтрации и сортировки
            importance_filter = request.query_params.get("importance_filter", "default")
            status_filter = request.query_params.get("status_filter", "default")
            priority_sort = request.query_params.get("priority_sort", "default")
            deadline_sort = request.query_params.get("deadline_sort", "default")
            
            # Начинаем с базового запроса
            query = select(Task).options(joinedload(Task.importance), joinedload(Task.status)).filter(Task.user_id == user.id, Task.status_id.notin_([3, 4]))
            
            # Применяем фильтрацию
            if importance_filter != "default":
                query = query.filter(Task.importance_id == int(importance_filter))
            if status_filter != "default":
                query = query.filter(Task.status.has(name=status_filter))

            # Выполняем сортировку
            if priority_sort == "highest":
                query = query.order_by(Task.importance_id.asc())
            elif priority_sort == "lowest":
                query = query.order_by(Task.importance_id.desc())
            if deadline_sort == "soonest":
                query = query.order_by(Task.deadline.asc())
            elif deadline_sort == "latest":
                query = query.order_by(Task.deadline.desc())
            
            # Выполняем запрос
            result2 = await session.execute(query)
            tasks = result2.scalars().all()


            if user:
                image_base64 = encode_image_to_base64(user.image)
                importance_image = {
                    "Критическая": "/images/critical_importance.png", 
                    "Высокая": "/images/high_importance.png",
                    "Средняя": "/images/medium_importance.jpg",
                    "Низкая": "/images/low_importance.png", 
                    "Очень низкая": "/images/very_low_importance.jpg"
                }
                status_color = {
                    "Открытая": "status-open",
                    "В процессе": "status-in-progress",
                    "Выполнено": "status-completed",
                    "Удалено": "status-removed"
                }

                return templates.TemplateResponse("My_tasks.html", {
                    "request": request,
                    "user": {
                        "name": user.name,
                        "role": user.role.name,
                        "image": f"data:image/jpeg;base64,{image_base64}"
                    },
                    "tasks": [
                        {
                            "id": task.id,
                            "name": task.name if len(task.name) <= 70 else task.name[:70] + "...",
                            "description": task.description if len(task.description) <= 150 else task.description[:150] + "...",
                            "importance_image": importance_image[task.importance.name],
                            "importance_id": task.importance_id,
                            "status": task.status.name,
                            "status_color": status_color[task.status.name],
                            "deadline": task.deadline.strftime("%d %B %Y")
                        } for task in tasks
                    ]
                })
            

# Получить страницу завершенных задач
@requires("authenticated", redirect="homepage")
async def complete_tasks_page(request):
    user_login = request.user.username
    async with SessionLocal() as session:
        async with session.begin():
            result1 = await session.execute(select(User).options(joinedload(User.role)).filter(User.login == user_login))
            user = result1.scalar_one_or_none()
            result2 = await session.execute(select(Task).options(joinedload(Task.importance), joinedload(Task.status)).filter(Task.user_id == user.id, Task.status_id == 3))
            tasks = result2.scalars().all()

            if user:
                image_base64 = encode_image_to_base64(user.image)
                importance_image = {
                    "Критическая": "/images/critical_importance.png", 
                    "Высокая": "/images/high_importance.png",
                    "Средняя": "/images/medium_importance.jpg",
                    "Низкая": "/images/low_importance.png", 
                    "Очень низкая": "/images/very_low_importance.jpg"
                }

                return templates.TemplateResponse("Complete_tasks.html", {
                    "request": request,
                    "user": {
                        "name": user.name,
                        "role": user.role.name,
                        "image": f"data:image/jpeg;base64,{image_base64}"
                    },
                    "tasks": [
                        {
                            "id": task.id,
                            "name": task.name if len(task.name) <= 70 else task.name[:70] + "...",
                            "description": task.description if len(task.description) <= 120 else task.description[:120] + "...",
                            "importance_image": importance_image[task.importance.name],
                            "importance_id": task.importance_id, # Проверить
                            "status": task.status.name, # Проверить
                            "deadline": task.deadline.strftime("%d %B %Y")
                        } for task in tasks
                    ]
                })
            

# Получить страницу корзины
@requires("authenticated", redirect="homepage")
async def the_trash_page(request):
    user_login = request.user.username
    async with SessionLocal() as session:
        async with session.begin():
            result1 = await session.execute(select(User).options(joinedload(User.role)).filter(User.login == user_login))
            user = result1.scalar_one_or_none()
            result2 = await session.execute(select(Task).options(joinedload(Task.importance), joinedload(Task.status)).filter(Task.user_id == user.id, Task.status_id == 4))
            tasks = result2.scalars().all()

            if user:
                image_base64 = encode_image_to_base64(user.image)
                importance_image = {
                    "Критическая": "/images/critical_importance.png", 
                    "Высокая": "/images/high_importance.png",
                    "Средняя": "/images/medium_importance.jpg",
                    "Низкая": "/images/low_importance.png", 
                    "Очень низкая": "/images/very_low_importance.jpg"
                }

                return templates.TemplateResponse("The_trash.html", {
                    "request": request,
                    "user": {
                        "name": user.name,
                        "role": user.role.name,
                        "image": f"data:image/jpeg;base64,{image_base64}"
                    },
                    "tasks": [
                        {
                            "id": task.id,
                            "name": task.name if len(task.name) <= 70 else task.name[:70] + "...",
                            "description": task.description if len(task.description) <= 120 else task.description[:120] + "...",
                            "importance_image": importance_image[task.importance.name],
                            "importance_id": task.importance_id, # Проверить
                            "status": task.status.name, # Проверить
                            "deadline": task.deadline.strftime("%d %B %Y")
                        } for task in tasks
                    ]
                })
            

# Получить страницу задачи
@requires("authenticated", redirect="homepage")
async def the_task_page_by_id(request):
    user_login = request.user.username
    task_id = request.path_params["task_id"]
    async with SessionLocal() as session:
        async with session.begin():
            result1 = await session.execute(select(User).options(joinedload(User.role)).filter(User.login == user_login))
            user = result1.scalar_one_or_none()
            result = await session.execute(select(Task).options(joinedload(Task.importance), joinedload(Task.status)).filter(Task.id == task_id))
            task = result.scalar_one_or_none()

            if user:
                image_base64 = encode_image_to_base64(user.image)
                importance_image = {
                    "Критическая": "/images/critical_importance.png", 
                    "Высокая": "/images/high_importance.png",
                    "Средняя": "/images/medium_importance.jpg",
                    "Низкая": "/images/low_importance.png", 
                    "Очень низкая": "/images/very_low_importance.jpg"
                }
                status_color = {
                    "Открытая": "status-open",
                    "В процессе": "status-in-progress",
                    "Выполнено": "status-completed",
                    "Удалено": "status-removed"
                }

                return templates.TemplateResponse("The_task.html", {
                    "request": request,
                    "user": {
                        "name": user.name,
                        "role": user.role.name,
                        "image": f"data:image/jpeg;base64,{image_base64}"
                    },
                    "task": {
                        "id": task.id,
                        "name": task.name,
                        "description": task.description,
                        "importance_image": importance_image[task.importance.name],
                        "importance_id": task.importance_id,
                        "status_color": status_color[task.status.name],
                        "status_id": task.status_id,
                        "deadline": task.deadline.strftime("%Y-%m-%d")
                    }
})
            

# Получить страницу добавления задачи
@requires("authenticated", redirect="homepage")
async def add_task_page(request):
    user_login = request.user.username
    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(User).options(joinedload(User.role)).filter(User.login == user_login))
            user = result.scalar_one_or_none()
            if user:
                image_base64 = encode_image_to_base64(user.image)
                return templates.TemplateResponse("Add_task.html", {
                    "request": request,
                    "user": {
                        "name": user.name,
                        "role": user.role.name,
                        "image": f"data:image/jpeg;base64,{image_base64}"
                    }
                })
            

# Получить страницу настроек
@requires("authenticated", redirect="homepage")
async def settings_page(request):
    user_login = request.user.username
    error = request.query_params.get("error", 0)
    print(error, "rrrrrrrrrrrrr")
    async with SessionLocal() as session:
        async with session.begin():
            result1 = await session.execute(select(User).options(joinedload(User.role)).filter(User.login == user_login))
            user = result1.scalar_one_or_none()
            result2 = await session.execute(select(Role))
            roles = result2.scalars().all()
            if user:
                image_base64 = encode_image_to_base64(user.image)
                return templates.TemplateResponse("Settings.html", {
                    "request": request,
                    "user": {
                        "name": user.name,
                        "login": user.login,
                        "role": user.role.name,
                        "image": f"data:image/jpeg;base64,{image_base64}"
                    },
                    "roles": [
                        {
                            "id": role.id,
                            "name": role.name
                        } for role in roles
                    ],
                    "error": error
                })


# Авторизовать пользователя
async def login_user(request):
    form = await request.form()
    login = form.get("login")
    password = form.get("password")
    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(User).filter(User.login == login))
            user = result.scalar_one_or_none()
            if user and verify_password(password, user.password):
                access_token = create_access_token(data={'sub': user.login})
                response = RedirectResponse(url="/my_tasks", status_code=302)
                response.set_cookie(key="access_token", value=access_token, httponly=True)
                return response
    return templates.TemplateResponse("Authorization.html", {
        "request": request,
        "error": "Неправильный логин или пароль"
    }, status_code=401)


# Зарегистрировать нового пользователя
async def register_new_user(request):
    form = await request.form()
    name = form.get("name")
    login = form.get("login")
    password = form.get("password")
    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(User).filter(User.login == login))
            existing_user = result.scalar_one_or_none()
            if existing_user:
                return templates.TemplateResponse("Registration.html", {
                    "request": request,
                    "error": "Пользователь с таким логином уже существует"
                }, status_code=409)

            with open("images/профиль.jpg", "rb") as file:
                image = file.read()
            try:
                user = User(
                    name=name,
                    login=login, 
                    password=get_password_hash(password), 
                    image=image, 
                    role_id=1
                )
                session.add(user)
                print("Пользователь зарегистрировался")
                await session.commit()
                response = RedirectResponse(url="/", status_code=302)
                return response
            except:
                await session.rollback()
                return templates.TemplateResponse("Registration.html", {
                    "request": request,
                    "error": "Что-то пошло не так"
                }, status_code=401)


# Изменить статус задачи
@requires("authenticated", redirect="homepage")
async def change_status(request):
    current_page = request.path_params["current_page"]
    task_id = request.path_params["task_id"]
    status_id = request.path_params["status_id"]
    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(Task).filter(Task.id == task_id))
            task = result.scalar_one_or_none()
            if task:
                task.status_id = status_id
            await session.commit()
            if current_page == "complete_tasks":
                return RedirectResponse(url='/complete_tasks', status_code=302)
            elif current_page == "the_trash":
                return RedirectResponse(url='/the_trash', status_code=302)
            else:
                return RedirectResponse(url='/my_tasks', status_code=302)
            

# Обновить информацию о задаче
@requires("authenticated", redirect="homepage")
async def update_task(request):
    form = await request.form()
    task_name = form.get("task_name")
    task_importance_id = form.get("task_importance_id")
    task_status_id = form.get("task_status_id")
    task_deadline = form.get("task_deadline")
    task_description = form.get("task_description")
    task_id = request.path_params["task_id"]
    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(Task).filter(Task.id == task_id))
            task = result.scalar_one_or_none()
            if task:
                task.name = task_name
                task.description = task_description
                task.importance_id = task_importance_id
                task.status_id = task_status_id
                task.deadline = task_deadline
                await session.commit()
                return RedirectResponse(url="/my_tasks", status_code=302)


# Добавить задачу
@requires("authenticated", redirect="homepage")          
async def add_task(request):
    user_login = request.user.username
    form = await request.form()
    task_name = form.get("task_name")
    task_description = form.get("task_description")
    task_importance_id = form.get("task_importance")
    task_deadline = form.get("task_deadline")
    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(User).options(joinedload(User.role)).filter(User.login == user_login))
            user = result.scalar_one_or_none()
            if user:
                task = Task(
                    name=task_name,
                    description=task_description,
                    importance_id=task_importance_id,
                    status_id=1,
                    deadline=task_deadline,
                    user_id=user.id
                )
                session.add(task)
                await session.commit()
                return RedirectResponse(url="/my_tasks", status_code=302)


# Выйти из аккаунта
@requires("authenticated", redirect="homepage") 
async def logout_of_account(request):
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    return response


# Удалить аккаунт
@requires("authenticated", redirect="homepage") 
async def delete_account(request):
    user_login = request.user.username
    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(User).filter(User.login == user_login))
            user = result.scalar_one_or_none()
            if user:
                await session.delete(user)
                await session.commit()
                response = RedirectResponse(url="/", status_code=302)
                response.delete_cookie("access_token")
                return response


def validateLogin(login):
    return re.match(r"^[a-zA-Z0-9]{3,}$", login)


def validatePassword(password):
    return len(password) >= 6


# Изменить информацию о пользователе
@requires("authenticated", redirect="homepage")
async def update_user(request):
    user_login = request.user.username
    form = await request.form()
    user_name = form.get("user_name")
    user_login_change = form.get("user_login_change")
    user_password = form.get("user_password")
    user_role_id = form.get("user_role_id")
    user_image: UploadFile = form.get("user_image")
    user_element = request.path_params["user_element"]

    if user_element == "user_login" and not validateLogin(user_login_change):
        return RedirectResponse(url=f"/settings?error=1")
    if user_element == "user_password" and not validatePassword(user_password):
        return RedirectResponse(url=f"/settings?error=2")

    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(User).options(joinedload(User.role)).filter(User.login == user_login))
            user = result.scalar_one_or_none()
            if user_element == "user_name":
                user.name = user_name
            elif user_element == "user_login":
                user.login = user_login_change
                # Создаем новый токен с обновленным логином
                access_token = create_access_token(data={'sub': user_login_change})
                response = RedirectResponse(url="/settings", status_code=302)
                response.set_cookie(key="access_token", value=access_token, httponly=True)
                await session.commit()
                return response
            elif user_element == "user_password":
                user.password = get_password_hash(user_password)
            elif user_element == "user_role":
                user.role_id = user_role_id
            elif user_element == "user_image":
                image_data = await user_image.read()
                user.image = image_data
            await session.commit()
            return RedirectResponse(url="/settings", status_code=302)


def encode_image_to_base64(image_data):
    return base64.b64encode(image_data).decode('utf-8') if image_data else None


routes = [
    Route("/", homepage, name="homepage"),
    Route("/authorization", authorization_page),
    Route("/registration", registration_page),
    Route("/my_tasks", my_tasks_page),
    Route("/users/login", login_user, methods=["POST"]),
    Route("/users/register", register_new_user, methods=["POST"]),
    Route("/complete_tasks", complete_tasks_page),
    Route("/{current_page:str}/task/{task_id:int}/change_status/{status_id:int}", change_status),
    Route("/the_trash", the_trash_page),
    Route("/the_task/{task_id:int}", the_task_page_by_id),
    Route("/task/{task_id:int}/update", update_task, methods=["POST"]),
    Route("/add_task", add_task_page),
    Route("/task/add", add_task, methods=["POST"]),
    Route("/settings", settings_page, methods=["POST", "GET"]),
    Route("/logout", logout_of_account, methods=["GET"]),
    Route("/delete_account", delete_account),
    Route("/user/{user_element:str}/update", update_user, methods=["POST"]),   
    Mount("/css", StaticFiles(directory="css"), name="css"),
    Mount("/js", StaticFiles(directory="js"), name="js"),
    Mount("/images", StaticFiles(directory="images"), name="images"),
]

app = Starlette(debug=True, routes=routes)
app.add_middleware(AuthenticationMiddleware, backend=JWTAuthanticationBackend())

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],  # Список разрешенных источников
    allow_credentials=True,
    allow_methods=["*"],  # Разрешенные методы
    allow_headers=["*"],  # Разрешенные заголовки
)