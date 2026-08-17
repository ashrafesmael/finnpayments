"""
finnpayments - PDF Report Generator
Generates comprehensive screening reports with branding
"""

import io
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    Image, HRFlowable, PageBreak, ListFlowable, ListItem
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing, Rect, String, Circle
from reportlab.graphics import renderPDF
import logging

logger = logging.getLogger(__name__)

# Brand colors
BRAND_PRIMARY = colors.HexColor("#0d9488")  # Teal
BRAND_DARK = colors.HexColor("#1e293b")     # Dark slate
BRAND_RED = colors.HexColor("#ef4444")      # Red for high risk
BRAND_ORANGE = colors.HexColor("#f97316")   # Orange for medium risk
BRAND_GREEN = colors.HexColor("#22c55e")    # Green for low risk
BRAND_GRAY = colors.HexColor("#64748b")     # Gray for text


def get_risk_color(risk_level: str) -> colors.Color:
    """Get color based on risk level"""
    risk_level = risk_level.upper() if risk_level else "LOW"
    if risk_level == "HIGH" or risk_level == "CRITICAL":
        return BRAND_RED
    elif risk_level == "MEDIUM":
        return BRAND_ORANGE
    else:
        return BRAND_GREEN


def create_logo_drawing(width=150, height=40):
    """Create finnpayments logo as a drawing"""
    d = Drawing(width, height)
    
    # Shield icon
    d.add(Rect(5, 5, 25, 30, fillColor=BRAND_PRIMARY, strokeColor=None, rx=3, ry=3))
    d.add(String(10, 15, "✓", fontSize=18, fillColor=colors.white, fontName="Helvetica-Bold"))
    
    # Text
    d.add(String(35, 20, "finnpayments", fontSize=18, fillColor=BRAND_DARK, fontName="Helvetica-Bold"))
    d.add(String(35, 8, "AML Compliance", fontSize=9, fillColor=BRAND_GRAY, fontName="Helvetica"))
    
    return d


