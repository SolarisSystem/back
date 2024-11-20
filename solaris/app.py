from flask import Flask, g, request, jsonify
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
            password VARCHAR(128) NOT NULL
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

def get_user_by_id(user_id):
    cursor = get_db().cursor()

    user = cursor.execute(f"SELECT * FROM users WHERE id={user_id};").fetchone()
    cursor.close()

    return user


def get_user_by_session_id(session_id):
    cursor = get_db().cursor()

    user_id = cursor.execute(f"SELECT user_id FROM sessions WHERE session_id={session_id};").fetchone()
    cursor.close()

    if user_id is None:
        return None
    return get_user_by_id(user_id[0])


def validate_session_id(session_id):
    return get_user_by_session_id(session_id) is not None


####################

def is_auth_valid():
    if 'SessionID' in request.headers:
        return validate_session_id(request.headers.get('SessionID'))
    return False

####################

def user_row_to_dict(user_row):
    return {
        'id': user_row[0],
        'name': user_row[1],
        'email': user_row[2]
    }

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
    cursor.execute(f'INSERT INTO users (email, name, password) VALUES ("{email}", "{name}", "{password}");')
    cursor.close()
    get_db().commit()
    return 'Created', 201

@solaris_app.route('/login', methods=['POST'])
def login():
    email = request.json['email']
    password = request.json['password']

    cursor = get_db().cursor()
    user = cursor.execute(f'SELECT * FROM users WHERE email="{email}" and password="{password}";').fetchone()
    print(user)
    if user is None:
       return 'Доступ запрещен', 403

    cursor.execute(f'INSERT INTO sessions (user_id) VALUES ("{user[0]}");')
    
    cursor.close()
    get_db().commit()

    return jsonify({'user_id': user[0], 'session_id':cursor.lastrowid}), 200

@solaris_app.route('/user/<int:user_id>')
def get_user(user_id):
    if not is_auth_valid():
        return 'Request denied, invalid session', 403
    
    user = get_user_by_id(user_id)
    if user is None:
        return 'User not found', 404
    return jsonify(user_row_to_dict(user)), 200

@solaris_app.route('/users')
def get_users():
    cursor = get_db().cursor()
    users = cursor.execute("SELECT * FROM users;").fetchall()
    cursor.close()
    
    res = []
    for u in users:
        res.append(user_row_to_dict(u))

    response = {
        'users': res
    }

    return jsonify(response), 200

# SELECT * FROM users;

#####################

if __name__ == '__main__':
    with solaris_app.app_context():
        prepare_tables()
    run_app()
