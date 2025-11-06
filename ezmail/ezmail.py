from datetime import datetime
from typing import List, Dict, Any

class EzMail:
    """Represents an email message retrieved by EzReader."""

    def __init__(self, uid: int, sender: str, subject: str, body: str, attachments: List[Dict[str, Any]] | None = None, date: datetime | None = None):
        self.uid = uid
        self.sender = sender
        self.subject = subject
        self.body = body
        self.attachments = attachments or []
        self.date = date

    def has_attachments(self) -> bool:
        return bool(self.attachments)

    def summary(self, max_length: int = 80) -> str:
        text = self.body.replace("\n", " ").strip()
        return text if len(text) <= max_length else text[:max_length] + "..."

    def __repr__(self) -> str:
        return f"<EzMail uid={self.uid} from={self.sender!r} subject={self.subject!r} attachments={len(self.attachments)}>"
