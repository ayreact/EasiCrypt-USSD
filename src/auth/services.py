from src.models.developer import Developer
from src.utils.security import hash_pin, check_pin

def register_developer(username, email, password):
    if Developer.find_by_email(email):
        raise ValueError("Developer with this email already exists")
    
    hashed_password = hash_pin(password) 
    developer_id = Developer.create(username, email, hashed_password)
    return developer_id

def login_developer(email, password):
    developer = Developer.find_by_email(email)
    if not developer or not check_pin(password, developer['password_hash']):
        raise ValueError("Invalid credentials")
    return developer

def reset_developer_password(email, new_password):
    developer = Developer.find_by_email(email)
    if not developer:
        raise ValueError("Developer not found")

    new_hashed_password = hash_pin(new_password)
    Developer.update_password(str(developer['_id']), new_hashed_password)
    return True