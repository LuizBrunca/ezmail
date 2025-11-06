from smtplib import SMTP, SMTP_SSL
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from mimetypes import guess_type
from uuid import uuid4
from os.path import isfile, basename
from re import sub
from jinja2 import Template
from time import sleep
from typing import Union, List
from .utils import validate_template, validate_image, validate_path, validate_sender, validate_protocol_config


class EzSender:
    """High-level SMTP helper for composing and sending emails.

    Provides a simple interface to build professional emails with text/HTML,
    inline images, and attachments. Manages SMTP connection (context manager
    friendly), MIME assembly, and optional rate limiting.

    Example:
        smtp = {"server": "smtp.domain.com", "port": 587}
        sender = {"email": "me@domain.com", "password": "secret"}

        with EzSender(smtp, sender) as ez:
            ez.subject = "Welcome!"
            ez.add_text("<h1>Hello!</h1><p>Welcome to our platform.</p>")
            ez.add_attachment("report.pdf")
            ez.send(["user@domain.com"])
    """

    def __init__(self, smtp: dict, sender: dict, max_emails_per_hour: int | None = None):
        """Initialize the EzSender with SMTP config and sender credentials.

        Args:
            smtp (dict): SMTP configuration.
                - server (str): SMTP hostname or IP.
                - port (int): Server port (587 STARTTLS, 465 SSL, others as configured).
            sender (dict): Sender credentials.
                - email (str): Sender email address.
                - password (str): Sender email password (or app password).
            max_emails_per_hour (int | None): Optional throttle to limit sent emails/hour.

        Raises:
            ValueError: If configuration/credentials are missing or invalid.
        """
        validate_protocol_config(smtp)
        validate_sender(sender)

        self.smtp_server = smtp["server"]
        self.smtp_port = smtp["port"]

        self.sender_email = sender["email"]
        self.sender_password = sender["password"]

        self.max_emails_per_hour = max_emails_per_hour

        self.subject: str | None = None
        self.body: list[str | dict] = []
        self.attachments: list[str] = []

    def __enter__(self):
        """Open an SMTP connection for use in a `with` block.

        Returns:
            EzSender: The instance with an active SMTP connection.
        """
        self._smtp_conn = self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Ensure SMTP disconnection when leaving the context."""
        try:
            if hasattr(self, "_smtp_conn") and self._smtp_conn:
                self._smtp_conn.quit()
        except Exception:
            pass

    def connect(self) -> Union[SMTP, SMTP_SSL]:
        """Establish an authenticated SMTP connection.

        Automatically chooses STARTTLS for most ports (e.g., 587) and SSL for 465.

        Returns:
            Union[SMTP, SMTP_SSL]: Authenticated SMTP connection object.

        Raises:
            RuntimeError: If connection or authentication fails.
        """
        conn_class = SMTP if self.smtp_port == 587 else SMTP_SSL
        smtp = conn_class(self.smtp_server, self.smtp_port, timeout=30)

        if self.smtp_port != 465:
            smtp.starttls()

        smtp.login(self.sender_email, self.sender_password)
        return smtp

    def add_text(self, html: str) -> None:
        """Append plain text or HTML content to the message body.

        Args:
            html (str): Text or HTML snippet to include.

        Raises:
            ValueError: If `html` is not a string.
        """
        if not isinstance(html, str):
            raise ValueError("Text must be a string.")
        self.body.append(html)

    def use_template(self, file: str, **variables) -> None:
        """Render a Jinja2 HTML template and append it to the body.

        Args:
            file (str): Path to an HTML template file.
            **variables: Context variables for template rendering.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the template path or content is invalid.
        """
        validate_template(file)
        with open(file, "r", encoding="utf-8") as f:
            html = Template(f.read()).render(**variables)
        self.add_text(html)

    def add_image(self, image_path: str, width: str | None = None, height: str | None = None, cid: str | None = None) -> None:
        """Queue an inline image to be embedded in the HTML body.

        Args:
            image_path (str): Path to the image file.
            width (str | None): CSS width (e.g., "200px", "50%").
            height (str | None): CSS height.
            cid (str | None): Optional Content-ID to reference in HTML (`src="cid:..."`).

        Raises:
            FileNotFoundError: If the image file does not exist.
            ValueError: If the image path is invalid.
        """
        validate_image(image_path)
        self.body.append({"image": image_path, "width": width, "height": height, "cid": cid})

    def add_attachment(self, attachment_path: str) -> None:
        """Attach a file to the message.

        Args:
            attachment_path (str): Path to the file to attach.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the path is invalid.
        """
        validate_path(attachment_path)
        self.attachments.append(attachment_path)

    def clear_body(self) -> None:
        """Remove all accumulated body content (keeps SMTP state)."""
        self.body = []

    def clear_attachments(self) -> None:
        """Remove all queued attachments."""
        self.attachments = []

    def _build_body(self) -> tuple[str, list[MIMEImage]]:
        """Assemble the unified HTML body and inline images.

        Returns:
            tuple[str, list[MIMEImage]]: A tuple with:
                - str: The final HTML body.
                - list[MIMEImage]: Inline images already prepared with headers.
        """
        html_parts: list[str] = []
        inline_images: list[MIMEImage] = []

        for block in self.body:
            if isinstance(block, str):
                html_parts.append(block)
            elif isinstance(block, dict) and "image" in block:
                path = block["image"]
                if isfile(path):
                    cid = block.get("cid") or f"img{uuid4().hex[:8]}"
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
                            mime_img = MIMEImage(img_file.read(), _subtype=mime_type.split("/")[1])
                            mime_img.add_header("Content-ID", f"<{cid}>")
                            mime_img.add_header("Content-Disposition", "inline", filename=basename(path))
                            inline_images.append(mime_img)

        unified_body = "".join(html_parts)
        return unified_body, inline_images

    def send(self, recipients: str | list[str]) -> dict:
        """Compose and send the prepared message to one or multiple recipients.

        Builds a MIME message (multipart/mixed with a multipart/alternative part),
        attaches inline images and files, and sends per-recipient. When used as a
        context manager, reuses the existing SMTP connection; otherwise, creates
        and closes a new connection around the operation.

        Args:
            recipients (str | list[str]): Single email or list of emails.

        Returns:
            dict: A summary with:
                - "sent" (list[str]): Successfully delivered addresses.
                - "failed" (dict[str, str]): Addresses mapped to error messages.

        Raises:
            RuntimeError: If preparing or sending the message fails.
        """
        if not isinstance(recipients, (list, tuple)):
            recipients = [recipients]

        result: dict = {"sent": [], "failed": {}}

        try:
            # Reuse existing connection if present; otherwise create a new one.
            smtp = getattr(self, "_smtp_conn", None) or self.connect()
            close_after = not hasattr(self, "_smtp_conn")

            unified_body, inline_images = self._build_body()
            emails_sent = 0

            for recipient in recipients:
                try:
                    message = MIMEMultipart("mixed")
                    message["From"] = self.sender_email
                    message["To"] = recipient
                    message["Subject"] = self.subject or ""

                    # Plain + HTML alternative
                    alt = MIMEMultipart("alternative")
                    plain_text = sub(r"<[^>]+>", "", unified_body)
                    plain_text = sub(r"\s+", " ", plain_text).strip() or "Content not available."

                    alt.attach(MIMEText(plain_text, "plain"))
                    alt.attach(MIMEText(unified_body, "html"))
                    message.attach(alt)

                    # Inline images
                    for img in inline_images:
                        message.attach(img)

                    # Attachments
                    for attachment_path in self.attachments:
                        if isfile(attachment_path):
                            with open(attachment_path, "rb") as f:
                                file_name = basename(attachment_path)
                                mime_type, _ = guess_type(attachment_path)
                                main_type, sub_type = (
                                    mime_type.split("/", 1) if mime_type else ("application", "octet-stream")
                                )

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

                    smtp.sendmail(self.sender_email, [recipient], message.as_string())
                    result["sent"].append(recipient)
                    emails_sent += 1

                    # Optional throttle
                    if self.max_emails_per_hour and emails_sent == self.max_emails_per_hour:
                        sleep(3600)

                except Exception as e:
                    result["failed"][recipient] = str(e)

            if close_after:
                smtp.quit()

        except Exception as e:
            raise RuntimeError(f"Failed to prepare or send email: {e}")

        return result
