"""
Data models for AML Intelligence System
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DocumentType(str, Enum):
    SAR = "SAR"
    TRANSACTION = "TRANSACTION"
    KYC = "KYC"


class SuspiciousActivityReport(BaseModel):
    """Suspicious Activity Report data model"""
    report_id: str
    filing_date: str
    filing_institution: str
    subject_name: str
    subject_account: str
    transaction_amount: float
    transaction_date: str
    suspicious_activity_type: str
    narrative: str
    confidence_scores: Dict[str, float] = Field(default_factory=dict)


class TransactionRecord(BaseModel):
    """Transaction record data model"""
    transaction_id: str
    transaction_date: str
    originator_name: str
    originator_account: str
    beneficiary_name: str
    beneficiary_account: str
    amount: float
    currency: str = "USD"
    purpose: str
    confidence_scores: Dict[str, float] = Field(default_factory=dict)


class KYCDocument(BaseModel):
    """KYC document data model"""
    customer_id: str
    full_name: str
    date_of_birth: str
    nationality: str
    document_type: str
    document_number: str
    issue_date: str
    expiry_date: str
    address: str
    politically_exposed_person: bool = False
    confidence_scores: Dict[str, float] = Field(default_factory=dict)


class AdverseMediaArticle(BaseModel):
    """Adverse media article finding"""
    title: str = ""
    snippet: Optional[str] = None
    link: str = ""
    source: str = ""


class AdverseMediaFindings(BaseModel):
    """Adverse media search results"""
    total_mentions: int = 0
    risk_keywords_found: List[str] = Field(default_factory=list)
    articles: List[AdverseMediaArticle] = Field(default_factory=list)
    risk_score: float = 0


class ScreeningCheck(BaseModel):
    """Individual screening check result"""
    source: str
    status: str  # "clear", "hits_found", "potential_match", "mentions_found", "patterns_detected"
    details: str


class FATFCheck(BaseModel):
    """FATF jurisdiction check result"""
    is_high_risk: bool = False
    risk_level: str = "normal"
    country: str = ""
    reason: Optional[str] = None
    risk_score: float = 0


class DilisenseMatch(BaseModel):
    """Individual Dilisense match record"""
    name: Optional[str] = None
    source_type: Optional[str] = None
    entity_type: Optional[str] = None
    positions: List[str] = Field(default_factory=list)
    sanction_details: Optional[str] = None
    match_type: Optional[str] = None  # EXACT, PARTIAL, or FUZZY
    match_score: Optional[int] = None  # 0-100 similarity score
    searched_name: Optional[str] = None  # The name that was searched

class DilisenseResult(BaseModel):
    """Dilisense or World-Check screening results"""
    provider: str = "Dilisense Screening"
    total_hits: int = 0
    sanctions_hits: int = 0
    pep_hits: int = 0
    criminal_hits: int = 0
    adverse_media_hits: int = 0
    special_interest_hits: int = 0
    records: List[DilisenseMatch] = Field(default_factory=list)
    risk_level: str = "LOW"
    fallback_used: bool = False
    requested_provider: Optional[str] = None
    actual_provider: Optional[str] = None

class SanctionsMatch(BaseModel):
    """Individual sanctions match record"""
    source: Optional[str] = None
    link: Optional[str] = None
    snippet: Optional[str] = None
    confidence: Optional[str] = None  # HIGH, MEDIUM, LOW

class SanctionsResult(BaseModel):
    """Sanctions screening result"""
    is_sanctioned: bool = False
    lists_checked: List[str] = Field(default_factory=list)
    matches: List[SanctionsMatch] = Field(default_factory=list)

class PositiveFindings(BaseModel):
    """Positive/clear screening results"""
    sanctions_clear: bool = True
    sanctions_matches: Optional[SanctionsResult] = None
    pep_clear: bool = True
    adverse_media_clear: bool = True
    behavioral_clear: bool = True
    jurisdiction_clear: bool = True
    dilisense_clear: bool = True
    dilisense_matches: Optional[DilisenseResult] = None
    fatf_check: Optional[FATFCheck] = None
    checks_performed: List[ScreeningCheck] = Field(default_factory=list)
    overall_clear: bool = True


class RiskScore(BaseModel):
    """Risk assessment result"""
    sanctions_risk: float = Field(ge=0, le=100)
    pep_risk: float = Field(ge=0, le=100)
    adverse_media_risk: float = Field(ge=0, le=100)
    behavioral_risk: float = Field(ge=0, le=100, default=0)
    jurisdiction_risk: float = Field(ge=0, le=100, default=0)
    final_risk_score: float = Field(ge=0, le=100)
    risk_level: RiskLevel
    flags: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    adverse_media_findings: Optional[AdverseMediaFindings] = None
    positive_findings: Optional[PositiveFindings] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AnalysisRequest(BaseModel):
    """Request model for manual analysis"""
    entity_name: str
    entity_type: str = "individual"
    screening_provider: str = "dilisense"
    country: Optional[str] = None  # Options: "worldcheck", "dilisense"
    additional_info: Optional[Dict[str, Any]] = None


class AnalysisResponse(BaseModel):
    """Response model for analysis results"""
    analysis_id: str
    entity_name: str
    entity_type: str
    risk_score: float
    risk_level: RiskLevel
    sanctions_risk: float
    pep_risk: float
    adverse_media_risk: float
    jurisdiction_risk: float = 0.0
    flags: List[str]
    recommendations: List[str]
    adverse_media_findings: Optional[AdverseMediaFindings] = None
    positive_findings: Optional[PositiveFindings] = None
    timestamp: str
    processing_time_ms: Optional[int] = None


class DocumentAnalysisResponse(BaseModel):
    """Response model for document analysis"""
    analysis_id: str
    document_type: DocumentType
    extracted_data: Dict
    risk_assessment: RiskScore
    processing_time_ms: int
    timestamp: str


class DashboardStats(BaseModel):
    """Dashboard statistics model"""
    total_analyses: int
    high_risk_count: int
    critical_count: int
    average_risk_score: float
    analyses: Dict = Field(default_factory=dict)


class SARFiling(BaseModel):
    """SAR filing document model"""
    sar_filing: str
    ready_to_submit: bool
    recipient: str = "FIU"
    analysis_id: str
    filing_date: str = Field(default_factory=lambda: datetime.utcnow().isoformat())