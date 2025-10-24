from smtplib import SMTP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from mimetypes import guess_type
from uuid import uuid4
from os.path import isfile, basename
from re import sub


class Email:
    def __init__(self, smtp, remetente):
        """
        Classe utilizada para enviar emails de forma customizável e automatizada usando Python.
        """
        self.smtp_servidor = smtp['servidor']
        self.smtp_porta = smtp['porta']
        
        self.remetente_email = remetente['email']
        self.remetente_senha = remetente['senha']
        
        self.assunto = None
        self.corpo = []
        self.anexos = []

    def add_texto(self, html):
        """
        Adiciona um texto comum ou HTML ao corpo do e-mail.
        Exemplo:
            add_texto("Texto comum")
            add_texto("<p>HTML</p>")
        """
        if isinstance(html, str):
            self.corpo.append(html)

    def add_imagem(self, caminho_imagem, largura=None, altura=None, cid=None):
        """
        Adiciona uma imagem inline ao corpo do e-mail.
        Pode definir largura e altura (em pixels, % ou outras unidades CSS).
        Exemplo:
            add_imagem("logo.png", largura="200px", altura="100px")
            add_imagem("assinatura.png", largura="50%")
        """
        if isinstance(caminho_imagem, str) and isfile(caminho_imagem):
            self.corpo.append({
                "imagem": caminho_imagem,
                "largura": largura,
                "altura": altura,
                "cid": cid
            })
    
    def add_anexo(self, caminho_anexo):
        """
        Adiciona um arquivo anexo ao e-mail.
        Exemplo:
            add_anexo("C:/arquivo/para/anexar")
        """
        if isinstance(caminho_anexo, str) and isfile(caminho_anexo):
            self.anexos.append(caminho_anexo)
    
    def limpar_corpo(self):
        """
        Limpa corpo do email para iniciar outra montagem usando a mesma estrutura.
        """
        self.corpo = []
    
    def limpar_anexos(self):
        """
        Limpa anexos do email para aproveitar o corpo do email.
        """
        self.anexos = []

    def enviar(self, destinatarios):
        """
        Unifica os textos, códigos HTML, imagens e anexos montando o email e envia separadamente para cada destinatário.
        Exemplo:
            enviar('email@email.com')
            enviar(['email1@email.com', 'email2@email.com'])
        """
        if not isinstance(destinatarios, (list, tuple)):
            destinatarios = [destinatarios]

        try:
            with SMTP(self.smtp_servidor, self.smtp_porta) as servidor:
                servidor.starttls()
                servidor.login(self.remetente_email, self.remetente_senha)

                html_partes = []
                imagens_inline = []

                for bloco in self.corpo:
                    if isinstance(bloco, str):
                        html_partes.append(bloco)
                    elif isinstance(bloco, dict) and "imagem" in bloco:
                        caminho = bloco["imagem"]
                        if isfile(caminho):
                            cid = bloco.get('cid') if bloco.get('cid') else f"img{uuid4().hex[:8]}"
                            largura = bloco.get("largura")
                            altura = bloco.get("altura")

                            style = ""
                            if largura or altura:
                                style = ' style="'
                                if largura:
                                    style += f'width:{largura};'
                                if altura:
                                    style += f'height:{altura};'
                                style += '"'

                            # Se o HTML já contém esse cid, não insere <img> automaticamente
                            if not bloco.get("cid"):
                                html_partes.append(f'<br><img src="cid:{cid}"{style}><br>')

                            with open(caminho, 'rb') as img_file:
                                tipo_mime, _ = guess_type(caminho)
                                if tipo_mime and tipo_mime.startswith('image/'):
                                    mime_img = MIMEImage(img_file.read(), _subtype=tipo_mime.split("/")[1])
                                    mime_img.add_header('Content-ID', f'<{cid}>')
                                    mime_img.add_header('Content-Disposition', 'inline', filename=basename(caminho))
                                    imagens_inline.append(mime_img)

                conteudo_unificado = ''.join(html_partes)

                for destinatario in destinatarios:
                    mensagem = MIMEMultipart('mixed')
                    mensagem['From'] = self.remetente_email
                    mensagem['To'] = destinatario
                    mensagem['Subject'] = self.assunto or ""

                    alt = MIMEMultipart('alternative')
                    
                    # Gera versão em texto plano removendo tags HTML
                    texto_plano = sub(r'<[^>]+>', '', conteudo_unificado)
                    texto_plano = sub(r'\s+', ' ', texto_plano).strip() or "Conteúdo não disponível."

                    alt.attach(MIMEText(texto_plano, 'plain'))
                    alt.attach(MIMEText(conteudo_unificado, 'html'))
                    mensagem.attach(alt)

                    for img in imagens_inline:
                        mensagem.attach(img)

                    for caminho_anexo in self.anexos:
                        if isfile(caminho_anexo):
                            with open(caminho_anexo, 'rb') as f:
                                nome_arquivo = basename(caminho_anexo)
                                mime_anexo = MIMEApplication(f.read(), Name=nome_arquivo)
                                mime_anexo['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
                                mensagem.attach(mime_anexo)

                    servidor.sendmail(self.remetente_email, [destinatario], mensagem.as_string())
        except Exception as e:
                print(f"Erro ao enviar email: {str(e)}")


'''
EXEMPLO DE USO:

smtp = {'servidor': 'smtp.seudominio.com', 'porta': 587}
remetente = {'email': 'email@seudominio.com', 'senha': 'sua_senha'}

email = Email(smtp, remetente)
email.assunto = "Aviso de Atualização"

email.add_texto("<h2>Olá, Fulano</h2>")
email.add_texto("<p>Segue abaixo o aviso de atualização do sistema:</p>")
email.add_texto("<p>Versão: 3.1.0</p>")
email.add_texto("<p>Data: 13/06/2025</p>")
email.adicionar_imagem("assinatura.png")
email.add_texto("<p>Atenciosamente,<br>Equipe Técnica</p>")

email.anexos = ["manual.pdf"]

destinatarios = ["destinatario@exemplo.com"]
email.enviar(destinatarios)

email.limpar_corpo()
email.limpar_anexos()

...'''
