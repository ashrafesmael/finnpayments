"""
Name Processing Utilities for AML Screening
Implements broad principles for name normalization, variant generation, and search optimization
"""

import re
from typing import List, Dict, Tuple, Optional


def normalize_name(name: str) -> str:
    """
    Normalize a name by removing titles, suffixes, and standardizing format
    """
    if not name:
        return ""
    
    # Convert to uppercase for consistency
    name = name.upper().strip()
    
    # Remove common titles and honorifics
    titles = [
        'MR', 'MRS', 'MS', 'MISS', 'DR', 'PROF', 'SIR', 'LADY', 'LORD',
        'HON', 'REV', 'FATHER', 'SISTER', 'BROTHER', 'SHEIKH', 'IMAM',
        'HIS EXCELLENCY', 'HER EXCELLENCY', 'H.E.', 'HE'
    ]
    for title in titles:
        name = re.sub(rf'\b{title}\.?\s+', '', name)
    
    # Remove common suffixes
    suffixes = ['JR', 'SR', 'II', 'III', 'IV', 'ESQ', 'PHD', 'MD', 'MBA']
    for suffix in suffixes:
        name = re.sub(rf'\s+{suffix}\.?$', '', name)
    
    # Normalize multiple spaces
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name


def extract_name_components(full_name: str) -> Dict[str, str]:
    """
    Extract name components from a full name
    Handles various naming conventions (Western, Arabic, Eastern European, etc.)
    
    Returns dict with: given_name, middle_names, family_name, patronymic
    """
    name = normalize_name(full_name)
    parts = name.split()
    
    result = {
        'given_name': '',
        'middle_names': '',
        'family_name': '',
        'patronymic': '',
        'full_normalized': name
    }
    
    if not parts:
        return result
    
    # Detect patronymic patterns (common in Azerbaijan, Russia, Arab world)
    patronymic_markers = ['OGLU', 'OGLI', 'OGLY', 'KIZI', 'QIZI', 'BIN', 'IBN', 'BINT', 
                          'OVICH', 'EVICH', 'OVNA', 'EVNA', 'VICH', 'VNA']
    
    patronymic_idx = -1
    for i, part in enumerate(parts):
        for marker in patronymic_markers:
            if marker in part or part.endswith(marker):
                patronymic_idx = i
                break
    
    if len(parts) == 1:
        result['given_name'] = parts[0]
    elif len(parts) == 2:
        result['given_name'] = parts[0]
        result['family_name'] = parts[1]
    elif patronymic_idx > 0:
        # Name with patronymic: GIVEN PATRONYMIC FAMILY
        # e.g., ANAR ELDAR OGLU MAHMUDOV -> given=ANAR, patronymic=ELDAR OGLU, family=MAHMUDOV
        result['given_name'] = parts[0]
        if patronymic_idx < len(parts) - 1:
            result['patronymic'] = ' '.join(parts[1:patronymic_idx+1])
            result['family_name'] = ' '.join(parts[patronymic_idx+1:])
        else:
            result['patronymic'] = ' '.join(parts[1:])
    else:
        # Standard: GIVEN MIDDLE... FAMILY
        result['given_name'] = parts[0]
        result['family_name'] = parts[-1]
        if len(parts) > 2:
            result['middle_names'] = ' '.join(parts[1:-1])
    
    return result


