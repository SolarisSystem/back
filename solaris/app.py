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
        CREATE TABLE IF NOT EXISTS cats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(128) NOT NULL                 
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

@solaris_app.route('/cats', methods=['GET'])
def list_cats():
    # Вытаскиваем из базы всех котов
    cursor = get_db().cursor();
    cats = cursor.execute("""
        SELECT name FROM cats;
    """)

    # И делаем список из их имён
    response = ''
    for cat in cats.fetchall():
        response += f'<p>Котик {cat[0]}</p>'

    return response

@solaris_app.route('/cat/<name>', methods=['POST'])
def add_cat(name: str):
    # Кладём в базу нового кота
    # Вместо ? будет подставлено то, что лежит в name
    cursor = get_db().cursor()
    cursor.execute("""
        INSERT INTO cats (name) VALUES (?);
    """, (name,))
    get_db().commit()

    return '', 201

#####################

if __name__ == '__main__':
    with solaris_app.app_context():
        prepare_tables()
    run_app()
