#!/bin/bash
# Project Snapshot Generator for TrueSignal
# Run this script to create a complete project state document

SNAPSHOT_FILE="PROJECT_SNAPSHOT_$(date +%Y%m%d_%H%M%S).md"

echo "# TrueSignal Project Snapshot" > $SNAPSHOT_FILE
echo "Generated: $(date)" >> $SNAPSHOT_FILE
echo "" >> $SNAPSHOT_FILE

echo "## 1. Git Status & Recent Commits" >> $SNAPSHOT_FILE
echo '```' >> $SNAPSHOT_FILE
git log --oneline -20 >> $SNAPSHOT_FILE 2>/dev/null || echo "No git history available" >> $SNAPSHOT_FILE
echo '```' >> $SNAPSHOT_FILE
echo "" >> $SNAPSHOT_FILE

echo "## 2. Project Structure" >> $SNAPSHOT_FILE
echo '```' >> $SNAPSHOT_FILE
tree -L 3 -I 'node_modules|__pycache__|*.pyc|.git' . >> $SNAPSHOT_FILE 2>/dev/null || find . -maxdepth 3 -type f ! -path '*/node_modules/*' ! -path '*/__pycache__/*' ! -path '*/.git/*' >> $SNAPSHOT_FILE
echo '```' >> $SNAPSHOT_FILE
echo "" >> $SNAPSHOT_FILE

echo "## 3. Current Tech Stack" >> $SNAPSHOT_FILE
cat >> $SNAPSHOT_FILE << 'TECH'
### Backend
- FastAPI (Python)
- SQLite database
- Pandas for data processing
- Predictive analytics engine

### Frontend
- React + Vite
- Tailwind CSS
- Axios for API calls
- Lucide React icons

### Endpoints Structure
- `/predictions/insights` - Maintenance insights
- `/predictions/failures` - Failure predictions
- `/predictions/failures/high-risk` - High-risk assets
- `/predictions/pm-optimization` - PM suggestions
- `/predictions/dashboard` - Consolidated dashboard data
- `/kpis/daily` - Daily KPI metrics

TECH
echo "" >> $SNAPSHOT_FILE

echo "## 4. Key Files & Their Purpose" >> $SNAPSHOT_FILE
cat >> $SNAPSHOT_FILE << 'FILES'
### Backend (backend/)
- `api.py` - Main FastAPI application with CORS
- `api_predictions.py` - Prediction API endpoints
- `predictive_analytics.py` - Analytics logic (failure prediction, PM optimization, insights)
- `prediction_storage.py` - Database storage/retrieval
- `calculate_kpis.py` - KPI calculation logic
- `pipeline.py` - Data processing pipeline
- `load_and_map_data.py` - Data loading utilities

### Frontend (frontend/src/)
- `App.jsx` - Root component
- `components/Dashboard.jsx` - Main dashboard UI
- `services/api.js` - API service layer

### Database
- Location: `data/db/truesignal.db`
- Tables: asset_failure_predictions, pm_optimization_suggestions, maintenance_insights, kpi_daily
FILES
echo "" >> $SNAPSHOT_FILE

echo "## 5. Recent Changes & Current Issues" >> $SNAPSHOT_FILE
cat >> $SNAPSHOT_FILE << 'STATUS'
### Last Known State
- Frontend dashboard connected to backend
- CORS configured
- Insights endpoint returning data but only showing one type (day_of_week_pattern)
- Need to add more insight detection functions

### In Progress
- Adding 5 new insight detection functions to generate diverse insights
- Updating frontend to display insights with dates
- Fixing duplicate insights issue

### Next Steps
- Update predictive_analytics.py with new insight functions
- Replace frontend api.js and Dashboard.jsx
- Re-run pipeline.py to regenerate insights
- Test dashboard with diverse insights
STATUS
echo "" >> $SNAPSHOT_FILE

echo "## 6. Environment Setup" >> $SNAPSHOT_FILE
cat >> $SNAPSHOT_FILE << 'ENV'
### Backend Setup
```bash
cd backend
pip install -r requirements.txt
python api.py  # Runs on http://localhost:8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev  # Runs on http://localhost:5173
```
ENV
echo "" >> $SNAPSHOT_FILE

echo "" >> $SNAPSHOT_FILE
echo "## 7. Package Versions" >> $SNAPSHOT_FILE
echo "### Backend (requirements.txt)" >> $SNAPSHOT_FILE
echo '```' >> $SNAPSHOT_FILE
cat requirements.txt 2>/dev/null || echo "requirements.txt not found" >> $SNAPSHOT_FILE
echo '```' >> $SNAPSHOT_FILE
echo "" >> $SNAPSHOT_FILE

echo "### Frontend (package.json dependencies)" >> $SNAPSHOT_FILE
echo '```json' >> $SNAPSHOT_FILE
cat package.json 2>/dev/null | grep -A 20 '"dependencies"' || echo "package.json not found" >> $SNAPSHOT_FILE
echo '```' >> $SNAPSHOT_FILE

echo "" >> $SNAPSHOT_FILE
echo "---" >> $SNAPSHOT_FILE
echo "End of snapshot. Use this to brief new AI assistants on project state." >> $SNAPSHOT_FILE

echo "✅ Snapshot created: $SNAPSHOT_FILE"
cat $SNAPSHOT_FILE
