from smtplib import SMTP, SMTP_SSL
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email import message_from_bytes
from email.header import decode_header
from mimetypes import guess_type
from uuid import uuid4
from os.path import isfile, basename
from re import sub
from typing import Union
from jinja2 import Template # type: ignore
from time import sleep
from imaplib import IMAP4_SSL
from base64 import b64encode
from typing import List, Dict, Any
from datetime import datetime
from .utils import validate_template, validate_image, validate_path, validate_sender, validate_protocol_config, validate_account


class EzSender:
    """Handles customizable and automated email composition and sending.

    This class provides an easy-to-use interface for creating professional
    emails that include text, HTML templates, inline images, and attachments.
    It automatically manages the SMTP connection, message formatting,
    and MIME handling.

    Example:
        smtp = {"server": "smtp.domain.com", "port": 587}
        sender = {"email": "me@domain.com", "password": "secret"}
        ez = EzSender(smtp, sender)
        ez.subject = "Welcome!"
        ez.add_text("<h1>Hello!</h1><p>Welcome to our platform.</p>")
        ez.add_attachment("report.pdf")
        ez.send("user@domain.com")
    """

    def __init__(self, smtp: dict, sender: dict, max_emails_per_hour: int | None = None):
        """Initializes the EzSender instance with SMTP and sender credentials.

        Args:
            smtp (dict): SMTP configuration with keys:
                - `server` (str): SMTP server hostname or IP.
                - `port` (int): Port used for SMTP connection (default: 587).
            sender (dict): Sender credentials with keys:
                - `email` (str): Sender email address.
                - `password` (str): Sender email password.
        """
        validate_protocol_config(smtp)
        validate_sender(sender)
        
        self.smtp_server = smtp["server"]
        self.smtp_port = smtp["port"]

        self.sender_email = sender["email"]
        self.sender_password = sender["password"]
        
        self.max_emails_per_hour = max_emails_per_hour

        self.subject = None
        self.body = []
        self.attachments = []

    def add_text(self, html: str) -> None:
        """Adds plain text or HTML content to the email body.

        Args:
            html (str): Text or HTML content to be included in the email body.

        Raises:
            ValueError: If `html` is not a string.

        Example:
            add_text("<p>Hello, this is a test message.</p>")
        """
        if not isinstance(html, str):
            raise ValueError("Text must be a string.")
        self.body.append(html)

    def use_template(self, file: str, **variables) -> None:
        """Loads and renders a Jinja2 HTML template into the email body.

        This method allows using dynamic templates with placeholders replaced
        by provided keyword arguments.

        Args:
            file (str): Path to the HTML template file.
            **variables: Key-value pairs for Jinja2 placeholders.

        Raises:
            ValueError: If the file is not a valid HTML template.
            FileNotFoundError: If the file does not exist.

        Example:
            use_template("templates/welcome.html", name="John", version="1.0.0")
        """
        validate_template(file)

        with open(file, "r", encoding="utf-8") as f:
            html = Template(f.read()).render(**variables)
        self.add_text(html)

    def add_image(self, image_path: str, width: str = None, height: str = None, cid: str = None) -> None:
        """Adds an inline image to the email body.

        Args:
            image_path (str): Path to the image file.
            width (str, optional): Width of the image (e.g., `"200px"`, `"50%"`).
            height (str, optional): Height of the image.
            cid (str, optional): Content-ID for referencing in the HTML template.

        Raises:
            ValueError: If the image path is invalid.
            FileNotFoundError: If the image does not exist.

        Example:
            add_image("logo.png", width="200px", cid="logo_cid")
        """
        validate_image(image_path)

        self.body.append(
            {"image": image_path, "width": width, "height": height, "cid": cid}
        )

    def add_attachment(self, attachment_path: str) -> None:
        """Adds an attachment file to the email.

        Args:
            attachment_path (str): Path to the file to be attached.

        Raises:
            ValueError: If the path is invalid.
            FileNotFoundError: If the file does not exist.

        Example:
            add_attachment("reports/monthly_report.pdf")
        """
        validate_path(attachment_path)
        self.attachments.append(attachment_path)

    def clear_body(self) -> None:
        """Clears the current email body content.

        This allows starting a new message composition while preserving
        the current SMTP and sender configurations.

        Example:
            clear_body()
        """
        self.body = []

    def clear_attachments(self) -> None:
        """Clears all attachments from the email.

        Example:
            clear_attachments()
        """
        self.attachments = []

    def _connect(self) -> Union[SMTP, SMTP_SSL]:
        """Establishes an authenticated SMTP connection.

        Automatically determines whether to use a secure (SSL) or
        standard (STARTTLS) connection based on the configured port.

        Returns:
            Union[SMTP, SMTP_SSL]: Authenticated SMTP connection object.

        Raises:
            RuntimeError: If connection or authentication fails.
        """
        conn = SMTP if self.smtp_port == 587 else SMTP_SSL
        smtp = conn(self.smtp_server, self.smtp_port, timeout=30)

        if self.smtp_port != 465:
            smtp.starttls()

        smtp.login(self.sender_email, self.sender_password)
        return smtp

    def _build_body(self) -> tuple[str, list[MIMEImage]]:
        """Builds the full HTML body and inline images for the email.

        Returns:
            tuple[str, list[MIMEImage]]: A tuple containing:
                - The unified HTML string.
                - A list of inline `MIMEImage` objects.
        """
        html_parts = []
        inline_images = []

        for block in self.body:
            if isinstance(block, str):
                html_parts.append(block)
            elif isinstance(block, dict) and "image" in block:
                path = block["image"]
                if isfile(path):
                    cid = (
                        block.get("cid")
                        if block.get("cid")
                        else f"img{uuid4().hex[:8]}"
                    )
                    width = block.get("width")
                    height = block.get("height")

                    style = ""
                    if width or height:
                        style = ' style="'
                        if width:
                            style += f"width:{width};"
                        if height:
                            style += f"height:{height};"
                        style += '"'

                    if not block.get("cid"):
                        html_parts.append(f'<br><img src="cid:{cid}"{style}><br>')

                    with open(path, "rb") as img_file:
                        mime_type, _ = guess_type(path)
                        if mime_type and mime_type.startswith("image/"):
                            mime_img = MIMEImage(
                                img_file.read(), _subtype=mime_type.split("/")[1]
                            )
                            mime_img.add_header("Content-ID", f"<{cid}>")
                            mime_img.add_header(
                                "Content-Disposition", "inline", filename=basename(path)
                            )
                            inline_images.append(mime_img)

        unified_body = "".join(html_parts)
        return unified_body, inline_images

    def send(self, recipients: str | list[str]) -> dict:
        """Builds and sends the email to one or more recipients.

        Combines all text, HTML, images, and attachments into a complete MIME
        message and sends each email individually.

        Args:
            recipients (str | list[str]): Single email address or list of addresses.

        Returns:
            dict: Summary of send results:
                - `"sent"` (list): Successfully delivered addresses.
                - `"failed"` (dict): Failed addresses with error messages.

        Raises:
            RuntimeError: If unable to prepare or connect to the SMTP server.

        Example:
            send(["user1@domain.com", "user2@domain.com"])
        """
        if not isinstance(recipients, (list, tuple)):
            recipients = [recipients]

        result = {"sent": [], "failed": {}}

        try:
            with self._connect() as smtp:
                unified_body, inline_images = self._build_body()
                emails_sent = 0

                for recipient in recipients:
                    try:
                        message = MIMEMultipart("mixed")
                        message["From"] = self.sender_email
                        message["To"] = recipient
                        message["Subject"] = self.subject or ""

                        alt = MIMEMultipart("alternative")

                        plain_text = sub(r"<[^>]+>", "", unified_body)
                        plain_text = (
                            sub(r"\s+", " ", plain_text).strip()
                            or "Content not available."
                        )

                        alt.attach(MIMEText(plain_text, "plain"))
                        alt.attach(MIMEText(unified_body, "html"))
                        message.attach(alt)

                        for img in inline_images:
                            message.attach(img)

                        for attachment_path in self.attachments:
                            if isfile(attachment_path):
                                with open(attachment_path, "rb") as f:
                                    file_name = basename(attachment_path)
                                    mime_type, _ = guess_type(attachment_path)
                                    main_type, sub_type = (mime_type.split("/", 1) if mime_type else ("application", "octet-stream"))

                                    if main_type == "text":
                                        mime_attachment = MIMEText(f.read().decode("utf-8", errors="ignore"), _subtype=sub_type)
                                    elif main_type == "image":
                                        mime_attachment = MIMEImage(f.read(), _subtype=sub_type)
                                    elif main_type == "audio":
                                        mime_attachment = MIMEAudio(f.read(), _subtype=sub_type)
                                    else:
                                        mime_attachment = MIMEApplication(f.read(), _subtype=sub_type)

                                    mime_attachment.add_header("Content-Disposition", "attachment", filename=file_name)
                                    message.attach(mime_attachment)

                        smtp.sendmail(
                            self.sender_email, [recipient], message.as_string()
                        )
                        result["sent"].append(recipient)
                        emails_sent += 1
                        
                        if self.max_emails_per_hour and emails_sent == self.max_emails_per_hour:
                            sleep(3600)

                    except Exception as e:
                        result["failed"][recipient] = str(e)

        except Exception as e:
            raise RuntimeError(f"Failed to prepare or connect to the SMTP server: {e}")

        return result