class ScreeningReportGenerator:
    """Generates comprehensive PDF screening reports"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=BRAND_DARK,
            spaceAfter=20,
            alignment=TA_CENTER
        ))
        
        # Section header
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=BRAND_PRIMARY,
            spaceBefore=15,
            spaceAfter=10,
            borderPadding=(5, 5, 5, 5)
        ))
        
        # Subsection header
        self.styles.add(ParagraphStyle(
            name='SubsectionHeader',
            parent=self.styles['Heading3'],
            fontSize=11,
            textColor=BRAND_DARK,
            spaceBefore=10,
            spaceAfter=5
        ))
        
        # Normal text
        self.styles.add(ParagraphStyle(
            name='ReportBody',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=BRAND_DARK,
            spaceAfter=8,
            alignment=TA_JUSTIFY
        ))
        
        # Risk indicator
        self.styles.add(ParagraphStyle(
            name='RiskHigh',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=BRAND_RED,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='RiskMedium',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=BRAND_ORANGE,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='RiskLow',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=BRAND_GREEN,
            fontName='Helvetica-Bold'
        ))
        self.styles.add(ParagraphStyle(
            name='RiskCritical',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=BRAND_RED,
            fontName='Helvetica-Bold'
        ))
        
        # Footer style
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=BRAND_GRAY,
            alignment=TA_CENTER
        ))
    
    def _create_header(self, analysis_id: str) -> List:
        """Create report header with logo and title"""
        elements = []
        
        # Logo
        logo = create_logo_drawing()
        elements.append(logo)
        elements.append(Spacer(1, 10))
        
        # Horizontal line
        elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_PRIMARY))
        elements.append(Spacer(1, 15))
        
        # Title
        elements.append(Paragraph("AML SCREENING REPORT", self.styles['ReportTitle']))
        
        # Report metadata
        meta_data = [
            ['Report ID:', analysis_id],
            ['Generated:', datetime.now().strftime("%d %B %Y, %H:%M:%S")],
            ['Classification:', 'CONFIDENTIAL']
        ]
        meta_table = Table(meta_data, colWidths=[100, 300])
        meta_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), BRAND_GRAY),
            ('TEXTCOLOR', (1, 0), (1, -1), BRAND_DARK),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_executive_summary(self, data: Dict[str, Any]) -> List:
        """Create executive summary section"""
        elements = []
        
        elements.append(Paragraph("EXECUTIVE SUMMARY", self.styles['SectionHeader']))
        elements.append(HRFlowable(width="100%", thickness=1, color=BRAND_PRIMARY))
        elements.append(Spacer(1, 10))
        
        # Risk score and level - check multiple possible field names
        risk_score = data.get('risk_score', data.get('final_risk_score', 0))
        risk_level = str(data.get('risk_level', 'LOW')).upper().replace('RISKLEVEL.', '')
        entity_name = data.get('entity_name', 'Unknown')
        entity_type = data.get('entity_type', 'individual').title()
        
        # Get extracted data for document uploads
        if entity_name == 'Unknown' and 'document_extraction' in data:
            doc_data = data.get('document_extraction', {})
            entity_name = doc_data.get('full_name', 'Unknown')
        
        risk_color = get_risk_color(risk_level)
        risk_style = f'Risk{risk_level.title()}' if f'Risk{risk_level.title()}' in self.styles.byName else 'RiskLow'
        
        # Summary table
        summary_data = [
            ['Entity Name:', entity_name],
            ['Entity Type:', entity_type.title()],
            ['Risk Score:', f"{risk_score}/100"],
            ['Risk Level:', risk_level.upper()],
            ['Processing Time:', f"{data.get('processing_time_ms', 0)}ms"],
        ]
        
        summary_table = Table(summary_data, colWidths=[120, 350])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (0, -1), BRAND_DARK),
            ('TEXTCOLOR', (1, 0), (1, -1), BRAND_DARK),
            ('TEXTCOLOR', (1, 3), (1, 3), risk_color),  # Risk level color
            ('FONTNAME', (1, 3), (1, 3), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 1, BRAND_GRAY),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 15))
        
        # AI Summary
        summary_text = data.get('summary', '')
        if summary_text:
            elements.append(Paragraph("AI Analysis Summary:", self.styles['SubsectionHeader']))
            elements.append(Paragraph(summary_text, self.styles['ReportBody']))
        
        return elements
    
    def _create_risk_breakdown(self, data: Dict[str, Any]) -> List:
        """Create risk breakdown section"""
        elements = []
        
        elements.append(Paragraph("RISK BREAKDOWN", self.styles['SectionHeader']))
        elements.append(HRFlowable(width="100%", thickness=1, color=BRAND_PRIMARY))
        elements.append(Spacer(1, 10))
        
        # Risk categories - get from multiple possible sources
        sanctions = data.get('sanctions_risk', 0)
        pep = data.get('pep_risk', 0) 
        adverse = data.get('adverse_media_risk', 0)
        # behavioral = data.get('behavioral_risk', 0)  # Disabled until transactional screening implemented
        jurisdiction = data.get('jurisdiction_risk', 0)
        
        risk_data = [
            ['Risk Category', 'Score', 'Weight', 'Weighted Score'],
            ['Sanctions Risk', f"{sanctions:.1f}%", '85%', f"{sanctions * 0.85:.1f}"],
            ['PEP Risk', f"{pep:.1f}%", '30%', f"{pep * 0.30:.1f}"],
            ['Adverse Media Risk', f"{adverse:.1f}%", '20%', f"{adverse * 0.20:.1f}"],
            ['Jurisdiction Risk', f"{jurisdiction:.1f}%", '20%', f"{jurisdiction * 0.20:.1f}"],
        ]
        
        risk_table = Table(risk_data, colWidths=[150, 80, 80, 100])
        risk_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), BRAND_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            # Body
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, BRAND_GRAY),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        # Color code the risk scores
        for i, row in enumerate(risk_data[1:], 1):
            score = float(row[1].replace('%', ''))
            if score >= 70:
                risk_table.setStyle(TableStyle([('TEXTCOLOR', (1, i), (1, i), BRAND_RED)]))
            elif score >= 40:
                risk_table.setStyle(TableStyle([('TEXTCOLOR', (1, i), (1, i), BRAND_ORANGE)]))
        
        elements.append(risk_table)
        elements.append(Spacer(1, 15))
        
        return elements
    
    def _create_screening_checks(self, data: Dict[str, Any]) -> List:
        """Create screening checks section"""
        elements = []
        
        elements.append(Paragraph("SCREENING CHECKS PERFORMED", self.styles['SectionHeader']))
        elements.append(HRFlowable(width="100%", thickness=1, color=BRAND_PRIMARY))
        elements.append(Spacer(1, 10))
        
        positive_findings = data.get('positive_findings', {})
        checks = positive_findings.get('checks_performed', [])
        
        if checks:
            checks_data = [['Database/Source', 'Status', 'Details']]
            for check in checks:
                source = check.get('source', 'Unknown')
                status = check.get('status', 'unknown')
                details = check.get('details', '-')
                
                status_display = '✓ Clear' if status == 'clear' else '⚠ Alert'
                checks_data.append([source, status_display, details])
            
            checks_table = Table(checks_data, colWidths=[180, 80, 180])
            checks_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), BRAND_PRIMARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, BRAND_GRAY),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
            ]))
            
            # Color code status
            for i in range(1, len(checks_data)):
                if '✓' in checks_data[i][1]:
                    checks_table.setStyle(TableStyle([('TEXTCOLOR', (1, i), (1, i), BRAND_GREEN)]))
                else:
                    checks_table.setStyle(TableStyle([('TEXTCOLOR', (1, i), (1, i), BRAND_RED)]))
            
            elements.append(checks_table)
        else:
            elements.append(Paragraph("No screening checks data available.", self.styles['ReportBody']))
        
        elements.append(Spacer(1, 15))
        return elements
    
    def _create_sanctions_section(self, data: Dict[str, Any]) -> List:
        """Create sanctions matches section"""
        elements = []
        
        positive_findings = data.get('positive_findings', {})
        sanctions_matches = positive_findings.get('sanctions_matches', {})
        
        if sanctions_matches and sanctions_matches.get('matches'):
            elements.append(Paragraph("SANCTIONS MATCHES", self.styles['SectionHeader']))
            elements.append(HRFlowable(width="100%", thickness=1, color=BRAND_RED))
            elements.append(Spacer(1, 10))
            
            elements.append(Paragraph(
                f"<b>⚠ WARNING:</b> {len(sanctions_matches.get('matches', []))} potential sanctions match(es) found.",
                self.styles['RiskHigh']
            ))
            elements.append(Spacer(1, 10))
            
            # Lists checked
            lists_checked = sanctions_matches.get('lists_checked', [])
            if lists_checked:
                elements.append(Paragraph(f"<b>Lists Checked:</b> {', '.join(lists_checked)}", self.styles['ReportBody']))
            
            # Match details
            for i, match in enumerate(sanctions_matches.get('matches', []), 1):
                elements.append(Paragraph(f"<b>Match {i}:</b> {match.get('source', 'Unknown Source')}", self.styles['SubsectionHeader']))
                elements.append(Paragraph(f"Snippet: {match.get('snippet', 'N/A')}", self.styles['ReportBody']))
                if match.get('link'):
                    elements.append(Paragraph(f"Source: {match.get('link')}", self.styles['ReportBody']))
                elements.append(Spacer(1, 5))
            
            elements.append(Spacer(1, 15))
        
        return elements
    
    def _create_adverse_media_section(self, data: Dict[str, Any]) -> List:
        """Create adverse media section"""
        elements = []
        
        adverse_media = data.get('adverse_media_findings', {})
        
        if adverse_media and adverse_media.get('total_mentions', 0) > 0:
            elements.append(Paragraph("ADVERSE MEDIA FINDINGS", self.styles['SectionHeader']))
            elements.append(HRFlowable(width="100%", thickness=1, color=BRAND_ORANGE))
            elements.append(Spacer(1, 10))
            
            elements.append(Paragraph(
                f"<b>Total Mentions Found:</b> {adverse_media.get('total_mentions', 0)}",
                self.styles['ReportBody']
            ))
            
            # Risk keywords
            keywords = adverse_media.get('risk_keywords_found', [])
            if keywords:
                elements.append(Paragraph(f"<b>Risk Keywords:</b> {', '.join(keywords)}", self.styles['ReportBody']))
            
            elements.append(Spacer(1, 10))
            
            # Articles
            articles = adverse_media.get('articles', [])
            if articles:
                elements.append(Paragraph("<b>Related Articles:</b>", self.styles['SubsectionHeader']))
                for article in articles[:5]:  # Limit to 5 articles
                    title = article.get('title', 'Untitled')
                    snippet = article.get('snippet', '')
                    elements.append(Paragraph(f"• <b>{title}</b>", self.styles['ReportBody']))
                    if snippet:
                        elements.append(Paragraph(f"  {snippet[:200]}...", self.styles['ReportBody']))
            
            elements.append(Spacer(1, 15))
        
        return elements
    
    def _create_risk_flags_section(self, data: Dict[str, Any]) -> List:
        """Create risk flags section"""
        elements = []
        
        flags = data.get('flags', [])
        
        if flags:
            elements.append(Paragraph("RISK FLAGS", self.styles['SectionHeader']))
            elements.append(HRFlowable(width="100%", thickness=1, color=BRAND_PRIMARY))
            elements.append(Spacer(1, 10))
            
            flag_items = []
            for flag in flags:
                flag_items.append(ListItem(Paragraph(flag.replace('_', ' ').title(), self.styles['ReportBody'])))
            
            elements.append(ListFlowable(flag_items, bulletType='bullet', start='•'))
            elements.append(Spacer(1, 15))
        
        return elements
    
    def _create_recommendations_section(self, data: Dict[str, Any]) -> List:
        """Create recommendations section"""
        elements = []
        
        recommendations = data.get('recommendations', [])
        
        if recommendations:
            elements.append(Paragraph("RECOMMENDATIONS", self.styles['SectionHeader']))
            elements.append(HRFlowable(width="100%", thickness=1, color=BRAND_PRIMARY))
            elements.append(Spacer(1, 10))
            
            for i, rec in enumerate(recommendations, 1):
                elements.append(Paragraph(f"{i}. {rec}", self.styles['ReportBody']))
            
            elements.append(Spacer(1, 15))
        
        return elements
    
    def _create_document_extraction_section(self, data: Dict[str, Any]) -> List:
        """Create document extraction section for KYC documents"""
        elements = []
        
        doc_extraction = data.get('document_extraction', {})
        
        if doc_extraction and doc_extraction.get('full_name'):
            elements.append(Paragraph("DOCUMENT EXTRACTION", self.styles['SectionHeader']))
            elements.append(HRFlowable(width="100%", thickness=1, color=BRAND_PRIMARY))
            elements.append(Spacer(1, 10))
            
            extraction_data = [
                ['Field', 'Extracted Value'],
                ['Full Name', doc_extraction.get('full_name', 'N/A')],
                ['Date of Birth', doc_extraction.get('date_of_birth', 'N/A')],
                ['Nationality', doc_extraction.get('nationality', 'N/A')],
                ['Document Type', doc_extraction.get('document_type', 'N/A')],
                ['Document Number', doc_extraction.get('document_number', 'N/A')],
                ['Issue Date', doc_extraction.get('issue_date', 'N/A')],
                ['Expiry Date', doc_extraction.get('expiry_date', 'N/A')],
                ['Address', doc_extraction.get('address', 'N/A')],
            ]
            
            extraction_table = Table(extraction_data, colWidths=[150, 300])
            extraction_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), BRAND_PRIMARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, BRAND_GRAY),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
            ]))
            
            elements.append(extraction_table)
            elements.append(Spacer(1, 15))
        
        return elements
    
    def _create_footer(self) -> List:
        """Create report footer"""
        elements = []
        
        elements.append(Spacer(1, 20))
        elements.append(HRFlowable(width="100%", thickness=1, color=BRAND_GRAY))
        elements.append(Spacer(1, 10))
        
        footer_text = f"""
        This report was generated by finnpayments.<br/>
        Report generated on {datetime.now().strftime("%d %B %Y at %H:%M:%S")}.<br/>
        This document is confidential and intended for authorized recipients only.<br/>
        © {datetime.now().year} finnpayments. All rights reserved.
        """
        elements.append(Paragraph(footer_text, self.styles['Footer']))
        
        return elements
    

    def _create_dilisense_section(self, data: Dict[str, Any]) -> List:
        """Create Dilisense AML database matches section"""
        elements = []
        
        positive_findings = data.get('positive_findings', {})
        dilisense_matches = positive_findings.get('dilisense_matches', {})
        
        if dilisense_matches and dilisense_matches.get('total_hits', 0) > 0:
            # Get provider name dynamically
            provider_name = dilisense_matches.get('provider', 'AML Database')
            elements.append(Paragraph(f"{provider_name.upper()} MATCHES", self.styles['SectionHeader']))
            elements.append(HRFlowable(width="100%", thickness=1, color=BRAND_RED))
            elements.append(Spacer(1, 10))
            
            total_hits = dilisense_matches.get('total_hits', 0)
            elements.append(Paragraph(
                f"<b>⚠ {total_hits} match(es) found in {provider_name}</b>",
                self.styles['RiskHigh']
            ))
            elements.append(Spacer(1, 10))
            
            # Summary stats
            sanctions_hits = dilisense_matches.get('sanctions_hits', 0)
            pep_hits = dilisense_matches.get('pep_hits', 0)
            adverse_hits = dilisense_matches.get('adverse_media_hits', 0)
            special_interest_hits = dilisense_matches.get('special_interest_hits', 0)
            
            stats_data = [
                ['Category', 'Matches'],
                ['Sanctions Hits', str(sanctions_hits)],
                ['PEP Hits', str(pep_hits)],
                ['Adverse Media Hits', str(adverse_hits)],
                ['Special Interest Hits', str(special_interest_hits)],
            ]
            
            stats_table = Table(stats_data, colWidths=[200, 100])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), BRAND_PRIMARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, BRAND_GRAY),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
            ]))
            elements.append(stats_table)
            elements.append(Spacer(1, 10))
            
            # Individual records
            records = dilisense_matches.get('records', [])
            if records:
                elements.append(Paragraph("<b>Match Details:</b>", self.styles['SubsectionHeader']))
                
                for i, record in enumerate(records[:10], 1):  # Limit to 10 records
                    name = record.get('name', 'Unknown')
                    match_type = record.get('match_type', 'UNKNOWN')
                    match_score = record.get('match_score', 0)
                    record_type = record.get('type', 'Unknown')
                    
                    # Record header
                    elements.append(Paragraph(
                        f"<b>Match {i}:</b> {name} [{match_type} - {match_score}%]",
                        self.styles['ReportBody']
                    ))
                    
                    # Record details
                    details = []
                    if record.get('entity_type'):
                        details.append(f"Entity Type: {record.get('entity_type')}")
                    if record.get('countries'):
                        countries = record.get('countries', [])
                        if isinstance(countries, list):
                            details.append(f"Countries: {', '.join(countries)}")
                    if record.get('sanction_details'):
                        details.append(f"Details: {record.get('sanction_details')}")
                    if record.get('sources'):
                        sources = record.get('sources', [])
                        if isinstance(sources, list):
                            details.append(f"Sources: {', '.join(sources[:3])}")
                    
                    if details:
                        for detail in details:
                            elements.append(Paragraph(f"  • {detail}", self.styles['ReportBody']))
                    
                    elements.append(Spacer(1, 5))
            
            elements.append(Spacer(1, 15))
        
        return elements
    
    def _create_web_search_section(self, data: Dict[str, Any]) -> List:
        """Create web search results section"""
        elements = []
        
        # Get adverse media articles which come from web search
        adverse_media = data.get('adverse_media_findings', {})
        articles = adverse_media.get('articles', [])
        
        if articles:
            elements.append(Paragraph("WEB SEARCH RESULTS", self.styles['SectionHeader']))
            elements.append(HRFlowable(width="100%", thickness=1, color=BRAND_PRIMARY))
            elements.append(Spacer(1, 10))
            
            elements.append(Paragraph(
                f"<b>Sources Analyzed:</b> {len(articles)} web sources reviewed",
                self.styles['ReportBody']
            ))
            elements.append(Spacer(1, 10))
            
            # Create table of search results
            search_data = [['Source', 'Title', 'Type']]
            
            for article in articles[:10]:  # Limit to 10 articles
                title = article.get('title', 'Untitled')[:50]
                if len(article.get('title', '')) > 50:
                    title += '...'
                source = article.get('source', 'Web')
                if article.get('link'):
                    # Extract domain from link
                    link = article.get('link', '')
                    try:
                        from urllib.parse import urlparse
                        domain = urlparse(link).netloc
                        source = domain[:30] if domain else 'Web'
                    except:
                        source = 'Web'
                
                article_type = article.get('type', 'Article')
                search_data.append([source, title, article_type])
            
            if len(search_data) > 1:
                search_table = Table(search_data, colWidths=[120, 250, 80])
                search_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), BRAND_PRIMARY),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('GRID', (0, 0), (-1, -1), 0.5, BRAND_GRAY),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                elements.append(search_table)
            
            elements.append(Spacer(1, 15))
        
        return elements
    
    def _create_fatf_section(self, data: Dict[str, Any]) -> List:
        """Create FATF jurisdiction check section"""
        elements = []
        
        positive_findings = data.get('positive_findings', {})
        fatf_check = positive_findings.get('fatf_check', {})
        
        if fatf_check:
            elements.append(Paragraph("FATF JURISDICTION CHECK", self.styles['SectionHeader']))
            elements.append(HRFlowable(width="100%", thickness=1, color=BRAND_PRIMARY))
            elements.append(Spacer(1, 10))
            
            jurisdiction = fatf_check.get('country', fatf_check.get('jurisdiction', 'Unknown'))
            is_high_risk = fatf_check.get('is_high_risk', False)
            is_grey_list = fatf_check.get('is_grey_list', False)
            is_black_list = fatf_check.get('is_black_list', False)
            
            # Jurisdiction status
            if is_black_list:
                status = "HIGH RISK - FATF Black List"
                status_style = self.styles['RiskHigh']
            elif is_grey_list:
                status = "ELEVATED RISK - FATF Grey List"
                status_style = self.styles['RiskMedium']
            else:
                status = "LOW RISK - Not on FATF Lists"
                status_style = self.styles['RiskLow']
            
            elements.append(Paragraph(f"<b>Jurisdiction:</b> {jurisdiction}", self.styles['ReportBody']))
            elements.append(Paragraph(f"<b>Status:</b> {status}", status_style))
            
            # List current FATF lists
            grey_list = fatf_check.get('grey_list_countries', [])
            black_list = fatf_check.get('black_list_countries', [])
            
            if black_list:
                elements.append(Spacer(1, 10))
                elements.append(Paragraph(
                    f"<b>FATF Black List Countries:</b> {', '.join(black_list[:10])}",
                    self.styles['ReportBody']
                ))
            
            if grey_list:
                elements.append(Paragraph(
                    f"<b>FATF Grey List Countries:</b> {', '.join(grey_list[:15])}{'...' if len(grey_list) > 15 else ''}",
                    self.styles['ReportBody']
                ))
            
            elements.append(Spacer(1, 15))
        
        return elements


    def generate_report(self, data: Dict[str, Any], output_path: Optional[str] = None) -> bytes:
        """
        Generate a comprehensive PDF screening report
        
        Args:
            data: Screening result data
            output_path: Optional path to save the PDF file
            
        Returns:
            PDF content as bytes
        """
        # Create buffer
        buffer = io.BytesIO()
        
        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )
        
        # Build content
        elements = []
        
        analysis_id = data.get('analysis_id', 'Unknown')
        
        # Add sections
        elements.extend(self._create_header(analysis_id))
        elements.extend(self._create_executive_summary(data))
        elements.extend(self._create_risk_breakdown(data))
        elements.extend(self._create_screening_checks(data))
        elements.extend(self._create_sanctions_section(data))
        elements.extend(self._create_dilisense_section(data))
        elements.extend(self._create_pep_findings_section(data))
        elements.extend(self._create_sanctions_findings_section(data))
        elements.extend(self._create_fatf_section(data))
        elements.extend(self._create_adverse_media_section(data))
        elements.extend(self._create_web_search_section(data))
        elements.extend(self._create_risk_flags_section(data))
        elements.extend(self._create_document_extraction_section(data))
        elements.extend(self._create_recommendations_section(data))
        elements.extend(self._create_footer())
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()
        
        # Save to file if path provided
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_content)
            logger.info(f"✓ Report saved to {output_path}")
        
        return pdf_content


# Convenience function
    def _create_pep_findings_section(self, data: Dict[str, Any]) -> List:
        """Create PEP (Politically Exposed Person) findings section"""
        elements = []
        
        positive_findings = data.get('positive_findings', {})
        dilisense_matches = positive_findings.get('dilisense_matches', {})
        pep_hits = dilisense_matches.get('pep_hits', 0)
        
        # Also check for PEP indicators from name analysis
        pep_indicators = data.get('pep_indicators', {})
        
        if pep_hits > 0 or pep_indicators.get('is_potential_pep'):
            elements.append(Paragraph("PEP FINDINGS", self.styles['SectionHeader']))
            elements.append(HRFlowable(width="100%", thickness=1, color=BRAND_ORANGE))
            elements.append(Spacer(1, 10))
            
            if pep_hits > 0:
                elements.append(Paragraph(
                    f"<b>⚠ {pep_hits} PEP match(es) found in screening databases</b>",
                    self.styles['RiskHigh']
                ))
                elements.append(Spacer(1, 10))
                
                # Show PEP records from AML database
                records = dilisense_matches.get('records', [])
                pep_records = [r for r in records if r.get('source_type', '').upper() == 'PEP' or 'PEP' in r.get('match_type', '').upper()]
                
                if pep_records:
                    elements.append(Paragraph("<b>PEP Match Details:</b>", self.styles['SubsectionHeader']))
                    
                    for i, record in enumerate(pep_records[:5], 1):
                        name = record.get('name', 'Unknown')
                        match_score = record.get('match_score', 0)
                        
                        elements.append(Paragraph(
                            f"<b>Match {i}:</b> {name} (Match Score: {match_score}%)",
                            self.styles['ReportBody']
                        ))
                        
                        # Show positions if available
                        positions = record.get('positions', [])
                        if positions:
                            elements.append(Paragraph(
                                f"  • Positions: {', '.join(positions[:3])}",
                                self.styles['ReportBody']
                            ))
                        
                        # Show countries if available
                        countries = record.get('countries', [])
                        if countries:
                            if isinstance(countries, list):
                                elements.append(Paragraph(
                                    f"  • Countries: {', '.join(countries[:3])}",
                                    self.styles['ReportBody']
                                ))
                        
                        # Show details if available
                        if record.get('sanction_details'):
                            elements.append(Paragraph(
                                f"  • Details: {record.get('sanction_details')}",
                                self.styles['ReportBody']
                            ))
                        
                        elements.append(Spacer(1, 5))
            
            # Show PEP indicators from name analysis
            if pep_indicators.get('is_potential_pep'):
                elements.append(Paragraph("<b>PEP Risk Indicators Detected:</b>", self.styles['SubsectionHeader']))
                indicators = pep_indicators.get('indicators', [])
                for indicator in indicators:
                    elements.append(Paragraph(f"  • {indicator}", self.styles['ReportBody']))
                
                confidence = pep_indicators.get('confidence', 0)
                elements.append(Paragraph(
                    f"  • Confidence Level: {confidence}%",
                    self.styles['ReportBody']
                ))
                elements.append(Paragraph(
                    f"  • Recommendation: {pep_indicators.get('recommendation', 'Enhanced due diligence recommended')}",
                    self.styles['ReportBody']
                ))
            
            elements.append(Spacer(1, 15))
        
        return elements

    def _create_sanctions_findings_section(self, data: Dict[str, Any]) -> List:
        """Create detailed sanctions findings section from official lists"""
        elements = []
        
        positive_findings = data.get('positive_findings', {})
        dilisense_matches = positive_findings.get('dilisense_matches', {})
        sanctions_hits = dilisense_matches.get('sanctions_hits', 0)
        
        if sanctions_hits > 0:
            elements.append(Paragraph("SANCTIONS LIST MATCHES", self.styles['SectionHeader']))
            elements.append(HRFlowable(width="100%", thickness=1, color=BRAND_RED))
            elements.append(Spacer(1, 10))
            
            elements.append(Paragraph(
                f"<b>⚠ CRITICAL: {sanctions_hits} match(es) found on official sanctions lists</b>",
                self.styles['RiskCritical']
            ))
            elements.append(Spacer(1, 10))
            
            # Show sanctions records from AML database
            records = dilisense_matches.get('records', [])
            sanctions_records = [r for r in records if r.get('source_type', '').upper() == 'SANCTION' or 'SANCTION' in r.get('match_type', '').upper()]
            
            if sanctions_records:
                elements.append(Paragraph("<b>Sanctions Match Details:</b>", self.styles['SubsectionHeader']))
                
                for i, record in enumerate(sanctions_records[:5], 1):
                    name = record.get('name', 'Unknown')
                    match_score = record.get('match_score', 0)
                    
                    elements.append(Paragraph(
                        f"<b>Match {i}:</b> {name} (Match Score: {match_score}%)",
                        self.styles['ReportBody']
                    ))
                    
                    # Show sanction source/list
                    sources = record.get('sources', [])
                    if sources:
                        if isinstance(sources, list):
                            elements.append(Paragraph(
                                f"  • Sanctions Lists: {', '.join(sources[:5])}",
                                self.styles['ReportBody']
                            ))
                    
                    # Show countries if available
                    countries = record.get('countries', [])
                    if countries:
                        if isinstance(countries, list):
                            elements.append(Paragraph(
                                f"  • Countries: {', '.join(countries[:3])}",
                                self.styles['ReportBody']
                            ))
                    
                    # Show details if available
                    if record.get('sanction_details'):
                        elements.append(Paragraph(
                            f"  • Details: {record.get('sanction_details')}",
                            self.styles['ReportBody']
                        ))
                    
                    # Show entity type
                    if record.get('entity_type'):
                        elements.append(Paragraph(
                            f"  • Entity Type: {record.get('entity_type')}",
                            self.styles['ReportBody']
                        ))
                    
                    elements.append(Spacer(1, 5))
                
                elements.append(Spacer(1, 10))
                elements.append(Paragraph(
                    "<b>IMPORTANT:</b> Sanctions matches require immediate review. "
                    "Do not proceed with any business relationship until sanctions status is verified and cleared.",
                    self.styles['RiskHigh']
                ))
            
            elements.append(Spacer(1, 15))
        
        return elements


def generate_screening_report(data: Dict[str, Any], output_path: Optional[str] = None) -> bytes:
    """Generate a screening report PDF"""
    generator = ScreeningReportGenerator()
    return generator.generate_report(data, output_path)
