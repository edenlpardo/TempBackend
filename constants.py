# constants.py by Eden Pardo

# Valid frequencies for incomes/expenses
VALID_FREQUENCIES = ["weekly", "biweekly", "monthly", "yearly"]

# Mapping of frequency to number of weeks
VALID_PERIODS = {
    "weekly": 1,
    "biweekly": 2,
    "monthly": 4,
    "yearly": 52
}

# Valid category types for expenses
VALID_CATEGORIES_503020 = ["Necessities", "Wants", "Savings"]

# Valid budget methods
VALID_METHODS = ["50-30-20", "zero-based", "pay-yourself-first"]
