# FloatChat Analytical Queries Guide

## Overview
FloatChat now supports advanced analytical queries with real-time oceanographic statistics including averages, ranges, and comparisons across different ocean regions.

## Supported Query Types

### 1. Regional Statistics
Query oceanographic data by ocean region with automatic statistical analysis.

**Examples:**
- "what is the average temperature in pacific ocean"
- "show me salinity data for indian ocean floats"
- "what is the temperature range in atlantic ocean"

**Returns:**
- Number of floats in the region
- Total profiles and measurements
- Geographic coverage (lat/lon extent)
- Data period (date range)
- Variable statistics (mean, min, max, standard deviation)

### 2. Multi-Variable Analysis
Compare multiple oceanographic variables in a single query.

**Examples:**
- "compare temperature and salinity in pacific ocean"
- "show me temperature and salinity in atlantic ocean"
- "analyze temperature, salinity, and pressure for indian ocean"

**Returns:**
- Statistics for each requested variable
- Side-by-side comparison of ranges
- Measurement counts per variable

### 3. Status-Based Queries
Filter by float operational status with statistics.

**Examples:**
- "show me pressure data for active floats"
- "what are the oxygen levels in active floats"
- "temperature data from inactive floats"

**Returns:**
- Filtered by status (active/inactive/maintenance)
- Full statistics for requested variables

### 4. Variable-Specific Queries
Focus on specific oceanographic parameters.

**Examples:**
- "show me all temperature measurements"
- "what is the salinity distribution"
- "pressure readings across all floats"
- "dissolved oxygen levels"

## Supported Variables

| Variable | Description | Units |
|----------|-------------|-------|
| `temperature` | Water temperature | °C (Celsius) |
| `salinity` | Salinity | PSU (Practical Salinity Units) |
| `pressure` | Water pressure / depth | dbar (decibars) |
| `dissolved_oxygen` | Dissolved oxygen concentration | µmol/kg |
| `ph` | pH level | pH units |
| `nitrate` | Nitrate concentration | µmol/kg |
| `chlorophyll` | Chlorophyll concentration | mg/m³ |

## Statistics Provided

For each variable, the system calculates:
- **Count**: Number of measurements
- **Mean**: Average value
- **Min**: Minimum value
- **Max**: Maximum value
- **Stddev**: Standard deviation

## Ocean Regions

Predefined regions with automatic bounding boxes:
- **Pacific Ocean**: -180° to -70° longitude, -60° to 60° latitude
- **Atlantic Ocean**: -80° to 20° longitude, -60° to 70° latitude
- **Indian Ocean**: 20° to 120° longitude, -60° to 30° latitude
- **Arctic Ocean**: -180° to 180° longitude, 60° to 90° latitude
- **Southern Ocean**: -180° to 180° longitude, -90° to -60° latitude

## Performance

- **Query Response Time**: 1.5 - 3 seconds
- **Optimized Queries**: Uses SQL aggregations (COUNT, AVG, MIN, MAX, STDDEV)
- **Efficient Filtering**: Subqueries prevent duplicate table joins
- **Scalable**: Handles millions of measurements efficiently

## Example Outputs

### Temperature Analysis in Pacific Ocean
```
Query: "what is the average temperature in pacific ocean"

Results: 31 floats
Found 31 floats with 886 profiles and 495,061 measurements.

📍 Geographic Coverage: 111.3° latitude × 359.8° longitude
📅 Data Period: 2025-10-04 to 2025-10-04

🌊 Oceanographic Data:
  • Temperature: 7.05°C (range: 1.49°C to 57.59°C)
```

### Multi-Variable Comparison
```
Query: "compare temperature and salinity in pacific ocean"

Results: 31 floats
Found 31 floats with 886 profiles and 495,061 measurements.

📍 Geographic Coverage: 111.3° latitude × 359.8° longitude
📅 Data Period: 2025-10-04 to 2025-10-04

🌊 Oceanographic Data:
  • Temperature: 7.05°C (range: 1.49°C to 57.59°C)
  • Salinity: 34.57 PSU (range: 2.02 to 36.87 PSU)
```

### Salinity in Indian Ocean
```
Query: "show me salinity data for indian ocean floats"

Results: 17 floats
Found 17 floats with 485 profiles and 203,798 measurements.

📍 Geographic Coverage: 79.7° latitude × 90.4° longitude
📅 Data Period: 2025-10-04 to 2025-10-04

🌊 Oceanographic Data:
  • Salinity: 34.78 PSU (range: 10.26 to 38.83 PSU)
```

## Technical Implementation

### Backend Components
1. **AI Service** (`backend/app/services/ai_service.py`)
   - Extracts variables from natural language queries
   - Generates enhanced insights with statistics

2. **Geospatial Service** (`backend/app/services/geospatial.py`)
   - Calculates variable statistics using SQL aggregations
   - Optimized queries with subqueries to avoid duplicate joins
   - Efficient filtering by region, status, and variables

3. **Query Parameters** (`backend/app/schemas.py`)
   - Supports `variables` list for multi-variable queries
   - Location-based filtering
   - Status-based filtering

### Database Optimization
- **No Eager Loading**: Queries don't load all profiles/measurements
- **Aggregation Queries**: Uses SQL COUNT, AVG, MIN, MAX, STDDEV
- **Subquery Filtering**: Prevents duplicate table joins
- **Indexed Columns**: Fast lookups on float_id, timestamp, location

## API Endpoint

**POST** `/api/v1/ai/query`

**Request:**
```json
{
  "question": "what is the average temperature in pacific ocean"
}
```

**Response:**
```json
{
  "query": "what is the average temperature in pacific ocean",
  "parameters": {
    "location": "Pacific Ocean",
    "variables": ["temperature"],
    "status": null
  },
  "floats": [...],
  "insights": "Found 31 floats with 886 profiles...",
  "data_summary": {
    "float_count": 31,
    "profile_count": 886,
    "measurement_count": 495061,
    "variable_statistics": {
      "temperature": {
        "count": 495061,
        "mean": 7.05,
        "min": 1.49,
        "max": 57.59,
        "stddev": 4.23
      }
    }
  },
  "recommendations": [...],
  "processing_time": 2.1
}
```

## Future Enhancements

Potential additions:
- Time-series analysis (seasonal trends)
- Depth profile comparisons
- Anomaly detection
- Cross-region comparisons
- Export to CSV/JSON
- Visualization endpoints (charts, maps)

## Access

- **Frontend**: http://localhost:8080
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
