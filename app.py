# app.py by Eden Pardo
from flask import Flask, jsonify
#from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from extensions import db # Import db from extension.py
from user_routes import user_bp
from initial_routes import initial_bp
from base_budget_routes import base_budget_bp
from budget_item_routes import budget_item_bp
from category_routes import category_bp
from purchase_routes import purchase_bp
from pyf_budget_routes import pyf_budget_bp

import os

# Flask wants to pass--> Important for relative pass
app = Flask(__name__)
CORS(app) # Allows requests/responses between websites

@app.route('/api/run-check')
def run_check():
    return jsonify({"status": "active", "message": "Backend running"})

# Register Blueprints
app.register_blueprint(user_bp)
app.register_blueprint(initial_bp)
app.register_blueprint(base_budget_bp)
app.register_blueprint(budget_item_bp)
app.register_blueprint(category_bp)
app.register_blueprint(purchase_bp)
app.register_blueprint(pyf_budget_bp)

## Configure database:
# database is created locally under the backend folder
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///budgetUsers.db"
# Performance: Do not consume resources, we do not care about modifications that sqlalc does
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#print(app.config.keys())

# Initialize db with app
db.init_app(app)

#Create all tables in our database
# Need to pass so sqlAlc can do it's job in a more optimized way
with app.app_context():
    db.create_all()

print(__name__)
if __name__ == "__main__":
    #Better debugging in console
    # ToDo: Hide for production by using environment variables
    app.run(host="0.0.0.0", port=10000, debug=True)
    #app.run(host="127.0.0.1", port=5000, debug=True)