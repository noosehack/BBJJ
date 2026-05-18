#!/bin/bash
# Run all matboard kernel regression tests

BLISP=/home/ubuntu/blisp/target/release/blisp
MATBOARD=/home/ubuntu/BBJJ/matboard
TESTS=/home/ubuntu/BBJJ/tests/matboard

LOAD="--load $MATBOARD/types.blisp \
      --load $MATBOARD/radicals.blisp \
      --load $MATBOARD/morphisms.blisp \
      --load $MATBOARD/resolve.blisp \
      --load $MATBOARD/footprints.blisp"

TOTAL_PASS=0
TOTAL_FAIL=0
SUITES=0

for test in $TESTS/test_*.blisp; do
    echo ""
    SUITES=$((SUITES + 1))
    OUTPUT=$($BLISP $LOAD --load "$test" -e 'nil' 2>&1 | grep -v "Running in HYBRID\|^nil$")
    echo "$OUTPUT"
    PASS=$(echo "$OUTPUT" | grep -c "PASS:")
    FAIL=$(echo "$OUTPUT" | grep -c "FAIL:")
    TOTAL_PASS=$((TOTAL_PASS + PASS))
    TOTAL_FAIL=$((TOTAL_FAIL + FAIL))
done

echo ""
echo "================================================================"
echo "TOTAL: $SUITES suites, $TOTAL_PASS passed, $TOTAL_FAIL failed"
if [ $TOTAL_FAIL -eq 0 ]; then
    echo "STATUS: ALL PASS"
else
    echo "STATUS: FAILURES DETECTED"
    exit 1
fi
