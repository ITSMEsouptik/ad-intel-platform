"""
Novara Step 2: Brand Identity Extraction
Extracts fonts and colors from CSS with role detection

Updated: Feb 2026 - Filter platform colors, limit to 2-3 fonts
"""

import os
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass
from collections import Counter
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExtractedFont:
    """Font with role and source"""
    name: str
    role: str  # heading, body, accent
    source: str  # css, google
    frequency: int = 0


@dataclass
class ExtractedColor:
    """Color with role"""
    hex: str
    role: str  # primary, secondary, accent, bg, text
    frequency: int = 0
    context: str = ""


class BrandIdentityExtractor:
    """
    Extracts fonts and colors from CSS text.
    Focuses on actual brand colors, not platform/framework colors.
    """
    
    # Common system/fallback fonts to ignore
    SYSTEM_FONTS = {
        'inherit', 'initial', 'sans-serif', 'serif', 'monospace', 'cursive', 'fantasy',
        'system-ui', '-apple-system', 'blinkmacsystemfont', 'segoe ui', 'roboto',
        'helvetica neue', 'helvetica', 'arial', 'noto sans', 'liberation sans',
        'dejavu sans', 'ubuntu', 'cantarell', 'fira sans', 'droid sans',
        'oxygen', 'lucida grande', 'geneva', 'verdana', 'tahoma', 'trebuchet ms',
        'times new roman', 'times', 'georgia', 'palatino', 'book antiqua',
        'courier new', 'courier', 'lucida console', 'monaco', 'andale mono',
        'meiryo', 'メイリオ', 'hiragino kaku gothic pro', 'ヒラギノ角ゴ pro w3',
        'ms pgothic', 'ms gothic', 'microsoft yahei', 'simsun', 'pingfang sc'
    }
    
    # Wix font slug → readable name mapping
    WIX_FONT_MAP = {
        'avenir-lt-w01_35-light': 'Avenir Light',
        'avenir-lt-w01_85-heavy': 'Avenir Heavy',
        'avenir-lt-w01_': 'Avenir',
        'avenir-lt-w02_': 'Avenir',
        'dinneuzeitgroteskltw01-': 'DIN Neuzeit Grotesk',
        'dinneuzeitgroteskltw02-': 'DIN Neuzeit Grotesk',
        'helvetica-w01-roman': 'Helvetica',
        'helvetica-w01-bold': 'Helvetica Bold',
        'helvetica-w01-light': 'Helvetica Light',
        'helvetica-w02-roman': 'Helvetica',
        'proxima-n-w01-reg': 'Proxima Nova',
        'proxima-n-w05-reg': 'Proxima Nova',
        'proxima-n-w01-smbd': 'Proxima Nova Semibold',
        'brandon-grot-w01-light': 'Brandon Grotesque Light',
        'brandon-grot-w01-thin': 'Brandon Grotesque Thin',
        'futura-lt-w01-book': 'Futura Book',
        'futura-lt-w01-light': 'Futura Light',
        'lulo-clean-w01-one-bold': 'Lulo Clean Bold',
        'cormorantgaramond-': 'Cormorant Garamond',
        'playfairdisplay-': 'Playfair Display',
        'raleway-': 'Raleway',
        'montserrat-': 'Montserrat',
        'oswald-': 'Oswald',
        'poppins-': 'Poppins',
        'lato-': 'Lato',
        'open-sans-': 'Open Sans',
        'roboto-': 'Roboto',
        'barlow-': 'Barlow',
    }
    
    # Platform/framework color prefixes to ignore
    PLATFORM_PREFIXES = [
        '--wbu-', '--wix-', '--tw-', '--bs-', '--chakra-', '--mantine-',
        '--mui-', '--ant-', '--radix-', '--shadcn-'
    ]
    
    # Wix-specific colors to filter (their default theme colors)
    WIX_PLATFORM_COLORS = {
        '#116dff', '#0f2ccf', '#2f5dff', '#597dff', '#acbeff', '#d5dfff',
        '#eaefff', '#f5f7ff', '#7fccf7', '#3899ec', '#5c7cfa', '#4c6ef5',
        '#ff4040',  # Wix error red
        '#09f', '#0099ff', '#4eb7f5', '#bcebff', '#e7f5ff',  # Wix blue variants
        '#e8e8e8', '#d6d6d6', '#c4c4c4',  # Wix grays
        '#00a98f', '#60bc57', '#ee5951', '#fb7d33', '#f2c94c',  # Wix palette
        '#dfe5eb', '#c1c1c1', '#84939e', '#577083', '#3b4057',  # Wix grays v2
    }
    
    # Squarespace/Shopify/common platform default colors
    PLATFORM_DEFAULT_COLORS = {
        '#1890ff', '#40a9ff', '#096dd9',  # Ant Design blues
        '#1677ff', '#4096ff',  # Ant Design v5
        '#0070f3', '#0761d1',  # Vercel/Next.js
        '#7c3aed', '#8b5cf6',  # Tailwind violet defaults
        '#bada55',  # Developer test color ("badass")
        '#deadbeef', '#c0ffee', '#facade',  # Common dev test colors
        '#1a73e8', '#4285f4', '#34a853', '#fbbc05', '#ea4335',  # Google brand (from tracking scripts)
        '#5f6368', '#3c4043', '#202124',  # Google grays
    }
    
    # Generic/utility colors to ignore
    IGNORE_COLORS = {
        '#ffffff', '#fff', '#000000', '#000', '#f5f5f5', '#fafafa',
        '#e5e5e5', '#d4d4d4', '#a3a3a3', '#737373', '#525252', '#404040',
        '#262626', '#171717', '#0a0a0a', '#f0f0f0', '#e0e0e0', '#cccccc',
        '#999999', '#666666', '#333333', '#111111', 'transparent', 'inherit', 
        'initial', 'currentcolor'
    }
    
    # Platform CSS variable patterns (colors not from the brand)
    PLATFORM_COLOR_PATTERNS = [
        r'wbu-color', r'wix-color', r'--tw-', r'--bs-', r'blue-\d+', 
        r'gray-\d+', r'red-\d+', r'green-\d+', r'yellow-\d+', r'orange-\d+',
        r'purple-\d+', r'pink-\d+', r'ai-\d+', r'color-\d+'
    ]
    
    def extract_fonts(self, css_texts: List[str], html_text: str = "") -> List[ExtractedFont]:
        """
        Extract fonts from CSS, returning only 2-3 main brand fonts.
        Cleans Wix/platform font slugs to readable names.
        """
        all_css = '\n'.join(css_texts)
        font_counts = Counter()
        font_contexts = {}
        google_fonts = set()
        
        # Find Google Fonts from @import or link
        google_pattern = r'fonts\.googleapis\.com/css[^"\']*family=([^"\'&]+)'
        for match in re.finditer(google_pattern, all_css + html_text, re.IGNORECASE):
            font_family = match.group(1).replace('+', ' ').split(':')[0]
            google_fonts.add(font_family.lower().strip())
        
        # Extract font-family declarations only
        font_pattern = r'font-family:\s*["\']?([^"\';\}\n]+)["\']?'
        
        matches = re.finditer(font_pattern, all_css, re.IGNORECASE)
        for match in matches:
            font_value = match.group(1).strip()
            fonts = [f.strip().strip('"\'') for f in font_value.split(',')]
            
            for font in fonts:
                font_lower = font.lower()
                
                # Skip system fonts
                if font_lower in self.SYSTEM_FONTS:
                    continue
                
                # Resolve CSS variables: var(--font-family-montserrat) → Montserrat
                if font_lower.startswith('var('):
                    var_match = re.search(r'var\(--(?:font[-_]?(?:family)?[-_]?)(.+?)\)', font, re.IGNORECASE)
                    if var_match:
                        var_name = var_match.group(1).strip().rstrip(')')
                        resolved = self._clean_font_name(var_name)
                        if resolved and resolved.lower() not in self.SYSTEM_FONTS:
                            font_counts[resolved] = font_counts.get(resolved, 0) + 1
                    continue
                
                # Skip if too short or CSS value
                if len(font) < 3 or font.startswith(('calc(', '--')):
                    continue
                
                # Skip if contains sizes/weights
                if any(x in font_lower for x in ['px', 'em', 'rem', 'normal', 'bold', 'italic', '/']):
                    continue
                
                # Clean the font name (resolve Wix slugs etc.)
                font_clean = self._clean_font_name(font.strip('"\''))
                if font_clean:
                    font_counts[font_clean] += 1
                    
                    # Capture context
                    start = max(0, match.start() - 100)
                    end = min(len(all_css), match.end() + 50)
                    context = all_css[start:end].lower()
                    
                    if font_clean not in font_contexts:
                        font_contexts[font_clean] = []
                    font_contexts[font_clean].append(context)
        
        # Build result - ONLY TOP 2-3 FONTS
        result = []
        sorted_fonts = font_counts.most_common(5)
        
        for i, (font_name, count) in enumerate(sorted_fonts):
            if i >= 3:  # Max 3 fonts
                break
                
            contexts = font_contexts.get(font_name, [])
            contexts_joined = ' '.join(contexts)
            
            # Determine role
            if i == 0:
                role = 'heading'  # Most common = primary/heading
            elif i == 1:
                role = 'body'  # Second = body
            else:
                role = 'accent'  # Third = accent (if present)
            
            # Override if context suggests otherwise
            if any(x in contexts_joined for x in ['h1', 'h2', 'h3', 'heading', 'title', 'hero']):
                role = 'heading'
            elif any(x in contexts_joined for x in ['body', 'paragraph', 'content', 'p {']):
                role = 'body'
            
            source = 'google' if font_name.lower() in google_fonts else 'css'
            
            result.append(ExtractedFont(
                name=font_name,
                role=role,
                source=source,
                frequency=count
            ))
        
        return result
    
    def extract_colors(self, css_texts: List[str], html_text: str = "") -> List[ExtractedColor]:
        """
        Extract brand colors from CSS, filtering out platform colors.
        Returns 5-8 actual brand colors.
        
        Strategy:
        1. Extract from CSS custom properties (Wix theme colors, etc.) — these are most reliable
        2. Extract from standard CSS properties (color, background, border)
        3. Filter platform/generic colors, deduplicate similar shades
        """
        all_css = '\n'.join(css_texts)
        color_data = {}
        
        # Skip colors from platform CSS variables
        def is_platform_color(context: str) -> bool:
            context_lower = context.lower()
            for pattern in self.PLATFORM_COLOR_PATTERNS:
                if re.search(pattern, context_lower):
                    return True
            for prefix in self.PLATFORM_PREFIXES:
                if prefix in context_lower:
                    return True
            return False
        
        def is_filtered_color(hex_color: str) -> bool:
            """Check if a color should be filtered out"""
            if hex_color in self.IGNORE_COLORS:
                return True
            if hex_color in self.WIX_PLATFORM_COLORS:
                return True
            if hex_color in self.PLATFORM_DEFAULT_COLORS:
                return True
            return False
        
        # PHASE 1: Extract from CSS custom properties (theme colors — high value)
        # Matches patterns like: --color_5: #f9ad4d; or --primary-color: #ff6600;
        custom_prop_pattern = r'--([a-zA-Z0-9_-]+)\s*:\s*#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b'
        for match in re.finditer(custom_prop_pattern, all_css, re.IGNORECASE):
            prop_name = match.group(1).lower()
            hex_color = match.group(2).lower()
            if len(hex_color) == 3:
                hex_color = ''.join([c*2 for c in hex_color])
            full_hex = f'#{hex_color}'
            
            if is_filtered_color(full_hex):
                continue
            
            # Skip platform-prefixed custom properties
            if any(prop_name.startswith(p.lstrip('-')) for p in self.PLATFORM_PREFIXES):
                continue
            
            # Skip Wix internal vars (wbu-*, wix-*)
            if prop_name.startswith(('wbu-', 'wix-', 'tw-', 'bs-', 'chakra-', 'mantine-', 'mui-')):
                continue
            
            if full_hex not in color_data:
                color_data[full_hex] = {'count': 0, 'roles': set(), 'contexts': []}
            
            # Theme custom properties get a significant boost
            color_data[full_hex]['count'] += 8
            
            # Try to detect role from property name
            if any(x in prop_name for x in ['primary', 'brand', 'main', 'accent']):
                color_data[full_hex]['roles'].add('primary')
            elif any(x in prop_name for x in ['secondary', 'alt']):
                color_data[full_hex]['roles'].add('secondary')
            elif any(x in prop_name for x in ['bg', 'background', 'surface']):
                color_data[full_hex]['roles'].add('bg')
            else:
                color_data[full_hex]['roles'].add('accent')
            color_data[full_hex]['contexts'].append(f'custom-prop: {prop_name}')
        
        # PHASE 2: Find colors in CSS properties (color, background, border)
        color_patterns = [
            (r'(?<![-\w])color:\s*#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b', 'text'),
            (r'background(?:-color)?:\s*#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b', 'bg'),
            (r'border(?:-color)?:\s*#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b', 'accent'),
        ]
        
        for pattern, default_role in color_patterns:
            for match in re.finditer(pattern, all_css, re.IGNORECASE):
                hex_color = match.group(1).lower()
                
                # Expand 3-char hex to 6-char
                if len(hex_color) == 3:
                    hex_color = ''.join([c*2 for c in hex_color])
                
                full_hex = f'#{hex_color}'
                
                if is_filtered_color(full_hex):
                    continue
                
                # Get context and skip platform colors
                start = max(0, match.start() - 80)
                end = min(len(all_css), match.end() + 20)
                context = all_css[start:end]
                
                if is_platform_color(context):
                    continue
                
                if full_hex not in color_data:
                    color_data[full_hex] = {
                        'count': 0,
                        'roles': set(),
                        'contexts': []
                    }
                
                color_data[full_hex]['count'] += 1
                color_data[full_hex]['roles'].add(default_role)
                color_data[full_hex]['contexts'].append(context)
        
        # PHASE 3: Extract from inline styles in HTML
        inline_pattern = r'style=["\'][^"\']*(?:color|background)[^:]*:\s*#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})'
        for match in re.finditer(inline_pattern, html_text, re.IGNORECASE):
            hex_color = match.group(1).lower()
            if len(hex_color) == 3:
                hex_color = ''.join([c*2 for c in hex_color])
            full_hex = f'#{hex_color}'
            
            if is_filtered_color(full_hex):
                continue
            
            # Skip platform colors by context
            start = max(0, match.start() - 80)
            end = min(len(html_text), match.end() + 20)
            context = html_text[start:end]
            if is_platform_color(context):
                continue
            
            if full_hex not in color_data:
                color_data[full_hex] = {'count': 0, 'roles': set(), 'contexts': []}
            
            # Inline styles are usually more important
            color_data[full_hex]['count'] += 5  # Boost weight
            color_data[full_hex]['roles'].add('accent')
        
        # Sort by count and deduplicate similar colors
        sorted_colors = sorted(color_data.items(), key=lambda x: x[1]['count'], reverse=True)
        
        deduplicated = []
        for hex_color, data in sorted_colors:
            is_similar = False
            for existing_hex, _ in deduplicated:
                if self._color_distance(hex_color, existing_hex) < 40:
                    is_similar = True
                    break
            if not is_similar:
                deduplicated.append((hex_color, data))
        
        # Build result - limit to 5-6 colors
        result = []
        role_assigned = {'primary': False, 'secondary': False, 'accent': False}
        
        for hex_color, data in deduplicated[:8]:
            roles = data['roles']
            
            # Assign roles
            if not role_assigned['primary']:
                role = 'primary'
                role_assigned['primary'] = True
            elif not role_assigned['secondary']:
                role = 'secondary'
                role_assigned['secondary'] = True
            elif 'accent' in roles or not role_assigned['accent']:
                role = 'accent'
                role_assigned['accent'] = True
            elif 'bg' in roles:
                role = 'bg'
            elif 'text' in roles:
                role = 'text'
            else:
                role = 'accent'
            
            result.append(ExtractedColor(
                hex=hex_color,
                role=role,
                frequency=data['count'],
                context=data['contexts'][0][:80] if data['contexts'] else ''
            ))
        
        return result[:6]  # Max 6 colors
    
    def _color_distance(self, color1: str, color2: str) -> float:
        """Calculate color distance between two hex colors"""
        try:
            h1 = color1.lstrip('#')
            h2 = color2.lstrip('#')
            
            r1, g1, b1 = int(h1[0:2], 16), int(h1[2:4], 16), int(h1[4:6], 16)
            r2, g2, b2 = int(h2[0:2], 16), int(h2[2:4], 16), int(h2[4:6], 16)
            
            return ((r1-r2)**2 + (g1-g2)**2 + (b1-b2)**2) ** 0.5
        except Exception:
            return 1000
    
    def _get_brightness(self, hex_color: str) -> int:
        """Get brightness of a color (0-255)"""
        hex_val = hex_color.lstrip('#')
        if len(hex_val) == 3:
            hex_val = ''.join([c*2 for c in hex_val])
        r = int(hex_val[0:2], 16)
        g = int(hex_val[2:4], 16)
        b = int(hex_val[4:6], 16)
        return int((r * 299 + g * 587 + b * 114) / 1000)

    def _clean_font_name(self, raw_name: str) -> str:
        """Clean platform font slugs to readable font names.
        
        Examples:
            'avenir-lt-w01_35-light1475496' → 'Avenir Light'
            'dinneuzeitgroteskltw01-_812426' → 'DIN Neuzeit Grotesk'
            'Poppins' → 'Poppins' (already clean)
        """
        name_lower = raw_name.lower()
        
        # Check WIX_FONT_MAP (prefix matching)
        for slug_prefix, readable in self.WIX_FONT_MAP.items():
            if name_lower.startswith(slug_prefix):
                return readable
        
        # Strip trailing Wix numeric IDs (e.g., "fontname1475496")
        cleaned = re.sub(r'\d{5,}$', '', raw_name).rstrip('_').rstrip('-')
        
        # If it looks like a slug (has hyphens/underscores + digits), try to humanize
        if re.search(r'[-_]w\d{2}', cleaned, re.IGNORECASE):
            # Strip Wix weight identifiers like "-w01", "_w02"
            cleaned = re.sub(r'[-_]w\d{2,3}[-_]?', ' ', cleaned)
            # Strip Wix style suffixes like "_35-light", "_85-heavy"
            cleaned = re.sub(r'[-_]\d{2,3}[-_]?', ' ', cleaned)
            # Replace hyphens/underscores with spaces
            cleaned = re.sub(r'[-_]+', ' ', cleaned)
            # Clean up multiple spaces
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            # Title-case
            if cleaned:
                cleaned = cleaned.title()
        else:
            # Already clean name — just ensure proper title case
            cleaned = re.sub(r'[-_]+', ' ', cleaned).strip()
            if cleaned and cleaned == cleaned.lower():
                cleaned = cleaned.title()
        
        return cleaned if len(cleaned) >= 2 else raw_name



