from pydantic import BaseModel


class FlagSubmission(BaseModel):
    flags: str

class FlagSubmissionAsync(BaseModel):
    flags: str
    execution_id: str