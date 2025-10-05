# FloatChat Query Examples - Quick Reference

## 🌊 Basic Queries

### Find Floats by Status
```
"show me active floats"
"find inactive floats"
"which floats are in maintenance"
```
**Returns**: All floats with specified status

### Find Floats by Region
```
"find floats in pacific ocean"
"show me floats in indian ocean"
"give me data for atlantic ocean"
```
**Returns**: Floats within the specified ocean region

### Find Floats by Variable
```
"which floats have temperature data"
"show me floats measuring salinity"
"find floats with oxygen measurements"
```
**Returns**: Floats that have measurements for the specified variable

## 📊 Analytical Queries

### Temperature Analysis
```
"what is the average temperature in pacific ocean"
"show me temperature range in indian ocean"
"temperature data for active floats"
"compare temperature between atlantic and pacific"
```
**Returns**: Temperature statistics (mean, min, max, count)

### Salinity Analysis
```
"show me salinity data for indian ocean floats"
"what is the salinity range in atlantic"
"average salinity in pacific ocean"
```
**Returns**: Salinity statistics in PSU

### Pressure/Depth Analysis
```
"show me pressure data for active floats"
"what is the maximum depth in pacific ocean"
"pressure readings across all floats"
```
**Returns**: Pressure statistics in decibars

### Multi-Variable Comparisons
```
"compare temperature and salinity in pacific ocean"
"show me temperature, salinity, and pressure for indian ocean"
"analyze all variables in atlantic ocean"
```
**Returns**: Statistics for all requested variables

### Oxygen Levels
```
"what are the oxygen levels in active floats"
"dissolved oxygen in indian ocean"
"show me oxygen data for pacific floats"
```
**Returns**: Dissolved oxygen statistics in µmol/kg

## 🎯 Combined Filters

### Region + Variable
```
"show me temperature data for pacific ocean"
"salinity measurements in indian ocean"
"pressure readings from atlantic floats"
```

### Status + Variable
```
"temperature data from active floats"
"salinity in inactive floats"
"oxygen levels in active floats"
```

### Region + Status + Variable
```
"show me temperature from active floats in pacific ocean"
"salinity data for active indian ocean floats"
```

## 📈 Expected Response Format

Every query returns:

1. **Float Count**: Number of matching floats
2. **Profile Count**: Total number of profiles
3. **Measurement Count**: Total measurements
4. **Geographic Coverage**: Latitude and longitude extent
5. **Data Period**: Date range of measurements
6. **Variable Statistics**: For each requested variable:
   - Mean (average)
   - Min (minimum)
   - Max (maximum)
   - Standard deviation
   - Count (number of measurements)

## ⚡ Performance Tips

1. **Be Specific**: More specific queries are faster
   - ✅ "temperature in pacific ocean" (31 floats, ~2s)
   - ❌ "show me all data" (97 floats, ~3s)

2. **Limit Variables**: Request only needed variables
   - ✅ "temperature in pacific" (1 variable)
   - ❌ "all variables in pacific" (7 variables)

3. **Use Regions**: Regional queries are optimized
   - ✅ "pacific ocean" (predefined bbox)
   - ❌ "near coordinates 35.5, -120.3" (slower)

## 🔍 Advanced Examples

### Research Scenarios

**Marine Heatwave Detection**
```
"what is the temperature range in pacific ocean"
```
Look for unusually high max temperatures

**Salinity Anomalies**
```
"compare salinity between indian and atlantic ocean"
```
Compare mean salinity across regions

**Oxygen Minimum Zones**
```
"what are the oxygen levels in indian ocean"
```
Identify low oxygen areas

**Deep Ocean Profiling**
```
"show me pressure data for active floats"
```
Analyze depth coverage

**Multi-Parameter Ocean State**
```
"compare temperature, salinity, and pressure in pacific ocean"
```
Get comprehensive ocean state

## 💡 Tips for Best Results

1. **Use Natural Language**: The AI understands conversational queries
   - "what is the average temperature" ✅
   - "avg temp" ✅
   - Both work!

2. **Specify Ocean Regions**: Use standard ocean names
   - Pacific Ocean
   - Atlantic Ocean
   - Indian Ocean
   - Arctic Ocean
   - Southern Ocean

3. **Variable Names**: Use common terms
   - temperature, temp
   - salinity, sal
   - pressure, depth
   - oxygen, dissolved oxygen
   - pH

4. **Status Keywords**: Use clear status terms
   - active
   - inactive
   - maintenance

## 🚀 Quick Test Queries

Copy and paste these to test the system:

```
show me active floats
what is the average temperature in pacific ocean
compare temperature and salinity in indian ocean
show me pressure data for active floats
find floats in atlantic ocean
what is the salinity range in pacific ocean
temperature data from active floats
show me all floats measuring oxygen
```

## 📊 Sample Output

```
Query: "what is the average temperature in pacific ocean"

Results: 31 floats
Found 31 floats with 886 profiles and 495,061 measurements.

📍 Geographic Coverage: 111.3° latitude × 359.8° longitude
📅 Data Period: 2025-10-04 to 2025-10-04

🌊 Oceanographic Data:
  • Temperature: 7.05°C (range: 1.49°C to 57.59°C)

Recommendations:
  • Consider examining temperature and salinity profiles
  • Specify a geographic region for more focused analysis
  • Add temporal constraints to examine seasonal patterns
```

## 🌐 Access Points

- **Web Interface**: http://localhost:8080
- **API Endpoint**: http://localhost:8000/api/v1/ai/query
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
