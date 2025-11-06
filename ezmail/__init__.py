"""EZMail package initialization module.

This package provides a high-level Python interface for sending and managing
emails using SMTP and IMAP. It includes tools for composing, sending, and
retrieving emails with support for HTML templates, inline images, and file
attachments.

Modules:
    sender (module): Implements the EzSender class for composing and sending emails via SMTP.
    reader (module): Implements the EzReader class for reading and managing emails via IMAP.
    mail (module): Defines the EzMail data model representing individual emails.
    utils (module): Provides helper functions for validating templates, images, and configurations.

Example:
    from ezmail import EzSender, EzReader

    # Sending an email
    smtp = {"server": "smtp.domain.com", "port": 587}
    sender = {"email": "me@domain.com", "password": "secret"}

    with EzSender(smtp, sender) as ez:
        ez.subject = "Hello!"
        ez.add_text("<p>This is a test email.</p>")
        ez.send("recipient@domain.com")

    # Reading unread emails
    imap = {"server": "imap.domain.com", "port": 993}
    account = {"email": "me@domain.com", "auth_value": "secret", "auth_type": "password"}

    with EzReader(imap, account) as reader:
        emails = reader.fetch_unread(limit=5)
        for mail in emails:
            print(mail.subject)
"""

from .ezsender import EzSender
from .ezreader import EzReader
from .ezmail import EzMail

__all__ = ["EzSender", "EzReader", "EzMail"]
