# pyf_budget_routes.py by Eden Pardo
from flask import Blueprint, request, jsonify
from models import Purchase, BudgetExpense, Budget, Category
from extensions import db
from constants import VALID_PERIODS

def create_base_savings_category(budget_id):
    try:
        budget = Budget.query.get(budget_id)
        if not budget:
            raise ValueError("Budget not found")

        savings_category = Category(
            title="Savings",
            priority=1,
            budget_id=budget.id,
            description="The Pay-Yourself-First Budgeting method requires a Savings category.",
            allocated_amount=0,
            is_savings=True
        )
        db.session.add(savings_category)
        db.session.flush()  # Save category without committing yet
        return savings_category

    except Exception as e:
        raise e

# Initial budget setup and allocations (when new categories are made)
def pyf_allocation_calculation(budget_id):
    try:
        # Load Budget
        budget = Budget.query.get(budget_id)
        if not budget:
            return {"status": "error", "msg": "Budget not found"}, 404

        # Calculate total income and total expenses
        total_income = sum(income.amount for income in budget.incomes)
        total_expenses = sum(expense.amount for expense in budget.expenses)

        # Check that expenses do not exceed income
        if total_expenses > total_income:
            return {
               "status": "error",
                "msg": f"Expenses exceed income by ${total_expenses - total_income:.2f}. Adjust your expenses."
            }, 400

        # Check that Savings category exists and has an allocation
        savings_category = next((c for c in budget.categories if c.is_savings), None)
        if not savings_category:
            return {"status": "error", "msg": "Savings category not found. Required for PYF budgeting."}, 400
        if savings_category.allocated_amount <= 0:
            return {"status": "error", "msg": "Savings category has no allocated amount."}, 400
        
        # Build category allocations output
        categories_info = []
        for category in budget.categories:
            categories_info.append({
                    "title": category.title,
                    "allocated_amount": category.allocated_amount,
                    "priority": category.priority
                })
        
        return {
            "status": "validated",
                "total_income": total_income,
                "total_expenses": total_expenses,
                "categories": categories_info
        }, 200

    except Exception as e:
        return {"status": "error", "msg": str(e)}, 500

