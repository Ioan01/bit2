import hashlib
import os

import aio_pika
import motor.motor_asyncio
import redis
import requests
import uvicorn
from aio_pika import ExchangeType, DeliveryMode
from fastapi import FastAPI, File, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from typing_extensions import Annotated

from models import eventModel, verdictModel, eventResponseModel

app = FastAPI()

redis_client = None
if os.getenv('REDIS_URL') is not None:
    redis_client = redis.Redis(host=os.getenv('REDIS_URL'), port=6379, db=0)
else:
    print('Redis not supplied')


async def rabbitmq_exchange():
    # Perform connection
    if os.getenv('RABBIT_URL') is None:
        print('Rabbit not found')
        return None

    connection = await aio_pika.connect(os.getenv('RABBIT_URL'))
    # Creating a channel
    channel = await connection.channel()
    return await channel.declare_exchange(
        "logs", ExchangeType.FANOUT,
    )


logs_exchange = None

connectionString = os.getenv("MONGO_URL") or "mongodb://root:example@localhost:27017"

client = motor.motor_asyncio.AsyncIOMotorClient(connectionString)
db = client["data"]
verdicts = db["verdicts"]

blackbox_path = 'https://beta.nimbus.bitdefender.net/liga-ac-labs-cloud/blackbox-scanner/'


async def findCachedOrQueryRiskLevel(hash: str) -> int:
    if redis_client is not None:
        riskLevel = redis_client.get(hash)
    else:
        riskLevel = None

    if riskLevel is None:
        verdict = await verdicts.find_one({"hash": hash})
        if verdict is not None and redis_client is not None:
            redis_client.set(hash, verdict["risk_level"], 30)
            return verdict["risk_level"]
        return -1

    return int(riskLevel)


@app.post("/events")
async def events(event: eventModel) -> eventResponseModel:
    fileVerdict = verdictModel(hash=event.file.file_hash, risk_level=-1)
    processVerdict = verdictModel(hash=event.file.file_hash, risk_level=-1)

    fileRiskLevel = await findCachedOrQueryRiskLevel(event.file.file_hash)
    processRiskLevel = await findCachedOrQueryRiskLevel(event.last_access.hash)

    fileVerdict.risk_level = fileRiskLevel
    processVerdict.risk_level = processRiskLevel

    global logs_exchange
    if logs_exchange is None:
        logs_exchange = await rabbitmq_exchange()

    response = {}
    message = aio_pika.Message(
        event.json().encode(),
        delivery_mode=DeliveryMode.PERSISTENT,
    )
    if logs_exchange is not None:
        await logs_exchange.publish(message, routing_key="test")

    return eventResponseModel(file=fileVerdict, process=processVerdict)


def validateFile(file) -> bool:
    return True


@app.post("/scanFile")
async def scanFile(file: Annotated[bytes, File()]):
    if not validateFile(file):
        return

    file_hash = hashlib.md5(file).hexdigest()

    verdictLookup = await verdicts.find_one({'hash': file_hash})
    if verdictLookup is not None:
        return verdictModel(hash=file_hash, risk_level=verdictLookup['risk_level'])

    try:
        response = requests.post(blackbox_path, files={"file": ("aaa.txt", file)}).json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    print(response)
    model = verdictModel(hash=file_hash, risk_level=response['risk_level'])
    verdicts.insert_one(model.dict())

    return model


if __name__ == '__main__':
    Instrumentator().instrument(app).expose(app)
    uvicorn.run(app, port=8000, host='0.0.0.0')
# See PyCharm help at https://www.jetbrains.com/help/pycharm/
