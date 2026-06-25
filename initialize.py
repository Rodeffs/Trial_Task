import sqlite3


"""
Этот файл нужен для инициализации базы данных, а также, чтобы добавить парочку значений
"""


con = sqlite3.connect("aybolit.db")
cur = con.cursor()


# Таблица животных

cur.execute("""
    CREATE TABLE IF NOT EXISTS user(
        user_id INTEGER PRIMARY KEY,
        user_name TEXT NOT NULL
    )
""")

cur.execute("""
    INSERT OR REPLACE INTO user VALUES
        (1, 'Squirrel'),
        (2, 'Bear'),
        (3, 'Cat'),
        (4, 'Dog'),
        (5, 'Sparrow')
""")

con.commit()


# Таблица расписаний

cur.execute("""
    CREATE TABLE IF NOT EXISTS schedule(
        schedule_id INTEGER PRIMARY KEY,
        pill_name TEXT NOT NULL,
        time_period TEXT NOT NULL,
        duration TEXT,
        user_id INTEGER,
        FOREIGN KEY(user_id) REFERENCES user(user_id)
    )
""")


con.close()
