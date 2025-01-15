import re
from django.core.exceptions import ValidationError


# email validation
def is_valid_email(email):
    """
    Validate email format.
    """
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(email_regex, email))


# name validation
def is_valid_name(name):
    """
    Validate name: only alphabets and spaces, 2-30 characters.
    Reject names consisting only of spaces.
    """
    name = name.strip()  # Remove leading and trailing spaces
    return bool(re.fullmatch(r"[A-Za-z ]{2,30}", name))


def is_valid_phone(mobile_number):
    pattern = re.compile(r"^\d{10}$")
    if not pattern.match(mobile_number):
        return False
    
    # Ensure the number is not all zeros
    if mobile_number == "0000000000":
        return False
    
    return True


# password validation
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


def convert_description(description):
    # Trim excess whitespace and reduce multiple line breaks to a single line break
    return "\n".join(line.strip() for line in description.splitlines() if line.strip())


def validate_product_name(name):
    if not name or not (2 <= len(name) <= 50):
        raise ValidationError("Name must be between 2 and 50 characters.")
    if not name.replace(" ", "").isalnum():  # Check for alphanumeric characters
        raise ValidationError("Name can only contain alphabets, numbers, and spaces.")

def is_valid_address(address):
    if not isinstance(address, str) or not address.strip():
        return False
    
    pattern = r"^[A-Za-z0-9\s.,-/#]+$"
    if not re.match(pattern, address):
        return False
    
    if len(address) < 5 or len(address) > 75:
        return False
    
    return True


def is_valid_postalcode(pcode):
    codelength = len(pcode)
    if codelength == 6 and pcode[0:5:2].isdigit and pcode[1:5:2].isalpha:
        return True
    else:
        return False
