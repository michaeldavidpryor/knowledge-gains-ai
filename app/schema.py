from typing import List, Optional
from pydantic import BaseModel, Field, computed_field


class Exercise(BaseModel):
    name: str
    sets: int
    reps: str
    # Use abbreviated muscle groups name. i.e. "triceps" instead of "triceps brachii" and "glutes" instead of "gluteus maximus".
    muscle_targeted: str
    # A url to a video demonstrating the proper technique of the exercise
    exercise_example: str
    rir: Optional[int] = Field(default=2)

    @computed_field
    @property
    def export_muscle_targeted(self) -> str:
        return self.muscle_targeted


class DayPlan(BaseModel):
    # days start at 1

    day: int
    exercises: List[Exercise]
    muscles_targeted: List[str]

    @computed_field
    def export_muscle_targeted(self) -> list[str]:
        return self.muscles_targeted


class WeekPlan(BaseModel):
    # weeks start at 1
    week: int
    days: List[DayPlan]


class Program(BaseModel):
    title: str
    summary: str
    weeks: List[WeekPlan]