def  pyf_purchase_calculation(budget_id):
    try:
        recommendations = []

        ## 1. Setup --> Loads all budget data
        # Retrieve budget
        budget = Budget.query.get(budget_id)
        if not budget:
            return {"status": "error", "msg": "Budget not found"}, 404
        
        # Retrieve all purchases linked to the budget
        purchases = Purchase.query.filter_by(budget_id=budget_id).order_by(Purchase.date).all()
        if not purchases:
            return {"status": "ok", "msg": "No purchases made yet."}, 200
        
        # Retrieve all categories and expenses
        categories = Category.query.filter_by(budget_id=budget_id).all()
        expenses = BudgetExpense.query.filter_by(budget_id=budget_id).all()

        # Find Savings category (PYF focuses on Savings category)
        savings_category = next((c for c in categories if c.is_savings), None)
        if not savings_category:
            return {"status": "error", "msg": "Savings category not found"}, 400
        
        expense_lookup = {e.id: e for e in expenses}

        ## 2. First Purchase check --> Savings?
        first_purchase = purchases[0] # Ordered by date above
        first_purchase_expense = None
        if first_purchase.budget_expense_id:
            first_purchase_expense = BudgetExpense.query.get(first_purchase.budget_expense_id)

        # Check if the first purchse went to Savings Expense (and Category)
        if first_purchase_expense and first_purchase_expense.category_id == savings_category.id:
            # Good: First purchase went to Savings
            pass
        else:
            recommendations.append("First purchase was not made towards Savings. Remember to prioritize Savings first.")

        ## 3. Savings fully paid --> Goal met?
        total_spent_on_savings = 0

        # Calculate total amount spent (purchased) on Savings
        for purchase in purchases:
            if purchase.budget_expense_id:
                linked_expense = expense_lookup.get(purchase.budget_expense_id)
                if linked_expense and linked_expense.category_id == savings_category.id:
                    total_spent_on_savings += purchase.amount
        
        # Compare total Savings Purchases to Savings allocation
        if total_spent_on_savings < savings_category.allocated_amount:
            recommendations.append(
                f'Savings goal not fully funded yet. ${ savings_category.allocated_amount - total_spent_on_savings:.2f} remaining.')

        ## 4. Check for overspending

        # Calculate total spent (all purchases regardless of link)
        total_spent = sum(p.amount for p in purchases)
        # Check if user spent more than their income
        total_income = sum(income.amount for income in budget.incomes)
        if total_spent > total_income:
            recommendations.append(
                f"Warning: You have exceeded your total income for this budget period by ${total_spent - total_income:.2f}."
            )

        # Map: category_id-->total spent
        category_spending = {}

        # For each purchase, if it's linked to an expense and category, it adds the amount
        for purchase in purchases:
            if purchase.budget_expense_id:
                linked_expense = expense_lookup.get(purchase.budget_expense_id)
                if linked_expense:
                    category_id = linked_expense.category_id
                    if category_id:
                        category_spending[category_id] = category_spending.get(category_id, 0) + purchase.amount

        # Check spending against each category's allocation
        for category in categories:
            spent = category_spending.get(category.id, 0)
            if spent > category.allocated_amount:
                overspent_amount = spent - category.allocated_amount
                recommendations.append(
                    f"Overspending detected: '{category.title}' is overspent by ${overspent_amount:.2f}"
                )
        
        ## 5. Category priority violation check --> Are lower categories being spent first?
        
        #########AM I EVEN USING THIS VARIABLE???
        # Retrieve all categories sorted by priority (lower num = higher priority)
        '''sorted_categories = sorted(categories, key=lambda c: c.priority)
        # Track whether higher-priority categories had purchases before lower-priority ones
        priorities_with_spending = sorted(priority_spending.keys())

        # Use sorted category priorities for order enforcement
        sorted_priorities = [c.priority for c in sorted_categories]

        for i, current_priority in enumerate(sorted_priorities):
            if current_priority in priorities_with_spending:
                for higher_priority in sorted_priorities[:i]:
                    if higher_priority not in priorities_with_spending:
                        recommendations.append(
                            f"Spending detected on lower-priority category (priority {current_priority}) before fully funding higher-priority category (priority {higher_priority})."
                        )'''

        # Track which priorities have had spending
        priority_spending = {}

        for purchase in purchases:
            if purchase.budget_expense_id:
                linked_expense = expense_lookup.get(purchase.budget_expense_id)
                if linked_expense and linked_expense.category_id:
                    # Find the linked category
                    linked_category = next((c for c in categories if c.id == linked_expense.category_id), None)
                    if linked_category:
                        priority_spending[linked_category.priority] = priority_spending.get(linked_category.priority, 0) + purchase.amount
        
        # Check if any lower-priority category has spending before higher ones
        seen_priorities = sorted(priority_spending.keys())

        for idx, priority in enumerate(seen_priorities):
            # For each priority spent, check if there were any earlier (more important) priorities missing
            for higher_priority in range(1, priority):
                if higher_priority not in priority_spending:
                    recommendations.append(
                        f"Spending detected on lower-priority category (priority {priority}) before fully funding higher-priority category (priority {higher_priority})."
                    )

        ## 6. Unexpected Purchase check
        for purchase in purchases:
            if not purchase.budget_expense_id:
                recommendations.append(
                    f"Unexpected purchase detected: '{purchase.title}' is not linked to any planned expense. Recommend adjusting lower-priority allocations to account for imbalance."
                )
        
        if not recommendations:
            recommendations.append("Nice! No budgeting issues detected.")
        return {
            "status": "analyzed",
            "recommendations": recommendations
        }, 200

    except Exception as e:
        return {"status": "error", "msg": str(e)}, 500

# THE PURCHASES ACT AS THE TRACKER BECAUSE THEY CAN SEE WHAT THEY SPENT IN EACH CATEGORY


pyf_budget_bp = Blueprint('pyf_budget', __name__)

@pyf_budget_bp.route("/api/budgets/<int:budget_id>/pay-yourself-first-budget", methods=["POST"])
def create_pyf_budget_route(budget_id):
    try:
        savings_category = create_base_savings_category(budget_id)
        db.session.commit()
        return jsonify({
            "msg": "Savings category created successfully.",
            "savings_category": savings_category.to_json()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
