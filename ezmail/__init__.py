"""EZMail package initialization module.

This package provides a high-level Python interface for sending and
managing emails using SMTP and (in future versions) IMAP. It includes
features for building messages with text, HTML templates, inline
images, and file attachments.

Modules:
    core (module): Implements the main email sending and reading classes.
    utils (module): Provides validation helpers for files and templates.

Example:
    from ezmail import Ezmail

    smtp = {"server": "smtp.domain.com", "port": 587}
    sender = {"email": "me@domain.com", "password": "secret"}

    ez = Ezmail(smtp, sender)
    ez.subject = "Hello!"
    ez.add_text("<p>This is a test email.</p>")
    ez.send("recipient@domain.com")
"""

from .core import Ezmail

__all__ = ["Ezmail"]
