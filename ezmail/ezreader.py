from imaplib import IMAP4_SSL
from email import message_from_bytes
from email.header import decode_header
from email.utils import parsedate_to_datetime
from base64 import b64encode
from typing import List, Dict, Any
from datetime import datetime
from .utils import validate_protocol_config, validate_account, validate_date
from .ezmail import EzMail


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
    
    def __enter__(self):
        """Enables usage of EzReader as a context manager.

        Automatically connects to the IMAP server when entering the context.

        Returns:
            EzReader: The active EzReader instance, ready for operations.

        Example:
            >>> with EzReader(imap, account) as reader:
            ...     emails = reader.fetch_unread()
            ...     print(emails)
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Ensures IMAP disconnection when leaving the context.

        This method is automatically called at the end of a `with` block,
        even if an exception occurs inside it.
        """
        self.disconnect()

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
    
    def disconnect(self) -> None:
        """Closes the IMAP connection safely.

        Example:
            disconnect()
        """
        try:
            if self.mail:
                self.mail.logout()
        except Exception:
            pass

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
                - `uid` (int): UID.
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
            validate_date(date)
            criteria += f' ON {date.strftime("%d-%b-%Y")}'
        if since:
            validate_date(since)
            criteria += f' SINCE {since.strftime("%d-%b-%Y")}'
        if before:
            validate_date(before)
            criteria += f' BEFORE {before.strftime("%d-%b-%Y")}'
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
                
                # 🔹 Extrai e converte a data
                raw_date = msg.get("Date")
                try:
                    email_date = parsedate_to_datetime(raw_date) if raw_date else None
                except Exception:
                    email_date = None

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
                    uid=msg_id,
                    sender=sender_decoded,
                    subject=subject_decoded,
                    body=body_content.strip(),
                    attachments=attachments,
                    date=email_date
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
            list[EzMail]: A list of `EzMail` objects containing:
                - `uid` (int): UID.
                - `sender` (str): Sender's name and address.
                - `subject` (str): Email subject (decoded).
                - `body` (str): Plain text body of the message.
                - `attachments` (list): List of attachments (not saved), each with:
                    - `filename` (str): File name.
                    - `content_type` (str): MIME type.
                    - `data` (bytes): Raw binary content.

        Raises:
            RuntimeError: If unable to fetch emails or not connected.
        """

        emails = self.fetch_messages(mailbox=mailbox, status="UNSEEN", limit=limit)
        return emails
    
    def mark_as_unread(self, email: EzMail, mailbox: str = "INBOX") -> bool:
        """Marks an EzMail message as unread (removes the \\Seen flag).

        This method reverts the read status of a given email by removing its
        `\\Seen` flag, effectively marking it as unread. The UID is extracted
        automatically from the provided `EzMail` instance.

        Args:
            email (EzMail): The EzMail instance representing the email to modify.
                The UID is obtained from `email.uid`.
            mailbox (str, optional): The mailbox (folder) containing the email.
                Defaults to "INBOX".

        Returns:
            bool: True if the operation was successful, False otherwise.

        Raises:
            RuntimeError: If not connected to any IMAP server or if the command fails.

        Example:
            >>> mail = emails[0]
            >>> reader.mark_as_unread(mail)
            True
        """
        if not self.mail:
            raise RuntimeError("Not connected to any IMAP server.")

        try:
            # Select the mailbox to operate on
            self.mail.select(mailbox)
            
            uid = email.uid

            # Execute the IMAP command to remove the \Seen flag
            status, _ = self.mail.uid("STORE", str(uid), "-FLAGS", "(\\Seen)")

            if status != "OK":
                raise RuntimeError(f"Failed to mark message {email} as unread.")

            return True

        except Exception as e:
            print(f"❌ Error marking email {email} as unread: {e}")
            return False
    
    def move_email(self, email: EzMail, destination: str, mailbox: str = "INBOX") -> bool:
        """Moves an email (EzMail object) to another mailbox (folder).

        This method moves the specified email to a different mailbox using its UID.
        It first attempts to use the native IMAP `MOVE` command (RFC 6851) if supported
        by the server. If not, it falls back to copying the message to the destination
        folder, marking it as deleted in the source folder, and expunging it.

        Args:
            email (EzMail): The EzMail instance representing the message to move.
                The method automatically retrieves its UID from `email.uid`.
            destination (str): The target mailbox (folder) to move the message to.
            mailbox (str, optional): The source mailbox containing the email.
                Defaults to "INBOX".

        Returns:
            bool: True if the message was successfully moved, False otherwise.

        Raises:
            RuntimeError: If not connected to an IMAP server or if the operation fails.

        Example:
            >>> mail = emails[0]
            >>> reader.move_email(mail, "Archive")
            True
        """
        if not self.mail:
            raise RuntimeError("Not connected to any IMAP server.")

        try:
            # Select source mailbox
            self.mail.select(mailbox)
            
            uid = email.uid

            # Check if server supports MOVE
            capabilities = self.mail.capabilities
            if "MOVE" in capabilities:
                status, _ = self.mail.uid("MOVE", str(uid), destination)
                if status != "OK":
                    raise RuntimeError(f"Failed to move {email} to {destination}.")
            else:
                # Fallback: COPY + DELETE + EXPUNGE
                status_copy, _ = self.mail.uid("COPY", str(uid), destination)
                if status_copy != "OK":
                    raise RuntimeError(f"Failed to copy {email} to {destination}.")

                # Mark as deleted and expunge
                self.mail.uid("STORE", str(uid), "+FLAGS", "(\\Deleted)")
                self.mail.expunge()

            return True

        except Exception as e:
            print(f"❌ Error moving email {email} to {destination}: {e}")
            return False
    
    def move_to_trash(self, email: EzMail, mailbox: str = "INBOX") -> bool:
        """Moves an EzMail message to the Trash folder.

        This method moves the given email from its current mailbox to the
        Trash folder using the existing `move_email()` method. It automatically
        detects the appropriate Trash folder name based on the IMAP server.

        Args:
            email (EzMail): The EzMail instance representing the email to move.
                The UID is obtained automatically from `email.uid`.
            mailbox (str, optional): The source mailbox containing the email.
                Defaults to "INBOX".

        Returns:
            bool: True if the message was successfully moved to Trash, False otherwise.

        Raises:
            RuntimeError: If not connected to an IMAP server or if the operation fails.

        Example:
            >>> mail = emails[0]
            >>> reader.move_to_trash(mail)
            True
        """
        if not self.mail:
            raise RuntimeError("Not connected to any IMAP server.")

        try:
            # Common folder names for Trash
            trash_folders = ["Trash", "Deleted Items", "Deleted Messages", "INBOX.Trash"]
            trash_folder = None

            # Try to detect an existing trash folder
            for folder in trash_folders:
                status, _ = self.mail.list(pattern=folder)
                if status == "OK":
                    trash_folder = folder
                    break

            # Default fallback
            if not trash_folder:
                trash_folder = "Trash"

            # Use the existing move_email method
            return self.move_email(email, destination=trash_folder, mailbox=mailbox)

        except Exception as e:
            print(f"❌ Error moving email {email} to Trash: {e}")
            return False
    
    def empty_folder(self, mailbox: str) -> bool:
        """Permanently deletes all messages from the specified mailbox.

        This method selects the given mailbox (folder), marks all messages inside it
        with the `\\Deleted` flag, and performs an `EXPUNGE` operation to remove them
        permanently from the server.

        Args:
            mailbox (str): The name of the mailbox (folder) to empty.
                Example: "Trash", "Spam", or "INBOX.Archive".

        Returns:
            bool: True if the folder was successfully emptied, False otherwise.

        Raises:
            RuntimeError: If not connected to an IMAP server or if the operation fails.

        Example:
            >>> reader.empty_folder("Trash")
            True
        """
        if not self.mail:
            raise RuntimeError("Not connected to any IMAP server.")

        try:
            # Select the mailbox to operate on
            status, _ = self.mail.select(mailbox)
            if status != "OK":
                raise RuntimeError(f"Failed to open mailbox '{mailbox}'.")

            # Mark all messages in the folder as deleted
            self.mail.store("1:*", "+FLAGS", "(\\Deleted)")

            # Permanently remove deleted messages
            self.mail.expunge()

            return True

        except Exception as e:
            print(f"❌ Error emptying folder '{mailbox}': {e}")
            return False

    def empty_trash(self) -> bool:
        """Permanently deletes all messages from the Trash folder.

        This method automatically detects the correct Trash mailbox name
        (e.g., "Trash", "Deleted Items", or "INBOX.Trash") and permanently
        deletes all messages inside it using the `empty_folder()` method.

        Returns:
            bool: True if the Trash was successfully emptied, False otherwise.

        Raises:
            RuntimeError: If not connected to an IMAP server or if the operation fails.

        Example:
            >>> reader.empty_trash()
            True
        """
        if not self.mail:
            raise RuntimeError("Not connected to any IMAP server.")

        try:
            # Detect the correct Trash folder name
            trash_folders = ["Trash", "Deleted Items", "Deleted Messages", "INBOX.Trash"]
            trash_folder = None

            for folder in trash_folders:
                status, _ = self.mail.list(pattern=folder)
                if status == "OK":
                    trash_folder = folder
                    break

            if not trash_folder:
                trash_folder = "Trash"

            # Reuse the generic empty_folder() method
            return self.empty_folder(trash_folder)

        except Exception as e:
            print(f"❌ Error emptying Trash folder: {e}")
            return False
    
    def delete_email(self, email: EzMail, mailbox: str = "INBOX") -> bool:
        """Permanently deletes an EzMail message from the specified mailbox.

        This method marks the given email as deleted using the IMAP `STORE` command
        with the `+FLAGS (\\Deleted)` operation and immediately performs an `EXPUNGE`
        to permanently remove it from the mailbox.

        Args:
            email (EzMail): The EzMail instance representing the email to delete.
                The UID is obtained automatically from `email.uid`.
            mailbox (str, optional): The mailbox (folder) containing the email.
                Defaults to "INBOX".

        Returns:
            bool: True if the message was successfully and permanently deleted,
            False otherwise.

        Raises:
            RuntimeError: If not connected to an IMAP server or if the command fails.

        Example:
            >>> mail = emails[0]
            >>> reader.delete_email(mail)
            True
        """
        if not self.mail:
            raise RuntimeError("Not connected to any IMAP server.")

        try:
            # Select the mailbox to operate on
            self.mail.select(mailbox)

            uid = email.uid

            # Mark message as deleted
            status, _ = self.mail.uid("STORE", str(uid), "+FLAGS", "(\\Deleted)")
            if status != "OK":
                raise RuntimeError(f"Failed to mark message {email} as deleted.")

            # Permanently remove it if requested
            self.mail.expunge()

            return True

        except Exception as e:
            print(f"❌ Error deleting email {email}: {e}")
            return False