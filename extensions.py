#extensions.py by Eden Pardo
from flask_sqlalchemy import SQLAlchemy

#Creating db isntance
db = SQLAlchemy()

# By moving db initialization to a separate file (extensions.py)
# this breaks the circular dependency of previous db initializaing in app.py