# category_routes.py by Eden Pardo
from flask import Blueprint, request, jsonify
from models import Category, Budget, BudgetExpense
from pyf_budget_routes import pyf_allocation_calculation
from extensions import db

def is_protected_category(budget_method, category_title):
    budget_method = budget_method.lower()
    category_title = category_title.lower()

    if budget_method == "pay-yourself-first":
        return category_title == "savings"
    elif budget_method == "50-30-20":
        return category_title in ["needs", "wants", "savings"]
    return False

# Reserved priority values for each budget method
def is_reserved_priority(budget, new_priority):
    if budget.method.lower() == "pay-yourself-first":
        savings = next((c for c in budget.categories if c.is_savings), None)
        if savings and new_priority == savings.priority:
            return True
    return False

category_bp = Blueprint('category', __name__)

# Add category for a budget
@category_bp.route("/api/budgets/<int:budget_id>/categories", methods=["POST"])
def add_category(budget_id):
    try:
        budget = Budget.query.get(budget_id)
        if budget is None:
            return({"status":"error", "msg":"Budget not found"}), 404
        
        data = request.json

        # Cannot create additional categories for 50-30-20 budget
        if budget.method.lower() == "50-30-20":
            return jsonify({"status":"error", "msg":"Cannot create additional categories for 50-30-20. Only 'Needs', 'Wants', and 'Savings' allowed."}), 400
        
        # Validate required fields
        required_fields = ["title", "priority", "allocated_amount"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({"status":"error", "msg":f"Missing required field: {', '.join(missing_fields)}"}), 400
            
        # Check for duplicate category title IN THIS BUDGET
        existing_category = Category.query.filter(Category.budget_id == budget_id,
                                                  Category.title.ilike(data["title"].strip())  # Case-insensitive and trimmed
                                                ).first()
        if existing_category:
            return jsonify({"status":"error", "msg": f"\"{data['title']}\" already exists in this budget."}), 400
        
        # Title length check (required)
        title = data['title'].strip()
        if len(title) == 0:
            return jsonify({"status": "error", "msg": "Title cannot be empty"}), 400
        if len(title) > 100:
            return jsonify({"status": "error", "msg": "Title too long (max 100 chars)"}), 400
        
        # Description length check
        description = data.get("description", "").strip()  # Default to empty string if not provided
        if description and len(description) > 100:
            return jsonify({"status": "error", "msg": "Description too long (max 100 chars)"}), 400
        
        # Check that priority is a positive int
        if data['priority'] < 1:
            return jsonify({"status":"error","msg": "Priority cannot be negative"}), 400
        # Prevent using reserved priority numbers
        if is_reserved_priority(budget, data['priority']):
            return jsonify({
                "status": "error",
                "msg": f"Priority {data['priority']} is reserved for a required category and cannot be used."
            }), 400
        
        if data['allocated_amount'] < 0:
            return jsonify({"status":"error","msg": "Allocated amount cannot be negative"}), 400
        
        # Create new category (description is optional)
        new_category = Category(
            title=data['title'],
            priority=data['priority'],
            allocated_amount=data['allocated_amount'],
            budget_id=budget_id,
            description=description if description else None  # Store NULL if empty
        )
        db.session.add(new_category)
        db.session.commit()

        if budget.method.lower() == "pay-yourself-first":
            recalculation, status = pyf_allocation_calculation(budget_id)

        return jsonify({
            "msg":"Category created successfully",
            "new_income":new_category.to_json(),
            "recalculation": recalculation
            }), status
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error":str(e)}), 500

# Update a category
@category_bp.route("/api/budgets/<int:budget_id>/categories/<int:category_id>", methods=["PATCH"])
def update_category(budget_id, category_id):
    try:
        budget = Budget.query.get(budget_id)
        if budget is None:
            return jsonify({"status":"error", "msg": "Budget not found"}), 404
        
        category = Category.query.filter_by(id=category_id, budget_id=budget_id).first()
        if not category:
            return jsonify({"status":"error", "msg": "Category not found"}), 404
        
        # Check if trying to update a protected category
        if is_protected_category(budget.method, category.title):
            # Only allow updating description and allocated amount if protected
            allowed_fields = ["description", "allocated_amount"]

            for field in request.json.keys():
                if field not in allowed_fields:
                    return jsonify({"status":"error", "msg": f"Cannot change '{field}' for protected category '{category.title}'."}), 400

        data = request.json

        # Check for duplicate category title IN THIS BUDGET and validate length
        if 'title' in data:
            existing_category = Category.query.filter(Category.budget_id == budget_id,
                                                    Category.title.ilike(data["title"].strip())
                                                    ).first()
            if existing_category and existing_category.id != category.id:
                return jsonify({"status":"error", "msg": f"'{data['title']}' already exists in this budget."}), 400
            
            title = data['title'].strip()
            if len(title) == 0:
                return jsonify({"status": "error", "msg": "Title cannot be empty"}), 400
            if len(title) > 100:
                return jsonify({"status": "error", "msg": "Title too long (max 100 chars)"}), 400

        # Description length check (if provided)
        if 'description' in data:
            description = data['description'].strip()
            if description and len(description) > 100:
                return jsonify({"status": "error", "msg": "Description too long (max 100 chars)"}), 400

        # Check that priority is a positive int and it is not a reserved priority
        if 'priority' in data:
            if data['priority'] < 1:
                return jsonify({"status":"error","msg": "Priority cannot be negative"}), 400
            if is_reserved_priority(budget, data['priority']) and not category.is_savings:
                return jsonify({
                    "status": "error",
                    "msg": f"Priority {data['priority']} is reserved for a required category and cannot be used."
                }), 400
            
        # Check that priority is a positive int
        if 'allocated_amount' in data:
            allocated_amount = float(data['allocated_amount'])
            if data['allocated_amount'] < 0:
                return jsonify({"status":"error","msg": "Allocated amount cannot be negative"}), 400
        

        # Update the category fields if provided and validated
        category.title = data.get("title", category.title)
        category.description = data.get("description", description if description else None)  # Store NULL if empty
        category.priority = data.get("priority", category.priority)
        category.allocated_amount = float(data['allocated_amount']) if 'allocated_amount' in data else category.allocated_amount

        db.session.commit()

        if budget.method.lower() == "pay-yourself-first":
            recalculation, status = pyf_allocation_calculation(budget_id)

        return jsonify({
            "msg":"Category updated successfully",
            "updated_category":category.to_json(),
            "recalculation": recalculation
            }), status
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
# Get all categories for a budget
@category_bp.route("/api/budgets/<int:budget_id>/categories", methods=["GET"])
def get_all_budget_categories(budget_id):
    try:
        budget = Budget.query.get(budget_id)
        if budget is None:
            return jsonify({"status":"error", "msg":"Budget not found"}), 404
        
        categories = [category.to_json() for category in budget.categories]
        return jsonify(categories), 200
    
    except Exception as e:
        return jsonify({"error":str(e)}), 500
    
# Get specific category for a budget
@category_bp.route("/api/budgets/<int:budget_id>/categories/<int:category_id>", methods=["GET"])
def get_specific_budget_category(budget_id, category_id):
    category = Category.query.filter_by(id=category_id, budget_id=budget_id).first()
    if not category:
        return jsonify({"status":"error", "msg": "Category not found"}), 404
        
    return jsonify(category.to_json())

# Delete a category
@category_bp.route("/api/budgets/<int:budget_id>/categories/<int:category_id>", methods=["DELETE"])
def delete_category(budget_id, category_id):
    try:
        budget = Budget.query.get(budget_id)
        if budget is None:
            return jsonify({"status":"error", "msg":"Budget not found"}), 404
        
        category = Category.query.filter_by(id=category_id, budget_id=budget_id).first()
        if not category:
            return jsonify({"status":"error", "msg": "Category not found"}), 404
        
        if is_protected_category(budget.method, category.title):
            return jsonify({"status":"error", "msg": f"Cannot delete protected category '{category.title}' in {budget.method} budgeting."}), 400

        db.session.delete(category)
        db.session.commit()

        if budget.method.lower() == "pay-yourself-first":
            recalculation, status = pyf_allocation_calculation(budget_id)

        return jsonify({
            "msg": "Category deleted successfully",
            "deleted_category":category.to_json(),
            "recalculation": recalculation
            }), status
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

