# 📧 ezmail

**Envie emails totalmente personalizados, em massa, com imagens, anexos, e muita facilidade.**

`ezmail` é uma biblioteca Python moderna para envio de e-mails HTML automatizados, ideal para notificações, marketing, relatórios e integrações corporativas.  
Ela combina a simplicidade do `smtplib` com recursos avançados como **imagens inline, anexos, corpo HTML e modo seguro (TLS)**.

---

## 🚀 Recursos

- Envio de emails em massa (lista de destinatários)
- Suporte a **HTML e texto puro** automaticamente
- Inserção de **imagens inline (embutidas no corpo)**
- Adição de **anexos de qualquer tipo**
- Controle total sobre **largura e altura das imagens**
- Login seguro via **TLS**
- API simples e intuitiva

---

## 💻 Exemplo de uso

```python
from ezmail import Email

smtp = {'servidor': 'smtp.seudominio.com', 'porta': 587}
remetente = {'email': 'email@seudominio.com', 'senha': 'sua_senha'}

email = Email(smtp, remetente)
email.assunto = "Aviso de Atualização do Sistema"

email.add_texto("<h2>Olá, Fulano!</h2>")
email.add_texto("<p>Segue o aviso de atualização do sistema:</p>")
email.add_texto("<p>Versão: 3.1.0</p>")
email.add_texto("<p>Data: 13/06/2025</p>")
email.add_imagem("assinatura.png", largura="200px")
email.add_anexo("manual.pdf")

email.enviar(["usuario1@dominio.com", "usuario2@dominio.com"])