def extract_brand_identity(css_texts: List[str], html_text: str = "", screenshot_base64: str = "", html_colors: List[str] = None) -> Dict:
    """
    Extract brand identity (fonts, colors) from HTML + CSS.
    Uses HTML-wide color extraction with clustering for accurate brand palette.
    Returns max 3 fonts and max 6 colors.
    """
    extractor = BrandIdentityExtractor()
    fonts = extractor.extract_fonts(css_texts, html_text)
    colors = _extract_brand_palette(css_texts, html_text, html_colors=html_colors)
    
    logger.info(f"[BRAND_IDENTITY] Extracted {len(fonts)} fonts, {len(colors)} colors")
    
    return {
        'fonts': [
            {'name': f.name, 'role': f.role, 'source': f.source}
            for f in fonts
        ],
        'colors': colors
    }


def _extract_brand_palette(css_texts: List[str], html_text: str, html_colors: List[str] = None) -> list:
    """
    Extract the brand's actual color palette from HTML + CSS.
    
    Strategy:
    1. Extract colors ACTIVELY USED in HTML (inline styles, SVG fills) — high confidence
    2. Extract from CSS properties (color:, background:) — medium confidence
    3. Colors only defined in CSS variables get low weight (often platform/auto-generated)
    4. Filter known platform colors
    5. Cluster by hue (accents) and brightness (neutrals)
    6. Build palette: accent colors first, then key neutrals
    """
    all_css = '\n'.join(css_texts)
    color_scores = Counter()  # hex6 -> weighted score
    
    PLATFORM_COLORS = {
        '116dff', '0f2ccf', '2f5dff', '597dff', 'acbeff', 'd5dfff',
        'eaefff', 'f5f7ff', '7fccf7', '3899ec', '5c7cfa', '4c6ef5',
        'ff4040', '0099ff', '4eb7f5', 'bcebff', 'e7f5ff',
        'dfe5eb', 'c1c1c1', '84939e', '577083', '3b4057',
        '00a98f', '60bc57', 'ee5951', 'fb7d33', 'f2c94c',
        '1890ff', '40a9ff', '096dd9', '1677ff', '4096ff',
        '0070f3', '0761d1', '7c3aed', '8b5cf6',
        'bada55', 'deadbe', 'c0ffee', 'facade',  # Dev test colors
        '1a73e8', '4285f4', '34a853', 'fbbc05', 'ea4335',  # Google brand colors (from tracking scripts)
        '5f6368', '3c4043', '202124',  # Google gray palette
    }
    
    def normalize_hex(h):
        h = h.lower()
        if len(h) == 3:
            return h[0]*2 + h[1]*2 + h[2]*2
        return h
    
    def add_color(hex6, weight):
        hex6 = normalize_hex(hex6)
        if hex6 in PLATFORM_COLORS:
            return
        color_scores[hex6] += weight
    
    # PHASE 0: HIGH WEIGHT — Pre-extracted colors from full HTML (before truncation)
    if html_colors:
        for hex6 in html_colors:
            add_color(hex6, 8)
    
    # PHASE 1: HIGH WEIGHT — Colors actively used in HTML elements
    # Inline styles (style="color:#xxx" or style="background:#xxx")
    if html_text:
        for m in re.finditer(r'style="[^"]*?(?:color|background)[^"]*?#([0-9a-fA-F]{3,6})\b', html_text, re.IGNORECASE):
            add_color(m.group(1), 10)
        
        # SVG fill/stroke attributes
        for m in re.finditer(r'(?:fill|stroke)="#([0-9a-fA-F]{3,6})"', html_text, re.IGNORECASE):
            add_color(m.group(1), 5)
        
        # data-color and similar attributes
        for m in re.finditer(r'data-color="([^"]*)"', html_text, re.IGNORECASE):
            for cm in re.finditer(r'#([0-9a-fA-F]{3,6})\b', m.group(1)):
                add_color(cm.group(1), 8)
    
    # PHASE 2: MEDIUM WEIGHT — Colors used in CSS rules (not variable definitions)
    if all_css:
        # Match color:, background:, background-color:, border-color: followed by #hex
        for m in re.finditer(r'(?:^|[{;])\s*(?:color|background(?:-color)?|border(?:-color)?)\s*:\s*#([0-9a-fA-F]{3,6})\b', all_css, re.IGNORECASE):
            add_color(m.group(1), 3)
    
    # PHASE 3: LOW WEIGHT — Colors defined in CSS variables (often auto-generated)
    if all_css:
        for m in re.finditer(r'--[a-zA-Z0-9_-]+\s*:\s*#([0-9a-fA-F]{3,6})\b', all_css, re.IGNORECASE):
            add_color(m.group(1), 1)
    
    if not color_scores:
        return []
    
    # PHASE 4: Separate accents and neutrals
    import colorsys
    
    accents = {}
    neutrals = {}
    
    for hex6, score in color_scores.items():
        r, g, b = int(hex6[0:2], 16), int(hex6[2:4], 16), int(hex6[4:6], 16)
        max_c, min_c = max(r, g, b), min(r, g, b)
        saturation = (max_c - min_c) / max(max_c, 1)
        
        if saturation > 0.15:
            accents[hex6] = score
        else:
            neutrals[hex6] = score
    
    # PHASE 5: Cluster by hue (accents) and brightness (neutrals)
    def get_hue(hex6):
        r, g, b = int(hex6[0:2], 16) / 255, int(hex6[2:4], 16) / 255, int(hex6[4:6], 16) / 255
        h, _, _ = colorsys.rgb_to_hsv(r, g, b)
        return h * 360
    
    # Cluster accents by hue
    hue_clusters = []  # [representative_hex, total_score]
    for hex6, score in sorted(accents.items(), key=lambda x: x[1], reverse=True):
        hue = get_hue(hex6)
        merged = False
        for cluster in hue_clusters:
            cluster_hue = get_hue(cluster[0])
            hue_diff = min(abs(hue - cluster_hue), 360 - abs(hue - cluster_hue))
            if hue_diff < 20:
                cluster[1] += score
                if score > accents.get(cluster[0], 0):
                    cluster[0] = hex6  # Higher-scoring color becomes representative
                merged = True
                break
        if not merged:
            hue_clusters.append([hex6, score])
    
    hue_clusters.sort(key=lambda x: x[1], reverse=True)
    
    # Cluster neutrals by brightness
    neutral_clusters = []
    for hex6, score in sorted(neutrals.items(), key=lambda x: x[1], reverse=True):
        brightness = sum(int(hex6[i:i+2], 16) for i in (0, 2, 4)) / 3
        merged = False
        for cluster in neutral_clusters:
            cb = sum(int(cluster[0][i:i+2], 16) for i in (0, 2, 4)) / 3
            if abs(brightness - cb) < 25:
                cluster[1] += score
                if score > neutrals.get(cluster[0], 0):
                    cluster[0] = hex6
                merged = True
                break
        if not merged:
            neutral_clusters.append([hex6, score])
    
    neutral_clusters.sort(key=lambda x: x[1], reverse=True)
    
    # PHASE 6: Build palette
    palette = []
    
    # Accents first (the brand's distinctive colors)
    # Only include accent clusters where the representative scored >= 3
    # (appeared in actual HTML/CSS usage, not just variable definitions)
    accent_roles = ['primary', 'secondary', 'accent']
    accent_count = 0
    for rep_hex, _score in hue_clusters:
        if accent_count >= 3:
            break
        # The representative's individual score must be meaningful
        individual_score = accents.get(rep_hex, 0)
        if individual_score < 3:
            continue
        palette.append({'hex': f'#{rep_hex}', 'role': accent_roles[min(accent_count, 2)]})
        accent_count += 1
    
    # Then key neutrals: lightest (bg) + darkest (text) first, then mid-tones
    if neutral_clusters:
        by_brightness = sorted(neutral_clusters, key=lambda c: sum(int(c[0][i:i+2], 16) for i in (0, 2, 4)), reverse=True)
        
        # Add lightest (bg)
        lightest = by_brightness[0]
        if len(palette) < 5:
            palette.append({'hex': f'#{lightest[0]}', 'role': 'bg'})
        
        # Add darkest (text)
        darkest = by_brightness[-1]
        if len(palette) < 5 and darkest != lightest:
            palette.append({'hex': f'#{darkest[0]}', 'role': 'text'})
        
        # Add a mid-tone neutral that's distinct from both extremes
        if len(by_brightness) > 2 and len(palette) < 5:
            for nc_hex, _score in by_brightness[1:-1]:
                if len(palette) >= 5:
                    break
                bri = sum(int(nc_hex[i:i+2], 16) for i in (0, 2, 4)) / 3
                # Must be at least 20 brightness units from all existing neutrals
                existing_bris = [sum(int(c['hex'][i:i+2], 16) for i in (1, 3, 5)) / 3 for c in palette if c['role'] in ('bg', 'text')]
                if all(abs(bri - eb) > 20 for eb in existing_bris):
                    palette.append({'hex': f'#{nc_hex}', 'role': 'bg'})
                    break
    
    logger.info(f"[BRAND_IDENTITY] Palette: {[c['hex'] for c in palette]} ({len(hue_clusters)} accent clusters, {len(neutral_clusters)} neutral clusters)")
    return palette


