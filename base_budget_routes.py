# base_budget_routes.py by Eden Pardo
from flask import Blueprint, request, jsonify
from models import Users, Budget, InitialExpense, InitialIncome, BudgetExpense, BudgetIncome
from constants import VALID_FREQUENCIES, VALID_PERIODS, VALID_CATEGORIES_503020, VALID_METHODS
from pyf_budget_routes import create_base_savings_category
from utils import normalize_to_weekly
from extensions import db
from copy import deepcopy

base_budget_bp = Blueprint("budget", __name__)

# Create a Budget
@base_budget_bp.route("/api/users/<int:user_id>/budget", methods=["POST"])
def create_budget(user_id):
    try:
        # 1. Validate user exists
        user = Users.query.get(user_id)
        if not user:
            return jsonify({"status":"error", "msg": "User not found"}), 404

        data = request.json

        # 2. Validate required fields
        required_fields = ["title", "method"] # providing period is optional
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({"status":"error", "msg":f"Missing required field: {', '.join(missing_fields)}"}), 400
        
        budget_title = data["title"].strip()
        if len(budget_title) == 0:
            return jsonify({"status": "error", "msg": "Title cannot be empty"}), 400
        if len(budget_title) > 100:
            return jsonify({"status": "error", "msg": "Title too long"}), 400

        # 3. Validate budget method
        if data['method'].lower() not in VALID_METHODS:
            return jsonify({
                "status":"error", "msg": "Invalid budget method",
                "valid_methods": VALID_METHODS
            }), 400

        # 4. Validate Initial Data Exists
        if not user.initial_expenses or not user.initial_incomes:
            return jsonify({
                "status":"error",
                "msg": "Need both initial expenses and initial income(s) before creating a budget"
            }), 400

        # Determine budget period based on user input OR income(s) frequency
        if "period" in data:
            chosen_period = data["period"].lower()
            if chosen_period not in VALID_PERIODS:
                return jsonify({
                    "status": "error",
                    "msg": f"Invalid period '{data['period']}'. Valid options are: {', '.join(VALID_PERIODS.keys())}"
                }), 400
            budget_period = chosen_period
        else:
            frequencies = {income.frequency.lower() for income in user.initial_incomes}
            # Case 1: All initial incomes have the same frequency
            if len(frequencies) == 1:
                budget_period = user.initial_incomes[0].frequency
            # Case 2: Mixed frequencies --> Normalize to weekly
            else:
                budget_period = "weekly"
        
        new_budget = Budget(user_id=user_id, title=data['title'], method=data['method'], period=budget_period)
        db.session.add(new_budget)
        db.session.flush() # Get the current budget ID

        # Copy initial expenses to budget expenses
        for expense in user.initial_expenses:
            expense_data = {
                    'budget_id':new_budget.id,
                    'title':expense.title,
                    'amount':expense.amount,
                    'frequency':expense.frequency,
                    #category_type=expense.category_type
                    }
            # Convert amount if frequency does not match budget period
            if budget_period.lower() != expense.frequency.lower():
                weekly_amount = normalize_to_weekly(expense.amount, expense.frequency, VALID_PERIODS)
                expense_data['amount'] = weekly_amount * VALID_PERIODS[budget_period]
                expense_data['frequency'] = budget_period
                #category_type=expense.category_type
            budget_expense = BudgetExpense(**expense_data)
            db.session.add(budget_expense)

        # Copy initial income(s) to budget income(s)
        # Convert income(s) to match budget period if needed
        for income in user.initial_incomes:
            income_data = {
                    'budget_id':new_budget.id,
                    'title':income.title,
                    'amount':income.amount,
                    'frequency':income.frequency
                    }
            # Convert income(s) to match budget period if needed
            if budget_period.lower() != income.frequency.lower():
                weekly_amount = normalize_to_weekly(income.amount, income.frequency, VALID_PERIODS)
                income_data['amount'] = weekly_amount * VALID_PERIODS[budget_period]
                income_data['frequency'] = budget_period

            budget_income = BudgetIncome(**income_data)
            db.session.add(budget_income)
        
        db.session.commit()
        
        if new_budget.method.lower() == "pay-yourself-first":
            # Creating required Savings category
            create_base_savings_category(new_budget.id)
            savings_category = next((c for c in new_budget.categories if c.is_savings), None)
            # Linking all expenses to Savings to begin
            if not savings_category:
                raise Exception("Savings category not found after creation.")

            for expense in new_budget.expenses:
                expense.category_id = savings_category.id
            
            db.session.commit()

        ###### calculate after categories are assigned --> Calculation is based on which calculation method is called
        #calculate_budget(user_id, new_budget.id)


        return jsonify({"msg":f'Budget created successfully', "budget":new_budget.to_json()}), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error":str(e)}), 500
    
