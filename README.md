# 📧 EzMail

**Send and read emails easily — with attachments, inline images, HTML templates, IMAP management, and OAuth2 authentication.**

`ezmail` is a modern Python library that simplifies email automation and management.  
It allows you to **send and receive emails** using SMTP and IMAP, supporting HTML templates, inline images, file attachments, and secure authentication (TLS/SSL or OAuth2).

---

## 🚀 Features

### ✉️ Sending Emails (`EzSender`)
- Send emails to one or multiple recipients  
- Supports both **HTML** and **plain text** messages  
- Embed **inline images** directly into the email body  
- Attach any file type (`PDF`, `CSV`, `ZIP`, `XML`, etc.)  
- Use **Jinja2 templates** for dynamic HTML emails  
- Secure connection via **TLS/SSL**  
- Optional hourly send rate limiting  
- **Broadcast mode** — send one email with all recipients visible in the `To:` header (`broadcast=True`)  
- Full **context manager** support (`with EzSender(...) as ez:`)
- `set_subject(subject)` — validates and sets the subject (rejects blank, newlines, or >255 chars)
- `reset()` — clears subject, body, and attachments to reuse the session for multiple sends

### 📥 Reading Emails (`EzReader`)
- Connect to any IMAP server using password or **OAuth2 token**  
- List all available mailboxes (Inbox, Trash, Sent, etc.)  
- Filter emails by `ALL`, `UNSEEN`, `SEEN`, `FROM`, `SUBJECT`, `TEXT`, `SINCE`, `BEFORE`  
- Retrieve emails and attachments in memory (no file saving required)  
- Mark as **unread**, **move**, **delete**, or **empty** folders (e.g., Trash)  
- Full **context manager** support (`with EzReader(...) as reader:`)

### 💌 Email Model (`EzMail`)
- Represents an individual email message  
- Provides access to:  
  - `sender`, `subject`, `body`, `date`, and `attachments`  
- Methods:  
  - `has_attachments()` — checks if attachments exist  
  - `summary()` — returns a short preview of the message body  

---

## 💻 Installation

```bash
pip install py-ezmail
```

No additional configuration is required — just provide your SMTP and IMAP credentials.

---

## 🧠 Quick Overview

| Class      | Description                                                          |
| -----------| -------------------------------------------------------------------- |
| `EzSender` | Composes and sends emails with HTML, inline images, and attachments. |
| `EzReader` | Reads, filters, and manages emails from IMAP servers.                |
| `EzMail`   | Represents a single email object (sender, subject, body, attachments).|

---

## ✉️ Example — Sending Emails

```python
from ezmail import EzSender

smtp = {"server": "smtp.gmail.com", "port": 587}
sender = {"email": "me@gmail.com", "password": "app_password"}

with EzSender(smtp, sender) as ez:
    ez.set_subject("System Update Report")
    ez.add_text("<h2>Hello!</h2><p>The latest report is attached below.</p>")
    ez.add_attachment("report.pdf")
    result = ez.send(["client@example.com", "team@example.com"])

print(result)
```

---

## 📬 Example — Reading Emails

```python
from ezmail import EzReader

imap = {"server": "imap.gmail.com", "port": 993}
account = {
    "email": "me@gmail.com",
    "auth_value": "app_password",
    "auth_type": "password"
}

with EzReader(imap, account) as reader:
    emails = reader.fetch_unread(limit=5)
    for mail in emails:
        print(mail.subject, "-", mail.sender)
        if mail.has_attachments():
            for a in mail.attachments:
                print("💎", a["filename"], len(a["data"]), "bytes")
```

---

## 🗑️ Managing Emails

```python
with EzReader(imap, account) as reader:
    emails = reader.fetch_unread(limit=1)
    if emails:
        mail = emails[0]
        reader.move_to_trash(mail)   # Move to Trash
        reader.empty_trash()         # Empty Trash
```

---

## 🯩 Advanced Example — HTML Templates & Inline Images

```python
from ezmail import EzSender

with EzSender(
    smtp={"server": "smtp.domain.com", "port": 587},
    sender={"email": "me@domain.com", "password": "mypassword"}
) as ez:
    ez.set_subject("Welcome to our platform!")
    ez.use_template("templates/welcome.html", name="John", version="3.2.1")
    ez.add_image("logo.png", width="150px", cid="logo_img")
    ez.send("john@client.com")
```

---

## 📢 Broadcast — Send to All Recipients at Once

Pass `broadcast=True` to send a single email where all recipients are visible in the `To:` header.  
This is ideal for group announcements or team notifications.

```python
with EzSender(smtp, sender) as ez:
    ez.set_subject("Team Announcement")
    ez.add_text("<p>This message was sent to the whole team.</p>")
    result = ez.send(["alice@example.com", "bob@example.com", "carol@example.com"], broadcast=True)

print(result)
```

> **Note:** In broadcast mode, every recipient can see all other addresses in the `To:` field.  
> For individual/private sends (each person sees only their own address), use the default `broadcast=False`.

---

## 🔄 Sending Multiple Emails in One Session

Use `reset()` to clear the subject, body, and attachments between sends without reopening the SMTP connection:

```python
with EzSender(smtp, sender) as ez:
    ez.set_subject("First email")
    ez.add_text("<p>Message one.</p>")
    ez.send("alice@example.com")

    ez.reset()

    ez.set_subject("Second email")
    ez.add_text("<p>Message two.</p>")
    ez.send("bob@example.com")
```

---

## 🔐 Authentication Methods

| Method     | Description                                                                     |
| ----------- | ------------------------------------------------------------------------------ |
| `password` | Standard login using email and password (supports app passwords).               |
| `oauth2`   | Secure OAuth2 token authentication (used by Gmail, Outlook, etc.).              |

---

## 📦 Dependencies

* [Jinja2](https://pypi.org/project/Jinja2/) ≥ 3.0.0  
* Built-in Python modules: `smtplib`, `imaplib`, `email`, `mimetypes`, `uuid`, `base64`, etc.

---

## 🧮 Requirements

* Python ≥ 3.8  
* Internet access (for SMTP/IMAP servers)

---

## 🧳 License

MIT © [Luiz Henrique Brunca](https://github.com/luizbrunca)

---

## 🌎 Other Languages

* 🇧🇷 **[Leia em Português (README.pt-BR.md)](https://github.com/LuizBrunca/ezmail/blob/main/README.pt-BR.md)**
