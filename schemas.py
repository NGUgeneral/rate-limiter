from pydantic import BaseModel, Field
from typing import Optional

class RateCheckRequest(BaseModel):
    access_key: Optional[str] = Field(
        None, 
        description="The authenticated identification token extracted from the JWT."
    )
    ip_key: str = Field(
        ..., 
        description="The resolved public client IP address passed explicitly by the edge service."
    )
    limit: Optional[int] = Field(
        None, 
        gt=0, 
        description="Dynamic request ceiling. Required if access_key is present."
    )
    window: Optional[int] = Field(
        None, 
        gt=0, 
        description="Sliding window duration in seconds. Required if access_key is present."
    )

    model_config = {
        "populate_by_name": True
    }