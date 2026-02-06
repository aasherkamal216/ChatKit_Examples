# app/types.py
from dataclasses import dataclass

@dataclass
class RequestContext:
    user_id: str