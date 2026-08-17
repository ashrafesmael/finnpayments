"""
Multi-layer Screening and Risk Assessment Engine
"""
import json
import time
from typing import Dict, Tuple, List
from datetime import datetime
import logging
from src.models import RiskScore, RiskLevel
from src.utils import fuzzy_match, generate_analysis_id
import os
from groq import Groq

# Name processing utilities for enhanced screening
try:
    from src.name_utils import (
        normalize_name, extract_name_components, generate_name_variants,
        generate_search_queries, detect_pep_indicators, is_arabic_name,
        transliterate_arabic_to_english
    )
    NAME_UTILS_AVAILABLE = True
except ImportError:
    NAME_UTILS_AVAILABLE = False

logger = logging.getLogger(__name__)


class ScreeningEngine:
    """Multi-layer screening and risk assessment with LLM-powered analysis"""
    
    def __init__(self, ofac_api_key: str = None, refinitiv_api_key: str = None, dilisense_api_key: str = None, worldcheck_api_key: str = None, worldcheck_api_secret: str = None, use_mock: bool = False, use_llm: bool = True):
        """
        Initialize screening engine
        
        Args:
            ofac_api_key: OFAC API key for sanctions screening (optional - LLM can analyze without)
            refinitiv_api_key: Refinitiv API key for PEP/adverse media (optional - LLM can analyze without)
            use_mock: Use mock databases for demo (default: False - use real LLM analysis)
            use_llm: Use LLM for risk analysis (default: True - REQUIRED for production)
        """
        self.ofac_api_key = ofac_api_key
        self.refinitiv_api_key = refinitiv_api_key
        self.dilisense_api_key = dilisense_api_key or os.getenv("DILISENSE_API_KEY")
        
        # World-Check One API credentials
        self.worldcheck_api_key = worldcheck_api_key or os.getenv("WORLDCHECK_API_KEY")
        self.worldcheck_api_secret = worldcheck_api_secret or os.getenv("WORLDCHECK_API_SECRET")
        self.worldcheck_base_url = os.getenv("WORLDCHECK_BASE_URL", "https://api-worldcheck.refinitiv.com/v3")
        self.worldcheck_access_token = None
        self.worldcheck_token_expiry = None
        self.use_mock = use_mock
        self.use_llm = use_llm
        
        # Initialize empty databases (will use LLM for analysis instead)
        self._init_mock_databases()
        
        # Check if AWS Bedrock is available for LLM analysis
        self.bedrock_available = self._check_bedrock_availability()
        if self.bedrock_available and use_llm:
            logger.info("✅ Groq LLM enabled for real-time risk analysis")
            logger.info("📊 Using LLM-based screening (no mock databases)")
        else:
            logger.warning("⚠️ Groq not available - risk analysis will be limited")
            logger.warning("⚠️ Please configure AWS credentials for full functionality")
    
    def _init_mock_databases(self):
        """Initialize mock screening databases"""
        
        # Mock sanctions database (OFAC, UN, EU lists)
        # Empty - connect to real OFAC API or load from external source
        self.sanctions_database = {}
        
        # Mock PEP (Politically Exposed Persons) database
        # Empty - connect to real PEP database or load from external source
        self.pep_database = {}
        
        # Mock adverse media database
        # Empty - connect to real adverse media API or load from external source
        self.adverse_media_database = {}
        
        # FATF high-risk jurisdictions database
        self.fatf_database = {"high_risk_jurisdictions": {}}
        
        # Mock behavioral patterns database
        self.behavioral_patterns = {
            "structuring": 70,
            "smurfing": 75,
            "layering": 80,
            "integration": 65,
            "round_dollar_amounts": 40,
            "frequent_small_transactions": 60,
            "unusual_transaction_patterns": 55,
            "cross_border_transfers": 45
        }
    
    def screen_entity(self, name: str, entity_type: str = "individual", 
                     additional_context: Dict = None, screening_provider: str = "dilisense") -> RiskScore:
        """
        Comprehensive screening of individual or entity with LLM-enhanced analysis
        
        Args:
            name: Name of entity to screen
            entity_type: Type of entity (individual, company, etc.)
            additional_context: Additional context for screening
        
        Returns:
            RiskScore object with comprehensive assessment
        """
        start_time = time.time()
        logger.info(f"🔍 Screening {entity_type}: {name} using provider: {screening_provider}")
        
        # Get nationality from additional_context
        nationality = additional_context.get("nationality", "") if additional_context else ""
        
        # Use selected screening provider (default: worldcheck)
        aml_result = None
        provider_name = screening_provider.lower() if screening_provider else "worldcheck"
        
        if provider_name == "dilisense":
            aml_result = self._check_dilisense(name)
            logger.info(f"📋 Using Dilisense Screening")
        else:  # Default to World-Check One
            aml_result = self._check_worldcheck(name, entity_type, nationality=nationality)
            logger.info(f"📋 Using World Check One Screening")
        
        # Fallback to other provider if primary fails
        if aml_result is None:
            if provider_name == "worldcheck":
                logger.warning(f"⚠️ World-Check unavailable, falling back to Dilisense")
                aml_result = self._check_dilisense(name)
                provider_name = "dilisense"
            else:
                logger.warning(f"⚠️ Dilisense unavailable, falling back to World-Check")
                aml_result = self._check_worldcheck(name, entity_type, nationality=nationality)
                provider_name = "worldcheck"
        
        # For backward compatibility, also set dilisense_result
        dilisense_result = aml_result
        
        # Check FATF high-risk jurisdiction
        fatf_result = self._check_fatf_jurisdiction(nationality)

        jurisdiction_risk = fatf_result.get("risk_score", 0)
        
        # Run parallel screening checks
        sanctions_risk = self._check_sanctions(name)
        pep_risk = self._check_pep(name)
        adverse_media_risk = self._check_adverse_media(name)
        # Behavioral risk is disabled until transactional data screening is implemented
        behavioral_risk = 0.0  # self._analyze_behavioral_patterns(additional_context or {})
        
        # Adjust risks based on Dilisense results
        if dilisense_result:
            total_hits = dilisense_result.get("total_hits", 0)
            
            # COMMON NAME DETECTION: If too many matches, results are unreliable
            # More than 10 matches = common name, can't reliably identify individual
            is_common_name = total_hits > 10
            
            if is_common_name:
                logger.warning(f"⚠️ COMMON NAME: {name} has {total_hits} matches - cannot reliably identify. Manual verification required.")
                # For common names, DO NOT auto-assign high risk - too many false positives
                # Only flag if there's overwhelming evidence (>50% of matches are a specific category)
                
                if dilisense_result["sanctions_hits"] > 0:
                    ratio = dilisense_result["sanctions_hits"] / total_hits
                    if ratio > 0.5:  # More than half are sanctions = likely real
                        sanctions_risk = max(sanctions_risk, 70)
                    # Otherwise don't auto-assign - common name false positive
                    
                if dilisense_result["pep_hits"] > 0:
                    ratio = dilisense_result["pep_hits"] / total_hits
                    if ratio > 0.5:
                        pep_risk = max(pep_risk, 60)
                        
                if dilisense_result["criminal_hits"] > 0:
                    ratio = dilisense_result["criminal_hits"] / total_hits
                    if ratio > 0.5:
                        adverse_media_risk = max(adverse_media_risk, 50)
            else:
                # Specific name (few matches) - apply normal risk
                if dilisense_result["sanctions_hits"] > 0:
                    sanctions_risk = max(sanctions_risk, 90)
                    logger.warning(f"⚠️ {dilisense_result.get('provider', 'AML Database')} SANCTIONS match for {name}")
                    
                if dilisense_result["pep_hits"] > 0:
                    pep_risk = max(pep_risk, 80)
                    logger.warning(f"⚠️ {dilisense_result.get('provider', 'AML Database')} PEP match for {name}")
                    
                if dilisense_result["criminal_hits"] > 0:
                    adverse_media_risk = max(adverse_media_risk, 70)
                    logger.warning(f"⚠️ {dilisense_result.get('provider', 'AML Database')} CRIMINAL match for {name}")
            
            # Check adverse_media_hits from World Check
            if dilisense_result.get("adverse_media_hits", 0) > 0:
                adverse_media_risk = max(adverse_media_risk, 70)
                logger.warning(f"⚠️ {dilisense_result.get('provider', 'AML Database')} ADVERSE MEDIA match for {name}")
            
            # Check special_interest_hits (regulatory enforcement, law enforcement)
            if dilisense_result.get("special_interest_hits", 0) > 0:
                adverse_media_risk = max(adverse_media_risk, 60)
                logger.warning(f"⚠️ {dilisense_result.get('provider', 'AML Database')} SPECIAL INTEREST match for {name}")
            
            # CRITICAL: Check for financial crimes in record details - but NOT for common names
            # For common names (>10 hits), records likely belong to different people
            if not is_common_name:
                financial_crime_keywords = ["FRAUD", "PONZI", "MONEY LAUNDERING", "EMBEZZLEMENT", "FINANCIAL CRIME", 
                                           "SECURITIES FRAUD", "SEC", "CRIME - FINANCIAL", "CONVICTED", "PRISON", "SENTENCED"]
                for record in dilisense_result.get("records", []):
                    record_text = " ".join([
                        str(record.get("sanction_details", "")),
                        str(record.get("entity_type", "")),
                        " ".join(record.get("positions", [])),
                        " ".join(record.get("sources", []))
                    ]).upper()
                    if any(keyword in record_text for keyword in financial_crime_keywords):
                        adverse_media_risk = max(adverse_media_risk, 70)  # Financial crimes affect adverse media risk
                        logger.warning(f"🚨 FINANCIAL CRIME indicators found for {name}: {record_text[:100]}")
                        break
        
        # Get detailed adverse media info for LLM context
        adverse_media_details = self._search_adverse_media_google(name, nationality)
        
        # Adjust risks based on jurisdiction
        if fatf_result["is_high_risk"]:
            # Removed: jurisdiction should not inflate sanctions risk
            logger.warning(f"⚠️ High-risk jurisdiction: {fatf_result['country']} - {fatf_result['reason']}")
        
        # Check adverse media for financial crime indicators - only if specific to this person
        # Be conservative for common names (many Dilisense hits = common name)
        is_common_name = dilisense_result and dilisense_result.get("total_hits", 0) > 10
        financial_crime_detected = False
        
        financial_crime_keywords = ["ponzi", "fraud", "money laundering", "embezzlement", "convicted", 
                                   "sentenced", "prison", "sec violation", "securities fraud", "financial crime"]
        if adverse_media_details and not is_common_name:
            adverse_text = str(adverse_media_details).lower()
            name_lower = name.lower()
            # Only trigger if financial crime keywords appear AND the name is directly mentioned
            # This prevents false positives from generic search results
            name_parts = name_lower.split()
            name_mentioned = any(part in adverse_text for part in name_parts if len(part) > 2)
            
            if name_mentioned and any(keyword in adverse_text for keyword in financial_crime_keywords):
                # Financial crime evidence in media affects adverse media risk only
                adverse_media_risk = max(adverse_media_risk, 100)
                financial_crime_detected = True
                logger.warning(f"🚨 FINANCIAL CRIME evidence in adverse media for {name}")
        
        # Combine risks with weighted scoring
        risks = {
            "sanctions": sanctions_risk,
            "pep": pep_risk,
            "adverse_media": adverse_media_risk,
            "jurisdiction": jurisdiction_risk
        }
        
        # Add adverse media details to context
        if additional_context is None:
            additional_context = {}
        additional_context["adverse_media_findings"] = adverse_media_details
        
        # Use LLM for enhanced risk analysis if available
        if self.use_llm and self.bedrock_available:
            logger.info("🤖 Enhancing analysis with Groq LLM")
            llm_analysis = self._llm_enhanced_analysis(name, entity_type, risks, additional_context or {})
            
            # Adjust risks based on LLM insights
            if llm_analysis:
                # Check if there are actual database matches
                has_db_matches = dilisense_result is not None and dilisense_result.get("total_hits", 0) > 0
                risks = self._adjust_risks_with_llm(risks, llm_analysis, has_database_matches=has_db_matches)
                flags = llm_analysis.get("flags") or []
                recommendations = llm_analysis.get("recommendations") or []
            else:
                # LLM failed, fall back to rules-based analysis
                flags = self._generate_flags(risks, name)
                recommendations = self._generate_recommendations(self._get_risk_level(self._calculate_final_score(risks)), flags, risks)
        else:
            # Generate flags and recommendations using rules
            flags = self._generate_flags(risks, name)
            recommendations = self._generate_recommendations(self._get_risk_level(self._calculate_final_score(risks)), flags, risks)
        
        # Calculate final score (weighted average)
        final_score = self._calculate_final_score(risks)
        
        # Determine risk level
        risk_level = self._get_risk_level(final_score)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        logger.info(f"✓ Screening complete for {name}: {risk_level} risk ({final_score:.1f}/100) in {processing_time}ms")
        
        # Compile positive findings
        jurisdiction_clear = not fatf_result["is_high_risk"]
        positive_findings = {
            "sanctions_clear": risks["sanctions"] < 10,
            "pep_clear": risks["pep"] < 10,
            "adverse_media_clear": risks["adverse_media"] < 10,
            "jurisdiction_clear": risks["jurisdiction"] < 10,
            "jurisdiction_clear": jurisdiction_clear,
            "dilisense_clear": dilisense_result is None or dilisense_result.get("total_hits", 0) == 0,
            "dilisense_matches": dilisense_result if dilisense_result else {"total_hits": 0, "sanctions_hits": 0, "pep_hits": 0, "criminal_hits": 0, "adverse_media_hits": 0, "special_interest_hits": 0, "records": []},
            "fatf_check": fatf_result,
            "checks_performed": [
                {"source": dilisense_result.get("provider", "Dilisense Screening") if dilisense_result else "Dilisense Screening", "status": "clear" if (dilisense_result is None or dilisense_result.get("total_hits", 0) == 0) else "hits_found", "details": f"{dilisense_result.get('total_hits', 0) if dilisense_result else 0} matches"},
                {"source": "Global Sanctions Lists", "status": "clear" if risks["sanctions"] < 10 else "potential_match", "details": "No sanctions matches" if risks["sanctions"] < 10 else "Review required"},
                {"source": "PEP Database", "status": "clear" if risks["pep"] < 10 else "potential_match", "details": "Not a PEP" if risks["pep"] < 10 else "PEP status detected"},
                {"source": "FATF Jurisdiction Check (Live)", "status": "clear" if jurisdiction_clear else "high_risk", "details": "Low-risk jurisdiction" if jurisdiction_clear else f"{fatf_result['country']} - {fatf_result['reason']}"},
                {"source": "Adverse Media Search", "status": "clear" if risks["adverse_media"] < 10 else "mentions_found", "details": f"{adverse_media_details.get('total_mentions', 0)} mentions found"},
                # Behavioral Analysis disabled - {"source": "Behavioral Analysis", "status": "clear" if risks["behavioral"] < 10 else "patterns_detected", "details": "No suspicious patterns" if risks["behavioral"] < 10 else "Patterns require review"}
            ],
            "overall_clear": final_score < 20 and jurisdiction_clear
        }

        return RiskScore(
            sanctions_risk=risks["sanctions"],
            pep_risk=risks["pep"],
            adverse_media_risk=risks["adverse_media"],
            jurisdiction_risk=risks["jurisdiction"],
            behavioral_risk=0,  # Disabled
            final_risk_score=final_score,
            risk_level=risk_level,
            flags=flags,
            recommendations=recommendations,
            adverse_media_findings=adverse_media_details,
            positive_findings=positive_findings,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def _load_sanctions_database(self) -> Dict[str, float]:
        """Load OFAC SDN sanctions list"""
        try:
            sdn_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'ofac_sdn_names.json')
            if os.path.exists(sdn_path):
                with open(sdn_path, 'r') as f:
                    data = json.load(f)
                    names = {name: 95.0 for name in data.get('names', [])}
                    logger.info(f"✅ Loaded {len(names)} names from OFAC SDN list")
                    return names
        except Exception as e:
            logger.warning(f"⚠️ Could not load OFAC database: {e}")
        return {}
    
    def _load_pep_database(self) -> Dict[str, float]:
        """Load local PEP database"""
        try:
            pep_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'mauritius_pep.json')
            if os.path.exists(pep_path):
                with open(pep_path, 'r') as f:
                    data = json.load(f)
                    peps = {p['name'].upper(): p.get('risk_score', 70) for p in data.get('peps', [])}
                    logger.info(f"✅ Loaded {len(peps)} PEPs from local database")
                    return peps
        except Exception as e:
            logger.warning(f"⚠️ Could not load PEP database: {e}")
        return {}

    def _load_fatf_database(self) -> Dict:
        """Load FATF high-risk jurisdictions - used as fallback cache"""
        try:
            fatf_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'fatf_high_risk.json')
            if os.path.exists(fatf_path):
                with open(fatf_path, 'r') as f:
                    data = json.load(f)
                    logger.info(f"✅ Loaded FATF fallback cache")
                    return data
        except Exception as e:
            logger.warning(f"⚠️ Could not load FATF fallback cache: {e}")
        return {}

    def _fetch_live_fatf_data(self) -> Dict:
        """Fetch latest FATF high-risk jurisdictions using live web search"""
        logger.info("🌐 Fetching LIVE FATF data via web search...")
        
        try:
            import httpx
            import os
            
            serper_key = os.getenv("SERPER_API_KEY")
            if not serper_key:
                logger.warning("⚠️ SERPER_API_KEY not set, cannot fetch live FATF data")
                return None
            
            # Search for current FATF grey list using Serper.dev
            response = httpx.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
                json={
                    "q": "FATF grey list increased monitoring countries list 2025 site:fatf-gafi.org OR site:complyadvantage.com",
                    "num": 10
                },
                timeout=15.0
            )
            
            if response.status_code != 200:
                logger.warning(f"⚠️ Serper.dev returned {response.status_code}")
                return None
            
            search_results = response.json()
            snippets = []
            
            for result in search_results.get("organic", [])[:5]:
                snippet = result.get("snippet", "")
                title = result.get("title", "")
                snippets.append(f"{title}: {snippet}")
            search_context = "\n".join(snippets)
            
            # Use Groq LLM to parse the search results and extract current FATF lists
            from groq import Groq

            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            
            prompt = f"""Based on these recent search results about FATF lists, extract the current countries on the FATF black list and grey list.

Search Results:
{search_context}

IMPORTANT NOTES:
- Mauritius was REMOVED from the grey list in October 2021 - do NOT include it
- South Africa was REMOVED from the grey list in October 2025 - do NOT include it
- Mali and Tanzania were REMOVED from the grey list in June 2025 - do NOT include them
- The black list (Call for Action) typically includes: North Korea, Iran, Myanmar
- The grey list changes frequently - only include countries explicitly mentioned as CURRENTLY on the list
- As of October 2025, grey list includes: Algeria, Angola, Bolivia, Bulgaria, Cameroon, Côte d'Ivoire, DRC, Haiti, Kenya, Lao PDR, Lebanon, Monaco, Namibia, Nepal, South Sudan, Syria, Venezuela, Vietnam, Virgin Islands (UK), Yemen

Return ONLY a valid JSON object:
{{
    "last_updated": "2025-11",
    "call_for_action": [
        {{"country": "Country Name", "codes": ["XX", "XXX"], "reason": "Brief reason"}}
    ],
    "grey_list": [
        {{"country": "Country Name", "codes": ["XX", "XXX"], "reason": "Brief reason"}}
    ]
}}

Be conservative - only include countries you are confident are CURRENTLY on the lists based on the search results."""

            llm_response = client.chat.completions.create(
                model="groq/compound",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2048
            )
            
            response_text = llm_response.choices[0].message.content
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                fatf_data = json.loads(response_text[json_start:json_end])
                
                # Validate - remove Mauritius if incorrectly included
                fatf_data["grey_list"] = [
                    c for c in fatf_data.get("grey_list", [])
                    if c.get("country", "").upper() != "MAURITIUS"
                ]
                
                # If grey list is empty, return error - no fallback to avoid outdated data
                if not fatf_data.get("grey_list") and not fatf_data.get("call_for_action"):
                    logger.error("❌ LLM returned empty FATF lists - cannot verify jurisdiction")
                    return None
                
                logger.info(f"✅ LIVE FATF data: {len(fatf_data.get('call_for_action', []))} black list, {len(fatf_data.get('grey_list', []))} grey list countries")
                
                # Cache for fallback
                # Caching disabled - always use live data
                return fatf_data
                
        except Exception as e:
            logger.warning(f"⚠️ Live FATF fetch failed: {e}")
        
        # Fallback to cached data if live fetch fails
        try:
            cache_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'fatf_high_risk_cache.json')
            if os.path.exists(cache_path):
                with open(cache_path, 'r') as f:
                    cached_data = json.load(f)
                    logger.info("📁 Using cached FATF data as fallback")
                    return cached_data
        except:
            pass
        
        return None


    def _cache_fatf_data(self, data: Dict):
        """Cache FATF data to local file"""
        try:
            fatf_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'fatf_high_risk_cache.json')
            with open(fatf_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.debug(f"Could not cache FATF data: {e}")

    def _check_fatf_jurisdiction(self, nationality: str) -> Dict:
        """Check if nationality is from a FATF high-risk jurisdiction (live check)"""
        result = {
            "is_high_risk": False,
            "risk_level": "normal",
            "country": nationality,
            "reason": None,
            "risk_score": 0,
            "source": "FATF"
        }
        
        if not nationality:
            return result
        
        nationality_upper = nationality.upper().strip()
        
        # Fetch live FATF data
        live_data = self._fetch_live_fatf_data()
        
        # ALWAYS require live data - no cache fallback for compliance accuracy
        if not live_data:
            logger.error(f"❌ FATF live check failed for {nationality} - unable to verify jurisdiction risk")
            return {
                "is_high_risk": False,
                "risk_level": "unknown",
                "country": nationality,
                "reason": "FATF live check unavailable - manual verification required",
                "risk_score": 0,
                "source": "FATF Live Check FAILED",
                "error": True,
                "error_message": "Unable to fetch live FATF data. Please verify jurisdiction risk manually."
            }
        
        fatf_data = live_data
        
        
        # Check Call for Action / Black List countries (highest risk)
        call_for_action = fatf_data.get("call_for_action", [])
        for country in call_for_action:
            country_name = country.get("country", "").upper()
            codes = [c.upper() for c in country.get("codes", [])]
            
            if nationality_upper == country_name or nationality_upper in codes or any(nationality_upper in country_name for _ in [1]) or any(country_name in nationality_upper for _ in [1]):
                logger.warning(f"⚠️ FATF Black List jurisdiction detected: {nationality}")
                return {
                    "is_high_risk": True,
                    "risk_level": "highest",
                    "country": country.get("country", nationality),
                    "reason": f"FATF Call for Action (Black List): {country.get('reason', 'Significant AML/CFT deficiencies')}",
                    "risk_score": 90,
                    "source": "FATF Live Check"
                }
        
        # Check Grey List countries (increased monitoring)
        grey_list = fatf_data.get("grey_list", fatf_data.get("increased_monitoring", []))
        for country in grey_list:
            country_name = country.get("country", "").upper()
            codes = [c.upper() for c in country.get("codes", [])]
            
            if nationality_upper == country_name or nationality_upper in codes or any(nationality_upper in country_name for _ in [1]) or any(country_name in nationality_upper for _ in [1]):
                logger.warning(f"⚠️ FATF Grey List jurisdiction detected: {nationality}")
                return {
                    "is_high_risk": True,
                    "risk_level": "high",
                    "country": country.get("country", nationality),
                    "reason": f"FATF Grey List (Increased Monitoring): {country.get('reason', 'Under increased monitoring')}",
                    "risk_score": 70,
                    "source": "FATF Live Check"
                }
        
        logger.info(f"✓ {nationality} is not on FATF high-risk lists")
        return result

    def _check_sanctions(self, name: str) -> float:
        """Check against OFAC and international sanctions lists"""
        
        try:
            # If we have a real API key, use it
            if self.ofac_api_key:
                return self._check_sanctions_real_api(name)
            
            # If mock database has entries, use them
            if self.use_mock and self.sanctions_database:
                for sanctioned_name, risk_score in self.sanctions_database.items():
                    similarity = fuzzy_match(name, sanctioned_name)
                    if similarity > 0.8:
                        logger.warning(f"⚠️ Sanctions match found for {name}: {sanctioned_name} (similarity: {similarity:.2f})")
                        return min(risk_score * similarity, 100)
                return 0  # No match found - zero baseline risk
            
            # Otherwise, return baseline - LLM will provide comprehensive analysis
            logger.debug(f"No sanctions database - LLM will analyze {name}")
            return 0  # No sanctions database match - zero baseline risk
                
        except Exception as e:
            logger.error(f"Sanctions screening failed: {e}")
            return 0  # Return zero on error - do not assume risk without evidence
    
    def _check_pep(self, name: str) -> float:
        """Check Politically Exposed Persons database"""
        
        try:
            # If we have a real API key, use it
            if self.refinitiv_api_key:
                return self._check_pep_real_api(name)
            
            # If mock database has entries, use them
            if self.use_mock and self.pep_database:
                for pep_name, risk_score in self.pep_database.items():
                    similarity = fuzzy_match(name, pep_name)
                    if similarity > 0.8:
                        logger.warning(f"⚠️ PEP match found: {name} -> {pep_name} (similarity: {similarity:.2f})")
                        return min(risk_score * similarity, 100)
                return 0  # Not a PEP
            
            # Otherwise, return baseline - LLM will provide comprehensive analysis
            logger.debug(f"No PEP database - LLM will analyze {name}")
            return 0  # Baseline risk, LLM will adjust if needed
                
        except Exception as e:
            logger.error(f"PEP screening failed: {e}")
            return 10
    
    def _search_adverse_media_google(self, name: str, nationality: str = None) -> Dict:
        """
        Search for adverse media mentions using web search.
        
        BROAD PRINCIPLES:
        1. Generate multiple name variants (patronymics, transliterations)
        2. Search with multiple query strategies for comprehensive coverage
        3. Check for PEP indicators based on naming patterns and nationality
        4. Use family-based searches to catch related party risks
        """
        try:
            import httpx
            
            results = {
                "total_mentions": 0,
                "risk_keywords_found": [],
                "articles": [],
                "risk_score": 0,
                "name_variants_searched": [],
                "pep_indicators": {}
            }
            
            # Extended risk keywords
            risk_keywords = ["fraud", "money laundering", "sanction", "crime", "corrupt",
                           "arrest", "convicted", "ponzi", "scandal", "embezzlement",
                           "bribery", "terrorism", "trafficking", "offshore", "investigation",
                           "kleptocrat", "oligarch", "laundromat", "unexplained wealth"]
            
            # Generate name variants and search queries
            search_queries = []
            if NAME_UTILS_AVAILABLE:
                name_variants = generate_name_variants(name)
                search_queries = generate_search_queries(name, nationality)
                results["name_variants_searched"] = name_variants[:5]
                
                # Check for PEP indicators
                pep_check = detect_pep_indicators(name, nationality)
                results["pep_indicators"] = pep_check
                if pep_check.get("is_potential_pep"):
                    logger.info(f"PEP indicators detected for {name}: {pep_check.get('indicators', [])}")
            else:
                search_queries = [f'"{name}" sanctions OR corruption OR fraud']
            
            # Try SerpAPI if available
            serper_key = os.getenv("SERPER_API_KEY")
            if serper_key:
                seen_links = set()
                try:
                    # Search with multiple queries
                    for query in search_queries[:3]:
                        logger.debug(f"Adverse media search: {query}")
                        response = httpx.get(
                            "https://serpapi.com/search",
                            params={"q": query, "api_key": serper_key, "num": 10, "engine": "google"},
                            timeout=15.0
                        )
                        if response.status_code == 200:
                            data = response.json()
                            organic = data.get("organic", [])
                            
                            # Check results with any name variant
                            name_variants_lower = [name.lower()]
                            if NAME_UTILS_AVAILABLE:
                                name_variants_lower = [v.lower() for v in generate_name_variants(name)]
                            
                            for item in organic[:5]:
                                link = item.get("link", "")
                                if link in seen_links:
                                    continue
                                seen_links.add(link)
                                
                                title = item.get("title", "").lower()
                                snippet = item.get("snippet", "").lower()
                                combined = title + " " + snippet
                                
                                # Check if any name variant appears
                                name_found = False
                                for variant in name_variants_lower:
                                    variant_parts = variant.split()
                                    # Match if family name + given name found
                                    if len(variant_parts) >= 2:
                                        if variant_parts[-1] in combined and variant_parts[0] in combined:
                                            name_found = True
                                            break
                                
                                if not name_found:
                                    continue
                                
                                for keyword in risk_keywords:
                                    if keyword in combined and keyword not in results["risk_keywords_found"]:
                                        results["risk_keywords_found"].append(keyword)
                                
                                if any(kw in combined for kw in risk_keywords):
                                    results["total_mentions"] += 1
                                    results["articles"].append({
                                        "title": item.get("title", ""),
                                        "snippet": item.get("snippet", ""),
                                        "link": link,
                                        "source": item.get("source", "Google")
                                    })
                except Exception as e:
                    logger.debug(f"Serper.dev search failed: {e}")
            
            # Fallback: Use Groq LLM to provide adverse media context
            if results["total_mentions"] == 0:
                try:
                    from groq import Groq
                    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                    
                    prompt = f"""Based on your knowledge, provide information about any adverse media, 
legal issues, or negative news associated with "{name}". 

If this person/entity has been involved in:
- Financial crimes (fraud, money laundering, embezzlement)
- Sanctions or regulatory actions
- Criminal convictions
- Corruption or bribery scandals
- Any other significant negative news

Return a JSON object with:
{{
    "has_adverse_media": true/false,
    "summary": "Brief summary of findings",
    "keywords": ["list", "of", "relevant", "keywords"],
    "notable_incidents": [
        {{"title": "Incident title", "description": "Brief description", "year": "YYYY"}}
    ]
}}

If no adverse media is known, return has_adverse_media: false with empty arrays."""

                    response = client.chat.completions.create(
                        model="groq/compound",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.1,
                        max_tokens=1024
                    )
                    
                    response_text = response.choices[0].message.content
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    
                    if json_start >= 0 and json_end > json_start:
                        llm_data = json.loads(response_text[json_start:json_end])
                        
                        if llm_data.get("has_adverse_media"):
                            results["risk_keywords_found"] = llm_data.get("keywords", [])[:5]
                            
                            incidents = llm_data.get("notable_incidents", [])
                            for incident in incidents[:3]:
                                results["articles"].append({
                                    "title": incident.get("title", ""),
                                    "snippet": incident.get("description", ""),
                                    "link": "",
                                    "source": f"Known incident ({incident.get('year', 'N/A')})"
                                })
                                results["total_mentions"] += 1
                            
                            # Add summary as first article
                            if llm_data.get("summary"):
                                results["articles"].insert(0, {
                                    "title": f"Adverse Media Summary: {name}",
                                    "snippet": llm_data.get("summary", ""),
                                    "link": "",
                                    "source": "AI Analysis"
                                })
                                
                except Exception as e:
                    logger.debug(f"LLM adverse media search failed: {e}")
            
            # Calculate risk score
            if len(results["risk_keywords_found"]) >= 3:
                results["risk_score"] = 80
            elif len(results["risk_keywords_found"]) >= 2:
                results["risk_score"] = 50
            elif len(results["risk_keywords_found"]) >= 1:
                results["risk_score"] = 30
            
            if results["total_mentions"] > 0:
                logger.info(f"🔍 Adverse media for {name}: {results['total_mentions']} mentions, keywords: {results['risk_keywords_found']}")
            
            return results
            
        except Exception as e:
            logger.error(f"Adverse media search failed: {e}")
            return {"total_mentions": 0, "risk_score": 0, "articles": [], "risk_keywords_found": []}

    def _check_adverse_media(self, name: str) -> float:
        """Check financial crime news databases"""
        
        try:
            # If we have a real API key, use it
            if self.refinitiv_api_key:
                return self._check_adverse_media_real_api(name)
            
            # If mock database has entries, use them
            if self.use_mock and self.adverse_media_database:
                for adverse_name, risk_score in self.adverse_media_database.items():
                    similarity = fuzzy_match(name, adverse_name)
                    if similarity > 0.8:
                        logger.warning(f"⚠️ Adverse media found: {name} -> {adverse_name} (similarity: {similarity:.2f})")
                        return min(risk_score * similarity, 100)
                return 0
            
            # Otherwise, return baseline - LLM will provide comprehensive analysis
            logger.debug(f"No adverse media database - LLM will analyze {name}")
            return 0  # Baseline risk, LLM will adjust if needed
                
        except Exception as e:
            logger.error(f"Adverse media screening failed: {e}")
            return 0  # No risk without evidence
    
    def _analyze_behavioral_patterns(self, context: Dict) -> float:
        """Analyze behavioral patterns for anomalies"""
        
        try:
            risk_score = 0
            pattern_count = 0
            
            # Check for suspicious transaction patterns
            transaction_amount = context.get("transaction_amount", 0)
            transaction_frequency = context.get("transaction_frequency", 0)
            
            # Round dollar amounts (potential structuring)
            if transaction_amount > 0 and transaction_amount % 1000 == 0:
                risk_score += self.behavioral_patterns["round_dollar_amounts"]
                pattern_count += 1
            
            # Amounts just below reporting thresholds
            if 9000 <= transaction_amount <= 9999:
                risk_score += self.behavioral_patterns["structuring"]
                pattern_count += 1
            
            # High frequency transactions
            if transaction_frequency > 10:
                risk_score += self.behavioral_patterns["frequent_small_transactions"]
                pattern_count += 1
            
            # Cross-border indicators
            if context.get("cross_border", False):
                risk_score += self.behavioral_patterns["cross_border_transfers"]
                pattern_count += 1
            
            # Average the risk if multiple patterns detected
            if pattern_count > 0:
                return min(risk_score / pattern_count, 100)
            
            return 0
            
        except Exception as e:
            logger.error(f"Behavioral analysis failed: {e}")
            return 10
    
    def _calculate_final_score(self, risks: Dict[str, float]) -> float:
        """Calculate weighted risk score from components"""
        
        weights = {
            "sanctions": 0.85,      # 85% weight - CRITICAL priority
            "pep": 0.30,           # 30% weight - MEDIUM
            "adverse_media": 0.20,  # 20% weight - MEDIUM
            "jurisdiction": 0.20   # 20% weight - MEDIUM
        }
        
        final_score = sum(risks[key] * weights[key] for key in risks if key in weights)
        return min(final_score, 100)  # Cap at 100
    
    def _get_risk_level(self, score: float) -> RiskLevel:
        """Convert risk score to risk level"""
        if score < 15:
            return RiskLevel.LOW
        elif score < 40:
            return RiskLevel.MEDIUM
        elif score < 75:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    def _generate_flags(self, risks: Dict[str, float], name: str) -> List[str]:
        """Generate compliance flags based on risks"""
        
        flags = []
        
        if risks["sanctions"] > 50:
            flags.append("SANCTIONS_MATCH")
        if risks["pep"] > 30:
            flags.append("PEP_MATCH")
        if risks["adverse_media"] > 50:
            flags.append("ADVERSE_MEDIA_MATCH")
        if risks["jurisdiction"] > 60:
            flags.append("SUSPICIOUS_PATTERNS")
        
        # Combination flags
        risk_count = sum(1 for risk in risks.values() if risk > 20)
        if risk_count >= 2:
            flags.append("MULTIPLE_RISK_FACTORS")
        
        if risks["sanctions"] > 80:
            flags.append("HIGH_SANCTIONS_RISK")
        
        return flags
    
    def _generate_recommendations(self, risk_level: RiskLevel, flags: List[str], risks: Dict[str, float]) -> List[str]:
        """Generate recommendations based on risk level and flags"""
        
        recommendations = []
        
        if risk_level == RiskLevel.LOW:
            recommendations.append("Auto-approve transaction")
            recommendations.append("Standard monitoring procedures")
        
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.append("Flag for compliance review")
            recommendations.append("Conduct enhanced due diligence")
            recommendations.append("Verify source of funds")
        
        elif risk_level == RiskLevel.HIGH:
            recommendations.append("Escalate to senior compliance officer")
            recommendations.append("Obtain additional documentation")
            recommendations.append("Monitor future transactions from this entity")
            recommendations.append("Consider filing Suspicious Activity Report")
        
        elif risk_level == RiskLevel.CRITICAL:
            recommendations.append("BLOCK TRANSACTION IMMEDIATELY")
            recommendations.append("File Suspicious Activity Report (SAR)")
            recommendations.append("Report to FIU within 30 days")
            recommendations.append("Implement remedial measures")
            recommendations.append("Consider account closure")
        
        # Specific flag-based recommendations
        if "SANCTIONS_MATCH" in flags:
            recommendations.append("Review against OFAC specially designated nationals list")
            recommendations.append("Freeze assets pending investigation")
        
        if "PEP_MATCH" in flags:
            recommendations.append("Verify beneficial ownership structure")
            recommendations.append("Enhanced ongoing monitoring required")
        
        if "ADVERSE_MEDIA_MATCH" in flags:
            recommendations.append("Review recent news and legal proceedings")
            recommendations.append("Assess reputational risk to institution")
        
        if "SUSPICIOUS_PATTERNS" in flags:
            recommendations.append("Analyze transaction history for patterns")
            recommendations.append("Interview customer about transaction purpose")
        
        return recommendations
    
    def _check_sanctions_real_api(self, name: str) -> float:
        """Real OFAC API implementation (placeholder)"""
        # This would implement actual OFAC API calls
        logger.info(f"Would call real OFAC API for: {name}")
        return 0  # No sanctions match
    
    def _check_pep_real_api(self, name: str) -> float:
        """Real PEP API implementation (placeholder)"""
        # This would implement actual PEP database API calls
        logger.info(f"Would call real PEP API for: {name}")
        return 0
    
    def _check_adverse_media_real_api(self, name: str) -> float:
        """Real adverse media API implementation (placeholder)"""
        # This would implement actual adverse media API calls
        logger.info(f"Would call real adverse media API for: {name}")
        return 0
    
    def _check_bedrock_availability(self) -> bool:
        """Check if AWS Bedrock is available"""
        try:
            import boto3
            from dotenv import load_dotenv
            load_dotenv()
            
            session = boto3.Session()
            credentials = session.get_credentials()
            
            if credentials is None:
                return False
            
            # Try to create bedrock client
            bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
            return True
        except Exception as e:
            logger.debug(f"Bedrock not available: {e}")
            return False
    
    def _check_dilisense(self, name: str, dob: str = None, gender: str = None) -> Dict:
        """Check individual against Dilisense AML database"""
        if not self.dilisense_api_key:
            logger.debug("No Dilisense API key configured")
            return None
        
        try:
            import httpx
            
            params = {
                "names": name,
                "fuzzy_search": 1,
                "search_type": "individual"
            }
            
            if dob:
                params["dob"] = dob
            if gender:
                params["gender"] = gender
            
            headers = {
                "x-api-key": self.dilisense_api_key
            }
            
            response = httpx.get(
                "https://api.dilisense.com/v1/checkIndividual",
                params=params,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
            total_hits = result.get("total_hits", 0)
            found_records = result.get("found_records", [])
            
            logger.info(f"🔍 Dilisense screening for {name}: {total_hits} hits")
            
            # Process results with name matching filter
            screening_result = {
                "total_hits": 0,
                "sanctions_hits": 0,
                "pep_hits": 0,
                "criminal_hits": 0,
                "special_interest_hits": 0,
                "records": [],
                "risk_level": "LOW",
                "provider": "Dilisense Screening"
            }
            
            # Filter results - only count strong name matches
            search_name_parts = set(name.upper().split())
            
            for record in found_records:
                record_name = record.get("name", "")
                record_name_parts = set(record_name.upper().split())
                
                # Calculate name overlap - require at least 50% of search name parts to match
                if search_name_parts:
                    overlap = len(search_name_parts & record_name_parts) / len(search_name_parts)
                else:
                    overlap = 0
                
                # Skip weak matches (less than 50% name overlap)
                if overlap < 0.75:
                    continue
                
                source_type = record.get("source_type", "")
                if source_type == "SANCTION":
                    screening_result["sanctions_hits"] += 1
                elif source_type == "PEP":
                    screening_result["pep_hits"] += 1
                elif source_type == "CRIMINAL":
                    screening_result["criminal_hits"] += 1

                screening_result["records"].append({
                    "name": record_name,
                    "source_type": source_type,
                    "entity_type": record.get("entity_type"),
                    "positions": record.get("positions", [])[:3],
                    "sanction_details": ", ".join(record.get("sanction_details", [])) if isinstance(record.get("sanction_details"), list) else (record.get("sanction_details") or ""),
                    "match_strength": f"{overlap*100:.0f}%"
                })
            
            # Update totals after filtering
            screening_result["total_hits"] = len(screening_result["records"])
            if screening_result["sanctions_hits"] > 0:
                screening_result["risk_level"] = "CRITICAL"
            elif screening_result["pep_hits"] > 0 or screening_result["criminal_hits"] > 0:
                screening_result["risk_level"] = "HIGH"
            elif screening_result["total_hits"] > 0:
                screening_result["risk_level"] = "MEDIUM"
            
            logger.info(f"🔍 Dilisense filtered: {screening_result['total_hits']} matches (from {total_hits} raw hits)")
            
            return screening_result
            
        except Exception as e:
            logger.error(f"❌ Dilisense screening failed: {e}")
            return None

    def _llm_enhanced_analysis(self, name: str, entity_type: str, risks: Dict[str, float], context: Dict) -> Dict:
        """
        Use Groq LLM to provide enhanced risk analysis
        """
        try:
            import os
            from dotenv import load_dotenv
            load_dotenv()
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            # Create comprehensive prompt for LLM
            prompt = f"""You are an expert AML (Anti-Money Laundering) compliance analyst with access to global sanctions lists, PEP databases, and adverse media sources. Analyze the following entity and provide a comprehensive risk assessment.

Entity Information:
- Name: {name}
- Type: {entity_type}
- Context: {json.dumps(context, indent=2)}

Adverse Media Search Results:
{json.dumps(context.get('adverse_media_findings', {}), indent=2)}

Initial Screening Results (baseline):
- Sanctions Risk Score: {risks['sanctions']:.1f}/100
- PEP (Politically Exposed Person) Risk: {risks['pep']:.1f}/100
- Adverse Media Risk: {risks['adverse_media']:.1f}/100
- Jurisdiction Risk: {risks['jurisdiction']:.1f}/100

Your Task:
1. Analyze if this entity appears on any sanctions lists (OFAC, UN, EU, etc.)
2. Determine if this is a Politically Exposed Person (PEP) or associated with one
3. CRITICALLY analyze adverse media with CONTEXTUAL UNDERSTANDING:
   - Is the person ACCUSED of wrongdoing, or merely MENTIONED in articles?
   - Is the person a SUBJECT of investigation/allegations, or a PROFESSIONAL working in the field?
   - Government officials speaking about combating crime should NOT be flagged for adverse media
   - Only flag adverse_media risk if the person is NEGATIVELY implicated (accused, investigated, charged, convicted)
   - A minister discussing AML policy is NOT adverse media - they are doing their job
   - Look for actual allegations, charges, investigations, or convictions against the person
4. Assess jurisdiction risk based on country/region
5. Provide adjusted risk scores based on your analysis (0-100 scale)
6. Generate specific compliance flags
7. Provide actionable recommendations for compliance officers

IMPORTANT: Base your analysis on real-world knowledge of:
- Current sanctions lists and designated persons
- Known PEPs and government officials
- Public records of financial crimes and fraud cases
- Typical money laundering patterns and red flags

Return your analysis in JSON format:
{{
    "risk_adjustments": {{
        "sanctions": <0-100 score based on sanctions list matches>,
        "pep": <0-100 score based on PEP status>,
        "adverse_media": <0-100 score - ONLY if person is ACCUSED/INVESTIGATED/CHARGED, NOT if merely mentioned professionally>,
        "jurisdiction": <0-100 score based on jurisdiction risk>
    }},
    "flags": ["Specific compliance flags like SANCTIONS_MATCH, PEP_MATCH, ADVERSE_MEDIA_MATCH, etc."],
    "recommendations": ["Specific actionable recommendations for compliance team"],
    "narrative": "2-3 sentence summary of key risk factors and recommended actions"
}}

CRITICAL ADVERSE MEDIA GUIDANCE:
- Score 0-20: Person mentioned in neutral/positive context (e.g., official speaking about policy)
- Score 30-50: Mixed mentions, some concerns but no direct accusations
- Score 60-80: Person is subject of allegations, investigation, or legal proceedings
- Score 90-100: Person is convicted or has confirmed involvement in financial crimes

Do NOT penalize people for doing their jobs (e.g., AML officers, ministers discussing financial crime policy).

Be thorough and base your assessment on factual information. If uncertain about adverse media context, default to LOW risk unless there are clear accusations."""

            # Call Bedrock Claude with updated model
            response = client.chat.completions.create(
                model="groq/compound",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2048
            )

            response_text = response.choices[0].message.content
            
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                llm_analysis = json.loads(json_str)
                
                logger.info(f"✅ LLM analysis complete: {llm_analysis.get('narrative', 'No narrative')[:100]}...")
                return llm_analysis
            else:
                logger.warning("⚠️ Could not extract JSON from LLM response")
                return None
            
        except Exception as e:
            logger.error(f"❌ LLM analysis failed: {e}")
            return None
    
    def _adjust_risks_with_llm(self, original_risks: Dict[str, float], llm_analysis: Dict, has_database_matches: bool = False) -> Dict[str, float]:
        """
        Adjust risk scores based on LLM recommendations
        IMPORTANT: LLM can only INCREASE risks, never DECREASE them when there are database matches
        """
        adjusted_risks = original_risks.copy()
        risk_adjustments = llm_analysis.get("risk_adjustments", {})
        
        for risk_type, adjustment in risk_adjustments.items():
            if adjustment is not None and risk_type in adjusted_risks:
                # CRITICAL: LLM can ONLY adjust adverse_media risk
                # Sanctions, PEP, Jurisdiction use authoritative database sources
                if risk_type != "adverse_media":
                    continue
                original_value = original_risks[risk_type]
                new_value = max(0, min(100, adjustment))
                
                # CRITICAL: If there are database matches, LLM can only INCREASE risks, not decrease
                if has_database_matches and new_value < original_value:
                    logger.warning(f"⚠️ LLM tried to reduce {risk_type} risk from {original_value:.1f} to {new_value:.1f} - BLOCKED (database matches exist)")
                    continue
                
                adjusted_risks[risk_type] = new_value
                if abs(new_value - original_value) > 5:
                    logger.info(f"🔄 LLM adjusted {risk_type} risk: {original_value:.1f} → {new_value:.1f}")
        
        return adjusted_risks
        

    def _get_worldcheck_headers(self, method: str, endpoint: str, body: str = "") -> Dict:
        """Generate HMAC authentication headers for World-Check One API"""
        import hmac
        import hashlib
        from datetime import datetime, timezone
        
        gateway_host = "api.risk.lseg.com"
        gateway_url = "/screening/v3/"
        
        date = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # Build the data to sign
        if body:
            content_length = str(len(body))
            data_to_sign = f"(request-target): {method.lower()} {gateway_url}{endpoint}\nhost: {gateway_host}\ndate: {date}\ncontent-type: application/json\ncontent-length: {content_length}\n{body}"
            headers_param = "(request-target) host date content-type content-length"
        else:
            data_to_sign = f"(request-target): {method.lower()} {gateway_url}{endpoint}\nhost: {gateway_host}\ndate: {date}"
            headers_param = "(request-target) host date"
        
        # IMPORTANT: Do NOT base64 decode the secret - use as raw UTF-8 bytes
        secret_bytes = self.worldcheck_api_secret.encode('utf-8')
        signature = hmac.new(secret_bytes, data_to_sign.encode('utf-8'), hashlib.sha256).digest()
        
        import base64
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        auth_header = f'Signature keyId="{self.worldcheck_api_key}",algorithm="hmac-sha256",headers="{headers_param}",signature="{signature_b64}"'
        
        headers = {
            "Authorization": auth_header,
            "Date": date,
            "Content-Type": "application/json"
        }
        
        if body:
            headers["Content-Length"] = str(len(body))
        
        return headers

    def _check_worldcheck(self, name: str, entity_type: str = "individual", dob: str = None, nationality: str = None) -> Dict:
        """Check individual/entity against World-Check One database"""
        
        if not self.worldcheck_api_key or not self.worldcheck_api_secret:
            logger.debug("No World-Check API credentials configured")
            return None
        
        if self.worldcheck_api_key == "your_worldcheck_api_key_here":
            logger.debug("World-Check API key not configured (placeholder value)")
            return None
        
        try:
            import httpx
            import json
            
            base_url = "https://api.risk.lseg.com/screening/v3"
            
            # Step 1: Get available groups
            logger.info(f"🔍 World-Check: Getting groups...")
            headers = self._get_worldcheck_headers("GET", "groups")
            
            response = httpx.get(
                f"{base_url}/groups",
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"❌ World-Check groups request failed: {response.status_code} - {response.text}")
                return None
            
            groups_data = response.json()
            if not groups_data:
                logger.error("❌ World-Check: No groups available")
                return None
            
            # Get the first group ID
            group_id = groups_data[0].get("id") if isinstance(groups_data, list) else groups_data.get("id")
            logger.info(f"🔍 World-Check: Using group ID: {group_id}")
            
            # Step 2: Create and screen a case synchronously
            case_payload = {
                "groupId": group_id,
                "entityType": "INDIVIDUAL" if entity_type.lower() == "individual" else "ORGANISATION",
                "caseId": f"INSTA-{name.replace(' ', '-').upper()[:15]}-{int(time.time())}",
                "name": name,
                "providerTypes": ["WATCHLIST"]
            }
            
            # Add optional fields
            if dob:
                case_payload["dateOfBirth"] = dob
            if nationality:
                case_payload["countryLocation"] = nationality
            
            body_json = json.dumps(case_payload)
            headers = self._get_worldcheck_headers("POST", "cases", body_json)
            
            logger.info(f"🔍 World-Check: Screening {name}...")
            
            response = httpx.post(
                f"{base_url}/cases?screen=SYNC",
                content=body_json,
                headers=headers,
                timeout=60.0
            )
            
            if response.status_code not in [200, 201]:
                logger.error(f"❌ World-Check screening failed: {response.status_code} - {response.text}")
                return None
            
            result = response.json()
            
            # Parse World-Check response
            screening_result = {
                "total_hits": 0,
                "sanctions_hits": 0,
                "pep_hits": 0,
                "criminal_hits": 0,
                "adverse_media_hits": 0,
                "special_interest_hits": 0,
                "records": [],
                "risk_level": "LOW",
                "provider": "World Check One Screening",
                "case_id": result.get("caseId", ""),
                "case_system_id": result.get("caseSystemId", "")
            }
            
            # Get results from response
            results = result.get("results", [])
            screening_result["total_hits"] = len(results)
            
            for match in results:
                # Get category information from World-Check sourceCategories
                source_categories = match.get("sourceCategories", [])
                category_str = " ".join(source_categories).upper() if source_categories else ""
                
                # Get reference ID
                reference_id = match.get("referenceId", "")
                
                # Get matched name from matchedTerms array
                matched_name = "Unknown"
                matched_terms = match.get("matchedTerms", [])
                if matched_terms:
                    matched_name = matched_terms[0].get("term", "Unknown")
                else:
                    # Fallback to names array
                    names = match.get("names", [])
                    for name_entry in names:
                        if name_entry.get("type") == "PRIMARY":
                            details = name_entry.get("details", [])
                            for detail in details:
                                if detail.get("type") == "FULL_NAME":
                                    matched_name = detail.get("value", "Unknown")
                                    break
                
                match_strength = match.get("matchStrength", "EXACT")
                match_score = match.get("matchScore", 100.0)
                
                # Get country information from locations
                countries = []
                locations = match.get("locations", [])
                for loc in locations:
                    country = loc.get("country", {})
                    if country.get("name"):
                        countries.append(country.get("name"))
                countries = list(set(countries))
                
                # Get positions/roles from recordType
                positions = []
                record_type = match.get("recordType", {})
                record_sub_types = record_type.get("recordSubTypes", [])
                for sub_type in record_sub_types:
                    if sub_type.get("value"):
                        positions.append(sub_type.get("value"))
                
                # Add PEP status if available
                pep_status = match.get("pepStatus", "")
                if pep_status:
                    positions.append(f"PEP Status: {pep_status}")
                
                record = {
                    "name": matched_name,
                    "source_type": "UNKNOWN",
                    "match_type": match_strength,
                    "match_score": int(match_score),
                    "entity_type": record_type.get("value", ""),
                    "positions": positions,
                    "countries": countries,
                    "sources": source_categories,
                    "sanction_details": ", ".join(source_categories) if source_categories else "",
                    "reference_id": reference_id
                }
                
                
                # Combine sourceCategories and positions for categorization
                all_categories = category_str + " " + " ".join(positions).upper()
                
                # Categorize the match based on all available category info
                if any(cat in all_categories for cat in ["SANCTION", "SANCTIONS", "SAN", "OFAC", "SDN"]):
                    screening_result["sanctions_hits"] += 1
                    record["source_type"] = "SANCTION"
                elif any(cat in all_categories for cat in ["PEP", "POLITICAL", "GOVERNMENT", "MINISTER", "PRESIDENT"]):
                    screening_result["pep_hits"] += 1
                    record["source_type"] = "PEP"
                elif any(cat in all_categories for cat in ["ADVERSE", "AME", "CRIME", "CRIMINAL", "TERROR", "FRAUD", "MONEY LAUNDERING"]):
                    screening_result["adverse_media_hits"] += 1
                    record["source_type"] = "ADVERSE_MEDIA"
                elif any(cat in all_categories for cat in ["SPECIAL INTEREST", "LAW ENFORCEMENT", "REGULATORY", "OTHER BODIES", "WATCHLIST", "ENFORCEMENT"]):
                    screening_result["special_interest_hits"] += 1
                    record["source_type"] = "SPECIAL_INTEREST"
                else:
                    # Default to special interest if there's a match but uncategorized
                    screening_result["special_interest_hits"] += 1
                    record["source_type"] = "SPECIAL_INTEREST"
    
                
                screening_result["records"].append(record)
            
            # Set risk level based on hits
            if screening_result["sanctions_hits"] > 0:
                screening_result["risk_level"] = "CRITICAL"
            elif screening_result["pep_hits"] > 0:
                screening_result["risk_level"] = "HIGH"
            elif screening_result["adverse_media_hits"] > 0:
                screening_result["risk_level"] = "MEDIUM"
            elif screening_result["total_hits"] > 0:
                screening_result["risk_level"] = "MEDIUM"
            
            logger.info(f"✅ World-Check screening for {name}: {screening_result['total_hits']} hits (Sanctions: {screening_result['sanctions_hits']}, PEP: {screening_result['pep_hits']}, Special Interest: {screening_result['special_interest_hits']})")
            
            return screening_result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ World-Check API error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"❌ World-Check screening failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _convert_match_strength_to_score(self, strength: str) -> int:
        """Convert World-Check match strength to numeric score"""
        strength_map = {
            "EXACT": 100,
            "STRONG": 90,
            "MEDIUM": 75,
            "WEAK": 50,
            "": 0
        }
        return strength_map.get(strength.upper(), 60)


if __name__ == "__main__":
    # Production mode: use_mock=False, use_llm=True
    # This will use AWS Bedrock LLM for comprehensive risk analysis
    engine = ScreeningEngine(use_mock=False, use_llm=True)
    
    # Test screening with real entity
    test_entity = "Sample Entity Name"
    risk_score = engine.screen_entity(test_entity, entity_type="individual")
    
    print(f"\n{'='*60}")
    print(f"Risk Assessment for: {test_entity}")
    print(f"{'='*60}")
    print(f"Risk Score: {risk_score.final_risk_score:.1f}/100")
    print(f"Risk Level: {risk_score.risk_level}")
    print(f"\nFlags: {', '.join(risk_score.flags) if risk_score.flags else 'None'}")
    print(f"\nRecommendations:")
    for i, rec in enumerate(risk_score.recommendations, 1):
        print(f"  {i}. {rec}")
    print(f"{'='*60}\n")