from fastapi import FastAPI, HTTPException
import psycopg2
import pika
import json
import time

app = FastAPI()

conn = psycopg2.connect(
    host="postgres-iot",
    database="iotdb",
    user="user",
    password="pass"
)

cursor = conn.cursor()

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

while True:
    try:
        rabbit = pika.BlockingConnection(
            pika.ConnectionParameters(host='rabbitmq')
        )
        channel = rabbit.channel()
        channel.queue_declare(queue='iot.analytics')
        print("Connected to RabbitMQ")
        break
    except pika.exceptions.AMQPConnectionError:
        print("RabbitMQ not ready, retrying...")
        time.sleep(5)


@app.post("/iot-data")
def add_data(data: dict):

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

    cursor.execute("""
    SELECT AVG(temperature),
           AVG(humidity),
           AVG(pressure),
           MAX(co2),
           MAX(noise),
           MIN(battery)
    FROM sensor_data
    WHERE device_id=%s
    """,(data["device_id"],))

    result = cursor.fetchone()

    message = {
        "device_id": data["device_id"],
        "avg_temperature": result[0],
        "avg_humidity": result[1],
        "avg_pressure": result[2],
        "max_co2": result[3],
        "max_noise": result[4],
        "min_battery": result[5]
    }

    connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='rabbitmq')
    )

    channel = connection.channel()
    channel.queue_declare(queue='iot.analytics')

    channel.basic_publish(
        exchange='',
        routing_key='iot.analytics',
        body=json.dumps(message)
    )

    connection.close()

    return {"status":"stored and aggregated"}


@app.get("/iot-data")
def read_data():
    cursor.execute("SELECT * FROM sensor_data")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    result = []

    for row in rows:
        result.append(dict(zip(columns,row)))

    return result

@app.get("/iot-data-sensorID")
def get_data(sensor_id: str | None = None):

    if sensor_id:
        query = "SELECT * FROM sensor_data WHERE device_id = %s"
        params = (sensor_id,)
    else:
        raise HTTPException(status_code=404, detail="Specify sensor ID")

    cursor.execute(query, params)
    rows = cursor.fetchall()

    if not rows:
        raise HTTPException(status_code=400, detail="Sensor with specified ID not found")

    columns = [desc[0] for desc in cursor.description]

    return [dict(zip(columns, row)) for row in rows]
