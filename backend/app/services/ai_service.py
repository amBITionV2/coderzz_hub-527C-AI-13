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
        self.model = "gemma2-9b-it"  # Fast and efficient model
        
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
        - status: Float status (active, inactive, or maintenance) if mentioned in query
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
                status=data.get("status"),
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
        
        # Check for float ID queries (e.g., "show me float 123", "data for float id 5904818")
        import re
        float_id_patterns = [
            r'float\s+(?:id\s+)?(\d+)',
            r'float\s+#(\d+)',
            r'id\s+(\d+)',
            r'wmo\s+(?:id\s+)?(\d+)',
        ]
        
        for pattern in float_id_patterns:
            match = re.search(pattern, question_lower)
            if match:
                float_id = match.group(1)
                # Store float ID in general_search_term with special prefix
                return QueryParameters(general_search_term=f"FLOAT_ID:{float_id}")
        
        # Check if query is relevant to oceanographic data
        irrelevant_keywords = ['weather', 'stock', 'news', 'sports', 'movie', 'music', 'recipe', 'game', 'joke', 'story', 'song']
        oceanographic_keywords = ['float', 'ocean', 'temperature', 'salinity', 'pressure', 'depth', 'water', 'sea', 'marine', 'oxygen', 'pacific', 'atlantic', 'indian', 'data', 'measurement']
        
        # If query contains irrelevant keywords, reject
        if any(keyword in question_lower for keyword in irrelevant_keywords):
            return QueryParameters()
        
        # If query doesn't contain any oceanographic keywords and is very short, might be irrelevant
        if not any(keyword in question_lower for keyword in oceanographic_keywords) and len(question_lower.split()) < 8:
            # Check if it's a greeting or casual conversation
            casual_phrases = ['hello', 'hi', 'hey', 'thanks', 'thank you', 'bye', 'goodbye']
            if any(phrase in question_lower for phrase in casual_phrases):
                return QueryParameters()
        
        # Extract variables with more keywords
        variables = []
        if any(word in question_lower for word in ['temperature', 'temp', 'warm', 'cold', 'heat']):
            variables.append('temperature')
        if any(word in question_lower for word in ['salinity', 'salt', 'saline']):
            variables.append('salinity')
        if any(word in question_lower for word in ['pressure', 'depth', 'deep']):
            variables.append('pressure')
        if any(word in question_lower for word in ['oxygen', 'o2', 'dissolved oxygen', 'do']):
            variables.append('dissolved_oxygen')
        if 'ph' in question_lower or 'acidity' in question_lower:
            variables.append('ph')
        if 'nitrate' in question_lower or 'nitrogen' in question_lower:
            variables.append('nitrate')
        if 'chlorophyll' in question_lower or 'chl' in question_lower:
            variables.append('chlorophyll')
        
        # Detect comparison queries (between two oceans)
        comparison_match = None
        if 'compare' in question_lower or 'between' in question_lower or 'versus' in question_lower or 'vs' in question_lower:
            # Extract all ocean names for comparison
            oceans = []
            if 'pacific' in question_lower:
                oceans.append('Pacific Ocean')
            if 'atlantic' in question_lower:
                oceans.append('Atlantic Ocean')
            if 'indian' in question_lower:
                oceans.append('Indian Ocean')
            if 'arctic' in question_lower:
                oceans.append('Arctic Ocean')
            if 'southern' in question_lower or 'south' in question_lower:
                oceans.append('Southern Ocean')
            
            if len(oceans) >= 2:
                comparison_match = oceans
        
        # Extract location keywords (single location)
        location = None
        if not comparison_match:
            if 'pacific' in question_lower:
                location = 'Pacific Ocean'
            elif 'atlantic' in question_lower:
                location = 'Atlantic Ocean'
            elif 'indian' in question_lower:
                location = 'Indian Ocean'
            elif 'arctic' in question_lower:
                location = 'Arctic Ocean'
            elif 'southern' in question_lower:
                location = 'Southern Ocean'
        
        # Extract status
        status = None
        if 'active' in question_lower:
            status = 'active'
        elif 'inactive' in question_lower:
            status = 'inactive'
        elif 'maintenance' in question_lower:
            status = 'maintenance'
        
        # Store comparison info in general_search_term temporarily
        if comparison_match:
            general_search_term = f"COMPARISON:{','.join(comparison_match)}"
        elif not (status or location or variables):
            # Only use text search if no specific filters found
            general_search_term = question
        else:
            general_search_term = None
        
        return QueryParameters(
            location=location,
            variables=variables,
            status=status,
            general_search_term=general_search_term
        )
    
    def _generate_basic_insights(self, data_summary: Dict[str, Any]) -> str:
        """Generate basic insights without AI."""
        float_count = data_summary.get('float_count', 0)
        profile_count = data_summary.get('profile_count', 0)
        measurement_count = data_summary.get('measurement_count', 0)
        
        insights = f"Found {float_count} floats with {profile_count} profiles and {measurement_count:,} measurements. "
        
        # Add spatial extent info
        if data_summary.get('spatial_extent'):
            extent = data_summary['spatial_extent']
            lat_range = extent['max_latitude'] - extent['min_latitude']
            lon_range = extent['max_longitude'] - extent['min_longitude']
            insights += f"\n\n📍 Geographic Coverage: {lat_range:.1f}° latitude × {lon_range:.1f}° longitude"
        
        # Add temporal info
        if data_summary.get('date_range'):
            date_range = data_summary['date_range']
            insights += f"\n📅 Data Period: {date_range['start'][:10]} to {date_range['end'][:10]}"
        
        # Add variable statistics if available
        if data_summary.get('variable_statistics'):
            stats = data_summary['variable_statistics']
            insights += "\n\n🌊 Oceanographic Data:"
            
            if 'temperature' in stats:
                temp = stats['temperature']
                insights += f"\n  • Temperature: {temp['mean']:.2f}°C (range: {temp['min']:.2f}°C to {temp['max']:.2f}°C)"
            
            if 'salinity' in stats:
                sal = stats['salinity']
                insights += f"\n  • Salinity: {sal['mean']:.2f} PSU (range: {sal['min']:.2f} to {sal['max']:.2f} PSU)"
            
            if 'pressure' in stats:
                pres = stats['pressure']
                insights += f"\n  • Pressure: {pres['mean']:.1f} dbar (max depth: {pres['max']:.1f} dbar)"
            
            if 'dissolved_oxygen' in stats:
                oxy = stats['dissolved_oxygen']
                insights += f"\n  • Dissolved Oxygen: {oxy['mean']:.2f} µmol/kg"
        
        return insights
    
    def _generate_basic_recommendations(self, parameters: QueryParameters) -> List[str]:
        """Generate actionable recommendations that can be queried."""
        recommendations = []
        
        # Make recommendations specific and queryable
        if parameters.location:
            # Suggest other regions for comparison
            other_oceans = ['Pacific Ocean', 'Atlantic Ocean', 'Indian Ocean']
            if parameters.location in other_oceans:
                other_oceans.remove(parameters.location)
                if len(other_oceans) >= 1:
                    recommendations.append(f"Compare {parameters.location} with {other_oceans[0]}")
        
        if parameters.variables:
            # Suggest additional variables (only those with data available)
            all_vars = ['temperature', 'salinity', 'pressure']  # Removed dissolved_oxygen
            missing_vars = [v for v in all_vars if v not in parameters.variables]
            if missing_vars and len(missing_vars) > 0:
                recommendations.append(f"Also examine {missing_vars[0]} in this region")
        else:
            # No variables specified, suggest some
            recommendations.append("Show me temperature data for these floats")
            recommendations.append("What is the salinity in this region")
        
        if not parameters.location:
            recommendations.append("Find floats in Pacific Ocean")
            recommendations.append("Show me data for Indian Ocean")
        
        if not parameters.status:
            recommendations.append("Filter by active floats only")
        
        # Always add a comparison suggestion if not already comparing
        if parameters.location and not (parameters.general_search_term and 'COMPARISON' in parameters.general_search_term):
            recommendations.append(f"Compare temperature between {parameters.location} and Atlantic Ocean")
        
        return recommendations[:5]  # Limit to 5


# Global AI service instance
ai_service = AIService()
