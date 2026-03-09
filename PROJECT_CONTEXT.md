# TrueSignal Project Context - Master Document
**Last Updated:** February 7, 2026  
**Purpose:** Brief new AI assistants on project state when starting fresh chat sessions

---

## 🎯 Project Overview

**TrueSignal** - Predictive Maintenance Analytics SaaS Platform
- Analyzes maintenance work order data to predict asset failures
- Provides PM optimization suggestions  
- Generates actionable maintenance insights
- Target: Small-to-medium manufacturing/facilities teams using MaintainX

---

## 📊 Current State Summary

### What's Working ✅
1. Backend FastAPI server with prediction engine
2. Frontend React dashboard displaying data
3. Database storing predictions, insights, and KPIs
4. CORS configured between frontend/backend
5. Basic dashboard with 4 summary cards, KPI table, insights panel, high-risk assets

### Current Issue ⚠️
- Insights endpoint returns 3 records but all have identical content (Thursday work pattern)
- Only ONE insight type being generated: `day_of_week_pattern`
- Need to add 5 more insight detection functions to generate diverse insights

### In Progress 🚧
- Adding new insight detection functions to `predictive_analytics.py`
- Updating frontend to properly display insight dates and types
- Planning feature additions and launch preparation

---

## 🏗️ Architecture

```
TrueSignal/
├── backend/
│   ├── api.py                      # Main FastAPI app (runs on :8000)
│   ├── api_predictions.py          # Prediction endpoints (/predictions/*)
│   ├── predictive_analytics.py     # Core analytics logic ⚠️ NEEDS UPDATE
│   ├── prediction_storage.py       # Database operations
│   ├── calculate_kpis.py           # KPI calculations
│   ├── pipeline.py                 # Full data pipeline
│   └── load_and_map_data.py        # Data loading utilities
│
├── frontend/
│   └── src/
│       ├── App.jsx                 # Root component
│       ├── components/
│       │   └── Dashboard.jsx       # Main dashboard ⚠️ NEEDS UPDATE
│       └── services/
│           └── api.js              # API client ⚠️ NEEDS UPDATE
│
└── data/db/
    └── truesignal.db               # SQLite database
```

---

## 🔌 API Endpoints

### Base URL: `http://localhost:8000`

**Predictions:**
- `GET /predictions/insights` - Get maintenance insights
- `GET /predictions/insights/high-impact` - High-impact insights only
- `GET /predictions/failures` - Asset failure predictions
- `GET /predictions/failures/high-risk` - High-risk assets
- `GET /predictions/pm-optimization` - PM schedule suggestions
- `GET /predictions/dashboard` - All data in one call
- `GET /predictions/summary` - Summary statistics

**KPIs:**
- `GET /kpis/daily` - Daily KPI metrics

---

## 📋 Database Schema

### Tables
1. **asset_failure_predictions**
   - Stores failure probability predictions per asset
   - Fields: asset_id, failure_probability, risk_level, recommendation, etc.

2. **pm_optimization_suggestions**
   - PM schedule optimization suggestions
   - Fields: asset_id, current/suggested frequency, cost savings, etc.

3. **maintenance_insights**
   - Actionable insights from pattern detection
   - Fields: insight_type, title, description, impact_level, confidence_score
   - ⚠️ Currently only contains "day_of_week_pattern" insights

4. **kpi_daily**
   - Daily KPI metrics with raw vs TrueSignal values
   - Fields: name, raw_value, truesignal_value, distortion_flag

---

## 🔧 Tech Stack

### Backend
- **Python 3.9+**
- **FastAPI** - Web framework
- **Pandas** - Data analysis
- **SQLite** - Database (will migrate to PostgreSQL/MySQL for production)
- **Uvicorn** - ASGI server

### Frontend
- **React 18**
- **Vite** - Build tool
- **Tailwind CSS 3.4** - Styling
- **Axios** - HTTP client
- **Lucide React** - Icons

---

## 🚀 Quick Start Commands

### Backend
```bash
cd backend
python api.py  # Starts FastAPI on http://localhost:8000
```

