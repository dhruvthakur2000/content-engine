from pydantic import BaseModel
from typing import Optional


class ContentRequest(BaseModel):
    """
    incoming request to generate content 
    
    """

    project_name: Optional[str] = "Saletech"

    #freeform notes
    notes: str 
     
    #git commit log history
    git_log: Optional[str] = None

    #platform type
    platform:str = "linkedinn"


class ContentResponse(BaseModel):
    """
    API response containning generated content 
    """

    platform: str
    generated_post: str