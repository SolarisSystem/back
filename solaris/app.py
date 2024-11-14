from flask import Flask, g
from os import getenv
from sqlite3 import connect

#####################

solaris_app = Flask('solaris') # Создаём экземпляр приложения
db_path = getenv('SOLARIS_SQLITE_PATH', 'dev.db') # Определяем, где будет лежать база данных

#####################

# Не особо важна часть с getattr
# Важно - функция подключается к базе данных и возвразает это подключение
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect(db_path)
    return db

#####################

# Выполяет SQL запрос на создание таблицы с котиками
def prepare_tables() -> None:
    # Все запросы к базе делаются через курсор
    cursor = get_db().cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(128) NOT NULL,
            email VARCHAR(128) NOT NULL,
            password_hash VARCHAR(128) NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            user_id INTEGER NOT NULL,
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            giver_id INTEGER NOT NULL,
            taker_id INTEGER NOT NULL,
            final_date DATE,
            FOREIGN KEY (book_id) REFERENCES books (id),
            FOREIGN KEY (giver_id) REFERENCES users (id),
            FOREIGN KEY (taker_id) REFERENCES users (id)
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(128) NOT NULL,
            authot VARCHAR(128) NOT NULL,
            release_year INTEGER NOT NULL,
            owner_id INTEGER NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES users (id)
        );
    """)


def run_app() -> None:
    # Просто запускаем наше приложение
    solaris_app.run(
        host=getenv('SOLARIS_HOST', '0.0.0.0'),
        port=int(getenv('SOLARIS_PORT', '5000')),
        debug=True
    )

#####################

@solaris_app.route('/', methods=['GET'])
def index():
    return 'Hello from Solaris app'

@solaris_app.route('/register', methods=['POST'])
def register():
    email = request.json['email']
    name = request.json['name']
    password = request.json['password']

    cursor = get_db().cursor()
    user = cursor.execute(f'SELECT * FROM users WHERE email="{email}";').fetchone()
    if user is not None:
        return 'User already exists', 400
    cursor.execute(f'INSERT INTO users (email, name, password_hash) VALUES ("{email}", "{name}", "{password}");')
    cursor.close()
    get_db().commit()
    return 'Created', 201

#####################

if __name__ == '__main__':
    with solaris_app.app_context():
        prepare_tables()
    run_app()
