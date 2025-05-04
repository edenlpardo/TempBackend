from flask import Blueprint, request, jsonify
from models import Users, Budget, InitialExpense, InitialIncome, BudgetExpense, BudgetIncome
from extensions import db
from copy import deepcopy
from base_budget_routes import* 

fiftythirtytwenty_budget_bp = Blueprint("budget", __name__)

@fiftythirtytwenty_budget_bp.route("/api/users/<int:user_id>/budget", methods=["POST"])
def create_budget(user_id):
    pass