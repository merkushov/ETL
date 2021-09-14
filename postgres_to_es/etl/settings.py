import pydantic

class Settings(pydantic.BaseSettings):
    start_date: str = '2000-01-01 00:00:00'
    sleep_time: int = 20    # sec

settings = Settings()