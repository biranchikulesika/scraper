#!/bin/bash

DISTRICT=("Koraput")
# insert multiple districts as need
# Ex DISTRICT=("Koraput" "Khurda" "Balasore")
SCHOOL=("")
# insert college names in the same way we did with DISTRICT
START=2024
END=2026

for year in {$START..$END}; do
    echo "Running for year: $year"
    python scraper.py "$year" "$DISTRICT" "$SCHOOL"

    if [ $? -ne 0 ]; then
        echo "❌ Failed for year: $year"
    else
        echo "✅ Completed for year: $year"
    fi

    echo "-----------------------------"
done

echo "All years processed."
