from pydantic import BaseModel

class ExampleSchema(BaseModel):
    name: str
    value: int