async def extract_colors_via_vision(screenshot_base64: str, api_key: str, website_url: str = "", jina_content: str = "") -> list:
    """
    Use vision LLM to identify brand colors from a website screenshot.
    If the screenshot is too bland (SPA loading state), falls back to
    asking the LLM using website URL + content context.
    Returns list of {'hex': '#...', 'role': '...'} dicts.
    """
    import base64
    
    if not screenshot_base64:
        return await _colors_from_context(api_key, website_url, jina_content) if website_url else []
    
    b64_data = screenshot_base64.split(',')[1] if ',' in screenshot_base64 else screenshot_base64
    
    # Check if screenshot has enough visual content
    if not _screenshot_has_color(b64_data):
        logger.info("[BRAND_COLORS_VISION] Screenshot too bland (SPA loading state), using context-based approach")
        return await _colors_from_context(api_key, website_url, jina_content)
    
    vision_prompt = """Look at this website screenshot. Identify the 3-5 main brand colors used in the design.

Focus on:
- Primary brand color (dominant accent color used for buttons, headings, or hero sections)
- Secondary brand color (supporting accent)
- Any other distinctive accent colors

DO NOT include pure white, pure black, or generic grays.

Return ONLY a JSON array:
[{"hex": "#5a48f5", "role": "primary"}, {"hex": "#d49341", "role": "secondary"}]"""

    # Try Gemini first
    if api_key:
        result = await _vision_via_gemini(b64_data, api_key, vision_prompt)
        if result:
            return result
    
    # If Gemini is unavailable or fails, we currently do not use any additional
    # hosted LLM integrations for vision. In that case, fall back to an empty
    # color list rather than requiring emergentintegrations.
    logger.warning("[BRAND_COLORS_VISION] No valid vision LLM available, returning empty color list")
    return []


