# models.py by Eden Pardo
from extensions import db
from datetime import date

class Users(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100), nullable = False)
    username = db.Column(db.String(100), nullable = False)
    password = db.Column(db.String(100), nullable = False) # Store hashed passwords

    # Relationships
    initial_incomes = db.relationship("InitialIncome", backref="user", lazy=True, cascade="all, delete-orphan")
    initial_expenses = db.relationship("InitialExpense", backref="user", lazy=True, cascade="all, delete-orphan")
    budgets = db.relationship("Budget", backref="user", lazy=True, cascade="all, delete-orphan")
    
    # Taking user and convert to json
    def to_json(self):
        return{
            "id":self.id,
            "name":self.name,
            "username":self.username,
            "initial_incomes": [initial_income.to_json() for initial_income in self.initial_incomes],
            "initial_expenses": [initial_expense.to_json() for initial_expense in self.initial_expenses]
        }

class InitialIncome(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    frequency = db.Column(db.String(100), nullable=False)

    def to_json(self):
        return {
            "id": self.id,
            "title": self.title,
            "amount": self.amount,
            "frequency": self.frequency,
            "user_id": self.user_id
        }

class InitialExpense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    frequency = db.Column(db.String(100), nullable=False)

    def to_json(self):
        return {
            "id": self.id,
            "title": self.title,
            "amount": self.amount,
            "frequency": self.frequency,
            "user_id": self.user_id
        }

class Budget(db.Model):
    __tablename__ = 'budgets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(100), default=str(id))
    method = db.Column(db.String(100), nullable=False)
    period = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: date.today())
    updated_at = db.Column(db.DateTime, default=lambda: date.today(),
                           onupdate=lambda: date.today())

    expenses = db.relationship("BudgetExpense", backref="budget", lazy=True, cascade="all, delete-orphan")
    incomes = db.relationship("BudgetIncome", backref="budget", lazy=True, cascade="all, delete-orphan")
    categories = db.relationship("Category", backref="budget", lazy=True, cascade="all, delete-orphan")

    def to_json(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "budget_id": self.id,
            "title": self.title,
            "method": self.method,
            "period": self.period,
            "createdAt": self.created_at.strftime("%d/%m/%y") if self.created_at else None,
            "updatedAt": self.updated_at.strftime("%d/%m/%y") if self.updated_at else None,
            "expenses": [expense.to_json() for expense in self.expenses],
            "incomes": [income.to_json() for income in self.incomes],
            "total_income": sum(income.amount for income in self.incomes),
            "total_expenses": sum(expense.amount for expense in self.expenses),
            "all_categories": [category.to_json() for category in self.categories],
            "balance_after_expenses": sum(income.amount for income in self.incomes) - sum(expense.amount for expense in self.expenses)
        }

class BudgetExpense(db.Model):
    __tablename__ = "budget_expense"
    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey("budgets.id"), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    frequency = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True) # Allow null initially
    # Relationship to category
    category = db.relationship("Category", backref="expenses")

    def to_json(self):
        return {
            "id": self.id,
            "budget_id": self.budget_id,
            "title": self.title,
            "amount": self.amount,
            "frequency": self.frequency,
            "category_id": self.category_id,
            "category_name": self.category.title if self.category else None
        }

class BudgetIncome(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey("budgets.id"), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    frequency = db.Column(db.String(100), nullable=False)

    def to_json(self):
        return {
            "id": self.id,
            "budget_id": self.budget_id,
            "title": self.title,
            "amount": self.amount,
            "frequency": self.frequency
        }

class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey("budgets.id"), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(100), nullable=True)
    # For 50/30/20 hard code these allocations
    allocated_amount = db.Column(db.Float, nullable=False)
    priority = db.Column(db.Integer, nullable=False)
    is_savings = db.Column(db.Boolean, default=False) #Used for PYFB

    def to_json(self):
         return {
            "id": self.id,
            "budget_id": self.budget_id,
            "title": self.title,
            "description": self.description,
            "allocated_amount": self.allocated_amount,
            "priority": self.priority,
            "is_savings": self.is_savings
        }
    
class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey("budgets.id"), nullable=False)
    budget_expense_id = db.Column(db.Integer, db.ForeignKey("budget_expense.id"), nullable=True)  # NULL = uncategorized
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=lambda: date.today())

    # Relationship to BudgetExpense
    budget_expense = db.relationship("BudgetExpense", backref="purchases")

    def to_json(self):
        return {
            "id": self.id,
            "budget_id": self.budget_id,
            "title": self.title,
            "amount": self.amount,
            "date": self.date.strftime("%d/%m/%y") if self.date else None,
            "budget_expense_id": self.budget_expense_id,
            "budget_expense": self.budget_expense.title if self.budget_expense else None
        }

