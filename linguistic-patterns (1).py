# app/linguistic_patterns.py
"""
Module for detecting problematic linguistic patterns in content.
"""

import re
import json
import os
from typing import Dict, List, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class PatternAnalyzer:
    """Analyzes text for problematic linguistic patterns."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the pattern analyzer with pattern databases.
        
        Args:
            config: Configuration for pattern analysis
        """
        self.config = config or {}
        
        # Load pattern databases
        self.clickbait_patterns = self._load_clickbait_patterns()
        self.propaganda_techniques = self._load_propaganda_techniques()
        self.hedging_language = self._load_hedging_language()
        self.sensationalist_patterns = self._load_sensationalist_patterns()
        
    def _load_clickbait_patterns(self) -> List[str]:
        """Load clickbait patterns from data file or use defaults."""
        try:
            data_path = self.config.get("clickbait_patterns_path", "data/clickbait_patterns.json")
            if os.path.exists(data_path):
                with open(data_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load clickbait patterns from file: {e}")
            
        # Default clickbait patterns
        return [
            r"(?:you won't believe|mind blowing|jaw dropping)",
            r"^\d+ (?:things|ways|reasons|facts|tips|tricks|ideas|secrets)",
            r"(?:number \d+|the last one) (?:will|could|can|may) (?:shock|surprise|amaze) you",
            r"what happens next (?:will|could|can|may) (?:shock|surprise|amaze) you",
            r"(?:doctors|experts|scientists) (?:hate|are afraid of) (?:this|him|her|them)",
            r"one (?:simple|weird|strange) trick",
            r"this (?:one|simple|weird|strange) trick",
            r"(?:shocking|surprising) (?:discovery|result|trick|tip|secret|fact)",
            r"(?:never|you should never|when not to) (?:do|try|attempt)",
            r"(?:this is why|the reason why|here's why)",
            r"(?:finally revealed|the truth about)",
            r"(?:secret|hidden) (?:trick|method|way|formula)"
        ]
        
    def _load_propaganda_techniques(self) -> Dict[str, List[str]]:
        """Load propaganda technique patterns from data file or use defaults."""
        try:
            data_path = self.config.get("propaganda_techniques_path", "data/propaganda_techniques.json")
            if os.path.exists(data_path):
                with open(data_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load propaganda techniques from file: {e}")
            
        # Default propaganda technique patterns
        return {
            "name_calling": [
                r"(?:libtard|snowflake|sheep|nazi|fascist|communist|socialist|radical|extremist|terrorist)"
            ],
            "glittering_generalities": [
                r"(?:freedom|liberty|justice|patriotic|patriot|american values|family values)"
            ],
            "bandwagon": [
                r"(?:everyone is|everybody is|everyone knows|everybody knows)",
                r"(?:most people|the majority|overwhelming majority)"
            ],
            "testimonial": [
                r"(?:according to experts|experts say|scientists confirm|science says)"
            ],
            "plain_folks": [
                r"(?:ordinary people|regular folks|hardworking americans|common sense)"
            ],
            "card_stacking": [
                r"(?:on the other hand|let me be clear|make no mistake)"
            ],
            "transfer": [
                r"(?:like the nazis|communist-style|stalinesque|hitler-like)"
            ]
        }
        
    def _load_hedging_language(self) -> List[str]:
        """Load hedging language patterns from data file or use defaults."""
        try:
            data_path = self.config.get("hedging_language_path", "data/hedging_language.json")
            if os.path.exists(data_path):
                with open(data_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load hedging language from file: {e}")
            
        # Default hedging language patterns
        return [
            r"\b(?:may|might|could|possibly|perhaps|seems|appears|likely|unlikely)\b",
            r"\b(?:some|sometimes|often|usually|generally|frequently)\b",
            r"\b(?:alleged|supposedly|purportedly|reportedly|claimed)\b",
            r"\b(?:sort of|kind of|relatively|comparatively|more or less)\b"
        ]
        
    def _load_sensationalist_patterns(self) -> List[str]:
        """Load sensationalist language patterns from data file or use defaults."""
        try:
            data_path = self.config.get("sensationalist_patterns_path", "data/sensationalist_patterns.json")
            if os.path.exists(data_path):
                with open(data_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load sensationalist patterns from file: {e}")
            
        # Default sensationalist language patterns
        return [
            r"\b(?:bombshell|explosive|destroying|obliterates|annihilates|devastating)\b",
            r"\b(?:insane|incredible|unbelievable|stunning|mind-blowing|jaw-dropping)\b",
            r"\b(?:game-changing|earth-shattering|revolutionary|ground-breaking)\b",
            r"\b(?:massive|enormous|gigantic|colossal|record-breaking|unprecedented)\b",
            r"\b(?:catastrophic|disastrous|horrific|terrifying|apocalyptic|extinction)\b",
            r"\b(?:meltdown|breaking news|urgent|emergency|critical|crucial)\b"
        ]
        
    def analyze_patterns(self, text: str) -> Dict[str, Any]:
        """
        Analyze linguistic patterns in text.
        
        Args:
            text: The text to analyze for problematic patterns
            
        Returns:
            Dictionary containing pattern analysis results
        """
        results = {
            "issues": [],
            "metadata": {
                "patterns_detected": [],
                "clickbait_level": 0.0,
                "propaganda_level": 0.0,
                "sensationalism_level": 0.0,
                "hedging_level": 0.0
            }
        }
        
        # Detect clickbait patterns
        clickbait_matches = self._detect_patterns(text, self.clickbait_patterns)
        if clickbait_matches:
            results["issues"].append({
                "type": "clickbait",
                "description": "Clickbait language detected",
                "confidence": 0.85,
                "spans": [[s, e] for s, e, _ in clickbait_matches]
            })
            results["metadata"]["patterns_detected"].append("clickbait")
            
            # Calculate clickbait level (0-1 scale)
            text_length = len(text.split())  # Word count
            clickbait_density = len(clickbait_matches) / (text_length / 100) if text_length > 0 else 0
            results["metadata"]["clickbait_level"] = min(1.0, clickbait_density / 2.0)
            
        # Detect propaganda techniques
        propaganda_matches = []
        propaganda_types = {}
        
        for technique, patterns in self.propaganda_techniques.items():
            technique_matches = self._detect_patterns(text, patterns)
            if technique_matches:
                propaganda_matches.extend(technique_matches)
                propaganda_types[technique] = len(technique_matches)
                
        if propaganda_matches:
            for technique, count in propaganda_types.items():
                results["issues"].append({
                    "type": "propaganda_technique",
                    "description": f"Propaganda technique detected: {technique.replace('_', ' ')}",
                    "confidence": 0.75,
                    "spans": [[s, e] for s, e, _ in propaganda_matches if _.get("technique") == technique]
                })
            results["metadata"]["patterns_detected"].append("propaganda_techniques")
            
            # Calculate propaganda level (0-1 scale)
            text_length = len(text.split())  # Word count
            propaganda_density = len(propaganda_matches) / (text_length / 100) if text_length > 0 else 0
            results["metadata"]["propaganda_level"] = min(1.0, propaganda_density / 2.0)
            
        # Detect sensationalist language
        sensationalist_matches = self._detect_patterns(text, self.sensationalist_patterns)
        if sensationalist_matches:
            results["issues"].append({
                "type": "sensationalist_language",
                "description": "Sensationalist language detected",
                "confidence": 0.8,
                "spans": [[s, e] for s, e, _ in sensationalist_matches]
            })
            results["metadata"]["patterns_detected"].append("sensationalist_language")
            
            # Calculate sensationalism level (0-1 scale)
            text_length = len(text.split())  # Word count
            sensationalism_density = len(sensationalist_matches) / (text_length / 100) if text_length > 0 else 0
            results["metadata"]["sensationalism_level"] = min(1.0, sensationalism_density / 3.0)
            
        # Detect hedging language
        hedging_matches = self._detect_patterns(text, self.hedging_language)
        
        # Only flag excessive hedging
        text_length = len(text.split())  # Word count
        if text_length > 0:
            hedging_density = len(hedging_matches) / (text_length / 100)
            results["metadata"]["hedging_level"] = min(1.0, hedging_density / 5.0)
            
            # Only flag as an issue if excessive (more than 5 per 100 words)
            if hedging_density > 5.0:
                results["issues"].append({
                    "type": "excessive_hedging",
                    "description": "Excessive use of hedging language",
                    "confidence": 0.7,
                    "spans": [[s, e] for s, e, _ in hedging_matches]
                })
                results["metadata"]["patterns_detected"].append("excessive_hedging")
                
        # Detect passive voice (simplified detection)
        passive_matches = self._detect_passive_voice(text)
        
        # Only flag excessive passive voice
        if text_length > 0:
            passive_density = len(passive_matches) / (text_length / 100)
            
            # Only flag as an issue if excessive (more than 8 per 100 words)
            if passive_density > 8.0:
                results["issues"].append({
                    "type": "excessive_passive_voice",
                    "description": "Excessive use of passive voice",
                    "confidence": 0.6,
                    "spans": [[s, e] for s, e in passive_matches]
                })
                results["metadata"]["patterns_detected"].append("excessive_passive_voice")
                
        return results
        
    def _detect_patterns(self, text: str, patterns: List[str]) -> List[Tuple[int, int, Dict[str, Any]]]:
        """
        Detect specified patterns in text.
        
        Args:
            text: The text to analyze
            patterns: List of regex patterns to detect
            
        Returns:
            List of matches with start and end positions
        """
        matches = []
        
        for pattern in patterns:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            for match in compiled_pattern.finditer(text):
                # Store match with position and original pattern
                matches.append((
                    match.start(), 
                    match.end(), 
                    {"text": match.group(0), "pattern": pattern}
                ))
                
        return matches
        
    def _detect_passive_voice(self, text: str) -> List[Tuple[int, int]]:
        """
        Detect passive voice constructions in text.
        
        Args:
            text: The text to analyze
            
        Returns:
            List of matches with start and end positions
        """
        # Simplified passive voice detection (not perfect but catches common cases)
        passive_patterns = [
            r'\b(?:is|are|was|were|be|been|being) (?:\w+ed|(?:brought|caught|done|found|given|held|kept|laid|led|left|lost|made|paid|put|read|said|sent|shown|sold|thought|told|won)) by\b',
            r'\b(?:is|are|was|were|be|been|being) (?:\w+ed)\b'
        ]
        
        matches = []
        
        for pattern in passive_patterns:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            for match in compiled_pattern.finditer(text):
                matches.append((match.start(), match.end()))
                
        return matches
        
    def get_clickbait_score(self, title: str) -> float:
        """
        Get a clickbait score for a title.
        
        Args:
            title: The title to analyze
            
        Returns:
            Clickbait score from 0 to 1
        """
        # Special analysis specifically for titles/headlines
        
        # Check all clickbait patterns
        clickbait_matches = []
        for pattern in self.clickbait_patterns:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            if compiled_pattern.search(title):
                clickbait_matches.append(pattern)
                
        # Check for question headlines (often clickbait)
        if title.endswith('?'):
            clickbait_matches.append("question_headline")
            
        # Check for incomplete headlines
        if title.endswith('...'):
            clickbait_matches.append("incomplete_headline")
            
        # Check for caps
        if re.search(r'\b[A-Z]{3,}\b', title):
            clickbait_matches.append("caps_for_emphasis")
            
        # Calculate score based on matches and title length
        base_score = len(clickbait_matches) * 0.2
        
        # Cap at 1.0
        return min(1.0, base_score)
