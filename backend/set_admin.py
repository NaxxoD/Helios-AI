"""Passe un utilisateur en admin. Usage : python set_admin.py email@exemple.com"""
import sys
from sqlalchemy.orm import Session
from database import engine
from models import User

if len(sys.argv) != 2:
    print("Usage : python set_admin.py email@exemple.com")
    sys.exit(1)

email = sys.argv[1].strip().lower()
with Session(engine) as db:
    user = db.query(User).filter_by(email=email).first()
    if not user:
        print(f"Utilisateur '{email}' introuvable.")
        sys.exit(1)
    user.role = "admin"
    db.commit()
    print(f"'{email}' est maintenant admin.")
