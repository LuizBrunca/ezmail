from imaplib import IMAP4_SSL
from email import message_from_bytes
from email.utils import parsedate_to_datetime
from email.header import decode_header, Header
from base64 import b64encode
from typing import List, Dict, Any
from datetime import datetime
from .utils import validate_protocol_config, validate_account, validate_date
from .ezmail import EzMail


class EzReader:
    """High-level IMAP client for reading and managing emails.

    Provides a unified interface to connect to an IMAP server (password or OAuth2),
    list mailboxes, search/filter messages, fetch contents and attachments, and
    perform common management operations (mark as unread, move, delete, empty folders).

    Example:
        imap = {"server": "imap.gmail.com", "port": 993}
        account = {"email": "user@gmail.com", "auth_value": "TOKEN_OR_PASSWORD", "auth_type": "oauth2"}
        with EzReader(imap, account) as reader:
            emails = reader.fetch_unread(limit=5)
            for mail in emails:
                print(mail.subject)
    """

    def __init__(self, imap: dict, account: dict):
        """Initialize the EzReader with IMAP and authentication details.

        Args:
            imap (dict): IMAP config with:
                - server (str): IMAP hostname or IP.
                - port (int): IMAP port (usually 993 for SSL).
            account (dict): Credentials with:
                - email (str): Account email address.
                - auth_value (str): Password or OAuth2 access token.
                - auth_type (str): "password" or "oauth2".

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
        """Enable context manager usage.

        Returns:
            EzReader: The connected instance ready for operations.
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Ensure IMAP disconnection when leaving the context."""
        self.disconnect()

    def _generate_oauth2_string(self, user_email: str, access_token: str) -> bytes:
        """Build the XOAUTH2 auth string for IMAP.

        Args:
            user_email (str): The user email.
            access_token (str): OAuth2 bearer token.

        Returns:
            bytes: Encoded XOAUTH2 string.
        """
        auth_string = f"user={user_email}\1auth=Bearer {access_token}\1\1"
        return b64encode(auth_string.encode("utf-8"))

    def connect(self) -> None:
        """Establish a secure IMAP connection and authenticate.

        Authenticates with either password or OAuth2 depending on `auth_type`.

        Raises:
            RuntimeError: On connection/authentication failure.
            ValueError: If `auth_type` is not "password" or "oauth2".
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
        """Close the IMAP connection safely."""
        try:
            if self.mail:
                self.mail.logout()
        except Exception:
            pass

    def list_mailboxes(self) -> List[str]:
        """List all available mailboxes (folders).

        Returns:
            List[str]: Mailbox names as returned by the server (decoded).

        Raises:
            RuntimeError: If not connected or unable to list mailboxes.
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

    def _quote_mailbox(self, name: str) -> str:
        """Quote a mailbox name if it contains special characters.

        Quotes names containing spaces, dots, slashes or brackets to avoid IMAP
        parser errors (e.g., "INBOX.Trash", "Deleted Items").

        Args:
            name (str): Raw mailbox name.

        Returns:
            str: Possibly quoted mailbox name, safe for IMAP commands.
        """
        if not name:
            return name
        n = name.strip().strip('"').strip("'")
        if any(ch in n for ch in [' ', '.', '/', '[', ']', '(', ')']):
            return f'"{n}"'
        return n

    def _list_mailboxes_detailed(self):
        """Return parsed IMAP LIST entries including attributes and delimiter.

        Returns:
            list[tuple[set[str], str, str]]: A list of (attributes, delimiter, name).

        Raises:
            RuntimeError: If not connected or list fails.
        """
        if not self.mail:
            raise RuntimeError("Not connected to any IMAP server.")
        status, lines = self.mail.list()
        if status != "OK":
            raise RuntimeError("Unable to retrieve mailbox list.")
        parsed = []
        for raw in lines or []:
            s = raw.decode(errors="ignore")
            # Format: (<attrs>) "delim" name
            left = s.find("(")
            right = s.find(")")
            attrs = set()
            if left != -1 and right != -1 and right > left:
                attrs = set(a.strip() for a in s[left + 1:right].split() if a.strip())
            rest = s[right + 1:].strip()
            delim = None
            if rest.startswith('"'):
                delim_end = rest.find('"', 1)
                if delim_end != -1:
                    delim = rest[1:delim_end]
                    rest = rest[delim_end + 1:].strip()
            name = rest.strip().strip('"')
            parsed.append((attrs, delim or "/", name))
        return parsed

    def fetch_messages(
        self,
        mailbox: str = "INBOX",
        limit: int | None = None,
        status: str = "ALL",
        sender: str | None = None,
        subject: str | None = None,
        text: str | None = None,
        body: str | None = None,
        date: datetime | None = None,
        since: datetime | None = None,
        before: datetime | None = None,
        uids: list[str] | None = None
    ) -> List[EzMail]:
        """Search and fetch messages with flexible IMAP filters.

        Performs a UID-based search in the selected mailbox and fetches
        message contents without marking them as seen. Returns `EzMail`
        objects with metadata, plain-text body and in-memory attachments.

        Args:
            mailbox (str, optional): Source mailbox to search. Defaults to "INBOX".
            limit (int | None, optional): Max number of emails to fetch. Defaults to None.
            status (str, optional): IMAP status filter ("ALL", "UNSEEN", "SEEN"). Defaults to "ALL".
            sender (str | None, optional): Filter by From header (substring match).
            subject (str | None, optional): Filter by subject text.
            text (str | None, optional): Search keyword in subject or body.
            body (str | None, optional): Search keyword only in body.
            date (datetime | None, optional): Exact date to match (ON).
            since (datetime | None, optional): Lower bound date (SINCE).
            before (datetime | None, optional): Upper bound (exclusive) date (BEFORE).

        Returns:
            List[EzMail]: Messages with:
                - uid (str): IMAP UID.
                - sender (str): Raw "From" header.
                - subject (str): Decoded subject.
                - body (str): Plain-text body (if present).
                - attachments (list[dict]): In-memory attachments (filename, content_type, data).
                - date (datetime | None): Parsed Date header.

        Raises:
            RuntimeError: If not connected, search fails, or parsing fails.

        Example:
            >>> emails = reader.fetch_messages(status="UNSEEN")
            >>> print(len(emails))
        """
        
        def safe_decode(value, encoding=None):
            """Decodifica bytes ou headers MIME de forma segura."""
            if not value:
                return ""
            if isinstance(value, Header):
                value = str(value)
            if isinstance(value, bytes):
                try:
                    return value.decode(encoding or "utf-8", errors="ignore")
                except LookupError:
                    return value.decode("utf-8", errors="ignore")
            try:
                parts = decode_header(value)
                decoded = ""
                for text, enc in parts:
                    if isinstance(text, bytes):
                        try:
                            decoded += text.decode(enc or "utf-8", errors="ignore")
                        except LookupError:
                            decoded += text.decode("utf-8", errors="ignore")
                    else:
                        decoded += text
                return decoded
            except Exception:
                return str(value)

        if not self.mail:
            raise RuntimeError("Not connected to any IMAP server.")

        # Build IMAP search criteria
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

            if uids:
                # Busca direta pelos UIDs informados
                search_uids = [uid.encode() for uid in uids]
            else:
                # Busca normal com critérios IMAP
                status_code, data = self.mail.uid("SEARCH", None, criteria)
                if status_code != "OK":
                    raise RuntimeError(f"Failed to search emails with criteria: {criteria}")
                search_uids = (data[0] or b"").split()
                
            if limit and not uids:
                search_uids = search_uids[:limit]

            emails = []
            for uid in search_uids:
                uid_str = uid.decode()

                # Do not set \Seen bit
                status_fetch, msg_data = self.mail.uid("FETCH", uid_str, "(BODY.PEEK[])")
                if status_fetch != "OK" or not msg_data or not msg_data[0]:
                    continue

                msg = message_from_bytes(msg_data[0][1])

                # --- Decodificação segura dos cabeçalhos ---
                subject_decoded = safe_decode(msg.get("Subject", ""))
                sender_decoded = safe_decode(msg.get("From", ""))
                raw_date = msg.get("Date")

                try:
                    email_date = parsedate_to_datetime(raw_date) if raw_date else None
                except Exception:
                    email_date = None

                # --- Corpo e anexos ---
                body_content = ""
                attachments = []

                for part in msg.walk():
                    content_disposition = str(part.get("Content-Disposition", "")).lower()
                    content_type = part.get_content_type()

                    if part.is_multipart():
                        continue

                    # Texto simples (ignora HTML e anexos)
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        try:
                            body_content = part.get_payload(decode=True).decode(errors="ignore")
                        except Exception:
                            pass

                    # Anexos
                    filename = part.get_filename()
                    if filename:
                        filename = safe_decode(filename)
                        try:
                            file_data = part.get_payload(decode=True)
                            attachments.append({
                                "filename": filename,
                                "content_type": content_type,
                                "data": file_data,
                            })
                        except Exception:
                            pass

                emails.append(EzMail(
                    uid=uid_str,
                    sender=sender_decoded,
                    subject=subject_decoded or "(Sem assunto)",
                    body=(body_content or "").strip(),
                    attachments=attachments,
                    date=email_date
                ))

            return emails

        except Exception as e:
            raise RuntimeError(f"Failed to fetch emails with the criteria {criteria}: {e}")

    def fetch_unread(self, mailbox: str = "INBOX", limit: int | None = None) -> List[EzMail]:
        """Convenience method to fetch unread messages.

        Args:
            mailbox (str): Mailbox to fetch from. Defaults to "INBOX".
            limit (int | None): Optional maximum number of messages.

        Returns:
            List[EzMail]: Unread messages as `EzMail` objects.

        Raises:
            RuntimeError: If not connected or on fetch errors.
        """
        return self.fetch_messages(mailbox=mailbox, status="UNSEEN", limit=limit)

    def mark_as_unread(self, email: EzMail, mailbox: str = "INBOX") -> bool:
        """Remove the ``\\Seen`` flag (mark message as unread).

        Args:
            email (EzMail): Message to modify (its UID is taken from `email.uid`).
            mailbox (str): Mailbox containing the message. Defaults to "INBOX".

        Returns:
            bool: True on success, False otherwise.

        Raises:
            RuntimeError: If not connected or the IMAP command fails.
        """
        if not self.mail:
            raise RuntimeError("Not connected to any IMAP server.")

        try:
            self.mail.select(mailbox)
            uid = email.uid
            status, _ = self.mail.uid("STORE", str(uid), "-FLAGS", "(\\Seen)")
            if status != "OK":
                raise RuntimeError(f"Failed to mark message {email} as unread.")
            return True
        except Exception as e:
            print(f"❌ Error marking email {email} as unread: {e}")
            return False
    
    def mark_as_read(self, email: EzMail, mailbox: str = "INBOX") -> bool:
        """Set the ``\\Seen`` flag (mark message as read).

        Args:
            email (EzMail): Message to modify (UID taken from `email.uid`).
            mailbox (str): Mailbox containing the message. Defaults to "INBOX".

        Returns:
            bool: True on success, False otherwise.

        Raises:
            RuntimeError: If not connected or the IMAP command fails.

        Example:
            >>> mail = emails[0]
            >>> reader.mark_as_read(mail)
            True
        """
        if not self.mail:
            raise RuntimeError("Not connected to any IMAP server.")

        try:
            self.mail.select(mailbox)
            uid = str(email.uid)
            status, _ = self.mail.uid("STORE", uid, "+FLAGS", "(\\Seen)")
            if status != "OK":
                raise RuntimeError(f"Failed to mark message {email} as read.")
            return True
        except Exception as e:
            print(f"❌ Error marking email {email} as read: {e}")
            return False

    def move_email(self, email: EzMail, destination: str, mailbox: str = "INBOX") -> bool:
        """Move a message to another mailbox (folder).

        Tries native `UID MOVE` (RFC 6851) if supported. Otherwise, falls back to
        `UID COPY` + `UID STORE +FLAGS (\\Deleted)` + `EXPUNGE`.

        Args:
            email (EzMail): Message to move (UID from `email.uid`).
            destination (str): Target mailbox name (e.g., "Archive", "INBOX.Trash").
            mailbox (str): Source mailbox that currently contains the message. Defaults to "INBOX".

        Returns:
            bool: True if moved successfully, False otherwise.

        Raises:
            RuntimeError: If not connected or the operation fails.
        """
        if not self.mail:
            raise RuntimeError("Not connected to any IMAP server.")
        try:
            self.mail.select(mailbox)
            uid = str(email.uid)
            dest = self._quote_mailbox(destination)

            if "MOVE" in self.mail.capabilities:
                status, _ = self.mail.uid("MOVE", uid, dest)
                if status != "OK":
                    raise RuntimeError(f"Failed to move {email} to {destination}.")
            else:
                status_copy, _ = self.mail.uid("COPY", uid, dest)
                if status_copy != "OK":
                    raise RuntimeError(f"Failed to copy {email} to {destination}.")
                self.mail.uid("STORE", uid, "+FLAGS", "(\\Deleted)")
                self.mail.expunge()
            return True
        except Exception as e:
            print(f"❌ Error moving email {email} to {destination}: {e}")
            return False

    def get_trash_folder(self) -> str:
        """Detect the Trash folder across providers/languages/hierarchies.

        Strategy:
          1) Prefer mailboxes flagged with ``\\Trash``.
          2) Try multilingual name heuristics ("Trash", "Deleted Items", "Lixeira", etc.).
          3) Gmail labels fallback (e.g., "[Gmail]/Lixeira" / "[Gmail]/Trash").
          4) Common hierarchy fallback ("INBOX.Trash").

        Returns:
            str: The best candidate mailbox name for Trash (server’s native name).

        Raises:
            RuntimeError: If not connected or listing fails.
        """
        if not self.mail:
            raise RuntimeError("Not connected to any IMAP server.")

        boxes = self._list_mailboxes_detailed()
        if not boxes:
            return "INBOX.Trash"

        # 1) \Trash attribute (most reliable)
        for attrs, _, name in boxes:
            if any(a.lower() == r'\trash' for a in attrs):
                return name

        # 2) Multilingual keywords
        keywords = [
            "trash", "deleted items", "deleted messages", "deleted",
            "lixeira", "itens excluídos", "eliminados",
            "papelera", "corbeille", "papierkorb", "cestino"
        ]
        names_lower = [(name, name.lower()) for _, _, name in boxes]
        for kw in keywords:
            for name, low in names_lower:
                if kw in low:
                    return name

        # 3) Gmail labels (localized)
        for name, low in names_lower:
            if "[gmail]" in low and ("trash" in low or "lixeira" in low or "bin" in low):
                return name

        # 4) Hierarchy fallback
        for name, low in names_lower:
            if low.endswith("inbox.trash"):
                return name

        return "INBOX.Trash"

    def move_to_trash(self, email: EzMail, mailbox: str = "INBOX") -> bool:
        """Move a message to Trash in a provider-safe way.

        For Gmail, applies label operations (remove ``\\Inbox`` and add ``\\Trash``)
        using ``X-GM-LABELS``. For other servers, detects the Trash mailbox and uses
        `move_email()` (or `copy+delete` fallback).

        Args:
            email (EzMail): Message to send to Trash (UID from `email.uid`).
            mailbox (str): Source mailbox containing the message. Defaults to "INBOX".

        Returns:
            bool: True on success, False otherwise.

        Raises:
            RuntimeError: If not connected or on IMAP errors.
        """
        if not self.mail:
            raise RuntimeError("Not connected to any IMAP server.")
        try:
            server = (self.imap_server or "").lower()
            uid = str(email.uid)

            if "gmail" in server:
                self.mail.select(mailbox)
                self.mail.uid("STORE", uid, "-X-GM-LABELS", "(\\Inbox)")
                self.mail.uid("STORE", uid, "+X-GM-LABELS", "(\\Trash)")
                return True

            trash_folder = self.get_trash_folder()
            return self.move_email(email, destination=trash_folder, mailbox=mailbox)

        except Exception as e:
            print(f"❌ Error moving email {email} to Trash: {e}")
            return False

    def empty_folder(self, mailbox: str) -> bool:
        """Permanently delete all messages from a mailbox.

        Marks every message in the given mailbox as ``\\Deleted`` and calls
        ``EXPUNGE`` to remove them permanently.

        Args:
            mailbox (str): Mailbox name to empty (e.g., "Trash", "INBOX.Trash").

        Returns:
            bool: True if the folder was emptied successfully, False otherwise.

        Raises:
            RuntimeError: If not connected or the mailbox cannot be opened.
        """
        if not self.mail:
            raise RuntimeError("Not connected to any IMAP server.")

        try:
            status, _ = self.mail.select(mailbox)
            if status != "OK":
                raise RuntimeError(f"Failed to open mailbox '{mailbox}'.")
            self.mail.store("1:*", "+FLAGS", "(\\Deleted)")
            self.mail.expunge()
            return True
        except Exception as e:
            print(f"❌ Error emptying folder '{mailbox}': {e}")
            return False

    def empty_trash(self) -> bool:
        """Permanently empty the Trash mailbox.

        Auto-detects the Trash folder name and reuses :meth:`empty_folder`.

        Returns:
            bool: True if Trash was emptied successfully, False otherwise.

        Raises:
            RuntimeError: If not connected or if the operation fails.
        """
        if not self.mail:
            raise RuntimeError("Not connected to any IMAP server.")

        try:
            trash_folder = self.get_trash_folder()
            return self.empty_folder(trash_folder)
        except Exception as e:
            print(f"❌ Error emptying Trash folder: {e}")
            return False

    def delete_email(self, email: EzMail, mailbox: str = "INBOX") -> bool:
        """Permanently delete a single message.

        Marks the message with ``\\Deleted`` and immediately calls ``EXPUNGE`` to
        remove it permanently from the selected mailbox.

        Args:
            email (EzMail): Message to delete (UID from `email.uid`).
            mailbox (str): Mailbox containing the message. Defaults to "INBOX".

        Returns:
            bool: True if permanently deleted, False otherwise.

        Raises:
            RuntimeError: If not connected or if the IMAP command fails.
        """
        if not self.mail:
            raise RuntimeError("Not connected to any IMAP server.")

        try:
            self.mail.select(mailbox)
            uid = email.uid
            status, _ = self.mail.uid("STORE", str(uid), "+FLAGS", "(\\Deleted)")
            if status != "OK":
                raise RuntimeError(f"Failed to mark message {email} as deleted.")
            self.mail.expunge()
            return True
        except Exception as e:
            print(f"❌ Error deleting email {email}: {e}")
            return False
