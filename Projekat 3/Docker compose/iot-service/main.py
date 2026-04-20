from fastapi import FastAPI, HTTPException
import psycopg2
from psycopg2 import pool
import pika
import json
import asyncio
import os

app = FastAPI()

# --- DB
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres-iot")
POSTGRES_DB = os.getenv("POSTGRES_DB", "iotdb")
POSTGRES_USER = os.getenv("POSTGRES_USER", "user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "pass")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))

# --- RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "iot.analytics")

# --- Connection pool for PostgreSQL ---
db_pool = pool.SimpleConnectionPool(1, 20,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
    host=POSTGRES_HOST,
    port=POSTGRES_PORT,
    database=POSTGRES_DB
)

conn = db_pool.getconn()
with conn.cursor() as cursor:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data(
            id SERIAL PRIMARY KEY,
            device_id TEXT,
            temperature FLOAT,
            humidity FLOAT,
            pressure FLOAT,
            co2 FLOAT,
            light FLOAT,
            noise FLOAT,
            battery FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
conn.commit()
db_pool.putconn(conn)

@app.post("/iot-data")
def add_data(data: dict):
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO sensor_data
                (device_id,temperature,humidity,pressure,co2,light,noise,battery)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """,(
                data["device_id"],
                data["temperature"],
                data["humidity"],
                data["pressure"],
                data["co2"],
                data["light"],
                data["noise"],
                data["battery"]
            ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_pool.putconn(conn)

    return {"status": "stored"}

async def aggregation_worker(interval: int = 5):
    while True:
        await asyncio.sleep(interval)
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT device_id,
                           AVG(temperature),
                           AVG(humidity),
                           AVG(pressure),
                           MAX(co2),
                           MAX(noise),
                           MIN(battery)
                    FROM sensor_data
                    GROUP BY device_id
                """)
                results = cursor.fetchall()
        finally:
            db_pool.putconn(conn)

        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            channel = connection.channel()
            channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)

            for r in results:
                message = {
                    "device_id": r[0],
                    "avg_temperature": r[1] or 0,
                    "avg_humidity": r[2] or 0,
                    "avg_pressure": r[3] or 0,
                    "max_co2": r[4] or 0,
                    "max_noise": r[5] or 0,
                    "min_battery": r[6] or 0
                }
                channel.basic_publish(
                    exchange='',
                    routing_key=RABBITMQ_QUEUE,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(
                        delivery_mode=1
                    )
                )
            connection.close()
        except Exception as e:
            print(f"RabbitMQ send error: {e}")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(aggregation_worker(interval=5))

@app.get("/iot-data")
def read_data():
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM sensor_data")
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns,row)) for row in rows]
    finally:
        db_pool.putconn(conn)

@app.get("/iot-data-sensorID")
def get_data(sensor_id: str | None = None):
    if not sensor_id:
        raise HTTPException(status_code=404, detail="Specify sensor ID")
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM sensor_data WHERE device_id = %s", (sensor_id,))
            rows = cursor.fetchall()
            if not rows:
                raise HTTPException(status_code=400, detail="Sensor with specified ID not found")
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    finally:
        db_pool.putconn(conn)