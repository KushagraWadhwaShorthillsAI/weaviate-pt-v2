#!/bin/bash
echo "Restoring all collections sequentially..."

for i in 1 2 3 4 5 6 7 8 9; do
  echo ""
  echo "═══════════════════════════════════════"
  echo "Restoring collection $i of 9"
  echo "═══════════════════════════════════════"
  echo "Note: Select collection $i when prompted"
  echo ""
  python restore_v4.py
  echo ""
  echo "Press Enter when restore complete, or Ctrl+C to stop"
  read
done

echo "✅ All collections restored!"
