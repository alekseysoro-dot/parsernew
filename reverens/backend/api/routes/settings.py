from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.db import get_db
from api.models import NotificationSettings
from api.schemas import SettingsOut, SettingsUpdate

router = APIRouter()


def _get_or_create_settings(db: Session) -> NotificationSettings:
    settings = db.query(NotificationSettings).first()
    if not settings:
        settings = NotificationSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("/settings", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    return _get_or_create_settings(db)


@router.put("/settings", response_model=SettingsOut)
def update_settings(body: SettingsUpdate, db: Session = Depends(get_db)):
    settings = _get_or_create_settings(db)
    settings.email = body.email
    settings.tg_chat_id = body.tg_chat_id
    settings.threshold = body.threshold
    db.commit()
    db.refresh(settings)
    return settings
