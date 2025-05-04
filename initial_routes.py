# initial_routes.py by Eden Pardo
from flask import Blueprint, request, jsonify
from models import Users, InitialExpense, InitialIncome
from extensions import db

initial_bp = Blueprint('initial', __name__)

# Add initial income for user (before budget creation)
@initial_bp.route("/api/users/<int:user_id>/initial-incomes", methods=["POST"])
def add_initial_income(user_id):
    try:
        user = Users.query.get(user_id)
        if user is None:
            return jsonify({"status":"error", "msg":"User not found"}), 404
        
        data = request.json

        # Validate required fields
        required_fields = ["title", "amount", "frequency"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({"status":"error", "msg":f"Missing required field: {', '.join(missing_fields)}"}), 400
        
        income_title = data["title"].strip()
        if len(income_title) == 0:
            return jsonify({"status": "error", "msg": "Title cannot be empty"}), 400
        if len(income_title) > 100:
            return jsonify({"status": "error", "msg": "Title too long"}), 400

        if float(data['amount']) < 0:
            return jsonify({"status":"error","msg": "Amount cannot be negative"}), 400
        
        if data['frequency'] not in ["weekly", "biweekly", "monthly", "yearly"]:
            return jsonify({"status":"error", "msg": "Frquency must be 'weekly', 'biweekly', 'monthly', or 'yearly'"}), 400

        # Create new income
        new_income = InitialIncome(title=data['title'], amount=data['amount'], frequency=data['frequency'], user_id=user_id)
        db.session.add(new_income)
        db.session.commit()

        return jsonify({"msg":"Income created successfully", "new_income":new_income.to_json()}), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error":str(e)}), 500
    
# Update an Initial Income
@initial_bp.route("/api/users/<int:user_id>/initial-incomes/<int:income_id>", methods=["PATCH"])
def update_initial_income(user_id, income_id):
    try:
        income = InitialIncome.query.filter_by(id=income_id, user_id=user_id).first()
        if not income:
            return jsonify({"status":"error", "msg": "Income not found"}), 404
        
        data = request.json

        # Validate required fields (if updated)
        if 'title' in data:
            income_title = data["title"].strip()
            if len(income_title) == 0:
                return jsonify({"status": "error", "msg": "Title cannot be empty"}), 400
            if len(income_title) > 100:
                return jsonify({"status": "error", "msg": "Title too long"}), 400

        if 'amount' in data:
            if float(data['amount']) < 0:
                return jsonify({"status":"error", "msg": "Amount cannot be negative"}), 400
            
        if 'frequency' in data:
            if data['frequency'] not in ["weekly", "biweekly", "monthly", "yearly"]:
                return jsonify({"status":"error", "msg": "Frquency must be 'weekly', 'biweekly', 'monthly', or 'yearly'"}), 400

        # Update the income fields if provided and validated
        income.title = data.get("title", income.title)
        income.amount = data.get("amount", income.amount)
        income.frequency = data.get("frequency", income.frequency)

        db.session.commit()
        return jsonify({"msg":"Income updated successfully", "updated_income":income.to_json()}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Get all initial incomes for a user
@initial_bp.route("/api/users/<int:user_id>/initial-incomes", methods=["GET"])
def get_all_initial_incomes(user_id):
    try:
        user = Users.query.get(user_id)
        if user is None:
            return jsonify({"status":"error", "msg":"User not found"}), 404
        
        incomes = [income.to_json() for income in user.initial_incomes]
        return jsonify(incomes), 200
    
    except Exception as e:
        return jsonify({"error":str(e)}), 500
    
# Get specific initial income
@initial_bp.route("/api/users/<int:user_id>/initial-incomes/<int:income_id>", methods=["GET"])
def get_specific_income(user_id, income_id):
        income = InitialIncome.query.filter_by(id=income_id, user_id=user_id).first()
        if not income:
            return jsonify({"status":"error", "msg": "Income not found"}), 404
        
        return jsonify(income.to_json())

# Delete an initial income
@initial_bp.route("/api/users/<int:user_id>/initial-incomes/<int:income_id>", methods=["DELETE"])
def delete_initial_income(user_id, income_id):
    try:
        income = InitialIncome.query.filter_by(id=income_id, user_id=user_id).first()
        if not income:
            return jsonify({"status":"error", "msg": "Income not found"}), 404
        
        db.session.delete(income)
        db.session.commit()
        return jsonify({"msg": "Income deleted successfully", "deleted_income":income.to_json()}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Add initial expense for user (before budget creation)
@initial_bp.route("/api/users/<int:user_id>/initial-expenses", methods=["POST"])
def add_initial_expense(user_id):
    try:
        user = Users.query.get(user_id)
        if user is None:
            return jsonify({"status":"error", "msg":"User not found"}), 404
        
        data = request.json

        # Validate required fields
        required_fields = ["title", "amount", "frequency"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({"status":"error", "msg":f'Missing required field: {', '.join(missing_fields)}'}), 400
        
        if float(data['amount']) < 0:
            return jsonify({"status":"error","msg": "Amount cannot be negative"}), 400
        
        expense_title = data["title"].strip()
        if len(expense_title) == 0:
            return jsonify({"status": "error", "msg": "Title cannot be empty"}), 400
        if len(expense_title) > 100:
            return jsonify({"status": "error", "msg": "Title too long"}), 400

        if data['frequency'] not in ["weekly", "biweekly", "monthly", "yearly"]:
            return jsonify({"status":"error", "msg": "Frquency must be 'weekly', 'biweekly', 'monthly', or 'yearly'"}), 400

        # Create new expense category
        new_expense = InitialExpense(title=data['title'], amount=data['amount'], frequency=data['frequency'], user_id=user_id)
        db.session.add(new_expense)
        db.session.commit()

        return jsonify(new_expense.to_json()), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error":str(e)}), 500
    
# Update an Expense Category
@initial_bp.route("/api/users/<int:user_id>/initial-expenses/<int:expense_id>", methods=["PATCH"])
def update_initial_expense(user_id, expense_id):
    try:
        expense = InitialExpense.query.filter_by(id=expense_id, user_id=user_id).first()
        if not expense:
            return jsonify({"status":"error", "msg": "Expense not found"}), 404
        
        data = request.json

        if 'amount' in data:
            if float(data['amount']) < 0:
                return jsonify({"status":"error", "msg": "Amount cannot be negative"}), 400
        
        if 'title' in data:
            expense_title = data["title"].strip()
            if len(expense_title) == 0:
                return jsonify({"status": "error", "msg": "Title cannot be empty"}), 400
            if len(expense_title) > 100:
                return jsonify({"status": "error", "msg": "Title too long"}), 400

        if 'frequency' in data:
            if data['frequency'] not in ["weekly", "biweekly", "monthly", "yearly"]:
                return jsonify({"status":"error", "msg": "Frquency must be 'weekly', 'biweekly', 'monthly', or 'yearly'"}), 400

        # Update the expense fields if provided and validated
        expense.title = data.get("title", expense.title)
        expense.amount = data.get("amount", expense.amount)
        expense.frequency = data.get("frequency", expense.frequency)

        db.session.commit()
        return jsonify(expense.to_json()), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Get all initial expenses for a user
@initial_bp.route("/api/users/<int:user_id>/initial-expenses", methods=["GET"])
def get_all_initial_expenses(user_id):
    try:
        user = Users.query.get(user_id)
        if user is None:
            return jsonify({"status":"error", "msg":"User not found"}), 404
        
        expenses = [expense.to_json() for expense in user.initial_expenses]
        return jsonify(expenses), 200
    
    except Exception as e:
        return jsonify({"error":str(e)}), 500

# Get specific initial expense
@initial_bp.route("/api/users/<int:user_id>/initial-expenses/<int:expense_id>", methods=["GET"])
def get_specific_expense(user_id, expense_id):
        expense = InitialExpense.query.filter_by(id=expense_id, user_id=user_id).first()
        if not expense:
            return jsonify({"status":"error", "msg": "Expense not found"}), 404
        
        return jsonify(expense.to_json())
    
# Delete an initial expense
@initial_bp.route("/api/users/<int:user_id>/initial-expenses/<int:expense_id>", methods=["DELETE"])
def delete_initial_expense(user_id, expense_id):
    try:
        expense = InitialExpense.query.filter_by(id=expense_id, user_id=user_id).first()
        if not expense:
            return jsonify({"status":"error", "msg": "Expense not found"}), 404
        
        db.session.delete(expense)
        db.session.commit()
        return jsonify({"msg": "Expense deleted successfully", "deleted_expense":expense.to_json()}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
