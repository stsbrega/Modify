from pydantic import BaseModel


class StatsResponse(BaseModel):
    modlists_generated: int
    games_supported: int
