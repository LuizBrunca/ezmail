from os.path import isfile
from datetime import datetime


def validate_path(path: str) -> None:
    """Validates whether a given path points to an existing file.

    Args:
        path (str): Path or filename to validate.

    Raises:
        ValueError: If the provided path is not a string.
        FileNotFoundError: If the file does not exist at the specified path.

    Example:
        validate_path("/path/to/file.txt")
    """
    if not isinstance(path, str):
        raise ValueError("The path/file must be a string.")
    if not isfile(path):
        raise FileNotFoundError(f"The path/file '{path}' was not found.")


def validate_template(file: str) -> None:
    """Validates whether the provided file path refers to a valid HTML template.

    Args:
        file (str): Path to the HTML template file.

    Raises:
        ValueError: If the file is not an HTML file.
        FileNotFoundError: If the file does not exist.

    Example:
        validate_template("templates/email_template.html")
    """
    validate_path(file)
    if not file.endswith(".html"):
        raise ValueError("The file must have a .html extension.")


def validate_image(image_path: str) -> None:
    """Validates whether the provided image path points to an existing image file.

    Args:
        image_path (str): Path to the image file.

    Raises:
        ValueError: If the path is not a string.
        FileNotFoundError: If the image file does not exist.

    Example:
        validate_image("images/logo.png")
    """
    validate_path(image_path)

def validate_protocol_config(protocol_config: dict) -> None:
    """Validates whether the provided protocol configuration dictionary is valid.

    Args:
        protocol_config (dict): Dictionary containing server configuration.
            Must include the keys:
                - 'server' (str): server hostname or IP.
                - 'port' (int): Port number for the SMTP connection.

    Raises:
        ValueError: If the dictionary is missing or required keys are not provided.

    Example:
        validate_server_dict({"server": "smtp.domain.com", "port": 587})
        validate_server_dict({"server": "imap.domain.com", "port": 993})
    """
    if not protocol_config:
        raise ValueError("The protocol configuration dictionary does not exist.")

    if not protocol_config.get("server") or not protocol_config.get("port"):
        raise ValueError("The keys 'server' and 'port' must be provided.")

def validate_sender(sender: dict) -> None:
    """Validates whether the provided sender credentials dictionary is valid.

    Args:
        sender (dict): Dictionary containing sender credentials.
            Must include the keys:
                - 'email' (str): Email address.
                - 'password' (str): Password.

    Raises:
        ValueError: If the dictionary is missing or required keys are not provided.

    Example:
        validate_sender({"email": "email@domain.com", "password": "1234"})
    """
    if not sender:
        raise ValueError("The 'sender' dictionary does not exist.")

    if not sender.get("email") or not sender.get("password"):
        raise ValueError("The keys 'email' and 'password' must be provided.")

def validate_account(account: dict) -> None:
    """Validates whether the provided account credentials dictionary is valid.

    Args:
        account (dict): Dictionary containing email account credentials.
            Must include the keys:
                - 'email' (str): Email address.
                - 'auth_value' (str): Password or OAuth2 token.
                - 'auth_type' (str): 'password' or 'oauth2'.

    Raises:
        ValueError: If the dictionary is missing or required keys are not provided.

    Example:
        validate_account({"email": "email@domain.com", "auth_value": "1234", "auth_type": "password"})
    """
    if not account:
        raise ValueError("The 'account' dictionary does not exist.")

    if not account.get("email") or not account.get("auth_value") or not account.get("auth_type"):
        raise ValueError("The keys 'email', 'auth_value' and 'auth_type' must be provided.")

def validate_date(date):
    if not isinstance(date, datetime):
        raise ValueError("The date must be a datetime object.")