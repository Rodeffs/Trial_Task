from fastapi import FastAPI, Depends
from datetime import datetime
import sqlite3


"""
Этот файл и будет тем самым бэкэндом для работы с FastAPI
"""

app = FastAPI()


closest_next_taking = 60  # ближайший период времени в минутах, в течении которого необходимо принять таблетку


def get_db():  # важно сделать отдельное соединение, а затем подключаться к нему через Depends, чтобы не было ошибок
    con = sqlite3.connect("aybolit.db")
    try:
        yield con
    finally:
        con.close()


# Предполагается, что период принятия таблеток поступает в виде временных меток, разделённых пробелом. То есть, к примеру: 8:00 9:20 10:30
# Затем разделяем по пробелам, округляем, если нужно, и добавляем в таблицу
def parse_period(period: str):
    split_period = []

    for stamp in period.split():
        hour_str, minute_str = stamp.split(':')
        hour, minute = int(hour_str), int(minute_str)

        if hour < 8 or (hour >= 22 and minute > 0):
            raise ValueError("Time period must be within 8:00-22:00")

        if minute < 0 or minute > 59:
            raise ValueError("Incorrect time format")

        if minute % 15 == 0:  # если кратно 15 минутам, то просто добавляем как есть
            split_period.append(stamp)

        else:
            minute += 15 - minute % 15  # округление до 15 минут

            if minute == 60:
                split_period.append(str(hour + 1) + ":00")  # добавили час

            else:
                split_period.append(hour_str + ':' + str(minute))

    return split_period


@app.post("/schedule")
def add_schedule(data: dict, con: sqlite3.Connection = Depends(get_db)):
    cur = con.cursor()

    try:
        pill, period_str, duration, user = data["pill_name"], data["time_period"], data["duration_days"], data["user_id"]

        period = parse_period(period_str)

        schedule_id = cur.execute(f"""
            INSERT INTO schedule(pill_name, duration_days, user_id) VALUES
                ({pill}, {duration}, {user})
            RETURNING schedule_id
        """).fetchone()

        con.commit()

        for stamp in period:
            cur.execute(f"""
                INSERT INTO time_period VALUES
                    ({schedule_id}, {stamp})
            """)
            con.commit()

    except Exception as e:
        return {"message": e}

    return {"message": "Success!", "schedule_id": schedule_id}


@app.get("/schedules")
def get_schedules(user_id: int, con: sqlite3.Connection = Depends(get_db)):
    cur = con.cursor()

    try:
        data = cur.execute(f"""
            SELECT schedule_id
            FROM schedule
            WHERE user_id={user_id}
        """).fetchall()

    except Exception as e:
        return {"message": e}

    return {"message": "Success!", "data": data}


@app.get("/schedule")
def get_schedule(schedule_id: int, con: sqlite3.Connection = Depends(get_db)):
    cur = con.cursor()

    try:
        pill = cur.execute(f"""
            SELECT pill_name, duration_days
            FROM schedule
            WHERE schedule_id={schedule_id}
        """).fetchone()

        time_period = cur.execute(f"""
            SELECT time_stamp
            FROM time_period
            WHERE schedule_id={schedule_id}
            ORDER BY time_stamp
        """).fetchall()

    except Exception as e:
        return {"message": e}

    return {"message": "Success!", "pill": pill, "time_period": time_period}


@app.get("/next_takings")
def next_takings(user_id: int, con: sqlite3.Connection = Depends(get_db)):
    cur = con.cursor()

    time_now = datetime.now()
    minutes_now = time_now.hour * 60 + time_now.minute

    try:
        pill_time = cur.execute(f"""
            SELECT pill_name, time_stamp
            FROM schedule
            INNER JOIN time_period ON schedule.schedule_id = time_period.schedule_id
            WHERE user_id = {user_id}
            ORDER BY time_stamp
        """).fetchall()

        next_pills = []

        for pill_name, stamp in pill_time:
            hour_str, minute_str = stamp.split(':')
            stamp_minute = int(hour_str) * 60 + int(minute_str)

            if 0 < stamp_minute - minutes_now <= closest_next_taking:
                next_pills.append((pill_name, stamp))

    except Exception as e:
        return {"message": e}

    return {"message": "Success!", "next_pills": next_pills}
