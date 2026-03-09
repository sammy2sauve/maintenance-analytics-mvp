# TrueSignal Project Snapshot
Generated: Sat Feb  7 19:46:25 EST 2026

## 1. Git Status & Recent Commits
```
f621227 Add frontend dashboard with CORS support
90efee5 Complete predictive analytics integration with duplicate prevention
a60eb73 Integrate predictive analytics into pipeline, fix imports
f2873c4 Fix pipeline execution and add prediction output support
e4681d1 Add complete predictive analytics system with API endpoints
9193a61 Add predictive analytics module with failure prediction and PM optimization
339decb Fix KPI table schema and add comprehensive diagnostics
a48e8e3 Fixing issues
ecafbbd Add create_db.py script to generate truesignal.db with dummy work orders
dfbaaf9 Add backend API test script for daily, weekly, and monthly KPI endpoints
8d95ff9 Add FastAPI API and database access layer
22ed6fe Add end-to-end KPI pipeline runner
45d133b Add SQLite persistence layer for KPI outputs
3391415 Add KPI calculation module with daily, weekly, and monthly TrueSignal metrics
67c39fe Add backend module to load and map data from SQL
8182f81 Add backend, frontend, and docs directories for MVP structure
b518037 Initial commit
```

## 2. Project Structure
```
./.gitignore
./backend/api.py
./backend/api_predictions.py
./backend/calculate_kpis.py
./backend/create_db.py
./backend/create_kpi_tables.py
./backend/create_prediction_tables.py
./backend/db.py
./backend/diagnose_kpi_tables.py
./backend/fix_kpi_schema.py
./backend/kpi_storage.py
./backend/load_and_map_data.py
./backend/pipeline.py
./backend/prediction_storage.py
./backend/predictive_analytics.py
./backend/python diagnose_kpi_tables.py
./backend/README.md
./backend/test_backend.py
./backend/__init__.py
./create_project_snapshot.sh
./data/db/truesignal.db
./docs/ARCHITECTURE.md
./frontend/.gitignore
./frontend/eslint.config.js
./frontend/index.html
./frontend/package-lock.json
./frontend/package.json
./frontend/postcss.config.js
./frontend/public/vite.svg
./frontend/README.md
./frontend/src/App.css
./frontend/src/App.jsx
./frontend/src/index.css
./frontend/src/main.jsx
./frontend/tailwind.config.js
./frontend/vite.config.js
./LAUNCH_ROADMAP.md
./PROJECT_CONTEXT.md
./PROJECT_SNAPSHOT_20260207_194625.md
./README.md
./__init__.py
```

## 3. Current Tech Stack
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


## 4. Key Files & Their Purpose
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

## 5. Recent Changes & Current Issues
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

## 6. Environment Setup
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


## 7. Package Versions
### Backend (requirements.txt)
```
requirements.txt not found
```

### Frontend (package.json dependencies)
```json
package.json not found
```

---
End of snapshot. Use this to brief new AI assistants on project state.
