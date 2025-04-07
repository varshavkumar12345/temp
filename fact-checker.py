# app/fact_checker.py
"""
Module for fact-checking claims against external databases.
"""

import re
import json
import os
import requests
from urllib.parse import quote
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class FactChecker:
    """Checks factual claims against external databases and sources."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the fact checker with API keys and configuration.
        
        Args:
            config: Configuration for fact checking
        """
        self.config = config or {}
        
        # Load API keys from config
        self.api_keys = {
            "fact_check_tools": self.config.get("fact_check_tools_api_key", os.environ.get("FACT_CHECK_TOOLS_API_KEY", "")),
            "news_api": self.config.get("news_api_key", os.environ.get("NEWS_API_KEY", ""))
        }
        
        # Load known false claims database
        self.known_claims = self._load_known_claims()
        
    def _load_known_claims(self) -> Dict[str, Any]:
        """Load database of known false or verified claims."""
        try:
            data_path = self.config.get("known_claims_path", "data/known_claims.json")
            if os.path.exists(data_path):
                with open(data_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load known claims database: {e}")
            
        # Return empty database if file not available
        return {"claims": []}
        
    def check_facts(self, text: str) -> Dict[str, Any]:
        """
        Check factual claims in text.
        
        Args:
            text: The text to analyze for factual claims
            
        Returns:
            Dictionary containing fact checking results
        """
        results = {
            "issues": [],
            "sources": [],
            "metadata": {
                "claims_detected": 0,
                "claims_verified": 0,
                "claims_refuted": 0,
                "overall_factual_accuracy": None
            }
        }
        
        # Extract potential factual claims
        claims = self._extract_claims(text)
        results["metadata"]["claims_detected"] = len(claims)
        
        if not claims:
            # No claims to check
            results["metadata"]["overall_factual_accuracy"] = None
            return results
            
        # Check each claim
        for claim in claims:
            claim_text = claim["text"]
            claim_start = claim["start"]
            claim_end = claim["end"]
            
            # First check against local database
            local_check = self._check_against_local_db(claim_text)
            
            if local_check["found"]:
                # Claim found in local database
                if not local_check["verified"]:
                    # Known false claim
                    results["issues"].append({
                        "type": "false_claim",
                        "description": f"False claim: \"{claim_text}\"",
                        "confidence": local_check["confidence"],
                        "spans": [[claim_start, claim_end]]
                    })
                    results["metadata"]["claims_refuted"] += 1
                else:
                    # Known true claim
                    results["metadata"]["claims_verified"] += 1
                    
                # Add source information
                results["sources"].append({
                    "claim": claim_text,
                    "verified": local_check["verified"],
                    "fact_check_url": local_check.get("source_url", ""),
                    "published_date": local_check.get("published_date", "")
                })
            else:
                # Check against external fact-checking services if API keys available
                if self.api_keys["fact_check_tools"]:
                    external_check = self._check_with_external_api(claim_text)
                    
                    if external_check["found"]:
                        if not external_check["verified"]:
                            # False claim according to external fact-checkers
                            results["issues"].append({
                                "type": "external_fact_check",
                                "description": f"Claim disputed by fact-checkers: \"{claim_text}\"",
                                "confidence": external_check["confidence"],
                                "spans": [[claim_start, claim_end]]
                            })
                            results["metadata"]["claims_refuted"] += 1
                        else:
                            # Verified claim
                            results["metadata"]["claims_verified"] += 1
                            
                        # Add source information
                        results["sources"].append({
                            "claim": claim_text,
                            "verified": external_check["verified"],
                            "fact_check_url": external_check.get("source_url", ""),
                            "published_date": external_check.get("published_date", "")
                        })
                    else:
                        # No fact check available
                        # Flag statistical claims without sources as potentially problematic
                        if self._is_statistical_claim(claim_text) and not self._has_citation(text, claim_start, claim_end):
                            results["issues"].append({
                                "type": "uncited_statistic",
                                "description": f"Statistical claim without citation: \"{claim_text}\"",
                                "confidence": 0.7,
                                "spans": [[claim_start, claim_end]]
                            })
                            
        # Calculate overall factual accuracy if we have checked claims
        if results["metadata"]["claims_detected"] > 0:
            accuracy = results["metadata"]["claims_verified"] / results["metadata"]["claims_detected"]
            results["metadata"]["overall_factual_accuracy"] = round(accuracy, 2)
            
        return results
        
    def _extract_claims(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract potential factual claims from text.
        
        Args:
            text: The text to analyze
            
        Returns:
            List of potential factual claims with positions
        """
        claims = []
        
        # Pattern to identify sentences likely to contain factual claims
        # Look for statements with numbers, percentages, or definitive language
        claim_patterns = [
            # Statistical claims with numbers or percentages
            r'(\d+(?:\.\d+)?(?:\s*%)?\s*(?:of|in|people|Americans|users|voters|patients).*?[.!?])',
            # Claims with definitive language
            r'([^.!?]*?(?:study shows|research indicates|scientists discovered|experts agree|data reveals|report states).*?[.!?])',
            # Claims about causation
            r'([^.!?]*?causes.*?[.!?])',
            # Claims with dates/years
            r'([^.!?]*?(?:in \d{4}|last year|last month|last week|yesterday|today).*?[.!?])'
        ]
        
        for pattern in claim_patterns:
            pattern_regex = re.compile(pattern, re.IGNORECASE)
            for match in pattern_regex.finditer(text):
                claim_text = match.group(1).strip()
                if len(claim_text) > 10:  # Filter out very short matches
                    claims.append({
                        "text": claim_text,
                        "start": match.start(),
                        "end": match.end()
                    })
                    
        # Deduplicate overlapping claims
        claims.sort(key=lambda x: x["start"])
        deduplicated_claims = []
        
        for claim in claims:
            # Check if this claim overlaps with the last added claim
            if not deduplicated_claims or claim["start"] >= deduplicated_claims[-1]["end"]:
                deduplicated_claims.append(claim)
            else:
                # Keep the longer claim if there's overlap
                if (claim["end"] - claim["start"]) > (deduplicated_claims[-1]["end"] - deduplicated_claims[-1]["start"]):
                    deduplicated_claims[-1] = claim
                    
        return deduplicated_claims
        
    def _check_against_local_db(self, claim: str) -> Dict[str, Any]:
        """
        Check a claim against the local database of known claims.
        
        Args:
            claim: The claim text to check
            
        Returns:
            Dictionary with check results
        """
        result = {
            "found": False,
            "verified": False,
            "confidence": 0.0,
            "source_url": "",
            "published_date": ""
        }
        
        # Prepare claim for comparison - lowercase and strip punctuation
        clean_claim = re.sub(r'[^\w\s]', '', claim.lower())
        words = set(clean_claim.split())
        
        best_match = None
        best_similarity = 0.0
        
        # Simple word overlap similarity for matching
        for db_claim in self.known_claims.get("claims", []):
            db_claim_text = db_claim.get("claim_text", "")
            clean_db_claim = re.sub(r'[^\w\s]', '', db_claim_text.lower())
            db_words = set(clean_db_claim.split())
            
            # Calculate Jaccard similarity
            if not words or not db_words:
                continue
                
            intersection = len(words.intersection(db_words))
            union = len(words.union(db_words))
            similarity = intersection / union if union > 0 else 0
            
            if similarity > best_similarity and similarity > 0.7:  # Threshold for considering a match
                best_similarity = similarity
                best_match = db_claim
                
        if best_match:
            result["found"] = True
            result["verified"] = best_match.get("verified", False)
            result["confidence"] = best_similarity
            result["source_url"] = best_match.get("source_url", "")
            result["published_date"] = best_match.get("published_date", "")
            
        return result
        
    def _check_with_external_api(self, claim: str) -> Dict[str, Any]:
        """
        Check a claim using external fact-checking APIs.
        
        Args:
            claim: The claim text to check
            
        Returns:
            Dictionary with check results
        """
        result = {
            "found": False,
            "verified": False,
            "confidence": 0.0,
            "source_url": "",
            "published_date": ""
        }
        
        # This would normally make API calls to fact-checking services
        # For this example, we'll simulate the API call
        
        # Simulate checking with Google Fact Check Tools API
        # In a real implementation, this would be:
        # url = f"https://factchecktools.googleapis.com/v1alpha1/claims:search?query={quote(claim)}&key={self.api_keys['fact_check_tools']}"
        # response = requests.get(url)
        # data = response.json()
        
        # But for this example, we'll simulate some responses based on claim content
        
        # Simulate found for claims containing specific keywords
        if any(keyword in claim.lower() for keyword in ["covid", "vaccine", "election", "climate change"]):
            result["found"] = True
            
            # Simulate unverified for claims containing specific misinformation patterns
            if "5g" in claim.lower() and "covid" in claim.lower():
                result["verified"] = False
                result["confidence"] = 0.9
                result["source_url"] = "https://www.factcheck.org/example-check"
                result["published_date"] = "2023-05-15"
            elif "vaccine" in claim.lower() and "microchip" in claim.lower():
                result["verified"] = False
                result["confidence"] = 0.95
                result["source_url"] = "https://www.snopes.com/example-check"
                result["published_date"] = "2023-03-22"
            elif "election" in claim.lower() and "stolen" in claim.lower():
                result["verified"] = False
                result["confidence"] = 0.85
                result["source_url"] = "https://www.politifact.com/example-check"
                result["published_date"] = "2023-02-10"
            else:
                # For other keywords, randomly simulate verified or not
                # In a real implementation, this would come from the API response
                import random
                result["verified"] = random.choice([True, False])
                result["confidence"] = random.uniform(0.7, 0.9)
                result["source_url"] = "https://www.factcheck.org/another-example"
                result["published_date"] = "2023-04-18"
                
        return result
        
    def _is_statistical_claim(self, claim: str) -> bool:
        """Check if a claim contains statistical information."""
        # Look for percentages or specific numbers
        return bool(re.search(r'\d+(?:\.\d+)?(?:\s*%)?', claim))
        
    def _has_citation(self, text: str, claim_start: int, claim_end: int) -> bool:
        """
        Check if a claim has a citation within or nearby.
        
        Args:
            text: The full text
            claim_start: Start position of the claim
            claim_end: End position of the claim
            
        Returns:
            Boolean indicating if a citation was found
        """
        # Look for citation patterns in the claim and in the text after it
        citation_patterns = [
            r'\([^)]*\d{4}[^)]*\)',  # (Author, 2020) or (2020)
            r'according to [^.,;:"]*',  # "according to [source]"
            r'cited by [^.,;:"]*',  # "cited by [source]"
            r'\[[^\]]*\]',  # [1] or [citation]
            r'https?://\S+',  # URLs
            r'www\.\S+'  # URLs without protocol
        ]
        
        # Check in the claim text itself
        claim_text = text[claim_start:claim_end]
        for pattern in citation_patterns:
            if re.search(pattern, claim_text, re.IGNORECASE):
                return True
                
        # Check in the text shortly after the claim (next 100 characters)
        after_claim = text[claim_end:min(claim_end + 100, len(text))]
        for pattern in citation_patterns:
            if re.search(pattern, after_claim, re.IGNORECASE):
                return True
                
        return False
