"""
AI Query Service for translating natural language into structured oceanographic queries.
Uses LangChain with Groq LLM for intelligent query parameter extraction.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import re

from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.schema import HumanMessage, SystemMessage
from pydantic import ValidationError

from app.config import settings
from app.schemas import QueryParameters

logger = logging.getLogger(__name__)


class AIQueryService:
    """
    Service for processing natural language queries about oceanographic data.
    
    Uses Groq's Llama3 model via LangChain to extract structured parameters
    from user questions about ocean floats, profiles, and measurements.
    """
    
    def __init__(self):
        """Initialize the AI query service with Groq LLM."""
        self.groq_api_key = settings.GROQ_API_KEY
        self.llm = None
        self.chain = None
        self.output_parser = None
        
        if self.groq_api_key:
            try:
                # Initialize Groq LLM
                self.llm = ChatGroq(
                    groq_api_key=self.groq_api_key,
                    model_name="llama3-8b-8192",
                    temperature=0.1,  # Low temperature for consistent structured output
                    max_tokens=1000,
                    timeout=30
                )
                
                # Initialize output parser
                self.output_parser = PydanticOutputParser(pydantic_object=QueryParameters)
                
                # Create the processing chain
                self._create_processing_chain()
                
                logger.info("AI Query Service initialized successfully with Groq LLM")
                
            except Exception as e:
                logger.error(f"Failed to initialize Groq LLM: {e}")
                self.llm = None
        else:
            logger.warning("GROQ_API_KEY not found in environment variables")
    
    def _create_processing_chain(self):
        """Create the LangChain processing chain with prompt template."""
        
        # Define the prompt template with few-shot examples
        prompt_template = """You are an expert oceanographic data query assistant. Your task is to extract structured parameters from natural language questions about ocean float data.

IMPORTANT: You must respond with ONLY valid JSON that matches this exact schema:
{{
    "location": "string or null",
    "bbox": [min_lon, min_lat, max_lon, max_lat] or null,
    "start_date": "YYYY-MM-DDTHH:MM:SS" or null,
    "end_date": "YYYY-MM-DDTHH:MM:SS" or null,
    "variables": ["temperature", "salinity", "pressure", "dissolved_oxygen", "ph", "nitrate", "chlorophyll"],
    "depth_range": [min_depth_meters, max_depth_meters] or null,
    "general_search_term": "string or null"
}}

EXTRACTION RULES:
1. GEOSPATIAL:
   - For specific regions (Pacific Ocean, Arabian Sea, etc.), set "location" field
   - For coordinate ranges or "near X", create bbox: [min_lon, min_lat, max_lon, max_lat]
   - Longitude: -180 to 180, Latitude: -90 to 90
   
2. TEMPORAL:
   - Convert relative dates ("last month", "2023") to ISO format
   - "last month" = previous calendar month
   - "this year" = current year Jan 1 to Dec 31
   
3. VARIABLES:
   - Extract only: temperature, salinity, pressure, dissolved_oxygen, ph, nitrate, chlorophyll
   - Include all mentioned variables in the array
   
4. DEPTH:
   - Convert to meters: "surface" = [0, 100], "deep" = [1000, 6000]
   - "0-1000m" = [0, 1000]

FEW-SHOT EXAMPLES:

Example 1:
Question: "Show me temperature data from the Pacific Ocean in 2023"
Response:
{{
    "location": "Pacific Ocean",
    "bbox": null,
    "start_date": "2023-01-01T00:00:00",
    "end_date": "2023-12-31T23:59:59",
    "variables": ["temperature"],
    "depth_range": null,
    "general_search_term": null
}}

Example 2:
Question: "Find salinity and temperature profiles near 30°N, 140°W from last month"
Response:
{{
    "location": null,
    "bbox": [135.0, 25.0, 145.0, 35.0],
    "start_date": "2024-02-01T00:00:00",
    "end_date": "2024-02-29T23:59:59",
    "variables": ["salinity", "temperature"],
    "depth_range": null,
    "general_search_term": null
}}

