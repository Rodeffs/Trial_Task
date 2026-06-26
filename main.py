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


def round_to_15(period: list):
    period_rounded = []

    for stamp in period:
        hour_str, minute_str = stamp.split(':')
        hour, minute = int(hour_str), int(minute_str)

        if hour < 8 or (hour >= 22 and minute > 0):
            raise ValueError("Time period must be within 8:00-22:00")

        if minute < 0 or minute > 59:
            raise ValueError("Incorrect time format")

        if minute % 15 == 0:  # если кратно 15 минутам, то просто добавляем как есть
            period_rounded.append(stamp)

        else:
            minute += 15 - minute % 15  # округление до 15 минут

            if minute == 60:
                hour_str = str(hour + 1) if hour >= 9 else '0' + str(hour + 1)  # чтобы добавить 0 перед часом, нужно для сортировки
                period_rounded.append(hour_str + ":00")  # добавили час

            else:
                period_rounded.append(hour_str + ':' + str(minute))

    return period_rounded


@app.post("/schedule")
def add_schedule(data: dict, con: sqlite3.Connection = Depends(get_db)):
    cur = con.cursor()

    try:  # получаем период времени, а также название таблетки и id пациента
        time_period = round_to_15(data["time_period"])
        pill_name, user_id = data["pill_name"], data["user_id"]

    except Exception as e:
        return {"message": str(e)}

    try:  # если указан период принятия лекарства в днях, что вводим его тоже
        duration_days = data["duration_days"]

        schedule_id = cur.execute(f"""
            INSERT INTO schedule(pill_name, duration_days, user_id) VALUES
                ('{pill_name}', {duration_days}, {user_id})
            RETURNING schedule_id
        """).fetchone()[0]

        con.commit()

    except KeyError:  # иначе период принятия лекарства NULL, что означает, что таблетку нужно принимать всегда
        schedule_id = cur.execute(f"""
            INSERT INTO schedule(pill_name, user_id) VALUES
                ('{pill_name}', {user_id})
            RETURNING schedule_id
        """).fetchone()[0]

        con.commit()

    try:
        for stamp in time_period:
            cur.execute(f"""
                INSERT INTO time_period VALUES
                    ({schedule_id}, '{stamp}')
            """)
            con.commit()

    except Exception as e:
        return {"message": str(e)}

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

        data = [row[0] for row in data]

    except Exception as e:
        return {"message": str(e)}

    return {"message": "Success!", "schedules_id": data}


@app.get("/schedule")
def get_schedule(schedule_id: int, con: sqlite3.Connection = Depends(get_db)):
    cur = con.cursor()

    try:
        data = cur.execute(f"""
            SELECT pill_name, duration_days
            FROM schedule
            WHERE schedule_id={schedule_id}
        """).fetchone()

        pill_info = {"pill_name": data[0], "duration_days": data[1]}

        time_period = cur.execute(f"""
            SELECT time_stamp
            FROM time_period
            WHERE schedule_id={schedule_id}
            ORDER BY time_stamp
        """).fetchall()

        time_period = [row[0] for row in time_period]

    except Exception as e:
        return {"message": str(e)}

    return {"message": "Success!", "pill_info": pill_info, "time_period": time_period}


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

            if 0 <= stamp_minute - minutes_now <= closest_next_taking:
                next_pills.append((stamp, pill_name))

    except Exception as e:
        return {"message": str(e)}

    return {"message": "Success!", "next_pills": next_pills}
