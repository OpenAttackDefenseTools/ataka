from pydantic import BaseModel


class FlagSubmission(BaseModel):
    flags: str