Example 3:
Question: "What are oxygen levels in the Southern Ocean between 0-500m depth?"
Response:
{{
    "location": "Southern Ocean",
    "bbox": null,
    "start_date": null,
    "end_date": null,
    "variables": ["dissolved_oxygen"],
    "depth_range": [0, 500],
    "general_search_term": null
}}

Now extract parameters from this question:
Question: {question}

Response:"""

        self.prompt = PromptTemplate(
            input_variables=["question"],
            template=prompt_template
        )
        
        # Create the chain
        self.chain = self.prompt | self.llm
        
        logger.info("Processing chain created successfully")
    
    async def process_ai_query(self, question: str) -> QueryParameters:
        """
        Process a natural language question and extract structured parameters.
        
        Args:
            question: User's natural language question about oceanographic data
            
        Returns:
            QueryParameters: Structured query parameters
            
        Raises:
            Exception: If LLM processing fails
        """
        if not self.llm or not self.chain:
            logger.warning("LLM not available, falling back to basic extraction")
            return self._fallback_extraction(question)
        
        try:
            logger.info(f"Processing AI query: {question[:100]}...")
            
            # Invoke the chain asynchronously
            response = await self._invoke_chain_async(question)
            
            # Parse the response
            parameters = self._parse_llm_response(response, question)
            
            logger.info(f"Successfully extracted parameters: {parameters.dict()}")
            return parameters
            
        except Exception as e:
            logger.error(f"Error in AI query processing: {e}")
            logger.info("Falling back to basic parameter extraction")
            return self._fallback_extraction(question)
    
    async def _invoke_chain_async(self, question: str) -> str:
        """Invoke the LangChain asynchronously."""
        loop = asyncio.get_event_loop()
        
        def _invoke():
            try:
                # Format the prompt
                formatted_prompt = self.prompt.format(question=question)
                
                # Invoke the LLM
                response = self.llm.invoke(formatted_prompt)
                
                # Extract content from response
                if hasattr(response, 'content'):
                    return response.content
                else:
                    return str(response)
                    
            except Exception as e:
                logger.error(f"Error invoking LLM: {e}")
                raise
        
        return await loop.run_in_executor(None, _invoke)
    
    def _parse_llm_response(self, response: str, original_question: str) -> QueryParameters:
        """
        Parse LLM response into QueryParameters.
        
        Args:
            response: Raw LLM response
            original_question: Original user question for fallback
            
        Returns:
            QueryParameters: Parsed parameters
        """
        try:
            # Clean the response - extract JSON if wrapped in markdown or text
            json_str = self._extract_json_from_response(response)
            
            # Parse JSON
            parsed_data = json.loads(json_str)
            
            # Convert to QueryParameters with validation
            parameters = QueryParameters(**parsed_data)
            
            logger.info("Successfully parsed LLM response")
            return parameters
            
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            logger.debug(f"Raw response: {response}")
            
            # Try to extract partial information
            return self._extract_partial_parameters(response, original_question)
    
    def _extract_json_from_response(self, response: str) -> str:
        """Extract JSON from LLM response that might contain extra text."""
        # Remove markdown code blocks
        response = re.sub(r'```json\s*', '', response)
        response = re.sub(r'```\s*', '', response)
        
        # Find JSON object
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        # If no JSON found, return original
        return response.strip()
    
    def _extract_partial_parameters(self, response: str, question: str) -> QueryParameters:
        """Extract partial parameters when full parsing fails."""
        try:
            # Try to extract individual fields using regex
            params = {}
            
            # Extract location
            location_match = re.search(r'"location":\s*"([^"]*)"', response)
            if location_match:
                params['location'] = location_match.group(1)
            
            # Extract variables
            variables_match = re.search(r'"variables":\s*\[([^\]]*)\]', response)
            if variables_match:
                vars_str = variables_match.group(1)
                variables = [v.strip().strip('"') for v in vars_str.split(',') if v.strip()]
                params['variables'] = variables
            
            # If we got some parameters, use them; otherwise fallback
            if params:
                return QueryParameters(**params)
            else:
                return self._fallback_extraction(question)
                
        except Exception as e:
            logger.error(f"Error in partial extraction: {e}")
            return self._fallback_extraction(question)
    
    def _fallback_extraction(self, question: str) -> QueryParameters:
        """
        Fallback parameter extraction using simple keyword matching.
        
        Args:
            question: User's question
            
        Returns:
            QueryParameters: Basic extracted parameters
        """
        logger.info("Using fallback parameter extraction")
        
        question_lower = question.lower()
        
        # Extract variables using keywords
        variables = []
        variable_keywords = {
            'temperature': ['temperature', 'temp', 'thermal'],
            'salinity': ['salinity', 'salt', 'sal'],
            'pressure': ['pressure', 'depth', 'press'],
            'dissolved_oxygen': ['oxygen', 'o2', 'dissolved oxygen'],
            'ph': ['ph', 'acidity', 'alkalinity'],
            'nitrate': ['nitrate', 'nitrogen', 'no3'],
            'chlorophyll': ['chlorophyll', 'chl', 'phytoplankton']
        }
        
        for var, keywords in variable_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                variables.append(var)
        
        # Extract location using keywords
        location = None
        location_keywords = {
            'Pacific Ocean': ['pacific'],
            'Atlantic Ocean': ['atlantic'],
            'Indian Ocean': ['indian'],
            'Southern Ocean': ['southern', 'antarctic'],
            'Arctic Ocean': ['arctic'],
            'Mediterranean Sea': ['mediterranean'],
            'Arabian Sea': ['arabian']
        }
        
        for loc, keywords in location_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                location = loc
                break
        
        # Extract temporal information
        start_date = None
        end_date = None
        
        # Simple year extraction
        year_match = re.search(r'\b(20\d{2})\b', question)
        if year_match:
            year = year_match.group(1)
            start_date = f"{year}-01-01T00:00:00"
            end_date = f"{year}-12-31T23:59:59"
        
        # "Last month" extraction
        if 'last month' in question_lower:
            now = datetime.utcnow()
            if now.month == 1:
                last_month = 12
                year = now.year - 1
            else:
                last_month = now.month - 1
                year = now.year
            
            start_date = f"{year}-{last_month:02d}-01T00:00:00"
            
            # Calculate last day of month
            if last_month in [1, 3, 5, 7, 8, 10, 12]:
                last_day = 31
            elif last_month in [4, 6, 9, 11]:
                last_day = 30
            else:
                last_day = 29 if year % 4 == 0 else 28
            
            end_date = f"{year}-{last_month:02d}-{last_day}T23:59:59"
        
        return QueryParameters(
            location=location,
            variables=variables,
            start_date=start_date,
            end_date=end_date,
            general_search_term=question if not (variables or location) else None
        )
    
    def is_available(self) -> bool:
        """Check if AI service is available."""
        return self.llm is not None and self.chain is not None
    
    async def test_connection(self) -> bool:
        """Test the connection to Groq API."""
        if not self.is_available():
            return False
        
        try:
            test_query = "Show temperature data"
            result = await self.process_ai_query(test_query)
            return isinstance(result, QueryParameters)
        except Exception as e:
            logger.error(f"AI service test failed: {e}")
            return False


# Global AI query service instance
ai_query_service = AIQueryService()


# Convenience function for direct use
async def process_natural_language_query(question: str) -> QueryParameters:
    """
    Process a natural language question about oceanographic data.
    
    Args:
        question: User's natural language question
        
    Returns:
        QueryParameters: Structured query parameters
    """
    return await ai_query_service.process_ai_query(question)
