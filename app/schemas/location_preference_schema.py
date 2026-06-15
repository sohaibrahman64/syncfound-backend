from pydantic import BaseModel, ConfigDict, Field


class LocationPreferenceAnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    answer_id: int = Field(validation_alias="id")
    answer: str


class LocationPreferenceQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: int = Field(validation_alias="id")
    question: str
    answers: list[LocationPreferenceAnswerResponse]
