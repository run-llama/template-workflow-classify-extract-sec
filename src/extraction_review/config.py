"""
For simple configuration of the extraction review application, just customize this file.

If you need more control, feel free to edit the rest of the application
"""

from __future__ import annotations
import os
from typing import Type

from llama_cloud import ExtractConfig
from llama_cloud_services.extract import ExtractMode
from pydantic import BaseModel, Field

# If you change this to true, the schema and extraction configuration will be fetched from the remote extraction agent
# rather than using the ExtractionSchema and configuration defined below.
USE_REMOTE_EXTRACTION_SCHEMA: bool = False
# The name of the extraction agent to use. Prefers the name of this deployment when deployed to isolate environments.
# Note that the application will create a new agent from the below ExtractionSchema if the extraction agent does not yet exist.
EXTRACTION_AGENT_NAME: str = (
    os.getenv("LLAMA_DEPLOY_DEPLOYMENT_NAME") or "extraction-review"
)
# The name of the collection to use for storing extracted data. This will be qualified by the agent name.
# When developing locally, this will use the _public collection (shared within the project), otherwise agent
# data is isolated to each agent
EXTRACTED_DATA_COLLECTION: str = "sec-filing-extraction"


# SEC Filing Classification Types
SEC_FILING_TYPES = ["10-K", "10-Q", "8-K", "other"]


# Base class for common fields across all SEC filings
class BaseSECFiling(BaseModel):
    """Common fields present in all SEC filings"""

    company_name: str = Field(
        description="The full legal name of the company filing the document"
    )
    ticker_symbol: str | None = Field(
        default=None,
        description="The stock ticker symbol of the company. May not be present for all filings.",
    )
    cik: str | None = Field(
        default=None,
        description="Central Index Key - the unique identifier assigned by the SEC to the company",
    )
    filing_date: str | None = Field(
        default=None,
        description="The date the document was filed with the SEC (format: YYYY-MM-DD)",
    )
    fiscal_year_end: str | None = Field(
        default=None,
        description="The fiscal year end date for the company (format: YYYY-MM-DD)",
    )
    sic_code: str | None = Field(
        default=None,
        description="Standard Industrial Classification code for the company's industry",
    )


# Financial metrics that appear in multiple filing types
class FinancialMetrics(BaseModel):
    """Key financial metrics extracted from statements"""

    total_revenue: str | None = Field(
        default=None,
        description="Total revenue/sales for the period. Include currency and amount (e.g., '$1.2B USD')",
    )
    net_income: str | None = Field(
        default=None,
        description="Net income/profit for the period. Include currency and amount",
    )
    total_assets: str | None = Field(
        default=None,
        description="Total assets as of the balance sheet date. Include currency and amount",
    )
    total_liabilities: str | None = Field(
        default=None,
        description="Total liabilities as of the balance sheet date. Include currency and amount",
    )
    stockholders_equity: str | None = Field(
        default=None,
        description="Total stockholders' equity. Include currency and amount",
    )
    cash_and_equivalents: str | None = Field(
        default=None,
        description="Cash and cash equivalents. Include currency and amount",
    )
    earnings_per_share: str | None = Field(
        default=None, description="Earnings per share (EPS) for the period"
    )


# Risk factor for use in 10-K and 10-Q
class RiskFactor(BaseModel):
    """Individual risk factor identified in the filing"""

    category: str = Field(
        description="Category of risk (e.g., 'Market Risk', 'Operational Risk', 'Legal Risk')"
    )
    description: str = Field(description="Brief description of the specific risk")


# 10-K: Annual Report
class Filing10K(BaseSECFiling):
    """
    Form 10-K is an annual report required by the SEC that provides a comprehensive
    summary of a company's financial performance.
    """

    document_type: str = Field(default="10-K", description="Should always be '10-K'")
    fiscal_year: int | None = Field(
        default=None,
        description="The fiscal year covered by this annual report (e.g., 2023)",
    )

    # Business overview
    business_description: str | None = Field(
        default=None,
        description="A 2-3 sentence summary of the company's business and operations",
    )

    # Financial data
    financial_metrics: FinancialMetrics | None = Field(
        default=None, description="Key financial metrics from the annual statements"
    )

    # Risk factors
    risk_factors: list[RiskFactor] | None = Field(
        default=None,
        description="List of material risk factors disclosed in the filing. Extract 3-5 most significant risks.",
    )

    # Management discussion
    management_discussion_summary: str | None = Field(
        default=None,
        description="2-3 sentence summary of Management's Discussion and Analysis (MD&A) section",
    )

    # Legal proceedings
    legal_proceedings: list[str] | None = Field(
        default=None,
        description="List of significant legal proceedings or litigation mentioned",
    )

    # Executive officers
    executive_officers: list[str] | None = Field(
        default=None,
        description="Names and titles of key executive officers (CEO, CFO, etc.)",
    )

    # Auditor information
    auditor_name: str | None = Field(
        default=None,
        description="Name of the independent registered public accounting firm",
    )

    # Key insights
    key_highlights: list[str] | None = Field(
        default=None,
        description="3-5 key highlights or notable items from the annual report",
    )