def generate_name_variants(name: str) -> List[str]:
    """
    Generate common spelling and format variants of a name
    Implements broad transliteration rules for multiple scripts/languages
    """
    variants = set()
    name = normalize_name(name)
    variants.add(name)
    
    components = extract_name_components(name)
    
    # Variant 1: Just given name + family name (drop patronymic/middle)
    if components['given_name'] and components['family_name']:
        simple = f"{components['given_name']} {components['family_name']}"
        variants.add(simple)
    
    # Variant 2: Family name, Given name (reversed order)
    if components['given_name'] and components['family_name']:
        reversed_name = f"{components['family_name']} {components['given_name']}"
        variants.add(reversed_name)
    
    # Variant 3: Just family name (for family-based searches)
    if components['family_name']:
        variants.add(components['family_name'])
    
    # Apply transliteration variants to all current variants
    transliteration_rules = {
        # Azerbaijani/Turkish
        'OGLU': ['OGHLU', 'OGLY', 'OGLI'],
        'KIZI': ['QIZI', 'KYZY'],
        
        # Russian patronymics
        'OVICH': ['OVITCH', 'OVIC'],
        'EVICH': ['EVITCH', 'EVIC'],
        'OVNA': ['OWNA'],
        'EVNA': ['EWNA'],
        
        # Arabic transliterations
        'AL-': ['AL ', 'EL-', 'EL ', ''],
        'AL ': ['AL-', 'EL-', 'EL ', ''],
        'ABD ': ['ABDUL ', 'ABDEL ', 'ABD-', 'ABDU '],
        'ABDUL ': ['ABD ', 'ABDEL ', 'ABD-', 'ABDU '],
        'ABDEL ': ['ABD ', 'ABDUL ', 'ABD-'],
        'MOHAMMED': ['MOHAMMAD', 'MUHAMMAD', 'MOHAMED', 'MUHAMMED'],
        'MOHAMMAD': ['MOHAMMED', 'MUHAMMAD', 'MOHAMED', 'MUHAMMED'],
        'AHMED': ['AHMAD', 'AHMET'],
        'AHMAD': ['AHMED', 'AHMET'],
        
        # Common letter substitutions
        'PH': ['F'],
        'KH': ['H', 'K'],
        'GH': ['G'],
        'SH': ['CH'],
        'TH': ['T'],
        'DH': ['D'],
        'Y': ['I', 'J'],
        'W': ['V', 'U'],
        'K': ['C', 'Q'],
        'C': ['K', 'S'],
        'Z': ['S'],
        
        # Double letters
        'MM': ['M'],
        'NN': ['N'],
        'DD': ['D'],
        'TT': ['T'],
        'LL': ['L'],
        'SS': ['S'],
    }
    
    # Apply transliteration rules
    current_variants = list(variants)
    for variant in current_variants:
        for pattern, replacements in transliteration_rules.items():
            if pattern in variant:
                for replacement in replacements:
                    new_variant = variant.replace(pattern, replacement)
                    if new_variant and new_variant != variant:
                        variants.add(new_variant)
    
    # Limit to reasonable number of variants
    return list(variants)[:10]


def generate_search_queries(name: str, nationality: Optional[str] = None) -> List[str]:
    """
    Generate optimized search queries for adverse media detection
    Returns multiple query variants for comprehensive coverage
    """
    queries = []
    components = extract_name_components(name)
    variants = generate_name_variants(name)
    
    # High-value risk keywords (prioritized)
    risk_terms = [
        'sanctions',
        'corruption',
        'money laundering', 
        'fraud',
        'embezzlement',
        'PEP',
        'politically exposed',
        'arrested',
        'convicted',
        'investigation',
        'scandal',
        'bribery',
        'offshore',
        'unexplained wealth'
    ]
    
    # Query 1: Simple name + risk terms (most effective)
    simple_name = f"{components['given_name']} {components['family_name']}".strip()
    if simple_name:
        queries.append(f'"{simple_name}" sanctions OR corruption OR fraud')
    
    # Query 2: Full name with quotes
    queries.append(f'"{normalize_name(name)}" sanctions OR money laundering OR PEP')
    
    # Query 3: Family name + nationality (if available)
    if components['family_name'] and nationality:
        queries.append(f'"{components["family_name"]}" {nationality} corruption OR scandal OR sanctions')
    
    # Query 4: Family name + "family" (for family-wide investigations)
    if components['family_name']:
        queries.append(f'"{components["family_name"]}" family corruption OR wealth OR investigation')
    
    # Query 5: Name variants
    for variant in variants[:3]:
        if variant != name and len(variant.split()) >= 2:
            queries.append(f'"{variant}" sanctions OR fraud OR corruption')
    
    return queries[:5]  # Limit to 5 queries


