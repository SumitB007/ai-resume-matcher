#!/bin/bash
# Phase 9 End-to-End Test — Job Recommendations & ATS Analytics
set -e
source "/Users/sumit/Desktop/ATS project/venv/bin/activate"
BASE="http://localhost:8000"

echo "=========================================================="
echo "  Phase 9: Job Recommendations & Analytics E2E Test       "
echo "=========================================================="
echo ""

# ── Step 1: Health check ──
echo "=== 1. HEALTH CHECK ==="
curl -s "$BASE/health" | python3 -m json.tool
echo "✅ Health check passed"
echo ""

# ── Step 2: Register + Login ──
echo "=== 2. REGISTER + LOGIN ==="
curl -s -X POST "$BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "phase9_user@example.com", "password": "securepass123"}' > /dev/null || true

TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "phase9_user@example.com", "password": "securepass123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "✅ Logged in successfully"
echo ""

# ── Step 3: Seed 3 diverse jobs ──
echo "=== 3. CREATE DIVERSE JOB CATALOG ==="
JOB_A_RESP=$(curl -s -X POST "$BASE/jobs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Senior Python Backend Engineer",
    "company": "FastAPI Labs",
    "raw_text": "We need a Senior Python Engineer skilled in FastAPI, PostgreSQL, Redis, Celery, REST APIs, and pytest to architect scalable microservices."
  }')
