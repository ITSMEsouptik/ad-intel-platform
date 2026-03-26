"""
Novara Step 2: Confidence Scoring
Computes confidence score and determines if user input is needed
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class ConfidenceResult:
    score: int  # 0-100
    missing_fields: List[str]
    needs_user_input: bool
    questions_to_ask: List[Dict]  # [{type, question, options?, placeholder?}]


class ConfidenceScorer:
    """
    Scoring weights (total 100):
    - Offer clarity: 35 pts
    - CTA clarity: 25 pts
    - Proof presence: 20 pts
    - Brand constraints: 20 pts
    
    Threshold: score < 60 triggers user input
    """
    
    THRESHOLD = 60
    
    def score(self, pack: Dict) -> ConfidenceResult:
        """Calculate confidence score and determine required questions"""
        score = 0
        missing_fields = []
        
        offer = pack.get('offer', {})
        proof = pack.get('proof', {})
        brand = pack.get('brand_identity', {})
        conversion = pack.get('conversion', {})
        
        # === Offer clarity (0-35) ===
        offer_score = 0
        
        # primary_offer_summary found: +20
        if offer.get('primary_offer_summary') and len(offer['primary_offer_summary']) > 20:
            offer_score += 20
        else:
            missing_fields.append('primary_offer_summary')
        
        # 3+ key_benefits: +10
        benefits = offer.get('key_benefits', [])
        if len(benefits) >= 3:
            offer_score += 10
        elif len(benefits) >= 1:
            offer_score += 5
        
        # 2+ differentiators: +5
        differentiators = offer.get('differentiators', [])
        if len(differentiators) >= 2:
            offer_score += 5
        elif len(differentiators) >= 1:
            offer_score += 2
        
        score += offer_score
        
        # === CTA clarity (0-25) ===
        cta_score = 0
        
        ctas = conversion.get('detected_primary_ctas', [])
        primary_action = conversion.get('primary_action', 'unknown')
        
        # 3+ detected CTAs: +15
        if len(ctas) >= 3:
            cta_score += 15
        elif len(ctas) >= 1:
            cta_score += 8
        else:
            missing_fields.append('detected_ctas')
        
        # primary action identified (not unknown): +10
        if primary_action != 'unknown':
            cta_score += 10
        else:
            missing_fields.append('primary_action')
        
        score += cta_score
        
        # === Proof presence (0-20) ===
        proof_score = 0
        
        # 1+ testimonial: +10
        testimonials = proof.get('testimonials', [])
        if len(testimonials) >= 1:
            proof_score += 10
        else:
            missing_fields.append('testimonials')
        
        # 1+ trust signal: +10
        trust_signals = proof.get('trust_signals', [])
        if len(trust_signals) >= 1:
            proof_score += 10
        else:
            missing_fields.append('trust_signals')
        
        score += proof_score
        
        # === Brand constraints (0-20) ===
        brand_score = 0
        
        visual = brand.get('visual', {})
        
        # logo found: +10
        if visual.get('logo_asset_url'):
            brand_score += 10
        
        # 3+ colors OR fonts found: +10
        colors = visual.get('primary_colors_hex', [])
        fonts = visual.get('fonts', [])
        if len(colors) >= 3 or len(fonts) >= 1:
            brand_score += 10
        elif len(colors) >= 1:
            brand_score += 5
        
        score += brand_score
        
        # === Determine if user input needed ===
        needs_user_input = score < self.THRESHOLD
        
        # === Determine which questions to ask (max 2) ===
        questions = []
        
        if needs_user_input:
            # Priority: Q1 (offer) → Q2A (action) → Q2B (trust)
            
            # Q1: Offer summary missing
            if 'primary_offer_summary' in missing_fields:
                questions.append({
                    'id': 'q1_offer',
                    'type': 'text',
                    'question': 'What do you sell? (one sentence)',
                    'placeholder': 'e.g., On-demand hair & makeup at home in Dubai.',
                    'max_length': 120,
                    'field': 'primary_offer_summary'
                })
            
            # Q2A: Primary action unclear
            if 'primary_action' in missing_fields and len(questions) < 2:
                questions.append({
                    'id': 'q2a_action',
                    'type': 'pills',
                    'question': "What's the ONE action we should optimize for?",
                    'helper': 'This is the action you want people to take right after seeing the ad.',
                    'options': [
                        {'value': 'book_appointment', 'label': 'Book'},
                        {'value': 'get_quote', 'label': 'Get a quote'},
                        {'value': 'buy_now', 'label': 'Buy'},
                        {'value': 'call', 'label': 'Call'},
                        {'value': 'whatsapp', 'label': 'WhatsApp'},
                        {'value': 'dm', 'label': 'DM'},
                        {'value': 'other', 'label': 'Other'}
                    ],
                    'field': 'primary_action'
                })
            
            # Q2B: Trust signal missing (only if Q2A not asked)
            if 'trust_signals' in missing_fields and 'primary_action' not in missing_fields and len(questions) < 2:
                questions.append({
                    'id': 'q2b_trust',
                    'type': 'pills',
                    'question': "What's your strongest trust signal?",
                    'helper': "This is the #1 reason someone should trust you.",
                    'options': [
                        {'value': 'reviews_rating', 'label': 'Reviews / rating'},
                        {'value': 'testimonials', 'label': 'Testimonials'},
                        {'value': 'before_after', 'label': 'Before-after results'},
                        {'value': 'certified', 'label': 'Certified / experts'},
                        {'value': 'known_clients', 'label': 'Known clients / partnerships'},
                        {'value': 'experience', 'label': 'Years of experience'},
                        {'value': 'other', 'label': 'Other'}
                    ],
                    'field': 'trust_signal'
                })
        
        # Limit to max 2 questions
        questions = questions[:2]
        
        return ConfidenceResult(
            score=score,
            missing_fields=missing_fields,
            needs_user_input=needs_user_input,
            questions_to_ask=questions
        )
    
    def apply_user_input(self, pack: Dict, user_input: Dict) -> Dict:
        """Apply user input to pack and return updated pack"""
        
        # Q1: primary_offer_summary
        if 'primary_offer_summary' in user_input and user_input['primary_offer_summary']:
            pack['offer']['primary_offer_summary'] = user_input['primary_offer_summary']
        
        # Q2A: primary_action
        if 'primary_action' in user_input and user_input['primary_action']:
            pack['conversion']['primary_action'] = user_input['primary_action']
            if user_input.get('primary_action_text'):
                pack['conversion']['primary_action_text'] = user_input['primary_action_text']
        
        # Q2B: trust_signal
        if 'trust_signal' in user_input and user_input['trust_signal']:
            signal_value = user_input['trust_signal']
            signal_map = {
                'reviews_rating': 'Reviews / rating',
                'testimonials': 'Testimonials',
                'before_after': 'Before-after results',
                'certified': 'Certified / experts',
                'known_clients': 'Known clients / partnerships',
                'experience': 'Years of experience',
            }
            
            if signal_value == 'other' and user_input.get('trust_signal_text'):
                signal_text = f"Other: {user_input['trust_signal_text']}"
            else:
                signal_text = signal_map.get(signal_value, signal_value)
            
            if 'trust_signals' not in pack['proof']:
                pack['proof']['trust_signals'] = []
            pack['proof']['trust_signals'].append(signal_text)
        
        return pack
