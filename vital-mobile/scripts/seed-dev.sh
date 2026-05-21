#!/usr/bin/env bash
# Seed the dev API with test data for the Today screen.
# Usage: bash scripts/seed-dev.sh [BASE_URL]
# After running, set EXPO_PUBLIC_DEV_DEVICE_ID=vital-dev-seed-001 in .env
# to have the app use this data.
set -euo pipefail

BASE="${1:-http://localhost:8000}"
DEVICE="vital-dev-seed-001"

echo "Seeding $BASE with device=$DEVICE"

# ── 1. Create guest user ──────────────────────────────────────────────────────
curl -sf -X POST "$BASE/v1/users/guest" \
  -H "X-Device-Id: $DEVICE" > /dev/null
echo "✓ User created"

# ── 2. Medication — Metformin 500mg, 2x daily ─────────────────────────────────
MED_ID=$(curl -sf -X POST "$BASE/v1/wellness/tracked-items/" \
  -H "X-Device-Id: $DEVICE" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "medication",
    "name": "Metformin 500mg",
    "metadata": {
      "drug_name": "Metformin",
      "dosage": "500mg",
      "form": "tablet",
      "with_food": true
    },
    "start_date": "2026-05-01"
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "✓ Medication created: $MED_ID"

curl -sf -X POST "$BASE/v1/wellness/tracked-items/$MED_ID/reminders" \
  -H "X-Device-Id: $DEVICE" \
  -H "Content-Type: application/json" \
  -d '{
    "schedule": {
      "type": "recurring",
      "times": ["08:00", "20:00"],
      "days_of_week": ["mon","tue","wed","thu","fri","sat","sun"],
      "start_date": "2026-05-01",
      "timezone": "Asia/Kolkata"
    },
    "message_template": "Take {drug_name} {dosage}"
  }' > /dev/null
echo "✓ Medication reminder set (08:00 and 20:00 IST)"

# ── 3. Water — 2.5L daily target, every 2h 8am–10pm ─────────────────────────
WATER_ID=$(curl -sf -X POST "$BASE/v1/wellness/tracked-items/" \
  -H "X-Device-Id: $DEVICE" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "water",
    "name": "Daily Hydration",
    "metadata": {
      "daily_target_ml": 2500,
      "glass_size_ml": 250
    },
    "start_date": "2026-05-01"
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "✓ Water item created: $WATER_ID"

curl -sf -X POST "$BASE/v1/wellness/tracked-items/$WATER_ID/reminders" \
  -H "X-Device-Id: $DEVICE" \
  -H "Content-Type: application/json" \
  -d '{
    "schedule": {
      "type": "interval",
      "interval_minutes": 120,
      "active_window": {"start": "08:00", "end": "22:00"},
      "days_of_week": ["mon","tue","wed","thu","fri","sat","sun"],
      "start_date": "2026-05-01",
      "timezone": "Asia/Kolkata"
    },
    "message_template": "Drink {glass_size_ml} ml of water"
  }' > /dev/null
echo "✓ Water reminder set (every 2h, 08:00–22:00 IST)"

# ── 4. Weight measurements — 5 readings over 14 days ─────────────────────────
WEIGHTS=("72.8" "72.5" "72.3" "72.1" "71.9")
OFFSETS=(13 10 7 4 1)

for i in "${!WEIGHTS[@]}"; do
  OFFSET=${OFFSETS[$i]}
  WEIGHT=${WEIGHTS[$i]}
  TS=$(python3 -c "
from datetime import datetime, timedelta, timezone
d = datetime.now(timezone.utc) - timedelta(days=$OFFSET)
d = d.replace(hour=8, minute=0, second=0, microsecond=0)
print(d.isoformat())
")
  curl -sf -X POST "$BASE/v1/wellness/measurements/" \
    -H "X-Device-Id: $DEVICE" \
    -H "Content-Type: application/json" \
    -d "{\"type\":\"weight\",\"value\":\"$WEIGHT\",\"unit\":\"kg\",\"measured_at\":\"$TS\"}" > /dev/null
  echo "✓ Weight $WEIGHT kg on $(echo $TS | cut -c1-10)"
done

echo ""
echo "Seed complete."
echo ""
echo "To use this data in the app:"
echo "  Add to .env:  EXPO_PUBLIC_DEV_DEVICE_ID=$DEVICE"
echo "  Or run:       echo 'EXPO_PUBLIC_DEV_DEVICE_ID=$DEVICE' >> .env"
