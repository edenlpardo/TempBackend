# budget_item_routes.py by Eden Pardo
from flask import Blueprint, request, jsonify, redirect, url_for
from models import Budget, BudgetExpense, BudgetIncome, Category
from constants import VALID_FREQUENCIES, VALID_PERIODS, VALID_CATEGORIES_503020, VALID_METHODS
import base_budget_routes
from utils import normalize_to_weekly
from pyf_budget_routes import pyf_purchase_calculation
from extensions import db

budget_item_bp = Blueprint('budget_items', __name__)

# Add Budget Income for user
@budget_item_bp.route("/api/budgets/<int:budget_id>/budget-incomes", methods=["POST"])
def add_budget_income(budget_id):
    try:
        budget = Budget.query.get(budget_id)
        if budget is None:
            return jsonify({"status":"error", "msg":"Budget not found"}), 404
        
        data = request.json

        # Validate required fields
        required_fields = ["title", "amount", "frequency"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({"status":"error", "msg":f'Missing required field: {', '.join(missing_fields)}'}), 400
        
        # Validation
        income_title = data["title"].strip()
        if len(income_title) == 0:
            return jsonify({"status": "error", "msg": "Title cannot be empty"}), 400
        if len(income_title) > 100:
            return jsonify({"status": "error", "msg": "Title too long"}), 400

        income_amount = float(data["amount"])
        if income_amount < 0:
            return jsonify({"status": "error", "msg": "Amount cannot be negative"}), 400

        income_frequency = data["frequency"].lower()
        if income_frequency not in VALID_FREQUENCIES:
            return jsonify({"status": "error", "msg": "Invalid frequency"}), 400

        # Normalize if needed
        budget_period = budget.period.lower()
        if income_frequency != budget_period:
            weekly = normalize_to_weekly(income_amount, income_frequency, VALID_PERIODS)
            income_amount = weekly * VALID_PERIODS[budget_period]
            income_frequency = budget_period

        new_income = BudgetIncome(
            title=data['title'],
            amount=income_amount,
            frequency=income_frequency,
            budget_id=budget_id
        )

        db.session.add(new_income)
        db.session.commit()

        # Trigger budget recalculations
        recalculation = None
        status = 201
        if budget.method.lower() == "pay-yourself-first":
            recalculation, status = pyf_purchase_calculation(budget_id)

        return jsonify({
            "msg": "Budget Income created successfully",
            "new_income": new_income.to_json(),
            "recalculation": recalculation
        }), status
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error":str(e)}), 500
    
# Update a Budget Income
@budget_item_bp.route("/api/budgets/<int:budget_id>/budget-incomes/<int:budget_income_id>", methods=["PATCH"])
def update_budget_income(budget_id, budget_income_id):
    try:
        income = BudgetIncome.query.filter_by(id=budget_income_id, budget_id=budget_id).first()
        if not income:
            return jsonify({"status":"error", "msg": "Budget Income not found"}), 404
        
        data = request.json

        # Validate required fields (if updated)
        updated_amount = income.amount
        updated_frequency = income.frequency

        if "amount" in data:
            updated_amount = float(data["amount"])
            if updated_amount < 0:
                return jsonify({"status": "error", "msg": "Amount cannot be negative"}), 400

        if "frequency" in data:
            freq = data["frequency"].lower()
            if freq not in VALID_FREQUENCIES:
                return jsonify({"status": "error", "msg": "Invalid frequency"}), 400
            updated_frequency = freq

        if "title" in data:
            income_title = data["title"].strip()
            if len(income_title) == 0:
                return jsonify({"status": "error", "msg": "Title cannot be empty"}), 400
            if len(income_title) > 100:
                return jsonify({"status": "error", "msg": "Title too long"}), 400
            income.title = data["title"]

        # Normalize if needed
        budget = Budget.query.get(budget_id)
        budget_period = budget.period.lower()
        if updated_frequency != budget_period:
            weekly = normalize_to_weekly(updated_amount, updated_frequency, VALID_PERIODS)
            updated_amount = weekly * VALID_PERIODS[budget_period]
            updated_frequency = budget_period

        # Assign normalized or updated values
        income.amount = updated_amount
        income.frequency = updated_frequency

        db.session.commit()

        # Trigger budget recalculations
        recalculation = None
        status = 200
        if budget.method.lower() == "pay-yourself-first":
            recalculation, status = pyf_purchase_calculation(budget_id)

        return jsonify({
            "msg": "Budget Income updated successfully",
            "updated_income": income.to_json(),
            "recalculation": recalculation
        }), status
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Get all incomes for a budget
@budget_item_bp.route("/api/budgets/<int:budget_id>/budget-incomes", methods=["GET"])
def get_all_budget_incomes(budget_id):
    try:
        budget = Budget.query.get(budget_id)
        if budget is None:
            return jsonify({"status":"error", "msg":"Budget not found"}), 404
        
        incomes = [income.to_json() for income in budget.incomes]
        return jsonify(incomes), 200
    
    except Exception as e:
        return jsonify({"error":str(e)}), 500
    
# Get specific income for a budget
@budget_item_bp.route("/api/budgets/<int:budget_id>/budget-incomes/<int:budget_income_id>", methods=["GET"])
def get_specific_income(budget_id, budget_income_id):
        income = BudgetIncome.query.filter_by(id=budget_income_id, budget_id=budget_id).first()
        if not income:
            return jsonify({"status":"error", "msg": "Budget Income not found"}), 404
        
        return jsonify(income.to_json())

# Delete a Budget Income
@budget_item_bp.route("/api/budgets/<int:budget_id>/budget-incomes/<int:budget_income_id>", methods=["DELETE"])
def delete_budget_income(budget_id, budget_income_id):
    try:
        income = BudgetIncome.query.filter_by(id=budget_income_id, budget_id=budget_id).first()
        if not income:
            return jsonify({"status":"error", "msg": "Budget Income not found"}), 404
        
        db.session.delete(income)
        db.session.commit()
        return jsonify({"msg": "Budget Income deleted successfully", "deleted_income":income.to_json()}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# Add expense for a budget
@budget_item_bp.route("/api/budgets/<int:budget_id>/budget-expenses", methods=["POST"])
def add_budget_expense(budget_id):
    try:
        budget = Budget.query.get(budget_id)
        if budget is None:
            return jsonify({"status":"error", "msg": "Budget not found"}), 404
        
        data = request.json

        # Validate required fields
        required_fields = ["title", "amount", "frequency", "category_type"]
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

        if data['frequency'] not in VALID_FREQUENCIES:
            return jsonify({"status":"error", "msg": "Frquency must be 'weekly', 'biweekly', 'monthly', or 'yearly'"}), 400
        
        # Normalize amount if frequency does not match budget's period
        expense_amount = float(data['amount'])
        expense_frequency = data['frequency'].lower()
        budget_period = budget.period.lower()

        # Convert amount if frequency does not match budget period
        if budget_period != expense_frequency:
            weekly_amount = normalize_to_weekly(expense_amount, expense_frequency, VALID_PERIODS)
            # Scale up to match budget period
            expense_amount = weekly_amount * VALID_PERIODS[budget_period]
            expense_frequency = budget_period
        
        # Validate categories: Find matching category in budget
        category = Category.query.filter_by(
            budget_id=budget_id,
            title=data['category_type']
        ).first()

        if not category:
            return jsonify({"error": f"Category '{data['category_type']}' does not exist in this budget. Please create it first."}), 400

        # Create new expense category
        new_expense = BudgetExpense(title=data['title'], amount=expense_amount, frequency=expense_frequency, budget_id=budget_id, category_id=category.id)
        db.session.add(new_expense)
        db.session.commit()

        # Trigger budget recalculations
        if budget.method.lower() == "pay-yourself-first":
            recalculation, status = pyf_purchase_calculation(budget_id)
        else:
            recalculation = None
            status = 200

        return jsonify({
            "msg": "Expense added successfully",
            "new_expense": new_expense.to_json(),
            "recalculation": recalculation
        }), status
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error":str(e)}), 500
    
# Update a budget expense
@budget_item_bp.route("/api/budgets/<int:budget_id>/budget-expenses/<int:budget_expense_id>", methods=["PATCH"])
def update_budget_expense(budget_id, budget_expense_id):
    try:
        expense = BudgetExpense.query.filter_by(id=budget_expense_id, budget_id=budget_id).first()
        if not expense:
            return jsonify({"status":"error", "msg": "Expense not found"}), 404
        
        data = request.json

        updated_amount = expense.amount
        updated_frequency = expense.frequency

        if 'amount' in data:
            updated_amount = float(data['amount'])
            if updated_amount < 0:
                return jsonify({"status":"error","msg": "Amount cannot be negative"}), 400
        
        if 'title' in data:
            expense_title = data["title"].strip()
            if len(expense_title) == 0:
                return jsonify({"status": "error", "msg": "Title cannot be empty"}), 400
            if len(expense_title) > 100:
                return jsonify({"status": "error", "msg": "Title too long"}), 400
            expense.title = data['title']

        if 'frequency' in data:
            freq = data['frequency'].lower()
            if freq not in VALID_FREQUENCIES:
                return jsonify({"status":"error", "msg": "Frquency must be 'weekly', 'biweekly', 'monthly', or 'yearly'"}), 400
            updated_frequency = freq

        budget = Budget.query.get(budget_id)
        budget_period = budget.period.lower()
        # Normalize amount if frequency does not match budget's period
        if updated_frequency != budget_period:
            weekly_amount = normalize_to_weekly(updated_amount, updated_frequency, VALID_PERIODS)
            # Scale up to match budget period
            updated_amount = weekly_amount * VALID_PERIODS[budget_period]
            updated_frequency = budget_period
            
        expense.amount = updated_amount
        expense.frequency = updated_frequency
        
        # Validate categories: Find matching category in budget
        if 'category_type' in data:
            category = Category.query.filter_by(
                budget_id=budget_id,
                title=data['category_type']
            ).first()
            if not category:
                return jsonify({"error": f"Category '{data['category_type']}' does not exist in this budget. Please create it first."}), 400
            expense.category_id = category.id

        db.session.commit()

        # Trigger budget recalculations
        if budget.method.lower() == "pay-yourself-first":
            recalculation, status = pyf_purchase_calculation(budget_id)
        else:
            recalculation = None
            status = 200

        return jsonify({
            "msg": "Expense updated successfully",
            "expense": expense.to_json(),
            "recalculation": recalculation
        }), status

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Get all expenses for a budget
@budget_item_bp.route("/api/budgets/<int:budget_id>/budget-expenses", methods=["GET"])
def get_all_budget_expenses(budget_id):
    try:
        budget = Budget.query.get(budget_id)
        if budget is None:
            return jsonify({"status":"error", "msg":"Budget not found"}), 404
        
        expenses = [expense.to_json() for expense in budget.expenses]
        return jsonify(expenses), 200
    
    except Exception as e:
        return jsonify({"error":str(e)}), 500

# Get specific Budget Expense
@budget_item_bp.route("/api/budgets/<int:budget_id>/budget-expenses/<int:budget_expense_id>", methods=["GET"])
def get_specific_budget_expense(budget_id, expense_id):
        expense = BudgetExpense.query.filter_by(id=expense_id, budget_id=budget_id).first()
        if not expense:
            return jsonify({"status":"error", "msg": "Expense not found"}), 404
        
        return jsonify(expense.to_json())
    
# Delete a Budget Expense
@budget_item_bp.route("/api/budgets/<int:budget_id>/budget-expenses/<int:budget_expense_id>", methods=["DELETE"])
def delete_budget_expense(budget_id, budget_expense_id):
    try:
        expense = BudgetExpense.query.filter_by(id=budget_expense_id, budget_id=budget_id).first()
        if not expense:
            return jsonify({"status":"error", "msg": "Expense not found"}), 404
        
        db.session.delete(expense)
        db.session.commit()

        budget = Budget.query.get(budget_id)
        if budget is None:
            return jsonify({"status":"error", "msg":"Budget not found"}), 404

        # Trigger budget recalculations
        if budget.method.lower() == "pay-yourself-first":
            recalculation, status = pyf_purchase_calculation(budget_id)
        else:
            recalculation = None
            status = 200

        return jsonify({
            "msg": "Expense deleted successfully",
            "deleted_expense": expense.to_json(),
            "recalculation": recalculation
        }), status
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500