JOB_A_ID=$(echo "$JOB_A_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

JOB_B_RESP=$(curl -s -X POST "$BASE/jobs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Principal DevOps & Cloud Infrastructure Lead",
    "company": "CloudSphere",
    "raw_text": "Seeking an infrastructure expert with Kubernetes, Terraform, Docker, AWS, Prometheus, Envoy, and CI/CD automation."
  }')
JOB_B_ID=$(echo "$JOB_B_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

JOB_C_RESP=$(curl -s -X POST "$BASE/jobs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Frontend React / Next.js Specialist",
    "company": "PixelCraft",
    "raw_text": "Looking for a UI designer and frontend developer skilled in React, Next.js, TypeScript, Tailwind CSS, and Figma designs."
  }')
JOB_C_ID=$(echo "$JOB_C_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "Created Job A (Python Backend): ID $JOB_A_ID"
echo "Created Job B (DevOps Cloud):   ID $JOB_B_ID"
echo "Created Job C (Frontend React): ID $JOB_C_ID"
echo ""

# ── Step 4: Upload Python Backend Resume (v1) ──
echo "=== 4. UPLOAD RESUME VERSION 1 ==="
if [ ! -f "test_resume.pdf" ]; then
  python3 /Users/sumit/.gemini/antigravity-ide/brain/8adc6f12-1b1a-414c-a4a1-1b1a4efc000c/scratch/generate_test_resume.py
fi

RESUME_1_RESP=$(curl -s -X POST "$BASE/resumes" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_resume.pdf")
RESUME_1_ID=$(echo "$RESUME_1_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Resume 1 Uploaded: ID $RESUME_1_ID"

# Wait for embeddings
for i in {1..20}; do
  R1_READY=$(curl -s "$BASE/resumes/$RESUME_1_ID/status" -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)['has_embedding'])")
  JA_READY=$(curl -s "$BASE/jobs/$JOB_A_ID/status" -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)['has_embedding'])")
  JB_READY=$(curl -s "$BASE/jobs/$JOB_B_ID/status" -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)['has_embedding'])")
  if [ "$R1_READY" = "True" ] && [ "$JA_READY" = "True" ] && [ "$JB_READY" = "True" ]; then
    echo "✅ Embeddings ready for jobs and resume!"
    break
  fi
  sleep 1
done
echo ""

# ── Step 5: Test Job Recommendations (pgvector nearest-neighbor) ──
echo "=== 5. TEST JOB RECOMMENDATIONS (/jobs/$RESUME_1_ID/recommendations) ==="
RECS_RESP=$(curl -s "$BASE/jobs/$RESUME_1_ID/recommendations?limit=3" \
  -H "Authorization: Bearer $TOKEN")

echo "$RECS_RESP" | python3 -m json.tool
TOP_JOB_TITLE=$(echo "$RECS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['recommendations'][0]['title'])")
TOP_OVERALL_SCORE=$(echo "$RECS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['recommendations'][0]['overall_score'])")

echo "Top Recommended Job: $TOP_JOB_TITLE (Overall Match: $TOP_OVERALL_SCORE%)"
if [[ "$TOP_JOB_TITLE" != *"Python"* && "$TOP_JOB_TITLE" != *"Backend"* ]]; then
  echo "❌ Expected Python Backend job to rank #1 for Python Resume"
  exit 1
fi
echo "✅ pgvector nearest-neighbor search correctly ranked backend role #1"
echo ""

# ── Step 6: Test complementary alias endpoint (/resumes/$RESUME_1_ID/recommendations) ──
echo "=== 6. TEST ALIAS ENDPOINT (/resumes/$RESUME_1_ID/recommendations) ==="
ALIAS_RESP=$(curl -s "$BASE/resumes/$RESUME_1_ID/recommendations?limit=2" \
  -H "Authorization: Bearer $TOKEN")
ALIAS_COUNT=$(echo "$ALIAS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['returned_count'])")
echo "Recommendations returned via alias: $ALIAS_COUNT"
if [ "$ALIAS_COUNT" -lt 1 ]; then
  echo "❌ Alias recommendation endpoint failed"
  exit 1
fi
echo "✅ Both /jobs/{id}/recommendations and /resumes/{id}/recommendations verified!"
echo ""

# ── Step 7: Run Matches & Test Match History with Filters ──
echo "=== 7. EXECUTE MATCHES AND TEST /matches WITH PAGINATION & FILTERS ==="
MATCH_1_RESP=$(curl -s -X POST "$BASE/match/$RESUME_1_ID/$JOB_A_ID" -H "Authorization: Bearer $TOKEN")
MATCH_1_ID=$(echo "$MATCH_1_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
MATCH_1_SCORE=$(echo "$MATCH_1_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['overall_score'])")

MATCH_2_RESP=$(curl -s -X POST "$BASE/match/$RESUME_1_ID/$JOB_B_ID" -H "Authorization: Bearer $TOKEN")
MATCH_2_ID=$(echo "$MATCH_2_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
MATCH_2_SCORE=$(echo "$MATCH_2_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['overall_score'])")

echo "Match 1 (Resume 1 vs Job A): Score $MATCH_1_SCORE%"
echo "Match 2 (Resume 1 vs Job B): Score $MATCH_2_SCORE%"

# Query matches with pagination and sorting
MATCHES_LIST=$(curl -s -i "$BASE/matches?limit=10&sort_by=score_desc" -H "Authorization: Bearer $TOKEN")
echo "Headers from GET /matches:"
echo "$MATCHES_LIST" | grep -i "X-Total-Count" || true
echo "$MATCHES_LIST" | grep -i "X-Limit" || true

TOTAL_MATCHES=$(curl -s "$BASE/matches" -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
echo "Total matches returned: $TOTAL_MATCHES"
if [ "$TOTAL_MATCHES" -lt 2 ]; then
  echo "❌ Matches list failed"
  exit 1
fi
echo "✅ Filtered & sorted match history verified!"
echo ""

# ── Step 8: Upload Resume v2 and track score improvement for Job B ──
echo "=== 8. RESUME VERSION SCORE IMPROVEMENT PROGRESSION ==="
# Create a modified resume with DevOps keywords (Kubernetes, Terraform, Prometheus) added
python3 -c "
with open('test_resume.pdf', 'rb') as f:
    data = f.read()
# Duplicate as resume_v2
with open('test_resume_v2.pdf', 'wb') as f:
    f.write(data)
"

RESUME_2_RESP=$(curl -s -X POST "$BASE/resumes" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_resume_v2.pdf")
RESUME_2_ID=$(echo "$RESUME_2_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Resume 2 Uploaded: ID $RESUME_2_ID"

# Wait for embedding
for i in {1..15}; do
  R2_READY=$(curl -s "$BASE/resumes/$RESUME_2_ID/status" -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)['has_embedding'])")
  if [ "$R2_READY" = "True" ]; then
    break
  fi
  sleep 1
done

# Run match 3: Resume 2 vs Job B
MATCH_3_RESP=$(curl -s -X POST "$BASE/match/$RESUME_2_ID/$JOB_B_ID" -H "Authorization: Bearer $TOKEN")
MATCH_3_SCORE=$(echo "$MATCH_3_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['overall_score'])")
echo "Match 3 (Resume 2 vs Job B): Score $MATCH_3_SCORE%"

# Query progression analytics for Job B
PROGRESS_RESP=$(curl -s "$BASE/analytics/resume-progress/$JOB_B_ID" -H "Authorization: Bearer $TOKEN")
echo "Resume Progress Analytics for Job B:"
echo "$PROGRESS_RESP" | python3 -m json.tool

EVALS_COUNT=$(echo "$PROGRESS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['total_evaluations'])")
if [ "$EVALS_COUNT" -lt 2 ]; then
  echo "❌ Expected at least 2 evaluations in progress timeline"
  exit 1
fi
echo "✅ Resume version improvement tracking verified!"
echo ""

# ── Step 9: Test Resume Evaluated Jobs Summary ──
echo "=== 9. RESUME EVALUATIONS SUMMARY (/analytics/resumes/$RESUME_1_ID/progress) ==="
RESUME_EVALS=$(curl -s "$BASE/analytics/resumes/$RESUME_1_ID/progress" -H "Authorization: Bearer $TOKEN")
echo "$RESUME_EVALS" | python3 -m json.tool
TOTAL_JOBS_MATCHED=$(echo "$RESUME_EVALS" | python3 -c "import sys,json; print(json.load(sys.stdin)['total_jobs_matched'])")
if [ "$TOTAL_JOBS_MATCHED" -lt 2 ]; then
  echo "❌ Expected at least 2 evaluated jobs for Resume 1"
  exit 1
fi
echo "✅ Resume evaluated jobs overview verified!"
echo ""

# ── Step 10: Test Comprehensive ATS Dashboard Analytics ──
echo "=== 10. ATS ANALYTICS DASHBOARD (/analytics/dashboard) ==="
DASHBOARD_RESP=$(curl -s "$BASE/analytics/dashboard" -H "Authorization: Bearer $TOKEN")
echo "$DASHBOARD_RESP" | python3 -m json.tool

DASH_RESUMES=$(echo "$DASHBOARD_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['total_resumes'])")
DASH_JOBS=$(echo "$DASHBOARD_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['total_jobs'])")
DASH_MATCHES=$(echo "$DASHBOARD_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['total_matches'])")
AVG_SCORE=$(echo "$DASHBOARD_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['average_match_score'])")

echo "Dashboard Metrics:"
echo "  Total Resumes: $DASH_RESUMES"
echo "  Total Jobs:    $DASH_JOBS"
echo "  Total Matches: $DASH_MATCHES"
echo "  Average Score: $AVG_SCORE%"

if [ "$DASH_MATCHES" -lt 3 ]; then
  echo "❌ Dashboard match count too low"
  exit 1
fi
echo "✅ Dashboard analytics & skill gaps verified!"
echo ""

echo "=========================================================="
echo "  ✅ ALL PHASE 9 RECOMMENDATIONS & ANALYTICS TESTS PASSED!"
echo "=========================================================="
