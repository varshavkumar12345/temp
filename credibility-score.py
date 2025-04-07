# app/credibility_score.py
"""
Module for calculating overall credibility score based on analysis results.
"""

from typing import Dict, List, Any, Optional
import logging
import math

logger = logging.getLogger(__name__)

class CredibilityScorer:
    """Calculates overall credibility score based on analysis results."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the credibility scorer with scoring configuration.
        
        Args:
            config: Configuration for scoring algorithm
        """
        self.config = config or {}
        
        # Define issue type weights for scoring
        self.issue_weights = self.config.get("issue_weights", {
            # Bias issues
            "loaded_language": 3,
            "generalization": 4,
            "exaggeration": 3,
            "subjective_language": 2,
            "political_bias": 3,
            
            # Emotional manipulation issues
            "emotional_trigger": 3,
            "urgency_manipulation": 4,
            "fear_manipulation": 5,
            "typography_manipulation": 2,
            
            # Fact-checking issues
            "false_claim": 10,
            "external_fact_check": 8,
            "uncited_statistic": 5,
            
            # Linguistic pattern issues
            "clickbait": 5,
            "propaganda_technique": 6,
            "sensationalist_language": 4,
            "excessive_hedging": 2,
            "excessive_passive_voice": 1
        })
        
        # Define metadata scoring factors
        self.metadata_factors = self.config.get("metadata_factors", {
            "bias_level": 0.2,
            "emotional_manipulation": 0.2,
            "factual_accuracy": 0.4,
            "linguistic_patterns": 0.2
        })
        
    def calculate_score(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate overall credibility score based on analysis results.
        
        Args:
            analysis_results: Results from various analysis modules
            
        Returns:
            Dictionary with overall credibility score and explanation
        """
        # Initialize scoring variables
        issues = analysis_results.get("issues", [])
        metadata = analysis_results.get("metadata", {})
        
        # Base score starts at 100 (perfect credibility)
        base_score = 100
        
        # Track issue penalties for explanation
        issue_penalties = {}
        
        # Apply penalties for each issue based on type and confidence
        for issue in issues:
            issue_type = issue.get("type", "unknown")
            confidence = issue.get("confidence", 0.5)
            
            # Get weight for this issue type
            weight = self.issue_weights.get(issue_type, 2)
            
            # Calculate penalty: weight * confidence
            penalty = weight * confidence
            
            # Add to issue type penalties (for explanation)
            if issue_type not in issue_penalties:
                issue_penalties[issue_type] = 0
            issue_penalties[issue_type] += penalty
            
            # Apply penalty to base score
            base_score -= penalty
            
        # Apply metadata factor adjustments
        
        # Bias level factor
        bias_level = metadata.get("bias", {}).get("overall_bias_level", 0)
        bias_penalty = bias_level * 15 * self.metadata_factors.get("bias_level", 0.2)
        base_score -= bias_penalty
        
        # Emotional manipulation factor
        emotional_score = metadata.get("emotional_manipulation", {}).get("emotional_manipulation_score", 0)
        emotional_penalty = emotional_score * 15 * self.metadata_factors.get("emotional_manipulation", 0.2)
        base_score -= emotional_penalty
        
        # Factual accuracy factor (heavily weighted)
        factual_accuracy = metadata.get("fact_checking", {}).get("overall_factual_accuracy")
        if factual_accuracy is not None:
            factual_bonus = factual_accuracy * 20 * self.metadata_factors.get("factual_accuracy", 0.4)
            base_score += factual_bonus
        
        # Linguistic patterns factor
        clickbait_level = metadata.get("linguistic_patterns", {}).get("clickbait_level", 0)
        propaganda_level = metadata.get("linguistic_patterns", {}).get("propaganda_level", 0)
        sensationalism_level = metadata.get("linguistic_patterns", {}).get("sensationalism_level", 0)
        
        # Average the linguistic pattern levels
        pattern_level = (clickbait_level + propaganda_level + sensationalism_level) / 3
        pattern_penalty = pattern_level * 15 * self.metadata_factors.get("linguistic_patterns", 0.2)
        base_score -= pattern_penalty
        
        # Ensure score is within 0-100 range
        final_score = max(0, min(100, base_score))
        
        # Calculate confidence in our assessment (higher with more signals)
        signals_count = len(issues) + (1 if factual_accuracy is not None else 0)
        confidence = min(0.95, 0.5 + (signals_count / 20) * 0.45)
        
        # Generate summary explanation
        summary = self._generate_summary(final_score, issue_penalties, metadata, analysis_results.get("sources", []))
        
        return {
            "score": round(final_score),
            "confidence": round(confidence, 2),
            "summary": summary,
            "issue_penalties": issue_penalties
        }
        
    def _generate_summary(self, 
                        score: float, 
                        issue_penalties: Dict[str, float], 
                        metadata: Dict[str, Any],
                        sources: List[Dict[str, Any]]) -> str:
        """
        Generate a human-readable summary of credibility assessment.
        
        Args:
            score: The final credibility score
            issue_penalties: Dictionary of penalties by issue type
            metadata: Analysis metadata
            sources: Fact-checking sources
            
        Returns:
            Summary string explaining the credibility assessment
        """
        # Categorize the credibility score
        if score >= 90:
            credibility_category = "very high"
        elif score >= 75:
            credibility_category = "high"
        elif score >= 60:
            credibility_category = "moderate"
        elif score >= 40:
            credibility_category = "low"
        else:
            credibility_category = "very low"
            
        # Start with overall assessment
        summary = f"This content has {credibility_category} credibility (score: {round(score)}/100). "
        
        # Add major issues identified
        if issue_penalties:
            # Sort issues by penalty (descending)
            sorted_issues = sorted(issue_penalties.items(), key=lambda x: x[1], reverse=True)
            
            # Take top 3 issues for summary
            major_issues = sorted_issues[:3]
            
            issue_descriptions = []
            for issue_type, penalty in major_issues:
                # Format the issue type for display
                formatted_issue = issue_type.replace('_', ' ').title()
                issue_descriptions.append(formatted_issue)
                
            if issue_descriptions:
                summary += "Major concerns include: " + ", ".join(issue_descriptions) + ". "
                
        # Add factual accuracy if available
        factual_accuracy = metadata.get("fact_checking", {}).get("overall_factual_accuracy")
        claims_verified = metadata.get("fact_checking", {}).get("claims_verified", 0)
        claims_refuted = metadata.get("fact_checking", {}).get("claims_refuted", 0)
        claims_detected = metadata.get("fact_checking", {}).get("claims_detected", 0)
        
        if factual_accuracy is not None and claims_detected > 0:
            summary += f"Factual claims analysis: {claims_verified} verified, {claims_refuted} refuted out of {claims_detected} detected claims. "
            
        # Add bias information if available
        political_leaning = metadata.get("bias", {}).get("political_leaning")
        bias_level = metadata.get("bias", {}).get("overall_bias_level")
        
        if political_leaning and bias_level and bias_level > 0.3:
            summary += f"The content shows {political_leaning}-leaning bias. "
            
        # Add emotional manipulation information if significant
        emotional_score = metadata.get("emotional_manipulation", {}).get("emotional_manipulation_score", 0)
        dominant_emotion = metadata.get("emotional_manipulation", {}).get("dominant_emotion")
        
        if emotional_score > 0.4 and dominant_emotion:
            summary += f"The content uses {dominant_emotion}-based emotional appeals. "
            
        # Add recommendation based on score
        if score >= 75:
            summary += "This content appears to be generally reliable."
        elif score >= 60:
            summary += "Consider verifying key claims with additional sources."
        elif score >= 40:
            summary += "Approach this content with skepticism and verify with trusted sources."
        else:
            summary += "This content shows significant credibility issues and should be treated with caution."
            
        return summary.strip()
        
    def get_credibility_badge(self, score: float) -> str:
        """
        Get a credibility badge label based on score.
        
        Args:
            score: Credibility score (0-100)
            
        Returns:
            Badge label string
        """
        if score >= 90:
            return "Highly Credible"
        elif score >= 75:
            return "Credible"
        elif score >= 60:
            return "Somewhat Credible"
        elif score >= 40:
            return "Low Credibility"
        else:
            return "Very Low Credibility"
