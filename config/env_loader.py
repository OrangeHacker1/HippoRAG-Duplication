# config/env_loader.py

import os
from dotenv import load_dotenv


def load_environment():
    load_dotenv()

    env = {
        "teacher_base": os.getenv("TEACHER_BASE_URL"),
        "teacher_model": os.getenv("TEACHER_MODEL"),
        "teacher_key": os.getenv("TEACHER_API_KEY"),
    }

    for key, value in env.items():
        if value is None:
            raise ValueError(f"Missing environment variable: {key}")

    return env