### Frontend
```bash
cd frontend
npm run dev  # Starts Vite dev server on http://localhost:5173
```

### Regenerate Predictions
```bash
cd backend
python pipeline.py  # Runs full analytics pipeline
```

---

## 📝 Git Commits (Recent)

```
[Include output of: git log --oneline -10]
```

---

## ⚠️ Known Issues & Next Steps

### Immediate (Current Session)
1. **Fix duplicate insights**
   - Add 5 new detection functions to `predictive_analytics.py`
   - Functions needed: detect_high_failure_assets, detect_cost_saving_opportunities, detect_pm_coverage_gaps, detect_workload_imbalances, detect_recurring_issues
   - Update `generate_maintenance_insights()` to call all 8 functions

2. **Update frontend files**
   - Replace `api.js` with version that has `/predictions/` prefix
   - Replace `Dashboard.jsx` with version that shows insight dates

### Roadmap to Launch
- [ ] Complete frontend visual improvements
- [ ] Add charts/visualizations
- [ ] Integrate with MaintainX API
- [ ] Migrate to production SQL database (PostgreSQL/MySQL)
- [ ] Implement user authentication/login
- [ ] Multi-tenant support
- [ ] Domain purchase & SSL setup
- [ ] Legal: Terms of Service, Privacy Policy, copyright
- [ ] Billing integration (Stripe)
- [ ] Email notifications
- [ ] Export functionality (PDF reports)

---

## 💡 Important Context for New Chats

### When You See This Document:
1. Review "Current State Summary" section first
2. Check "Known Issues & Next Steps" for what we were working on
3. Review recent git commits to see latest changes
4. Ask user if anything has changed since last session

### Common Questions to Ask:
- "Did you make the changes from the last session?"
- "Are there any new errors or issues?"
- "What would you like to work on next?"

### Files User Will Share:
When starting new chat, user should upload:
1. This context document (PROJECT_CONTEXT.md)
2. Relevant code files if working on specific features
3. Error logs if debugging

---

## 📊 Current Metrics (Approximate)

- **Lines of Code:** ~5,000 (backend) + ~500 (frontend)
- **API Endpoints:** 15+
- **Data Pipeline Steps:** 7
- **Insight Types:** 3 (need to expand to 8+)
- **Test Coverage:** Minimal (needs improvement)

---

## 🎨 Design System

### Colors
- Primary: Blue (#007bff)
- Success: Green (#28a745)
- Warning: Orange/Yellow (#ffc107)
- Danger: Red (#dc3545)

### Components
- Summary cards with icons
- Data tables with hover states
- Insight cards with impact badges
- Risk level badges (LOW/MEDIUM/HIGH/CRITICAL)

---

## 🔐 Security Notes

- Currently no authentication (development only)
- CORS enabled for localhost:5173
- Database is local SQLite (not production-ready)
- No API rate limiting yet
- No input validation on most endpoints

---

## 📚 Resources

### Documentation Locations
- API docs (auto-generated): `http://localhost:8000/docs`
- Frontend components: `frontend/src/components/`
- Backend modules: `backend/`

### External Dependencies
- MaintainX API docs (for future integration)
- Anthropic Claude API (for AI-powered features - future)

---

## 🎯 Product Vision

**Short-term (MVP - Next 2 weeks):**
- Functional dashboard with diverse insights
- Reliable predictions
- Clean, professional UI

**Medium-term (Beta - Next 1-2 months):**
- MaintainX integration
- User authentication
- Production database
- Domain & hosting

**Long-term (v1.0 - 3-6 months):**
- Multi-tenant SaaS
- Billing system
- Advanced visualizations
- Mobile app
- AI-powered recommendations

---

## 💬 Communication Protocol for New Chats

**When starting a new chat session:**

1. Upload this document first
2. State what you were working on last
3. Mention any changes made since last session
4. Ask specific question or state goal

**Example opening message:**
> "I'm working on TrueSignal (see attached PROJECT_CONTEXT.md). Last session we were fixing duplicate insights. I've added the new detection functions to predictive_analytics.py. Now I need help with [next task]."

---

**End of Context Document**  
*Update this file after significant changes or milestones*