@base_budget_bp.route("/api/users/<int:user_id>/budgets/<int:budget_id>", methods=["PATCH"])
def update_budget(user_id, budget_id):
    try:
        budget = Budget.query.filter_by(id=budget_id, user_id=user_id).first()
        if not budget:
            return jsonify({"status": "error", "msg": "Budget not found"}), 404

        data = request.json

        if 'title' not in data:
            return jsonify({"status": "error", "msg": "Missing field: 'title'"}), 400

        # Validate title length
        new_title = data['title'].strip()
        if len(new_title) == 0:
            return jsonify({"status": "error", "msg": "Title cannot be empty"}), 400
        if len(new_title) > 100:
            return jsonify({"status": "error", "msg": "Title too long (max 100 chars)"}), 400

        budget.title = new_title
        db.session.commit()

        return jsonify({
            "msg": "Budget updated successfully",
            "updated_budget": budget.to_json()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

'''@budget_bp.route("/api/users/<int:user_id>/budgets/<int:budget_id>/calculate", methods=["POST", "GET"])
def calculate_budget(user_id, budget_id):
    try:
        # Get budget with ownership check
        budget = Budget.query.filter_by(
            id=budget_id,
            user_id=user_id
        ).first()
        
        if not budget:
            return jsonify({"error": "Budget not found or access denied"}), 404
        
        # Route to the appropriate calculator
        calculators = {
            '50-30-20': calculate_50_30_20,
            'zero-based': calculate_zero_based,
            'pay-yourself-first': calculate_pay_yourself_first
        }
        
        if budget.method not in calculators:
            return jsonify({"error": "Unsupported budget method"}), 400
            
        # Pass budget_id instead of budget object
        return calculators[budget.method](budget_id)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500'''

# Get all Budgets for a User
@base_budget_bp.route("/api/users/<int:user_id>/budgets", methods=["GET"])
def get_all_budgets(user_id):
    try:
        user = Users.query.get(user_id)
        if user is None:
            return jsonify({"status":"error", "msg":"User not found"}), 404
        
        budgets = Budget.query.filter_by(user_id=user_id).all()
        if not budgets:
            return jsonify({"msg": "User does not have a budget."}), 200
        
        return jsonify([budget.to_json() for budget in budgets]), 200
    except Exception as e:
        return jsonify({"error":str(e)}), 500
    
# Get specific budget for a user
@base_budget_bp.route("/api/users/<int:user_id>/budgets/<int:budget_id>", methods=["GET"])
def get_specific_budget(user_id, budget_id):
        budget = Budget.query.filter_by(id=budget_id, user_id=user_id).first()
        if not budget:
            return jsonify({"status":"error", "msg": "Budget not found"}), 404
        
        return jsonify(budget.to_json())

# Deleting a Budget
@base_budget_bp.route("/api/users/<int:user_id>/budgets/<int:budget_id>", methods=["DELETE"])
def delete_budget(user_id, budget_id):
    try:
        # Verify the budget exists AND belongs to the specified user
        budget = Budget.query.filter_by(id=budget_id, user_id=user_id).first()
        if not budget:
            return jsonify({"status":"error", "msg": "Budget not found"}), 404
        
        deleted_budget_data = budget.to_json()

        db.session.delete(budget)
        db.session.commit()
        return jsonify({"msg": "Budget deleted successfully", "deleted_budget":deleted_budget_data}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
'''def handle_overspending(budget_id, overspent_amount):
    budget = Budget.query.get(budget_id)
    lowest_priority_category = Category.query.filter_by(
        budget_id=budget.id
    ).order_by(Category.priority.desc()).first()
    
    # Reduce the category's allocation
    lowest_priority_category.allocated_amount -= overspent_amount
    db.session.commit()'''

'''def update_budget_recommendations(budget_id):
    budget = Budget.query.get(budget_id)
    total_income = sum(i.amount for i in budget.incomes)
    total_expenses = sum(e.amount for e in budget.expenses)
    
    # Check if overspent
    if total_expenses > total_income:
        overspent_amount = total_expenses - total_income
        lowest_priority_category = Category.query.filter_by(
            budget_id=budget.id
        ).order_by(Category.priority.desc()).first()
        
        return {
            "alert": f"Overspent by ${overspent_amount:.2f}. "
                    f"Reduce '{lowest_priority_category.title}' by this amount."
        }
    else:
        return {"status": "On track!"}'''