# 10-Q: Quarterly Report
class Filing10Q(BaseSECFiling):
    """
    Form 10-Q is a quarterly report that provides a continuing view of a company's
    financial position during the year.
    """

    document_type: str = Field(default="10-Q", description="Should always be '10-Q'")
    fiscal_quarter: str | None = Field(
        default=None,
        description="The fiscal quarter covered (e.g., 'Q1 2024', 'Q2 2023')",
    )
    fiscal_year: int | None = Field(
        default=None, description="The fiscal year for this quarter (e.g., 2024)"
    )
    period_end_date: str | None = Field(
        default=None,
        description="The end date of the quarterly period (format: YYYY-MM-DD)",
    )

    # Financial data
    financial_metrics: FinancialMetrics | None = Field(
        default=None, description="Key financial metrics from the quarterly statements"
    )

    # Comparison to prior periods
    year_over_year_revenue_change: str | None = Field(
        default=None,
        description="Year-over-year revenue change percentage or description (e.g., 'up 15%')",
    )
    quarter_over_quarter_revenue_change: str | None = Field(
        default=None,
        description="Quarter-over-quarter revenue change percentage or description",
    )

    # Management discussion
    management_discussion_summary: str | None = Field(
        default=None,
        description="2-3 sentence summary of Management's Discussion and Analysis for the quarter",
    )

    # Risk factors
    material_changes_to_risks: str | None = Field(
        default=None,
        description="Summary of any material changes to risk factors since the last 10-K",
    )

    # Legal updates
    legal_proceedings_updates: list[str] | None = Field(
        default=None,
        description="Updates to legal proceedings or new litigation since last filing",
    )

    # Key insights
    key_highlights: list[str] | None = Field(
        default=None,
        description="3-5 key highlights or notable items from the quarterly report",
    )


# 8-K: Current Report
class Filing8K(BaseSECFiling):
    """
    Form 8-K is a current report used to notify investors of significant events
    that shareholders should know about.
    """

    document_type: str = Field(default="8-K", description="Should always be '8-K'")

    # Event information
    event_date: str | None = Field(
        default=None,
        description="The date of the event being reported (format: YYYY-MM-DD)",
    )
    event_type: str | None = Field(
        default=None,
        description="Type of event (e.g., 'Merger/Acquisition', 'Leadership Change', 'Earnings Release', 'Material Agreement')",
    )
    item_numbers: list[str] | None = Field(
        default=None,
        description="Item numbers from the 8-K form (e.g., ['1.01', '5.02']) indicating which sections are included",
    )

    # Event description
    event_summary: str = Field(
        description="2-4 sentence summary describing the material event being reported"
    )
    event_details: str | None = Field(
        default=None,
        description="More detailed description of the event and its implications",
    )

    # Financial impact
    estimated_financial_impact: str | None = Field(
        default=None,
        description="Estimated financial impact of the event, if disclosed",
    )

    # Related parties
    related_parties: list[str] | None = Field(
        default=None,
        description="Names of other companies, individuals, or entities involved in the event",
    )

    # Exhibits filed
    material_exhibits: list[str] | None = Field(
        default=None,
        description="Description of significant exhibits filed with the 8-K (e.g., 'Press Release', 'Material Agreement')",
    )

    # Forward-looking statements
    contains_forward_looking_statements: bool | None = Field(
        default=None,
        description="Whether the filing contains forward-looking statements",
    )

    # Key takeaways
    investment_implications: str | None = Field(
        default=None,
        description="1-2 sentence assessment of potential implications for investors",
    )


# Other filings catch-all
class FilingOther(BaseSECFiling):
    """
    Catch-all schema for other SEC filing types (e.g., S-1, DEF 14A, 13F, etc.)
    """

    document_type: str = Field(
        description="The type of SEC filing (e.g., 'S-1', 'DEF 14A', '13F', 'SC 13D')"
    )

    filing_purpose: str | None = Field(
        default=None,
        description="The purpose of this filing type (e.g., 'IPO Registration', 'Proxy Statement', 'Insider Holdings')",
    )

    summary: str = Field(
        description="3-4 sentence summary of the filing's key content and purpose"
    )

    key_information: list[str] | None = Field(
        default=None,
        description="List of 3-7 key pieces of information from the filing",
    )

    financial_data: FinancialMetrics | None = Field(
        default=None, description="Any relevant financial metrics present in the filing"
    )

    material_events: list[str] | None = Field(
        default=None,
        description="List of any material events or transactions described",
    )

    parties_involved: list[str] | None = Field(
        default=None,
        description="Other parties mentioned (companies, executives, investors, etc.)",
    )

    investment_relevance: str | None = Field(
        default=None,
        description="Brief note on why this filing might be relevant for investment analysis",
    )


# Default schema for backward compatibility - now uses 10-K as the base
class ExtractionSchema(Filing10K):
    """Default extraction schema - uses 10-K structure for backward compatibility"""

    pass


# Mapping of filing types to their schemas
FILING_SCHEMAS = {
    "10-K": Filing10K,
    "10-Q": Filing10Q,
    "8-K": Filing8K,
    "other": FilingOther,
}


# This is only used if USE_REMOTE_EXTRACTION_SCHEMA is False.
EXTRACT_CONFIG = ExtractConfig(
    extraction_mode=ExtractMode.PREMIUM,
    system_prompt=None,
    # advanced. Only compatible with Premium mode.
    use_reasoning=False,
    cite_sources=False,
    confidence_scores=True,
)


SCHEMA: Type[BaseModel] | None = (
    None if USE_REMOTE_EXTRACTION_SCHEMA else ExtractionSchema
)
