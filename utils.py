# utils.py by Eden Pardo
from constants import VALID_PERIODS

# Helper function to convert amounts to weekly equivalent
def normalize_to_weekly(amount, frequency, periods):
    frequency.lower()
    if frequency not in periods:
        raise ValueError(f"Invalid frequency: {frequency}")
    return amount / periods[frequency]