def _screenshot_has_color(b64_data: str) -> bool:
    """Check if screenshot has enough colorful pixels to be useful for vision analysis."""
    try:
        import base64
        from io import BytesIO
        from PIL import Image
        
        img = Image.open(BytesIO(base64.b64decode(b64_data)))
        img = img.resize((80, 60), Image.LANCZOS).convert('RGB')
        pixels = list(img.getdata())
        
        colorful = sum(1 for r, g, b in pixels if max(r, g, b) - min(r, g, b) > 50)
        pct = colorful * 100 // len(pixels)
        logger.info(f"[BRAND_COLORS_VISION] Screenshot colorfulness: {pct}%")
        return pct >= 3  # At least 3% colorful pixels
    except Exception:
        return True  # If check fails, assume screenshot is usable


async def _colors_from_context(api_key: str, website_url: str, jina_content: str = "") -> list:
    """
    Identify brand colors using website context (no image needed).

    The previous implementation used Emergent's proprietary LLM client
    (emergentintegrations.llm.chat), which is not available outside
    Emergent's hosting environment. For the GCP deployment we disable
    that integration and simply return an empty list if vision is not
    available, relying on CSS-based color extraction instead.
    """
    logger.info("[BRAND_COLORS_VISION] Context-based color extraction via Emergent LLM is disabled in this deployment")
    return []


