#!/bin/bash
# Phase 10 End-to-End Test — PDF Export, Global Exception Handling, and Documentation
set -e
source "/Users/sumit/Desktop/ATS project/venv/bin/activate"
BASE="http://localhost:8000"

echo "=========================================================="
echo "  Phase 10: Polish, PDF Export & Error Handling Test      "
echo "=========================================================="
echo ""

# ── Step 1: Health check ──
echo "=== 1. HEALTH CHECK ==="
curl -s "$BASE/health" | python3 -m json.tool
echo "✅ Health check passed"
echo ""

# ── Step 2: Register + Login ──
echo "=== 2. AUTHENTICATION ==="
curl -s -X POST "$BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "phase10_user@example.com", "password": "securepass123"}' > /dev/null || true

TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "phase10_user@example.com", "password": "securepass123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "✅ Logged in successfully"
echo ""

# ── Step 3: Setup Resume & Job ──
echo "=== 3. SETUP RESUME AND JOB FOR MATCH REPORT ==="
if [ ! -f "test_resume.pdf" ]; then
  python3 /Users/sumit/.gemini/antigravity-ide/brain/8adc6f12-1b1a-414c-a4a1-1b1a4efc000c/scratch/generate_test_resume.py
fi

RESUME_RESP=$(curl -s -X POST "$BASE/resumes" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_resume.pdf")
RESUME_ID=$(echo "$RESUME_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

JOB_RESP=$(curl -s -X POST "$BASE/jobs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Principal Distributed Systems Engineer",
    "company": "ScaleCloud Systems",
    "raw_text": "Seeking a Principal Engineer with expertise in Python, FastAPI, PostgreSQL, Redis, Celery, Kubernetes, and Kafka."
  }')
JOB_ID=$(echo "$JOB_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "Resume ID: $RESUME_ID, Job ID: $JOB_ID"

# Wait for embeddings
for i in {1..15}; do
  R_READY=$(curl -s "$BASE/resumes/$RESUME_ID/status" -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)['has_embedding'])")
  J_READY=$(curl -s "$BASE/jobs/$JOB_ID/status" -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)['has_embedding'])")
  if [ "$R_READY" = "True" ] && [ "$J_READY" = "True" ]; then
    echo "✅ Embeddings ready"
    break
  fi
  sleep 1
done

# Run match with feedback
MATCH_RESP=$(curl -s -X POST "$BASE/match/$RESUME_ID/$JOB_ID?generate_feedback=true" -H "Authorization: Bearer $TOKEN")
MATCH_ID=$(echo "$MATCH_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
SCORE=$(echo "$MATCH_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['overall_score'])")
echo "Match Created: ID $MATCH_ID (Score: $SCORE%)"
echo ""

# ── Step 4: Test PDF Export ──
echo "=== 4. TEST PDF REPORT EXPORT (/matches/$MATCH_ID/export-pdf) ==="
PDF_HEADERS=$(curl -s -D - -o /dev/null -X GET "$BASE/matches/$MATCH_ID/export-pdf" -H "Authorization: Bearer $TOKEN")
echo "$PDF_HEADERS"

CONTENT_TYPE=$(echo "$PDF_HEADERS" | grep -i "content-type" || true)
CONTENT_DISP=$(echo "$PDF_HEADERS" | grep -i "content-disposition" || true)

if ! echo "$CONTENT_TYPE" | grep -qi "application/pdf"; then
  echo "❌ Expected Content-Type application/pdf"
  exit 1
fi

# Download PDF file and verify magic bytes
curl -s "$BASE/matches/$MATCH_ID/export-pdf" -H "Authorization: Bearer $TOKEN" -o "downloaded_report.pdf"
FILE_SIZE=$(wc -c < "downloaded_report.pdf")
echo "Downloaded PDF file size: $FILE_SIZE bytes"

if [ "$FILE_SIZE" -lt 2000 ]; then
  echo "❌ PDF file size unexpectedly small"
  exit 1
fi

HEAD_BYTES=$(head -c 5 "downloaded_report.pdf")
if [ "$HEAD_BYTES" != "%PDF-" ]; then
  echo "❌ File does not begin with valid PDF magic bytes"
  exit 1
fi
echo "✅ PDF report generated and validated successfully!"
echo ""

# ── Step 5: Test Global Exception Handlers ──
echo "=== 5. TEST GLOBAL EXCEPTION HANDLERS ==="

# 5a. Validation Error (422)
echo "Testing 422 validation error envelope:"
VAL_ERROR=$(curl -s -X POST "$BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"invalid_field": 123}')
echo "$VAL_ERROR" | python3 -m json.tool
VAL_TYPE=$(echo "$VAL_ERROR" | python3 -c "import sys,json; print(json.load(sys.stdin).get('type'))")
if [ "$VAL_TYPE" != "validation_error" ]; then
  echo "❌ Validation error handler did not produce expected envelope"
  exit 1
fi
echo "✅ 422 Validation error handler verified!"

# 5b. HTTP Error (404)
echo "Testing 404 HTTP error envelope:"
NOT_FOUND_ERROR=$(curl -s "$BASE/matches/999999" -H "Authorization: Bearer $TOKEN")
echo "$NOT_FOUND_ERROR" | python3 -m json.tool
NF_TYPE=$(echo "$NOT_FOUND_ERROR" | python3 -c "import sys,json; print(json.load(sys.stdin).get('type'))")
if [ "$NF_TYPE" != "http_error" ]; then
  echo "❌ HTTP 404 error handler did not produce expected envelope"
  exit 1
fi
echo "✅ 404 HTTP error handler verified!"
echo ""

# ── Step 6: Verify Documentation Files ──
echo "=== 6. VERIFY DOCUMENTATION FILES ==="
for file in "decisions.md" "decision.md" "flow.md" "README.md"; do
  if [ -f "$file" ]; then
    LINES=$(wc -l < "$file")
    echo "✅ $file exists ($LINES lines)"
  else
    echo "❌ Missing documentation file: $file"
    exit 1
  fi
done
echo ""

echo "=========================================================="
echo "  ✅ ALL PHASE 10 POLISH & EXPORT TESTS PASSED!           "
echo "=========================================================="
