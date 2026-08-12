"""Centralised configuration for the standalone market-dashboard API."""
import os
from dotenv import load_dotenv

load_dotenv()

OANDA_TOKEN = os.getenv("OANDA_TOKEN")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
OANDA_ENVIRONMENT = os.getenv("OANDA_ENVIRONMENT", "practice")
