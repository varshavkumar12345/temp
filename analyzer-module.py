# app/analyzer.py
"""
Core analyzer module for Content Integrity AI.
Orchestrates the analysis of text content for credibility assessment.
"""

import re
import json
from typing import Dict, List, Any, Tuple, Optional
import logging
from datetime import datetime

from .bias_detection import BiasDetector
from .emotion_analysis import EmotionAnalyzer
from .fact_checker import FactChecker
from .linguistic_patterns import PatternAnalyzer
from .credibility_score import CredibilityScorer

logger = logging.getLogger(__name__)

class ContentAnalyzer:
    """Main content analysis class that orchestrates different analysis modules."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the content analyzer with various detection modules.
        
        Args:
            config_path: Optional path to configuration file
        """
        config = {}
        if config_path:
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
                
        self.bias_detector = BiasDetector(config.get('bias_detection', {}))
        self.emotion_analyzer = EmotionAnalyzer(config.get('emotion_analysis', {}))
        self.fact_checker = FactChecker(config.get('fact_checking', {}))
        self.pattern_analyzer = PatternAnalyzer(config.get('linguistic_patterns', {}))
        self.credibility_scorer = CredibilityScorer(config.get('scoring', {}))
        
    def analyze_text(self, 
                     text: str, 
                     options: Dict[str, bool] = None) -> Dict[str, Any]:
        """
        Analyze text content for credibility issues.
        
        Args:
            text: The text content to analyze
            options: Configuration options for analysis
                - check_facts: Whether to check factual claims
                - analyze_bias: Whether to detect bias
                - detect_emotional_manipulation: Whether to detect emotional manipulation
                
        Returns:
            A dictionary containing analysis results
        """
        options = options or {
            "check_facts": True,
            "analyze_bias": True,
            "detect_emotional_manipulation": True,
            "analyze_linguistic_patterns": True
        }
        
        # Prepare results dictionary
        results = {
            "timestamp": datetime.now().isoformat(),
            "text_length": len(text),
            "issues": [],
            "metadata": {},
            "sources": []
        }
        
        # Analyze text using different detectors based on options
        if options.get("analyze_bias", True):
            bias_results = self.bias_detector.detect_bias(text)
            results["issues"].extend(bias_results["issues"])
            results["metadata"]["bias"] = bias_results["metadata"]
            
        if options.get("detect_emotional_manipulation", True):
            emotion_results = self.emotion_analyzer.detect_manipulation(text)
            results["issues"].extend(emotion_results["issues"])
            results["metadata"]["emotional_manipulation"] = emotion_results["metadata"]
            
        if options.get("check_facts", True):
            fact_results = self.fact_checker.check_facts(text)
            results["issues"].extend(fact_results["issues"])
            results["sources"].extend(fact_results["sources"])
            results["metadata"]["fact_checking"] = fact_results["metadata"]
            
        if options.get("analyze_linguistic_patterns", True):
            pattern_results = self.pattern_analyzer.analyze_patterns(text)
            results["issues"].extend(pattern_results["issues"])
            results["metadata"]["linguistic_patterns"] = pattern_results["metadata"]
            
        # Calculate overall credibility score
        score_results = self.credibility_scorer.calculate_score(results)
        results["credibility_score"] = score_results["score"]
        results["confidence"] = score_results["confidence"]
        results["summary"] = score_results["summary"]
        
        return results
        
    def analyze_url(self, 
                   url: str, 
                   options: Dict[str, bool] = None) -> Dict[str, Any]:
        """
        Analyze content from a URL.
        
        Args:
            url: The URL to fetch and analyze
            options: Configuration options for analysis
                
        Returns:
            A dictionary containing analysis results
        """
        from urllib.parse import urlparse
        import requests
        from bs4 import BeautifulSoup
        
        # Basic URL validation
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return {
                "error": "Invalid URL format",
                "credibility_score": 0
            }
        
        try:
            # Fetch URL content
            headers = {
                'User-Agent': 'ContentIntegrityAI/1.0 Credibility Analyzer Bot'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Extract main text content using BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
                
            # Extract article content - focus on article, main, and content elements first
            article_elements = soup.select("article, main, #content, .content, .article")
            if article_elements:
                text = article_elements[0].get_text(separator='\n', strip=True)
            else:
                # Fall back to body content if no article elements found
                text = soup.body.get_text(separator='\n', strip=True)
            
            # Get title
            title = ""
            title_element = soup.find("title")
            if title_element:
                title = title_element.get_text(strip=True)
                
            # Get metadata
            meta_description = ""
            meta_element = soup.find("meta", attrs={"name": "description"})
            if meta_element:
                meta_description = meta_element.get("content", "")
                
            # Analyze the extracted text
            results = self.analyze_text(text, options)
            
            # Add URL-specific metadata
            results["url"] = url
            results["title"] = title
            results["meta_description"] = meta_description
            results["domain"] = parsed_url.netloc
            
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing URL {url}: {str(e)}")
            return {
                "error": f"Failed to analyze URL: {str(e)}",
                "credibility_score": 0,
                "url": url
            }
    
    def get_highlighted_text(self, text: str, results: Dict[str, Any]) -> str:
        """
        Generate HTML with highlights for identified issues.
        
        Args:
            text: Original text content
            results: Analysis results containing issue spans
            
        Returns:
            HTML string with highlighted issues
        """
        # Create a list of all spans with their issue types
        all_spans = []
        for issue in results.get("issues", []):
            for span in issue.get("spans", []):
                if len(span) == 2:  # Ensure span has start and end positions
                    all_spans.append({
                        "start": span[0],
                        "end": span[1],
                        "type": issue["type"],
                        "description": issue.get("description", "Issue detected")
                    })
        
        # Sort spans by start position
        all_spans.sort(key=lambda x: x["start"])
        
        # Generate HTML with highlights
        html_parts = []
        last_pos = 0
        
        for span in all_spans:
            # Add text before the current span
            if span["start"] > last_pos:
                html_parts.append(text[last_pos:span["start"]])
                
            # Add the highlighted span
            span_text = text[span["start"]:span["end"]]
            highlight_class = f"highlight-{span['type'].lower().replace('_', '-')}"
            html_parts.append(
                f'<span class="{highlight_class}" title="{span["description"]}">{span_text}</span>'
            )
            
            last_pos = span["end"]
            
        # Add remaining text
        if last_pos < len(text):
            html_parts.append(text[last_pos:])
            
        return "".join(html_parts)
