import hashlib

import motor.motor_asyncio
import requests
import uvicorn
from fastapi import FastAPI, File, HTTPException
from typing_extensions import Annotated

from models import eventModel, verdictModel, eventResponseModel

app = FastAPI()

client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://root:example@localhost:27017")
db = client["data"]
verdicts = db["verdicts"]

blackbox_path = 'https://beta.nimbus.bitdefender.net/liga-ac-labs-cloud/blackbox-scanner/'


@app.post("/events")
async def events(event: eventModel) -> eventResponseModel:
    fileVerdict = verdictModel(hash=event.file.file_hash, risk_level=-1)
    processVerdict = verdictModel(hash=event.file.file_hash, risk_level=-1)

    fileVerdictLookup = await verdicts.find_one({"hash": event.file.file_hash})
    processVerdictLookup = await verdicts.find_one({"hash": event.last_access.hash})

    if fileVerdictLookup is not None:
        fileVerdict.risk_level = fileVerdictLookup["risk_level"]
    if processVerdictLookup is not None:
        processVerdict.risk_level = processVerdictLookup["risk_level"]

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
        response = requests.post(blackbox_path, files={"file":("aaa.txt",file)}).json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    print(response)
    model = verdictModel(hash=file_hash, risk_level=response['risk_level'])
    verdicts.insert_one(model.dict())

    return model


if __name__ == '__main__':
    uvicorn.run(app,port=8000,host='0.0.0.0')
# See PyCharm help at https://www.jetbrains.com/help/pycharm/
