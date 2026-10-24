
// =========================================================================
// API Configuration (Environment-aware with local fallback)
// =========================================================================

const API_BASE = window.API_BASE_URL || "http://127.0.0.1:8000";
const API = `${API_BASE}/students`;
const AI_HEALTH_API = `${API_BASE}/api/ai/health`;
const AI_METRICS_API = `${API_BASE}/api/ai/model-metrics`;
const AI_PREDICT_API = `${API_BASE}/api/ai/benchmark-predict`;
const AI_ANALYZE_API = `${API_BASE}/api/ai/college/analyze-dataset`;


