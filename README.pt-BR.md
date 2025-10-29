# 📧 EzMail

**Envie e leia e-mails com anexos, imagens inline, templates HTML e autenticação OAuth2 — de forma simples e segura.**

`ezmail` é uma biblioteca Python moderna para automação de e-mails.
Ela permite **enviar e receber mensagens** via SMTP e IMAP, com suporte a anexos, corpo HTML, imagens inline e autenticação segura (TLS ou OAuth2).

---

## 🚀 Recursos

### ✉️ Envio de e-mails (EzSender)

* Envio individual ou em massa
* Suporte a HTML e texto puro
* Imagens embutidas no corpo do e-mail
* Anexos de qualquer tipo (`PDF`, `CSV`, `XML`, etc.)
* Templates HTML com **Jinja2**
* Conexão segura (TLS/SSL)
* Limite de envio por hora

### 📥 Leitura de e-mails (EzReader)

* Conexão IMAP segura com senha ou token OAuth2
* Listagem de caixas de e-mail (`INBOX`, `Sent`, etc.)
* Filtros avançados: `ALL`, `UNSEEN`, `FROM`, `SUBJECT`, `TEXT`, `SINCE`, `BEFORE`
* Extração de anexos em memória (não salva automaticamente)
* Retorno estruturado via classe `EzMail`

---

## 💻 Instalação

```bash
pip install ezmail
```

Sem necessidade de configuração extra — basta informar suas credenciais SMTP e IMAP.

---

## 🧠 Visão geral

| Classe     | Descrição                                                             |
| ---------- | --------------------------------------------------------------------- |
| `EzSender` | Cria e envia e-mails com HTML, imagens inline e anexos.               |
| `EzReader` | Lê e filtra e-mails de qualquer servidor IMAP.                        |
| `EzMail`   | Representa um e-mail individual (remetente, assunto, corpo e anexos). |

---

## ✉️ Exemplo — Envio de e-mails

```python
from ezmail import EzSender

smtp = {"server": "smtp.gmail.com", "port": 587}
sender = {"email": "me@gmail.com", "password": "senha_de_app"}

ez = EzSender(smtp, sender)
ez.subject = "Relatório Mensal"
ez.add_text("<h2>Olá!</h2><p>Segue o relatório em anexo.</p>")
ez.add_attachment("relatorio.pdf")
ez.send(["cliente@empresa.com"])
```

---

## 📬 Exemplo — Leitura de e-mails

```python
from ezmail import EzReader

imap = {"server": "imap.gmail.com", "port": 993}
account = {
    "email": "me@gmail.com",
    "auth_value": "senha_ou_token",
    "auth_type": "password"
}

reader = EzReader(imap, account)
reader.connect()
emails = reader.fetch_messages(status="UNSEEN", since="01-Oct-2025")

for mail in emails:
    print(mail.subject, "-", mail.sender)
    if mail.has_attachments():
        for a in mail.attachments:
            print("💎", a["filename"], len(a["data"]), "bytes")

reader.disconnect()
```

---

## 🯩 Exemplo Avançado — Template e Imagem Inline

```python
ez = EzSender(
    smtp={"server": "smtp.dominio.com", "port": 587},
    sender={"email": "eu@dominio.com", "password": "minhasenha"}
)

ez.subject = "Bem-vindo à nossa plataforma!"
ez.use_template("templates/boas_vindas.html", nome="João", versao="3.2.1")
ez.add_image("logo.png", width="150px", cid="logo_img")
ez.send("joao@cliente.com")
```

---

## 🔐 Métodos de autenticação

| Método     | Descrição                                                              |
| ---------- | ---------------------------------------------------------------------- |
| `password` | Login tradicional com senha (ou senha de app).                         |
| `oauth2`   | Autenticação segura com token OAuth2 — exigido pelo Gmail e Microsoft. |

---

## 📦 Dependências

* [Jinja2](https://pypi.org/project/Jinja2/) ≥ 3.0.0 (para templates HTML)
* Apenas módulos nativos: `smtplib`, `imaplib`, `email`, `mimetypes`, `uuid`, etc.

---

## 🧮 Requisitos

* Python ≥ 3.8
* Acesso à internet (para servidores SMTP/IMAP)

---

## 💚 Licença

MIT © [Luiz Henrique Brunca](https://github.com/luizbrunca)

---

## 🌎 Outros idiomas

* 🇺🇸 **[Read in English (README.md)](https://github.com/LuizBrunca/ezmail/blob/main/README.md)**
