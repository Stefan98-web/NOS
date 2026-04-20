from fastapi import FastAPI, HTTPException
import psycopg2
import pika
import json
import threading
import time

app = FastAPI()

conn = psycopg2.connect(
    host="postgres-analytics",
    database="analyticsdb",
    user="user",
    password="pass"
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS analytics(
id SERIAL PRIMARY KEY,
device_id TEXT,
avg_temperature FLOAT,
avg_humidity FLOAT,
avg_pressure FLOAT,
max_co2 FLOAT,
max_noise FLOAT,
min_battery FLOAT,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()


def consume():
    while True:
        try:
            connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='rabbitmq')
            )
            channel = connection.channel()
            channel.queue_declare(queue='iot.analytics', durable=True)
            print("Connected to RabbitMQ")
            break
        except pika.exceptions.AMQPConnectionError:
            print("RabbitMQ not ready, retrying...")
            time.sleep(5)      

    def callback(ch,method,properties,body):

        data = json.loads(body.decode())

        cursor.execute("""
        INSERT INTO analytics
        (device_id,avg_temperature,avg_humidity,avg_pressure,max_co2,max_noise,min_battery)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,(
            data["device_id"],
            data["avg_temperature"],
            data["avg_humidity"],
            data["avg_pressure"],
            data["max_co2"],
            data["max_noise"],
            data["min_battery"]
        ))

        conn.commit()

    channel.basic_consume(
        queue='iot.analytics',
        on_message_callback=callback,
        auto_ack=True
    )

    channel.start_consuming()


threading.Thread(target=consume, daemon=True).start()


@app.get("/analytics")
def get_data():
    cursor.execute("SELECT * FROM analytics")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns,row)) for row in rows]

@app.get("/analytics/search")
def search_analytics(
    device_id: str | None = None,
    min_temp: float | None = None,
    max_co2: float | None = None,
    min_battery: float | None = None
):

    query = "SELECT * FROM analytics WHERE 1=1"
    params = []

    if device_id:
        query += " AND device_id=%s"
        params.append(device_id)

    if min_temp:
        query += " AND avg_temperature >= %s"
        params.append(min_temp)

    if max_co2:
        query += " AND max_co2 <= %s"
        params.append(max_co2)

    if min_battery:
        query += " AND min_battery >= %s"
        params.append(min_battery)

    cursor.execute(query, params)
    rows = cursor.fetchall()

    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns,row)) for row in rows]
