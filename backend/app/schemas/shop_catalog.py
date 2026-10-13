from pydantic import BaseModel, ConfigDict, Field


class CommentReq(BaseModel):
    score: int = Field(ge=1, le=5)
    content: str = Field(min_length=1, max_length=1000)

    model_config = ConfigDict(populate_by_name=True)
