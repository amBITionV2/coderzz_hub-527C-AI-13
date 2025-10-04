"""
AI service for processing natural language queries about oceanographic data.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

from app.config import settings
from app.schemas import AIQueryInput, QueryParameters, AIQueryResponse

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI-powered query processing using Groq Llama."""
    
    def __init__(self):
        self.groq_api_key = settings.GROQ_API_KEY
        self.groq_api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.3-70b-versatile"  # Groq's Llama model
        
        if not self.groq_api_key:
            logger.warning("No Groq API key configured - AI features will be limited")
        else:
            logger.info(f"AI Service initialized with Groq model: {self.model}")
    
    async def process_query(self, query_input: AIQueryInput) -> QueryParameters:
        """
        Process natural language query and extract structured parameters.
        
        Args:
            query_input: User's natural language query
            
        Returns:
            QueryParameters: Structured query parameters
        """
        if not self.groq_api_key:
            # Fallback to basic keyword extraction
            return self._extract_basic_parameters(query_input.question)
        
        try:
            # Create prompt for parameter extraction
            prompt = self._create_extraction_prompt(query_input.question)
            
            # Get AI response
            response = await self._call_llm(prompt)
            
            # Parse response to QueryParameters
            parameters = self._parse_ai_response(response)
            
            return parameters
            
        except Exception as e:
            logger.error(f"Error processing AI query: {e}")
            # Fallback to basic extraction
            return self._extract_basic_parameters(query_input.question)
    
    async def generate_insights(
        self, 
        query: str, 
        parameters: QueryParameters, 
        data_summary: Dict[str, Any]
    ) -> str:
        """
        Generate AI insights about the oceanographic data.
        
        Args:
            query: Original user query
            parameters: Extracted query parameters
            data_summary: Summary of retrieved data
            
        Returns:
            str: AI-generated insights
        """
        if not self.groq_api_key:
            return self._generate_basic_insights(data_summary)
        
        try:
            prompt = self._create_insights_prompt(query, parameters, data_summary)
            insights = await self._call_llm(prompt)
            return insights
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return self._generate_basic_insights(data_summary)
    
    async def generate_recommendations(
        self, 
        query: str, 
        parameters: QueryParameters, 
        data_summary: Dict[str, Any]
    ) -> List[str]:
        """
        Generate AI recommendations for further analysis.
        
        Args:
            query: Original user query
            parameters: Extracted query parameters
            data_summary: Summary of retrieved data
            
        Returns:
            List[str]: List of recommendations
        """
        if not self.groq_api_key:
            return self._generate_basic_recommendations(parameters)
        
        try:
            prompt = self._create_recommendations_prompt(query, parameters, data_summary)
            response = await self._call_llm(prompt)
            
            # Parse recommendations from response
            recommendations = self._parse_recommendations(response)
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return self._generate_basic_recommendations(parameters)
    
    def _create_extraction_prompt(self, question: str) -> str:
        """Create prompt for parameter extraction."""
        template = """
        You are an oceanographic data expert. Extract structured parameters from the user's question.
        
        User Question: {question}
        
        Extract the following information and return as JSON:
        - location: Geographic location or region mentioned
        - bbox: Bounding box coordinates [min_lon, min_lat, max_lon, max_lat] if specific area mentioned
        - start_date: Start date in ISO format if temporal range mentioned
        - end_date: End date in ISO format if temporal range mentioned
        - variables: List of oceanographic variables (temperature, salinity, pressure, etc.)
        - depth_range: Depth range [min_depth, max_depth] in meters if mentioned
        - general_search_term: Any general search terms for text matching
        
        Return only valid JSON. Use null for missing values.
        """
        
        return template.format(question=question)
    
    def _create_insights_prompt(
        self, 
        query: str, 
        parameters: QueryParameters, 
        data_summary: Dict[str, Any]
    ) -> str:
        """Create prompt for generating insights."""
        template = """
        You are an oceanographic expert analyzing data. Provide insights about the following data.
        
        User Query: {query}
        
        Query Parameters: {parameters}
        
        Data Summary: {data_summary}
        
        Provide scientific insights about:
        1. What the data shows about ocean conditions
        2. Notable patterns or anomalies
        3. Oceanographic significance
        4. Potential implications
        
        Keep response concise and scientific.
        """
        
        return template.format(
            query=query,
            parameters=parameters.dict(),
            data_summary=data_summary
        )
    
    def _create_recommendations_prompt(
        self, 
        query: str, 
        parameters: QueryParameters, 
        data_summary: Dict[str, Any]
    ) -> str:
        """Create prompt for generating recommendations."""
        template = """
        You are an oceanographic expert. Based on the user's query and available data, 
        suggest 3-5 specific recommendations for further analysis.
        
        User Query: {query}
        Parameters: {parameters}
        Data Summary: {data_summary}
        
        Provide actionable recommendations such as:
        - Additional variables to examine
        - Different time periods to explore
        - Comparative analyses to perform
        - Visualization suggestions
        
        Return as a numbered list, one recommendation per line.
        """
        
        return template.format(
            query=query,
            parameters=parameters.dict(),
            data_summary=data_summary
        )
    
    async def _call_llm(self, prompt: str) -> str:
        """Call Groq Llama model with the given prompt."""
        if not self.groq_api_key:
            raise ValueError("No Groq API key configured")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.groq_api_url,
                    headers={
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert oceanographic data analyst. Provide concise, accurate responses."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.1,
                        "max_tokens": 1000
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
                
        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            raise
    
    def _parse_ai_response(self, response: str) -> QueryParameters:
        """Parse AI response to QueryParameters."""
        try:
            # Try to parse as JSON
            data = json.loads(response)
            
            # Convert to QueryParameters
            return QueryParameters(
                location=data.get("location"),
                bbox=data.get("bbox"),
                start_date=data.get("start_date"),
                end_date=data.get("end_date"),
                variables=data.get("variables", []),
                depth_range=data.get("depth_range"),
                general_search_term=data.get("general_search_term")
            )
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse AI response: {e}")
            # Return empty parameters
            return QueryParameters()
    
    def _parse_recommendations(self, response: str) -> List[str]:
        """Parse recommendations from AI response."""
        try:
            # Split by lines and clean up
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            
            # Extract numbered items or bullet points
            recommendations = []
            for line in lines:
                # Remove numbering and bullet points
                clean_line = line.lstrip('0123456789.- ').strip()
                if clean_line:
                    recommendations.append(clean_line)
            
            return recommendations[:5]  # Limit to 5 recommendations
            
        except Exception as e:
            logger.error(f"Failed to parse recommendations: {e}")
            return []
    
    def _extract_basic_parameters(self, question: str) -> QueryParameters:
        """Basic parameter extraction without AI."""
        question_lower = question.lower()
        
        # Extract variables
        variables = []
        if 'temperature' in question_lower:
            variables.append('temperature')
        if 'salinity' in question_lower:
            variables.append('salinity')
        if 'pressure' in question_lower:
            variables.append('pressure')
        if 'oxygen' in question_lower:
            variables.append('dissolved_oxygen')
        
        # Extract location keywords
        location = None
        if 'pacific' in question_lower:
            location = 'Pacific Ocean'
        elif 'atlantic' in question_lower:
            location = 'Atlantic Ocean'
        elif 'indian' in question_lower:
            location = 'Indian Ocean'
        
        return QueryParameters(
            location=location,
            variables=variables,
            general_search_term=question
        )
    
    def _generate_basic_insights(self, data_summary: Dict[str, Any]) -> str:
        """Generate basic insights without AI."""
        float_count = data_summary.get('float_count', 0)
        profile_count = data_summary.get('profile_count', 0)
        
        insights = f"Found {float_count} floats with {profile_count} profiles. "
        
        if 'temperature_range' in data_summary:
            temp_range = data_summary['temperature_range']
            insights += f"Temperature ranges from {temp_range[0]:.1f}°C to {temp_range[1]:.1f}°C. "
        
        if 'salinity_range' in data_summary:
            sal_range = data_summary['salinity_range']
            insights += f"Salinity ranges from {sal_range[0]:.1f} to {sal_range[1]:.1f} PSU. "
        
        return insights
    
    def _generate_basic_recommendations(self, parameters: QueryParameters) -> List[str]:
        """Generate basic recommendations without AI."""
        recommendations = []
        
        if not parameters.variables:
            recommendations.append("Consider examining temperature and salinity profiles")
        
        if not parameters.bbox and not parameters.location:
            recommendations.append("Specify a geographic region for more focused analysis")
        
        if not parameters.start_date:
            recommendations.append("Add temporal constraints to examine seasonal patterns")
        
        recommendations.append("Visualize data on a map to identify spatial patterns")
        recommendations.append("Compare with historical data for trend analysis")
        
        return recommendations


# Global AI service instance
ai_service = AIService()
