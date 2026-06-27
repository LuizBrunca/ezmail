# 📧 EzMail

**Envie e leia e-mails com anexos, imagens inline, templates HTML, gerenciamento IMAP e autenticação OAuth2 — de forma simples e segura.**

`ezmail` é uma biblioteca Python moderna para automação e gerenciamento de e-mails.  
Ela permite **enviar e receber mensagens** via SMTP e IMAP, com suporte a templates HTML, imagens embutidas, anexos e autenticação segura (TLS/SSL ou OAuth2).

---

## 🚀 Recursos

### ✉️ Envio de E-mails (`EzSender`)
- Envio individual ou múltiplo  
- Suporte a **HTML** e **texto puro**  
- Inserção de **imagens embutidas** diretamente no corpo do e-mail  
- Anexos de qualquer tipo (`PDF`, `CSV`, `ZIP`, `XML`, etc.)  
- Templates dinâmicos com **Jinja2**  
- Conexão segura via **TLS/SSL**  
- Limite opcional de envio por hora  
- **Modo broadcast** — envia um único e-mail com todos os destinatários visíveis no campo `To:` (`broadcast=True`)  
- Suporte total a **context manager** (`with EzSender(...) as ez:`)
- `set_subject(subject)` — valida e define o assunto (rejeita vazio, quebras de linha ou mais de 255 caracteres)
- `reset()` — limpa assunto, corpo e anexos para reutilizar a sessão em múltiplos envios

### 📥 Leitura e Gerenciamento (`EzReader`)
- Conexão IMAP segura com senha ou **token OAuth2**  
- Listagem de pastas (Inbox, Lixeira, Enviados, etc.)  
- Filtros avançados: `ALL`, `UNSEEN`, `SEEN`, `FROM`, `SUBJECT`, `TEXT`, `SINCE`, `BEFORE`  
- Leitura de anexos diretamente na memória (sem salvar arquivos)  
- Marcar como **não lido**, **mover**, **excluir** ou **esvaziar pastas** (ex: Lixeira)  
- Suporte total a **context manager** (`with EzReader(...) as reader:`)

### 💌 Modelo de E-mail (`EzMail`)
- Representa um e-mail individual  
- Acesso a: `remetente`, `assunto`, `corpo`, `data`, `anexos`  
- Métodos úteis:
  - `has_attachments()` — verifica se há anexos  
  - `summary()` — retorna um resumo do corpo do e-mail  

---

## 💻 Instalação

```bash
pip install py-ezmail
```

Sem necessidade de configuração extra — basta informar suas credenciais SMTP e IMAP.

---

## 🧠 Visão Geral

| Classe     | Descrição                                                              |
| ----------- | ---------------------------------------------------------------------- |
| `EzSender` | Cria e envia e-mails com HTML, imagens inline e anexos.                |
| `EzReader` | Lê, filtra e gerencia e-mails de servidores IMAP.                      |
| `EzMail`   | Representa um e-mail individual (remetente, assunto, corpo e anexos).  |

---

## ✉️ Exemplo — Envio de E-mails

```python
from ezmail import EzSender

smtp = {"server": "smtp.gmail.com", "port": 587}
sender = {"email": "me@gmail.com", "password": "senha_de_app"}

with EzSender(smtp, sender) as ez:
    ez.set_subject("Relatório do Sistema")
    ez.add_text("<h2>Olá!</h2><p>Segue o relatório em anexo.</p>")
    ez.add_attachment("relatorio.pdf")
    result = ez.send(["cliente@empresa.com", "ti@empresa.com"])

print(result)
```

---

## 📬 Exemplo — Leitura de E-mails

```python
from ezmail import EzReader

imap = {"server": "imap.gmail.com", "port": 993}
account = {
    "email": "me@gmail.com",
    "auth_value": "senha_ou_token",
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

## 🗑️ Gerenciamento de E-mails

```python
with EzReader(imap, account) as reader:
    emails = reader.fetch_unread(limit=1)
    if emails:
        mail = emails[0]
        reader.move_to_trash(mail)   # Move para a Lixeira
        reader.empty_trash()         # Esvazia a Lixeira
```

---

## 🯩 Exemplo Avançado — Template HTML e Imagem Inline

```python
from ezmail import EzSender

with EzSender(
    smtp={"server": "smtp.dominio.com", "port": 587},
    sender={"email": "eu@dominio.com", "password": "minhasenha"}
) as ez:
    ez.set_subject("Bem-vindo à nossa plataforma!")
    ez.use_template("templates/boas_vindas.html", nome="João", versao="3.2.1")
    ez.add_image("logo.png", width="150px", cid="logo_img")
    ez.send("joao@cliente.com")
```

---

## 📢 Broadcast — Enviar para Todos de Uma Vez

Use `broadcast=True` para enviar um único e-mail com todos os destinatários visíveis no campo `To:`.  
Ideal para comunicados em grupo ou notificações para equipes.

```python
with EzSender(smtp, sender) as ez:
    ez.set_subject("Comunicado da Equipe")
    ez.add_text("<p>Esta mensagem foi enviada para toda a equipe.</p>")
    result = ez.send(["alice@exemplo.com", "bob@exemplo.com", "carol@exemplo.com"], broadcast=True)

print(result)
```

> **Atenção:** No modo broadcast, todos os destinatários conseguem ver os endereços uns dos outros no campo `To:`.  
> Para envios individuais (cada pessoa vê apenas o próprio endereço), use o padrão `broadcast=False`.

---

## 🔄 Múltiplos Envios na Mesma Sessão

Use `reset()` para limpar assunto, corpo e anexos entre envios sem reabrir a conexão SMTP:

```python
with EzSender(smtp, sender) as ez:
    ez.set_subject("Primeiro e-mail")
    ez.add_text("<p>Mensagem um.</p>")
    ez.send("alice@exemplo.com")

    ez.reset()

    ez.set_subject("Segundo e-mail")
    ez.add_text("<p>Mensagem dois.</p>")
    ez.send("bob@exemplo.com")
```

---

## 🔐 Métodos de Autenticação

| Método     | Descrição                                                               |
| ----------- | ---------------------------------------------------------------------- |
| `password` | Login tradicional com senha (ou senha de app).                          |
| `oauth2`   | Autenticação segura com token OAuth2 — usada por Gmail e Microsoft.     |

---

## 📦 Dependências

* [Jinja2](https://pypi.org/project/Jinja2/) ≥ 3.0.0  
* Módulos nativos do Python: `smtplib`, `imaplib`, `email`, `mimetypes`, `uuid`, `base64`, etc.

---

## 🧮 Requisitos

* Python ≥ 3.8  
* Acesso à internet (para servidores SMTP/IMAP)

---

## 💚 Licença

MIT © [Luiz Henrique Brunca](https://github.com/luizbrunca)

---

## 🌎 Outros Idiomas

* 🇺🇸 **[Read in English (README.md)](https://github.com/LuizBrunca/ezmail/blob/main/README.md)**
