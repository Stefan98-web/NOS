import http from 'k6/http';

function randomFloat(min, max) {
  return Math.random() * (max - min) + min;
}

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

export default function () {
  const payload = JSON.stringify({
    device_id: `sensor${randomInt(1, 10)}`,
    temperature: randomFloat(15, 30).toFixed(2),
    humidity: randomInt(30, 80),
    pressure: randomInt(990, 1030),
    co2: randomInt(350, 1000),
    light: randomInt(100, 1000),
    noise: randomInt(20, 90),
    battery: randomInt(10, 100)
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  http.post('http://127.0.0.1:53200/iot-data', payload, params); //use minikube tunnel to iot-service
}