import hashlib

import fastapi
import motor.motor_asyncio
from fastapi import FastAPI, File, Form, UploadFile
from typing_extensions import Annotated

from models import eventModel, verdictModel, eventResponseModel

app = FastAPI()

client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://root:example@localhost:27017")
db = client["data"]
verdicts = db["verdicts"]

@app.post("/events")
async def events(event : eventModel):
    fileVerdict = verdictModel(hash = event.file.file_hash,risk_level = -1)
    processVerdict = verdictModel(hash = event.file.file_hash,risk_level = -1)

    fileVerdictLookup = await verdicts.find_one({"hash":event.file.file_hash})
    processVerdictLookup = await verdicts.find_one({"hash":event.last_access.hash})

    if fileVerdictLookup is not None:
        fileVerdict.risk_level = fileVerdictLookup["risk_level"]
    if processVerdictLookup is not None:
        processVerdict.risk_level = processVerdictLookup["risk_level"]

    return eventResponseModel(file = fileVerdict, process= processVerdict)


def validateFile(file) -> bool:
    pass

@app.post("/scanFile")
async def scanFile(file: Annotated[bytes, File()]):

    if not validateFile(file):
        return

    file_hash = hashlib.md5(file).hexdigest()
    return file_hash


if __name__ == '__main__':
    pass
# See PyCharm help at https://www.jetbrains.com/help/pycharm/
