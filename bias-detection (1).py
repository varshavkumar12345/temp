# app/bias_detection.py
"""
Module for detecting bias in text content.
"""

import re
import json
import os
from typing import Dict, List, Any, Tuple, Optional
import logging
from collections import Counter

logger = logging.getLogger(__name__)

class BiasDetector:
    """Detects various forms of bias in text content."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the bias detector with bias patterns and keywords.
        
        Args:
            config: Configuration for bias detection
        """
        self.config = config or {}
        
        # Load bias phrases and patterns
        self.bias_phrases = self._load_bias_phrases()
        self.political_bias_terms = self._load_political_bias_terms()
        self.loaded_sources = self._load_source_bias()
        
    def _load_bias_phrases(self) -> Dict[str, List[str]]:
        """Load bias phrases from data file or use defaults."""
        try:
            data_path = self.config.get("bias_phrases_path", "data/bias_phrases.json")
            if os.path.exists(data_path):
                with open(data_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load bias phrases from file: {e}")
            
        # Default bias phrases by category if file not available
        return {
            "loaded_language": [
                "obviously", "clearly", "without a doubt", "certainly", 
                "undoubtedly", "definitely", "absolutely", "everyone knows", 
                "of course", "naturally", "inevitably", "indisputably"
            ],
            "subjective_qualifiers": [
                "best", "worst", "terrible", "excellent", "horrible", 
                "amazing", "awful", "extraordinary", "wonderful", "appalling"
            ],
            "generalization": [
                "all", "none", "every", "always", "never", "everyone", 
                "nobody", "everywhere", "anywhere", "throughout history"
            ],
            "exaggeration": [
                "countless", "endless", "infinite", "unprecedented", "massive",
                "monumental", "epic", "colossal", "gigantic", "staggering"
            ]
        }
        
    def _load_political_bias_terms(self) -> Dict[str, List[str]]:
        """Load political bias terms."""
        try:
            data_path = self.config.get("political_bias_path", "data/political_bias_terms.json")
            if os.path.exists(data_path):
                with open(data_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load political bias terms from file: {e}")
            
        # Default political bias terms by leaning
        return {
            "left_leaning": [
                "progressive", "liberal", "social justice", "diversity", 
                "equity", "inclusion", "structural racism", "climate crisis", 
                "reproductive rights", "universal healthcare"
            ],
            "right_leaning": [
                "conservative", "traditional values", "individual liberty",
                "free market", "fiscal responsibility", "religious freedom",
                "limited government", "family values", "immigration control"
            ]
        }
        
    def _load_source_bias(self) -> Dict[str, str]:
        """Load known source bias ratings."""
        try:
            data_path = self.config.get("source_bias_path", "data/source_bias.json")
            if os.path.exists(data_path):
                with open(data_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load source bias data from file: {e}")
            
        # Default source bias data
        return {
            "example-left.com": "left",
            "example-right.com": "right",
            "example-center.com": "center",
            # More domains would be included in the actual file
        }
        
    def detect_bias(self, text: str) -> Dict[str, Any]:
        """
        Detect various forms of bias in text.
        
        Args:
            text: The text to analyze for bias
            
        Returns:
            Dictionary containing bias analysis results
        """
        results = {
            "issues": [],
            "metadata": {
                "bias_types_detected": [],
                "political_leaning": None,
                "political_leaning_confidence": 0.0,
                "overall_bias_level": 0.0
            }
        }
        
        # Detect loaded language
        loaded_language_issues = self._detect_loaded_language(text)
        if loaded_language_issues:
            results["issues"].extend(loaded_language_issues)
            results["metadata"]["bias_types_detected"].append("loaded_language")
            
        # Detect generalizations
        generalization_issues = self._detect_generalizations(text)
        if generalization_issues:
            results["issues"].extend(generalization_issues)
            results["metadata"]["bias_types_detected"].append("generalizations")
            
        # Detect exaggerations
        exaggeration_issues = self._detect_exaggerations(text)
        if exaggeration_issues:
            results["issues"].extend(exaggeration_issues)
            results["metadata"]["bias_types_detected"].append("exaggerations")
            
        # Detect subjective language
        subjective_issues = self._detect_subjective_language(text)
        if subjective_issues:
            results["issues"].extend(subjective_issues)
            results["metadata"]["bias_types_detected"].append("subjective_language")
            
        # Detect political bias
        political_bias = self._detect_political_bias(text)
        if political_bias["leaning"] != "neutral":
            results["metadata"]["political_leaning"] = political_bias["leaning"]
            results["metadata"]["political_leaning_confidence"] = political_bias["confidence"]
            political_issue = {
                "type": "political_bias",
                "description": f"Political bias detected ({political_bias['leaning']}-leaning)",
                "confidence": political_bias["confidence"],
                "spans": political_bias["spans"]
            }
            results["issues"].append(political_issue)
            results["metadata"]["bias_types_detected"].append("political_bias")
            
        # Calculate overall bias level (0-1 scale)
        bias_count = len(results["issues"])
        text_length = len(text.split())  # Word count
        
        # Scale bias level based on number of issues per 100 words
        bias_density = bias_count / (text_length / 100) if text_length > 0 else 0
        bias_level = min(1.0, bias_density / 5.0)  # Cap at 1.0, with 5 issues per 100 words being maximum
        
        results["metadata"]["overall_bias_level"] = round(bias_level, 2)
        
        return results
        
    def _detect_loaded_language(self, text: str) -> List[Dict[str, Any]]:
        """Detect loaded language that presupposes facts or attempts to influence opinion."""
        issues = []
        
        for phrase in self.bias_phrases.get("loaded_language", []):
            pattern = re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(text):
                issues.append({
                    "type": "loaded_language",
                    "description": f"Loaded language: '{match.group(0)}'",
                    "confidence": 0.8,
                    "spans": [[match.start(), match.end()]]
                })
                
        return issues
        
    def _detect_generalizations(self, text: str) -> List[Dict[str, Any]]:
        """Detect generalizations that oversimplify complex situations."""
        issues = []
        
        for phrase in self.bias_phrases.get("generalization", []):
            pattern = re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(text):
                # Check context to reduce false positives
                start_idx = max(0, match.start() - 30)
                end_idx = min(len(text), match.end() + 30)
                context = text[start_idx:end_idx]
                
                # Skip if it appears to be in a negative or qualified statement
                if re.search(r'\bnot\b|\bexcept\b|\bbut\b|\bsome\b|\bfew\b|\bmany\b', context, re.IGNORECASE):
                    continue
                    
                issues.append({
                    "type": "generalization",
                    "description": f"Generalization: '{match.group(0)}'",
                    "confidence": 0.7,
                    "spans": [[match.start(), match.end()]]
                })
                
        return issues
        
    def _detect_exaggerations(self, text: str) -> List[Dict[str, Any]]:
        """Detect exaggerated language that overstates facts."""
        issues = []
        
        for phrase in self.bias_phrases.get("exaggeration", []):
            pattern = re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(text):
                issues.append({
                    "type": "exaggeration",
                    "description": f"Exaggerated language: '{match.group(0)}'",
                    "confidence": 0.75,
                    "spans": [[match.start(), match.end()]]
                })
                
        return issues
        
    def _detect_subjective_language(self, text: str) -> List[Dict[str, Any]]:
        """Detect subjective qualifiers and opinion statements presented as facts."""
        issues = []
        
        for phrase in self.bias_phrases.get("subjective_qualifiers", []):
            pattern = re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(text):
                # Check for attribution markers that would indicate opinion is attributed
                start_idx = max(0, match.start() - 40)
                context_before = text[start_idx:match.start()]
                
                # Skip if attributed to someone (opinion properly framed)
                if re.search(r'\bsaid\b|\bstated\b|\bclaimed\b|\baccording to\b|\bbelieves\b|\bthinks\b', 
                            context_before, re.IGNORECASE):
                    continue
                    
                issues.append({
                    "type": "subjective_language",
                    "description": f"Subjective language presented as fact: '{match.group(0)}'",
                    "confidence": 0.65,
                    "spans": [[match.start(), match.end()]]
                })
                
        return issues
        
    def _detect_political_bias(self, text: str) -> Dict[str, Any]:
        """Detect political bias in content."""
        result = {
            "leaning": "neutral",
            "confidence": 0.0,
            "spans": []
        }
        
        left_matches = []
        right_matches = []
        
        # Check for left-leaning terms
        for term in self.political_bias_terms.get("left_leaning", []):
            pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(text):
                left_matches.append((match.start(), match.end(), match.group(0)))
                
        # Check for right-leaning terms
        for term in self.political_bias_terms.get("right_leaning", []):
            pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(text):
                right_matches.append((match.start(), match.end(), match.group(0)))
                
        # Calculate political leaning based on term frequency
        left_count = len(left_matches)
        right_count = len(right_matches)
        total_count = left_count + right_count
        
        if total_count > 0:
            # Need sufficient political terms to make a determination
            if total_count >= 3:
                if left_count > right_count * 2:
                    result["leaning"] = "left"
                    result["confidence"] = min(0.9, 0.5 + (left_count - right_count) / total_count * 0.5)
                    result["spans"] = [[s, e] for s, e, _ in left_matches]
                elif right_count > left_count * 2:
                    result["leaning"] = "right"
                    result["confidence"] = min(0.9, 0.5 + (right_count - left_count) / total_count * 0.5)
                    result["spans"] = [[s, e] for s, e, _ in right_matches]
                elif abs(left_count - right_count) / total_count > 0.3:
                    # There's a significant difference, but not overwhelming
                    if left_count > right_count:
                        result["leaning"] = "center-left"
                        result["confidence"] = 0.6
                        result["spans"] = [[s, e] for s, e, _ in left_matches]
                    else:
                        result["leaning"] = "center-right"
                        result["confidence"] = 0.6
                        result["spans"] = [[s, e] for s, e, _ in right_matches]
                else:
                    # Balanced political terms
                    result["leaning"] = "center"
                    result["confidence"] = 0.7
                    # Include both left and right spans
                    result["spans"] = [[s, e] for s, e, _ in (left_matches + right_matches)]
            else:
                # Not enough terms to make a confident determination
                if left_count > right_count:
                    result["leaning"] = "slight-left"
                    result["confidence"] = 0.4
                    result["spans"] = [[s, e] for s, e, _ in left_matches]
                elif right_count > left_count:
                    result["leaning"] = "slight-right"
                    result["confidence"] = 0.4
                    result["spans"] = [[s, e] for s, e, _ in right_matches]
                
        return result