async def _vision_via_gemini(b64_data: str, api_key: str, prompt: str) -> list:
    """Try Gemini vision for color extraction."""
    import base64
    try:
        from google import genai
        from google.genai import types
        
        image_bytes = base64.b64decode(b64_data)
        client = genai.Client(api_key=api_key)
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                prompt
            ],
            config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=300)
        )
        
        return _parse_color_response(response.text)
    except Exception as e:
        logger.warning(f"[BRAND_COLORS_VISION] Gemini vision failed: {e}")
        return []


async def _vision_via_emergent(b64_data: str, api_key: str, prompt: str) -> list:
    """
    Placeholder retained for compatibility with tests.

    In the original Emergent-hosted environment this used
    emergentintegrations.llm.chat to call OpenAI vision via Emergent.
    That package is not available in the GCP deployment, so this
    function now logs and returns an empty list instead of importing
    the proprietary client.
    """
    logger.info("[BRAND_COLORS_VISION] _vision_via_emergent is disabled (no emergentintegrations installed)")
    return []


def _parse_color_response(text: str) -> list:
    """Parse color JSON from LLM response text."""
    import json
    import re
    
    content = text.strip()
    if content.startswith('```'):
        lines = content.split('\n')
        lines = [line for line in lines if not line.startswith('```')]
        content = '\n'.join(lines).strip()
    
    json_match = re.search(r'\[.*\]', content, re.DOTALL)
    if json_match:
        colors = json.loads(json_match.group())
        valid = []
        for c in colors:
            h = c.get('hex', '').strip().lower()
            if h and h.startswith('#') and len(h) == 7:
                valid.append({'hex': h, 'role': c.get('role', 'accent')})
        logger.info(f"[BRAND_COLORS_VISION] Identified {len(valid)} colors: {[c['hex'] for c in valid]}")
        return valid
    
    logger.warning(f"[BRAND_COLORS_VISION] Could not parse JSON from: {content[:200]}")
    return []


