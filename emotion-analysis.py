# app/emotion_analysis.py
"""
Module for detecting emotional manipulation techniques in content.
"""

import re
import json
import os
from typing import Dict, List, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class EmotionAnalyzer:
    """Detects emotional manipulation techniques in text."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the emotion analyzer with emotional trigger patterns.
        
        Args:
            config: Configuration for emotion analysis
        """
        self.config = config or {}
        
        # Load emotional trigger patterns
        self.emotional_triggers = self._load_emotional_triggers()
        self.urgency_patterns = self._load_urgency_patterns()
        self.fear_patterns = self._load_fear_patterns()
        
    def _load_emotional_triggers(self) -> Dict[str, List[str]]:
        """Load emotional trigger words and phrases from data file or use defaults."""
        try:
            data_path = self.config.get("emotional_triggers_path", "data/emotional_triggers.json")
            if os.path.exists(data_path):
                with open(data_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load emotional triggers from file: {e}")
            
        # Default emotional triggers by category
        return {
            "fear": [
                "terrifying", "horrific", "dangerous", "deadly", "alarming",
                "frightening", "scary", "threat", "panic", "disaster", "crisis"
            ],
            "anger": [
                "outrageous", "shocking", "appalling", "disgusting", "infuriating",
                "scandalous", "offensive", "betrayal", "corrupt", "unjust"
            ],
            "joy": [
                "amazing", "incredible", "wonderful", "revolutionary", "breakthrough",
                "miraculous", "astonishing", "life-changing", "extraordinary"
            ],
            "sadness": [
                "heartbreaking", "devastating", "tragic", "depressing", "sorrowful",
                "painful", "miserable", "grim", "hopeless"
            ]
        }
        
    def _load_urgency_patterns(self) -> List[str]:
        """Load urgency patterns or use defaults."""
        try:
            data_path = self.config.get("urgency_patterns_path", "data/urgency_patterns.json")
            if os.path.exists(data_path):
                with open(data_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load urgency patterns from file: {e}")
            
        # Default urgency patterns
        return [
            r"act now", r"limited time", r"urgent", r"breaking", r"time is running out",
            r"don't wait", r"last chance", r"immediately", r"soon", r"before it's too late",
            r"while supplies last", r"exclusive offer", r"today only", r"deadline"
        ]
        
    def _load_fear_patterns(self) -> List[str]:
        """Load fear-based manipulation patterns or use defaults."""
        try:
            data_path = self.config.get("fear_patterns_path", "data/fear_patterns.json")
            if os.path.exists(data_path):
                with open(data_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load fear patterns from file: {e}")
            
        # Default fear patterns
        return [
            r"you can't afford to miss", r"warning", r"danger", r"risk",
            r"what you don't know", r"might be killing you", r"hidden dangers",
            r"protect yourself", r"fear of missing out", r"fomo",
            r"you will regret", r"devastating consequences"
        ]
        
    def detect_manipulation(self, text: str) -> Dict[str, Any]:
        """
        Detect emotional manipulation techniques in text.
        
        Args:
            text: The text to analyze for emotional manipulation
            
        Returns:
            Dictionary containing emotion analysis results
        """
        results = {
            "issues": [],
            "metadata": {
                "emotion_types_detected": [],
                "dominant_emotion": None,
                "emotional_manipulation_score": 0.0,
                "emotional_intensity": 0.0
            }
        }
        
        # Detect emotional triggers
        emotion_counts = {}
        for emotion_type, triggers in self.emotional_triggers.items():
            emotion_matches = []
            for trigger in triggers:
                pattern = re.compile(r'\b' + re.escape(trigger) + r'\b', re.IGNORECASE)
                for match in pattern.finditer(text):
                    emotion_matches.append((match.start(), match.end(), match.group(0)))
            
            if emotion_matches:
                results["metadata"]["emotion_types_detected"].append(emotion_type)
                emotion_counts[emotion_type] = len(emotion_matches)
                
                # Add emotional trigger issue
                results["issues"].append({
                    "type": "emotional_trigger",
                    "description": f"Emotional language ({emotion_type})",
                    "confidence": 0.75,
                    "spans": [[s, e] for s, e, _ in emotion_matches]
                })
                
        # Determine dominant emotion
        if emotion_counts:
            dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])
            results["metadata"]["dominant_emotion"] = dominant_emotion[0]
            
        # Detect urgency language
        urgency_matches = []
        for pattern in self.urgency_patterns:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            for match in compiled_pattern.finditer(text):
                urgency_matches.append((match.start(), match.end(), match.group(0)))
                
        if urgency_matches:
            results["metadata"]["emotion_types_detected"].append("urgency")
            results["issues"].append({
                "type": "urgency_manipulation",
                "description": "Creates artificial sense of urgency",
                "confidence": 0.8,
                "spans": [[s, e] for s, e, _ in urgency_matches]
            })
            
        # Detect fear-based manipulation
        fear_matches = []
        for pattern in self.fear_patterns:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            for match in compiled_pattern.finditer(text):
                fear_matches.append((match.start(), match.end(), match.group(0)))
                
        if fear_matches:
            if "fear" not in results["metadata"]["emotion_types_detected"]:
                results["metadata"]["emotion_types_detected"].append("fear")
            results["issues"].append({
                "type": "fear_manipulation",
                "description": "Uses fear-based manipulation",
                "confidence": 0.85,
                "spans": [[s, e] for s, e, _ in fear_matches]
            })
            
        # Check for all caps sections (shouting)
        all_caps_pattern = re.compile(r'\b[A-Z]{3,}\b')
        all_caps_matches = []
        for match in all_caps_pattern.finditer(text):
            # Exclude common acronyms
            if len(match.group(0)) > 5:  # Only consider longer all caps as potential manipulation
                all_caps_matches.append((match.start(), match.end(), match.group(0)))
                
        if all_caps_matches:
            results["issues"].append({
                "type": "typography_manipulation",
                "description": "Using ALL CAPS for emphasis (shouting)",
                "confidence": 0.7,
                "spans": [[s, e] for s, e, _ in all_caps_matches]
            })
            
        # Check for excessive exclamation marks
        exclamation_pattern = re.compile(r'!{2,}|(?:![ \t]*){3,}')
        exclamation_matches = []
        for match in exclamation_pattern.finditer(text):
            exclamation_matches.append((match.start(), match.end(), match.group(0)))
            
        if exclamation_matches:
            results["issues"].append({
                "type": "typography_manipulation",
                "description": "Excessive exclamation marks",
                "confidence": 0.75,
                "spans": [[s, e] for s, e, _ in exclamation_matches]
            })
            
        # Calculate emotional manipulation score (0-1 scale)
        manipulation_techniques = len(results["issues"])
        text_length = len(text.split())  # Word count
        
        # Scale based on manipulation techniques per 100 words
        manipulation_density = manipulation_techniques / (text_length / 100) if text_length > 0 else 0
        manipulation_score = min(1.0, manipulation_density / 3.0)  # Cap at 1.0, with 3 techniques per 100 words being maximum
        
        results["metadata"]["emotional_manipulation_score"] = round(manipulation_score, 2)
        
        # Calculate emotional intensity based on frequency and variety of emotional language
        emotion_variety = len(results["metadata"]["emotion_types_detected"])
        total_emotional_triggers = sum(emotion_counts.values()) if emotion_counts else 0
        emotional_trigger_density = total_emotional_triggers / (text_length / 100) if text_length > 0 else 0
        
        # Combine density and variety for intensity score
        intensity_score = (emotional_trigger_density / 5.0) * 0.7 + (emotion_variety / 4.0) * 0.3
        results["metadata"]["emotional_intensity"] = round(min(1.0, intensity_score), 2)
        
        return results
        
    def get_excessive_emotion_sentences(self, text: str) -> List[str]:
        """
        Identify sentences with excessive emotional language.
        
        Args:
            text: The text to analyze
            
        Returns:
            List of sentences with high emotional content
        """
        # Split text into sentences
        sentence_pattern = re.compile(r'[^.!?]+[.!?]')
        sentences = sentence_pattern.findall(text)
        
        # Flatten all emotional triggers into one list
        all_triggers = []
        for triggers in self.emotional_triggers.values():
            all_triggers.extend(triggers)
            
        # Check each sentence for emotional triggers
        excessive_sentences = []
        for sentence in sentences:
            emotional_word_count = 0
            for trigger in all_triggers:
                pattern = re.compile(r'\b' + re.escape(trigger) + r'\b', re.IGNORECASE)
                emotional_word_count += len(pattern.findall(sentence))
                
            # If more than 2 emotional triggers in a sentence, consider it excessive
            if emotional_word_count > 2:
                excessive_sentences.append(sentence.strip())
                
        return excessive_sentences
