# purchase_routes.py by Eden Pardo
from flask import Blueprint, request, jsonify
from models import Purchase, Budget, BudgetExpense
from pyf_budget_routes import pyf_purchase_calculation
from extensions import db

purchase_bp = Blueprint('purchase', __name__)

# Create a purchase (linked or unlinked to an expense)
@purchase_bp.route("/api/budgets/<int:budget_id>/purchases", methods=["POST"])
def create_purchase(budget_id):
    try:
        budget = Budget.query.get(budget_id)
        if not budget:
            return jsonify({"status": "error", "msg": "Budget not found"}), 404

        data = request.json

        # Validate required fields
        required_fields = ["title", "amount"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({"status":"error", "msg":f'Missing required field: {', '.join(missing_fields)}'}), 400

        if float(data['amount']) < 0:
            return jsonify({"status": "error", "msg": "Amount cannot be negative"}), 400

        purchase_title = data["title"].strip()
        if len(purchase_title) == 0:
            return jsonify({"status": "error", "msg": "Title cannot be empty"}), 400
        if len(purchase_title) > 100:
            return jsonify({"status": "error", "msg": "Title too long"}), 400

        # Check if a budget expense is linked
        expense_id = data.get("budget_expense_id")
        expense = None
        if expense_id:
            expense = BudgetExpense.query.filter_by(id=expense_id, budget_id=budget_id).first()
            if not expense:
                return jsonify({"status": "error", "msg": "Linked Budget Expense not found"}), 404

        # Create the purchase
        new_purchase = Purchase(
            title=data['title'],
            amount=float(data['amount']),
            budget_id=budget_id,
            budget_expense_id=expense_id
        )
        db.session.add(new_purchase)
        db.session.commit()

        if budget.method.lower() == "pay-yourself-first":
            recalculation, status = pyf_purchase_calculation(budget_id)

        return jsonify({
            "msg": "Purchase created successfully",
            "purchase": new_purchase.to_json(),
            "recalculation": recalculation
            }), status

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Update a purchase
@purchase_bp.route("/api/budgets/<int:budget_id>/purchases/<int:purchase_id>", methods=["PATCH"])
def update_purchase(budget_id, purchase_id):
    try:
        purchase = Purchase.query.filter_by(id=purchase_id, budget_id=budget_id).first()
        if not purchase:
            return jsonify({"status": "error", "msg": "Purchase not found"}), 404

        data = request.json

        if 'amount' in data and float(data['amount']) < 0:
            return jsonify({"status": "error", "msg": "Amount cannot be negative"}), 400

        if 'title' in data:
            purchase_title = data["title"].strip()
            if len(purchase_title) == 0:
                return jsonify({"status": "error", "msg": "Title cannot be empty"}), 400
            if len(purchase_title) > 100:
                return jsonify({"status": "error", "msg": "Title too long"}), 400

        # Update fields if provided
        purchase.title = data.get("title", purchase.title)
        purchase.amount = float(data.get("amount", purchase.amount))

        # Update linked budget expense (if provided)
        if "budget_expense_id" in data:
            new_expense_id = data["budget_expense_id"]

        # None = unlink the purchase
        if new_expense_id is None:
            purchase.budget_expense_id = None
        else:
            # Validate expense exists and belongs to the budget
            new_expense = BudgetExpense.query.filter_by(
                id=new_expense_id,
                budget_id=budget_id
            ).first()
            if not new_expense:
                return jsonify({
                "status": "error",
                "msg": f"Expense with ID {new_expense_id} not found in this budget."
            }), 404
            purchase.budget_expense_id = new_expense.id

        db.session.commit()

        budget = Budget.query.get(budget_id)
        if not budget:
            return jsonify({"status": "error", "msg": "Budget not found"}), 404

        if budget.method.lower() == "pay-yourself-first":
            recalculation, status = pyf_purchase_calculation(budget_id)

        return jsonify({
            "msg": "Purchase updated successfully",
            "purchase": purchase.to_json(),
            "recalculation": recalculation
        }), status

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Get all purchases for a budget
@purchase_bp.route("/api/budgets/<int:budget_id>/purchases", methods=["GET"])
def get_all_purchases(budget_id):
    try:
        purchases = Purchase.query.filter_by(budget_id=budget_id).all()
        if not purchases:
            return jsonify({"msg": "User has made no purchases."}), 200
        return jsonify([purchase.to_json() for purchase in purchases]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get a specific purchase for a budget
@purchase_bp.route("/api/budgets/<int:budget_id>/purchases/<int:purchase_id>", methods=["GET"])
def get_specific_purchase(budget_id, purchase_id):
    try:
        purchase = Purchase.query.filter_by(id=purchase_id, budget_id=budget_id).first()
        if not purchase:
            return jsonify({"status": "error", "msg": "Purchase not found"}), 404
        return jsonify(purchase.to_json()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Delete a purchase
@purchase_bp.route("/api/budgets/<int:budget_id>/purchases/<int:purchase_id>", methods=["DELETE"])
def delete_purchase(budget_id, purchase_id):
    try:
        purchase = Purchase.query.filter_by(id=purchase_id, budget_id=budget_id).first()
        if not purchase:
            return jsonify({"status": "error", "msg": "Purchase not found"}), 404
        
        budget = Budget.query.get(budget_id)
        if not budget:
            return jsonify({"status": "error", "msg": "Budget not found"}), 404

        deleted_purchase_data = purchase.to_json()

        db.session.delete(purchase)
        db.session.commit()

        if budget.method.lower() == "pay-yourself-first":
            recalculation, status = pyf_purchase_calculation(budget_id)

        return jsonify({
            "msg": "Purchase deleted successfully",
            "deleted_purchase": deleted_purchase_data,
            "recalculation": recalculation
        }), status

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500