def _extract_colors_from_screenshot(screenshot_base64: str) -> List[ExtractedColor]:
    """
    Extract dominant brand colors from a screenshot image.
    Uses a saturation-aware approach to find accent/brand colors
    even when they appear in small areas (buttons, accents).
    """
    try:
        import base64
        from io import BytesIO
        from PIL import Image
        from collections import Counter
        import colorsys
        
        # Decode base64 screenshot
        if ',' in screenshot_base64:
            screenshot_base64 = screenshot_base64.split(',')[1]
        
        img_data = base64.b64decode(screenshot_base64)
        img = Image.open(BytesIO(img_data))
        
        # Resize for faster processing
        img = img.resize((300, 200), Image.LANCZOS)
        img = img.convert('RGB')
        
        pixels = list(img.getdata())
        
        # Separate into two buckets: saturated (brand/accent) and neutral (bg/text)
        saturated_colors = Counter()
        neutral_colors = Counter()
        
        for r, g, b in pixels:
            # Quantize (round to nearest 8 for finer granularity)
            rq, gq, bq = (r // 8) * 8, (g // 8) * 8, (b // 8) * 8
            
            brightness = (rq * 299 + gq * 587 + bq * 114) / 1000
            max_c = max(rq, gq, bq)
            min_c = min(rq, gq, bq)
            saturation = (max_c - min_c) / max(max_c, 1)
            
            # Skip pure white/black
            if brightness > 245 or brightness < 10:
                continue
            
            if saturation > 0.2:
                saturated_colors[(rq, gq, bq)] += 1
            elif 30 < brightness < 200:
                neutral_colors[(rq, gq, bq)] += 1
        
        brand_colors = []
        seen_hexes = set()
        
        # Prioritize saturated (colorful) colors — these are likely brand accents
        for (r, g, b), count in saturated_colors.most_common(20):
            hex_color = f'#{r:02x}{g:02x}{b:02x}'
            
            # Check distance from already-selected colors
            is_similar = False
            for existing in seen_hexes:
                er, eg, eb = int(existing[1:3], 16), int(existing[3:5], 16), int(existing[5:7], 16)
                dist = ((r-er)**2 + (g-eg)**2 + (b-eb)**2) ** 0.5
                if dist < 50:
                    is_similar = True
                    break
            
            if not is_similar:
                role = 'primary' if not brand_colors else ('secondary' if len(brand_colors) == 1 else 'accent')
                brand_colors.append(ExtractedColor(
                    hex=hex_color, role=role, frequency=count, context='screenshot'
                ))
                seen_hexes.add(hex_color)
            
            if len(brand_colors) >= 4:
                break
        
        # Add 1-2 dominant neutral colors (likely bg or text tones)
        for (r, g, b), count in neutral_colors.most_common(10):
            if len(brand_colors) >= 5:
                break
            hex_color = f'#{r:02x}{g:02x}{b:02x}'
            is_similar = any(
                ((r - int(eh[1:3], 16))**2 + (g - int(eh[3:5], 16))**2 + (b - int(eh[5:7], 16))**2) ** 0.5 < 50
                for eh in seen_hexes
            )
            if not is_similar:
                brand_colors.append(ExtractedColor(
                    hex=hex_color, role='bg' if count > 200 else 'text',
                    frequency=count, context='screenshot'
                ))
                seen_hexes.add(hex_color)
        
        logger.info(f"[BRAND_IDENTITY] Screenshot extraction found {len(brand_colors)} colors")
        return brand_colors
        
    except Exception as e:
        logger.warning(f"[BRAND_IDENTITY] Screenshot color extraction failed: {e}")
        return []
