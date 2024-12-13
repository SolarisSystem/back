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
            final_date VARCHAR(32),
            FOREIGN KEY (book_id) REFERENCES books (id),
            FOREIGN KEY (giver_id) REFERENCES users (id),
            FOREIGN KEY (taker_id) REFERENCES users (id)
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(128) NOT NULL,
            author VARCHAR(128) NOT NULL,
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

def get_book_by_id(book_id):
    cursor = get_db().cursor()

    book = cursor.execute(f"SELECT * FROM books WHERE id={book_id};").fetchone()
    cursor.close()

    return book

def get_share_by_id(share_id):
    cursor = get_db().cursor()

    share = cursor.execute(f"SELECT * FROM shares WHERE id={share_id};").fetchone()
    cursor.close()

    return share

####################

def user_row_to_dict(user_row):
    return {
        'id': user_row[0],
        'name': user_row[1],
        'email': user_row[2]
    }

####################

def book_row_to_dict(book_row):
    return {
        'id': book_row[0],
        'title': book_row[1],
        'author': book_row[2],
        'release_year:': book_row[3],
        'owner_id': book_row[4],
    }

#####################

def share_row_to_dict(share_row):
    return {
        'id': share_row[0],
        'book_id': share_row[1],
        'giver_id': share_row[2],
        'taker_id:': share_row[3],
        'final_date': share_row[4],
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
    if not is_auth_valid():
        return 'Request denied, invalid session', 403
    
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

@solaris_app.route('/book', methods=['POST'])
def add_book():
    if not is_auth_valid():
        return 'Request denied, invalid session', 403
    
    owner_id = get_user_by_session_id(request.headers.get('SessionID'))[0]
    
    title = request.json['title']
    author = request.json['author']
    release_year = request.json['release_year']

    cursor = get_db().cursor()
    cursor.execute(f'INSERT INTO books(title, author, release_year, owner_id) VALUES("{title}", "{author}", {release_year}, {owner_id});')
    get_db().commit()

    return 'Created', 201

@solaris_app.route('/books', methods=['GET'])
def get_books():
    if not is_auth_valid():
        return 'Request denied, invalid session', 403
    
    cursor = get_db().cursor()
    books = cursor.execute("SELECT * FROM books;").fetchall()
    cursor.close()
    
    res = []
    for u in books:
        res.append(book_row_to_dict(u))

    response = {
        'book': res
    }

    return jsonify(response), 200

@solaris_app.route('/book/<int:book_id>')
def get_book(book_id):
    if not is_auth_valid():
        return 'Request denied, invalid session', 403

    books = get_book_by_id(book_id)
    if books is None:
        return 'Book not found', 404
    return jsonify(book_row_to_dict(books)), 200

@solaris_app.route('/share', methods=['POST'])
def share_book():
    if not is_auth_valid():
        return 'Request denied, invalid session', 403
    
    owner_id = get_user_by_session_id(request.headers.get('SessionID'))[0]
    
    book_id = request.json['book_id']
    taker_id = request.json['taker_id']
    final_date = request.json['final_date']
    
    if get_user_by_id(taker_id) == None:
        return 'Taker not found', 404
    if get_book_by_id(book_id) == None:
        return 'Book not found', 404

    cursor = get_db().cursor()
    cursor.execute(
        f'INSERT INTO shares(book_id, giver_id, taker_id, final_date) VALUES({book_id}, {owner_id}, {taker_id}, "{final_date}");')
    get_db().commit()

    return jsonify({'share_id': cursor.lastrowid}), 200

@solaris_app.route('/return', methods=['POST'])
def return_book():
    if not is_auth_valid():
        return 'Request denied, invalid session', 403

    owner_id = get_user_by_session_id(request.headers.get('SessionID'))[0]
    
    share_id = request.json['share_id']

    share = get_share_by_id(share_id)
    if share == None:
        return 'Share not found', 404
    
    if share[2] != owner_id:
        return 'You are not an owner of the book', 403

    cursor = get_db().cursor()
    cursor.execute(
        f'DELETE * FROM shares WHERE id={share_id};')
    get_db().commit()

    return 'Book was returned', 200

@solaris_app.route('/shares', method=['GET'])
def get_shares():
    if not is_auth_valid():
        return 'Request denied, invalid session', 403
    
    cursor = get_db().cursor()
    shares = cursor.execute("SELECT * FROM shares;").fetchall()
    cursor.close()
    
    res = []
    for u in shares:
        res.append(share_row_to_dict(u))

    response = {
        'shares': res
    }

    return jsonify(response), 200

#####################

if __name__ == '__main__':
    with solaris_app.app_context():
        prepare_tables()
    run_app()
