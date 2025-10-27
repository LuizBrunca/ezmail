from smtplib import SMTP, SMTP_SSL
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from mimetypes import guess_type
from uuid import uuid4
from os.path import isfile, basename
from re import sub
from typing import Union
from jinja2 import Template # type: ignore
from utils import validate_template, validate_image, validate_path, validate_sender, validate_smtp
from time import sleep


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
                - `port` (int): Port used for SMTP connection.
            sender (dict): Sender credentials with keys:
                - `email` (str): Sender email address.
                - `password` (str): Sender email password.
        """
        validate_smtp(smtp)
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

    def add_image(
        self, image_path: str, width: str = None, height: str = None, cid: str = None
    ) -> None:
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
                                    mime_attachment = MIMEApplication(
                                        f.read(), Name=file_name
                                    )
                                    mime_attachment["Content-Disposition"] = (
                                        f'attachment; filename="{file_name}"'
                                    )
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


class EzReader:
    """Handles reading and managing emails via IMAP protocol.

    This class is a placeholder for future development and will include
    IMAP-based reading, searching, and parsing of inbox messages.
    """

    def __init__(self, imap: dict, email: dict):
        """Initializes the EzReader instance with IMAP configuration.

        Args:
            imap (dict): IMAP configuration with keys:
                - `server` (str): IMAP server hostname or IP.
                - `port` (int): IMAP port number.
            email (dict): Email credentials with keys:
                - `email` (str): Email address to connect with.
                - `password` (str): Corresponding email password.
        """
        self.imap_server = imap["server"]
        self.imap_port = imap["port"]

        self.email_email = email["email"]
        self.email_password = email["password"]
