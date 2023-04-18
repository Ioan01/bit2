from pydantic import BaseModel

class deviceModel(BaseModel):
    id : str
    os : str

class timeModel(BaseModel):
    a : int
    m : int

class lastAccessModel(BaseModel):
    hash : str
    path : str
    pid : int
class fileModel(BaseModel):
    file_hash : str
    file_path : str
    time : timeModel

class eventModel(BaseModel):
    device : deviceModel
    file : fileModel
    last_access : lastAccessModel


class verdictModel(BaseModel):
    hash : str
    risk_level : int

class eventResponseModel(BaseModel):
    file : verdictModel
    process : verdictModel