def detect_pep_indicators(name: str, nationality: Optional[str] = None, 
                          additional_info: Optional[Dict] = None) -> Dict:
    """
    Detect indicators that someone may be a PEP or related to a PEP
    Returns confidence score and indicators found
    """
    indicators = []
    confidence = 0
    
    # Check for government/political titles in name
    political_titles = [
        'MINISTER', 'PRESIDENT', 'GOVERNOR', 'AMBASSADOR', 'SENATOR',
        'GENERAL', 'COLONEL', 'ADMIRAL', 'CHIEF', 'DIRECTOR', 'SECRETARY',
        'MAYOR', 'COUNCILLOR', 'MP', 'CONGRESSMAN', 'DEPUTY'
    ]
    
    name_upper = name.upper()
    for title in political_titles:
        if title in name_upper:
            indicators.append(f"Political title in name: {title}")
            confidence += 30
    
    # Check for high-risk nationalities (countries with known corruption issues)
    high_pep_risk_countries = [
        'AZERBAIJAN', 'RUSSIA', 'UKRAINE', 'KAZAKHSTAN', 'UZBEKISTAN',
        'TURKMENISTAN', 'BELARUS', 'VENEZUELA', 'NIGERIA', 'ANGOLA',
        'EQUATORIAL GUINEA', 'DEMOCRATIC REPUBLIC OF CONGO', 'LIBYA',
        'SYRIA', 'IRAN', 'NORTH KOREA', 'MYANMAR', 'CAMBODIA'
    ]
    
    if nationality:
        nat_upper = nationality.upper()
        for country in high_pep_risk_countries:
            if country in nat_upper:
                indicators.append(f"High PEP-risk nationality: {country}")
                confidence += 20
                break
    
    # Check additional info for PEP indicators
    if additional_info:
        info_str = str(additional_info).upper()
        
        pep_keywords = [
            'GOVERNMENT', 'MINISTRY', 'PARLIAMENT', 'SENATE', 'CONGRESS',
            'STATE COMPANY', 'STATE OWNED', 'NATIONAL BANK', 'CENTRAL BANK',
            'MILITARY', 'POLICE', 'SECURITY SERVICE', 'INTELLIGENCE'
        ]
        
        for keyword in pep_keywords:
            if keyword in info_str:
                indicators.append(f"PEP keyword in profile: {keyword}")
                confidence += 15
    
    # Check for patronymic patterns (often indicate Eastern European/Central Asian origin)
    # These regions have higher rates of politically connected families
    patronymic_markers = ['OGLU', 'OGLI', 'KIZI', 'QIZI', 'OVICH', 'EVICH', 'OVNA', 'EVNA']
    for marker in patronymic_markers:
        if marker in name.upper():
            indicators.append(f"Patronymic naming pattern suggests potential family PEP connection")
            confidence += 10
            break
    
    return {
        'is_potential_pep': confidence >= 30,
        'confidence': min(confidence, 100),
        'indicators': indicators,
        'recommendation': 'Enhanced due diligence recommended' if confidence >= 30 else 'Standard screening'
    }


def is_arabic_name(name: str) -> bool:
    """Check if name contains Arabic characters"""
    for char in name:
        if '\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F':
            return True
    return False


def transliterate_arabic_to_english(text: str) -> str:
    """
    Transliterate Arabic text to English/Latin characters
    """
    if not text or not is_arabic_name(text):
        return text
    
    # Arabic to English character map
    arabic_map = {
        'ا': 'a', 'أ': 'a', 'إ': 'i', 'آ': 'aa', 'ب': 'b', 'ت': 't', 'ث': 'th',
        'ج': 'j', 'ح': 'h', 'خ': 'kh', 'د': 'd', 'ذ': 'dh', 'ر': 'r', 'ز': 'z',
        'س': 's', 'ش': 'sh', 'ص': 's', 'ض': 'd', 'ط': 't', 'ظ': 'z', 'ع': 'a',
        'غ': 'gh', 'ف': 'f', 'ق': 'q', 'ك': 'k', 'ل': 'l', 'م': 'm', 'ن': 'n',
        'ه': 'h', 'و': 'w', 'ي': 'y', 'ى': 'a', 'ة': 'a', 'ء': "'",
        'ئ': 'e', 'ؤ': 'o',
        # Diacritics
        'َ': 'a', 'ُ': 'u', 'ِ': 'i', 'ّ': '', 'ْ': '',
        'ً': 'an', 'ٌ': 'un', 'ٍ': 'in',
    }
    
    # Common Arabic name mappings
    common_names = {
        'نهاد': 'Nihad', 'عبد': 'Abd', 'الرحيم': 'Al-Raheem', 'المقداد': 'Al-Miqdad',
        'محمد': 'Mohammad', 'أحمد': 'Ahmad', 'علي': 'Ali', 'حسن': 'Hassan',
        'عمر': 'Omar', 'خالد': 'Khaled', 'يوسف': 'Youssef', 'إبراهيم': 'Ibrahim',
    }
    
    result = []
    words = text.split()
    
    for word in words:
        if word in common_names:
            result.append(common_names[word])
        else:
            transliterated = ''
            for char in word:
                transliterated += arabic_map.get(char, char if char.isascii() else '')
            if transliterated:
                result.append(transliterated.capitalize())
    
    return ' '.join(result)


# Test
if __name__ == "__main__":
    test_names = [
        "ANAR ELDAR OGLU MAHMUDOV",
        "MAHMUDOVA LEYLA",
        "نهاد عبد الرحيم المقداد",
        "VLADIMIR VLADIMIROVICH PUTIN",
        "SHEIKH MOHAMMED BIN RASHID AL MAKTOUM"
    ]
    
    for name in test_names:
        print(f"\n{'='*60}")
        print(f"Original: {name}")
        components = extract_name_components(name)
        print(f"Components: {components}")
        variants = generate_name_variants(name)
        print(f"Variants: {variants[:5]}")
        queries = generate_search_queries(name, "Azerbaijan")
        print(f"Search queries: {queries[:3]}")
        pep = detect_pep_indicators(name, "Azerbaijan")
        print(f"PEP indicators: {pep}")
