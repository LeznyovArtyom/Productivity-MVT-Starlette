from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Role, Importance, Status

# Имя базы данных
DATABASE_NAME = "Productivity"

# Строка подключения к вновь созданной базе данных
DATABASE_URL = f"mysql+pymysql://root:TikTakfoke86!@localhost:3306/{DATABASE_NAME}"
# DATABASE_URL = f"mysql+pymysql://root:PApMPOEEpPmxXCRtXpGgzCErCNIjihtJ@roundhouse.proxy.rlwy.net:45012/{DATABASE_NAME}"

# Создание нового engine для подключения к созданной базе данных
engine = create_engine(DATABASE_URL)

# Создание сессии для взаимодействия с базой данных
Session = sessionmaker(bind=engine)
session = Session()

# Заполнение базы данных начальными данными
def populate_initial_data(session):
    importances = [("Критическая",), ("Высокая",), ("Средняя",), ("Низкая",), ("Очень низкая",)]
    for name in importances:
        session.add(Importance(name=name[0]))

    statuses = [("Открытая",), ("В процессе",), ("Выполнено",), ("Удалено",)]
    for name in statuses:
        session.add(Status(name=name[0]))

    roles = [("Пользователь",), ("Веб-разработчик",), ("Дизайнер",), ("Архитектор",), ("Фотограф",), ("Администратор",), 
             ("Проектный менеджер",), ("Контент-менеджер",), ("Тестировщик",), ("Аналитик",), ("SEO-специалист",), 
             ("Маркетолог",), ("Системный администратор",), ("Редактор",), ("Копирайтер",)]
    for name in roles:
        session.add(Role(name=name[0]))

    # Применение изменений
    session.commit()

populate_initial_data(session)