# 🌊 FloatChat - Oceanographic AI Explorer

An intelligent oceanographic data visualization and analysis platform that combines real-time float monitoring with AI-powered natural language querying.

![FloatChat Banner](https://img.shields.io/badge/FloatChat-Oceanographic%20AI-blue?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTMgMTJIMjEiIHN0cm9rZT0iY3VycmVudENvbG9yIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K)

## 🎯 Overview

FloatChat is a comprehensive oceanographic data platform that provides:

- **🗺️ Interactive Global Map**: Real-time visualization of oceanographic floats worldwide
- **🤖 AI-Powered Chat**: Natural language queries for ocean data exploration
- **📊 Real-Time Analytics**: Dynamic statistics and regional breakdowns
- **🌊 Ocean Monitoring**: Live status tracking of active, maintenance, and inactive floats

## ✨ Features

### 🗺️ Interactive Map Visualization
- **Global Float Distribution**: 50+ oceanographic floats positioned at real coordinates
- **Status-Based Color Coding**: Green (active), Yellow (maintenance), Red (inactive)
- **Interactive Markers**: Click for detailed float information
- **Real-Time Updates**: Live data from backend API
- **Zoom & Pan Controls**: Explore specific ocean regions

### 🤖 AI-Powered Natural Language Interface
- **Smart Queries**: Ask questions like "Show me temperature data from the Pacific Ocean"
- **Variable-Specific Searches**: Query temperature, salinity, oxygen levels
- **Regional Analysis**: Focus on specific ocean basins
- **Intelligent Responses**: AI-generated insights and recommendations

### 📊 Dynamic Analytics Dashboard
- **Real-Time Statistics**: Live float counts and status breakdowns
- **Ocean Region Analysis**: Automatic geographic classification
- **Data Quality Metrics**: Performance and availability indicators
- **Loading States**: Smooth user experience with proper feedback

### 🌊 Oceanographic Data Integration
- **Multiple Variables**: Temperature, salinity, dissolved oxygen, pH
- **Profile Data**: Vertical water column measurements
- **Temporal Tracking**: Historical data and trends
- **Quality Control**: Data validation and filtering

## 🏗️ Architecture

### Frontend (React/TypeScript)
```
src/
├── components/           # React components
│   ├── MapView.tsx      # Interactive Leaflet map
│   ├── ChatbotPanel.tsx # AI chat interface
│   ├── Sidebar.tsx      # Analytics dashboard
│   └── ui/              # Reusable UI components
├── lib/
│   └── api.ts           # Centralized API client
├── pages/
│   └── Index.tsx        # Main application layout
└── styles/              # Tailwind CSS configuration
```

### Backend (FastAPI/Python)
```
backend/
├── app/
│   ├── main_simple.py   # FastAPI application
│   ├── schemas.py       # Pydantic models
│   ├── crud.py          # Database operations
│   └── services/        # Business logic
├── scripts/
│   └── ingest_from_ftp.py # Data ingestion
└── alembic/             # Database migrations
```

## 🚀 Quick Start

### Prerequisites
- **Node.js** (v18+) and npm
- **Python** (v3.9+) and pip
- **Git** for version control

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/floatchat.git
cd floatchat
```

### 2. Frontend Setup
```bash
# Install dependencies
npm install

# Copy environment template
cp .env.example .env.local

# Start development server
npm run dev
```
Frontend will be available at `http://localhost:8081`

### 3. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install fastapi uvicorn python-dotenv pydantic pydantic-settings

# Copy environment template
cp .env.example .env

# Start backend server
python -m uvicorn app.main_simple:app --reload --host 0.0.0.0 --port 8000
```
Backend API will be available at `http://localhost:8000`

### 4. Access Application
Open your browser and navigate to `http://localhost:8081` to start exploring!

## 🛠️ Technology Stack

### Frontend
- **⚛️ React 18** - Modern UI library
- **📘 TypeScript** - Type-safe development
- **⚡ Vite** - Fast build tool and dev server
- **🎨 Tailwind CSS** - Utility-first styling
- **🗺️ Leaflet** - Interactive maps
- **🎯 Shadcn/ui** - Beautiful UI components
- **🔄 TanStack Query** - Data fetching and caching

### Backend
- **🚀 FastAPI** - Modern Python web framework
- **🐍 Python 3.9+** - Core language
- **📊 Pydantic** - Data validation and serialization
- **🌐 CORS Middleware** - Cross-origin resource sharing
- **📡 Uvicorn** - ASGI server

### Development Tools
- **📦 npm/yarn** - Package management
- **🔧 ESLint** - Code linting
- **💅 Prettier** - Code formatting
- **🔄 Hot Reload** - Development experience

## 📡 API Endpoints

### Core Endpoints
- `GET /health` - Health check
- `GET /api/v1/floats` - List all floats with pagination
- `GET /api/v1/float/{wmo_id}` - Get detailed float data
- `POST /api/v1/query` - AI-powered natural language queries

### Example API Usage
```javascript
// Fetch all floats
const response = await fetch('http://localhost:8000/api/v1/floats?size=50');
const data = await response.json();

// AI query
const aiResponse = await fetch('http://localhost:8000/api/v1/query', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ 
    question: "Show me temperature data from the Pacific Ocean" 
  })
});
```

## 🎮 Usage Examples

### Natural Language Queries
Try these example queries in the chat interface:

```
🌊 "Show me temperature data from the Pacific Ocean"
🌡️ "Find floats with salinity measurements"
🫧 "What are oxygen levels in the Atlantic?"
📊 "Compare active vs inactive floats"
🗺️ "Show floats near the equator"
```

### Map Interactions
- **Click markers** to view float details
- **Zoom in/out** to explore regions
- **Pan around** to see global distribution
- **Use controls** for better navigation

## 🔧 Configuration

### Environment Variables

#### Frontend (.env.local)
```env
VITE_API_URL=http://localhost:8000
VITE_API_TIMEOUT=30000
VITE_API_DEBUG=false
```

#### Backend (.env)
```env
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:8081"]
```

## 🚢 Deployment

### Frontend Deployment
```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

### Backend Deployment
```bash
# Production server
uvicorn app.main_simple:app --host 0.0.0.0 --port 8000
```

### Docker Support
```bash
# Build and run with Docker
docker-compose up --build
```

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Guidelines
- Follow TypeScript best practices
- Write meaningful commit messages
- Add tests for new features
- Update documentation as needed

## 📊 Data Sources

FloatChat integrates with various oceanographic data sources:
- **Argo Float Network** - Global ocean profiling
- **Real-time Measurements** - Temperature, salinity, oxygen
- **Quality Controlled Data** - Validated scientific measurements

## 🔒 Security

- **CORS Protection** - Configured for development and production
- **Input Validation** - Pydantic schemas for API security
- **Error Handling** - Graceful error management
- **Rate Limiting** - API protection (configurable)

## 📈 Performance

- **Lazy Loading** - Components load on demand
- **API Caching** - Efficient data fetching
- **Optimized Rendering** - React best practices
- **Responsive Design** - Works on all devices

## 🐛 Troubleshooting

### Common Issues

**Frontend not loading?**
- Check if backend is running on port 8000
- Verify CORS settings in backend
- Check browser console for errors

**API errors?**
- Ensure backend dependencies are installed
- Check environment variables
- Verify API endpoints are accessible

**Map not showing floats?**
- Check browser console for coordinate errors
- Verify API is returning valid data
- Ensure Leaflet CSS is loaded

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Argo Program** - Global ocean observing system
- **Leaflet** - Open-source mapping library
- **FastAPI** - Modern Python web framework
- **React Community** - Amazing ecosystem and tools

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/floatchat/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/floatchat/discussions)
- **Email**: support@floatchat.dev

---

**Built with ❤️ for ocean science and data visualization**

🌊 **Explore the oceans. Discover insights. Make waves.** 🌊
