import re

#email validation
def is_valid_email(email):
    """
    Validate email format.
    """
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(email_regex, email))


# name validation
def is_valid_name(name):
    """
    Validate name: only alphabets and spaces, 2-50 characters.
    Reject names consisting only of spaces.
    """
    name = name.strip()  # Remove leading and trailing spaces
    return bool(re.fullmatch(r"[A-Za-z ]{2,50}", name))


#password validation
def is_valid_password(password):
    """
    Validate password: 
    - Minimum 8 characters
    - At least one uppercase, one lowercase, one digit, and one special character.
    """
    if len(password) < 8:
        return False
    if not any(char.isupper() for char in password):
        return False
    if not any(char.islower() for char in password):
        return False
    if not any(char.isdigit() for char in password):
        return False
    if not any(char in "!@#$%^&*()-_=+[]{}|;:',.<>?/`~" for char in password):
        return False
    return True