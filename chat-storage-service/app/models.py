from pydantic import BaseModel

class ResponsePayload(BaseModel):
    prompt: str
    response: str