class EzMail:
    """Represents an email message retrieved by EzReader.

    Each instance contains metadata, body content, and in-memory attachments.
    """

    def __init__(self, sender: str, subject: str, body: str, attachments: List[Dict[str, Any]] | None = None, date: datetime | None = None):
        self.sender = sender
        self.subject = subject
        self.body = body
        self.attachments = attachments or []
        self.date = date

    def has_attachments(self) -> bool:
        """Checks whether the email contains any attachments."""
        return bool(self.attachments)

    def summary(self, max_length: int = 80) -> str:
        """Returns a short text summary of the email body."""
        text = self.body.replace("\n", " ").strip()
        return text if len(text) <= max_length else text[:max_length] + "..."

    def __repr__(self) -> str:
        return f"<EzMail from={self.sender!r} subject={self.subject!r} attachments={len(self.attachments)}>"

class EzReader:
    """Handles reading and managing emails via the IMAP protocol.

    This class provides a unified and extensible interface for connecting to
    an IMAP server using either traditional password authentication or OAuth2
    access tokens. It allows listing mailboxes, fetching unread emails, and
    reading message details.

    Example:
        imap = {"server": "imap.gmail.com", "port": 993}
        account = {
            "email": "user@gmail.com",
            "auth_value": "SENHA_OU_TOKEN",
            "auth_type": "password"
        }

        reader = EzReader(imap, account)
        reader.connect()
        emails = reader.fetch_unread(limit=5)
        reader.disconnect()
    """

    def __init__(self, imap: dict, account: dict):
        """Initializes the EzReader instance with IMAP and authentication details.

        Args:
            imap (dict): IMAP configuration with keys:
                - `server` (str): IMAP server hostname or IP.
                - `port` (int): IMAP port number (default: 993).
            account (dict): Email credentials with keys:
                - `email` (str): Email address to connect with.
                - `auth_value` (str): Password or OAuth2 access token.
                - `auth_type` (str): "password" or "oauth2".

        Raises:
            ValueError: If required parameters are missing or invalid.
        """
        validate_protocol_config(imap)
        validate_account(account)

        self.imap_server = imap["server"]
        self.imap_port = imap["port"]
        
        self.user_email = account["email"]
        self.auth_value = account["auth_value"]
        self.auth_type = account["auth_type"]

        self.mail = None

    def _generate_oauth2_string(self, user_email: str, access_token: str) -> bytes:
        """Generates the IMAP OAuth2 authentication string.

        Args:
            user_email (str): Email address of the user.
            access_token (str): OAuth2 access token.

        Returns:
            bytes: Encoded OAuth2 authentication string.
        """
        auth_string = f"user={user_email}\1auth=Bearer {access_token}\1\1"
        return b64encode(auth_string.encode("utf-8"))

    def connect(self) -> None:
        """Establishes an authenticated IMAP connection.

        This method connects securely via SSL and authenticates using either
        password or OAuth2 token based on the chosen authentication type.

        Raises:
            RuntimeError: If connection or authentication fails.
            ValueError: If the authentication type is invalid.
        """
        try:
            self.mail = IMAP4_SSL(self.imap_server, self.imap_port)

            if self.auth_type == "password":
                self.mail.login(self.user_email, self.auth_value)
            elif self.auth_type == "oauth2":
                auth_string = self._generate_oauth2_string(self.user_email, self.auth_value)
                self.mail.authenticate("XOAUTH2", lambda x: auth_string)
            else:
                raise ValueError("Invalid authentication type. Use 'password' or 'oauth2'.")

        except Exception as e:
            raise RuntimeError(f"Failed to connect or authenticate to IMAP server: {e}")

    def list_mailboxes(self) -> List[str]:
        """Lists all available mailboxes (folders) for the connected account.

        Returns:
            List[str]: List of mailbox names.

        Raises:
            RuntimeError: If unable to list mailboxes or not connected.
        """
        if not self.mail:
            raise RuntimeError("Not connected to any IMAP server.")

        try:
            status, mailboxes = self.mail.list()
            if status != "OK":
                raise RuntimeError("Unable to retrieve mailbox list.")
            return [box.decode().split(' "/" ')[-1] for box in mailboxes]
        except Exception as e:
            raise RuntimeError(f"Failed to list mailboxes: {e}")
    
    def fetch_messages(
        self,
        mailbox: str = "INBOX",
        limit: int | None = None,
        status: str = "ALL",
        sender: str | None = None,
        subject: str | None = None,
        text: str | None = None,
        body: str | None = None,
        date: str | None = None,
        since: str | None = None,
        before: str | None = None,
    ) -> List[EzMail]:
        """Lists and retrieves emails from the specified mailbox using flexible IMAP filters.

        This method provides a generalized way to search and fetch emails with multiple
        optional filters such as status (`ALL`, `SEEN`, `UNSEEN`), sender, subject, text,
        body content, or date-based constraints (`SINCE`, `BEFORE`, `ON`).

        Each message is returned as an `EzMail` instance, which includes metadata,
        message content, and attachments loaded in memory (not saved to disk).

        Args:
            mailbox (str, optional): Mailbox (folder) name to search. Defaults to `"INBOX"`.
            limit (int | None, optional): Maximum number of emails to fetch. Defaults to `None`.
            status (str, optional): IMAP status filter, e.g., `"ALL"`, `"UNSEEN"`, or `"SEEN"`. Defaults to `"ALL"`.
            sender (str, optional): Filters emails from a specific sender. Defaults to `None`.
            subject (str, optional): Filters emails containing the given subject text. Defaults to `None`.
            text (str, optional): Searches for a keyword in the subject and body. Defaults to `None`.
            body (str, optional): Searches for a keyword only in the message body. Defaults to `None`.
            date (str, optional): Fetches emails from a specific date (`"DD-MMM-YYYY"`). Defaults to `None`.
            since (str, optional): Fetches emails sent on or after a date (`"DD-MMM-YYYY"`). Defaults to `None`.
            before (str, optional): Fetches emails sent before a date (`"DD-MMM-YYYY"`). Defaults to `None`.

        Returns:
            list[EzMail]: A list of `EzMail` objects containing:
                - `sender` (str): Sender's name and address.
                - `subject` (str): Email subject (decoded).
                - `body` (str): Plain text body of the message.
                - `attachments` (list): List of attachments (not saved), each with:
                    - `filename` (str): File name.
                    - `content_type` (str): MIME type.
                    - `data` (bytes): Raw binary content.

        Raises:
            RuntimeError: If not connected, search fails, or message parsing fails.

        Example:
            >>> emails = reader.fetch_messages(status="UNSEEN", since="01-Oct-2025")
            >>> for mail in emails:
            ...     print(mail.subject, len(mail.attachments))
        """
        if not self.mail:
            raise RuntimeError("Not connected to any IMAP server.")

        # Build IMAP search criteria dynamically
        criteria = f"({status}"
        if sender:
            criteria += f' FROM "{sender}"'
        if subject:
            criteria += f' SUBJECT "{subject}"'
        if text:
            criteria += f' TEXT "{text}"'
        if body:
            criteria += f' BODY "{body}"'
        if date:
            criteria += f' ON {date}'
        if since:
            criteria += f' SINCE {since}'
        if before:
            criteria += f' BEFORE {before}'
        criteria += ")"

        try:
            self.mail.select(mailbox)
            status_code, data = self.mail.search(None, criteria)

            if status_code != "OK":
                raise RuntimeError(f"Failed to search emails with criteria: {criteria}")

            ids = data[0].split()
            if limit:
                ids = ids[:limit]

            emails = []
            for msg_id in ids:
                status_fetch, msg_data = self.mail.fetch(msg_id, "(RFC822)")
                if status_fetch != "OK" or not msg_data:
                    continue

                msg = message_from_bytes(msg_data[0][1])

                # Decode subject
                subject_raw, enc = decode_header(msg["Subject"] or "")[0]
                if isinstance(subject_raw, bytes):
                    subject_decoded = subject_raw.decode(enc or "utf-8", errors="ignore")
                else:
                    subject_decoded = subject_raw

                sender_decoded = msg.get("From", "")
                body_content = ""
                attachments = []

                # Walk through all parts of the message
                for part in msg.walk():
                    content_disposition = str(part.get("Content-Disposition", "")).lower()
                    content_type = part.get_content_type()

                    if part.is_multipart():
                        continue

                    # Body (text/plain)
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        try:
                            body_content = part.get_payload(decode=True).decode(errors="ignore")
                        except Exception:
                            continue

                    # Attachment
                    filename = part.get_filename()
                    if filename:
                        try:
                            file_data = part.get_payload(decode=True)
                            attachments.append({
                                "filename": filename,
                                "content_type": content_type,
                                "data": file_data,
                            })
                        except Exception:
                            continue

                emails.append(EzMail(
                    sender=sender_decoded,
                    subject=subject_decoded,
                    body=body_content.strip(),
                    attachments=attachments
                ))

            return emails

        except Exception as e:
            raise RuntimeError(f"Failed to fetch emails with the criteria {criteria}: {e}")

    def fetch_unread(self, mailbox: str = "INBOX", limit: int | None = None) -> List[Dict[str, Any]]:
        """Fetches unread emails from the specified mailbox.

        Args:
            mailbox (str): Mailbox to fetch from (default: "INBOX").
            limit (int, optional): Maximum number of emails to retrieve.

        Returns:
            List[Dict[str, Any]]: List of unread email metadata, including:
                - `from` (str): Sender.
                - `subject` (str): Email subject.
                - `body` (str): Plaintext body (if available).

        Raises:
            RuntimeError: If unable to fetch emails or not connected.
        """

        emails = self.fetch_messages(mailbox=mailbox, status="UNSEEN", limit=limit)
        return emails

    def disconnect(self) -> None:
        """Closes the IMAP connection safely.

        Example:
            disconnect()
        """
        try:
            if self.mail:
                self.mail.close()
                self.mail.logout()
        except Exception:
            pass