from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.models import User
from app.services import role_classifier

router = APIRouter(prefix="/api/ml", tags=["ML"])


@router.get("/info")
def ml_info(user: User = Depends(get_current_user)):
    """Status and real evaluation metrics of the trained role classifier (or 'not trained')."""
    return {"role_classifier": role_classifier.info()}
