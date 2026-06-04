"""Provider interfaces for market data sources."""

from .finnhub import fetch_company_news

__all__ = ["fetch_company_news"]
