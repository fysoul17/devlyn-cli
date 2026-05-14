#!/usr/bin/env bash
# Shared rejected/ceiling pair-candidate fixture registry.
# Includes active fixtures and calibrated shadow controls that should not spend
# pair-candidate runs unless explicitly requested for diagnostics.

rejected_pair_fixture_reason() {
  local fid="$1"
  case "$fid" in
    F1-*|F1)
      echo "trivial calibration fixture; every arm is expected to one-shot it"
      ;;
    F2-*|F2)
      echo "bare 83 / solo_claude 95 in 20260512-f2-medium-headroom"
      ;;
    F3-*|F3)
      echo "bare 97 / solo_claude 99 in 20260511-f3-http-error-headroom"
      ;;
    F4-*|F4)
      echo "bare 70 / solo_claude 92 with bare disqualifier in 20260512-f4-web-headroom"
      ;;
    F5-*|F5)
      echo "bare 99 / solo_claude 99 in 20260512-f5-fixloop-headroom"
      ;;
    F6-*|F6)
      echo "bare 97 / solo_claude 96 in 20260512-f6-checksum-headroom"
      ;;
    F7-*|F7)
      echo "bare 99 / solo_claude 100 in 20260512-f7-scope-headroom"
      ;;
    F8-*|F8)
      echo "known-limit ambiguity fixture; expected margin is [-3,+3], not pair-lift evidence"
      ;;
    F9-*|F9)
      echo "bare 60 / solo_claude 90 with bare headroom 0 and bare judge disqualifier in 20260512-f9-e2e-headroom"
      ;;
    F10-*|F10)
      echo "bare 75 / solo_claude 94 in 20260507-f10-f11-tier1-full-pipeline"
      ;;
    F11-*|F11)
      echo "bare 98 / solo_claude 97 in 20260507-f10-f11-tier1-full-pipeline"
      ;;
    F12-*|F12)
      echo "bare 85 / solo_claude 99 in 20260511-f12-webhook-headroom"
      ;;
    F15-*|F15)
      echo "bare 99 / solo_claude 94 in 20260511-f15-concurrency-headroom"
      ;;
    F22-*|F22)
      echo "bare 94 / solo_claude 98 in 20260508-f22-exact-error-headroom"
      ;;
    F26-*|F26)
      echo "solo_claude scored 98 in 20260508-f26-headroom"
      ;;
    F27-*|F27)
      echo "solo_claude scored 94 in 20260511-f27-headroom-smoke-061401"
      ;;
    F28-*|F28)
      echo "corrected-oracle reverify scored solo_claude 98 in 20260511-f28-policy-oraclefix-reverified-pair"
      ;;
    F29-*|F29)
      echo "corrected headroom scored solo_claude 92 in 20260510-f29-headroom-v2"
      ;;
    F30-*|F30)
      echo "solo_claude scored 98 in 20260511-f30-headroom-v1"
      ;;
    F31-*|F31)
      echo "solo_claude scored 98 with bare disqualifiers in 20260512-f31-seat-rebalance-headroom"
      ;;
    F32-*|F32)
      echo "bare 33 / solo_claude 98 in 20260512-f32-subscription-renewal-headroom"
      ;;
    S2-*|S2)
      echo "bare 33 / solo_claude 99 with solo timeout in 20260513-s2-inventory-headroom"
      ;;
    S3-*|S3)
      echo "bare 33 / solo_claude 99 with solo timeout in 20260513-s3-ticket-headroom"
      ;;
    S4-*|S4)
      echo "bare 33 / solo_claude 98 with solo timeout in 20260513-s4-return-headroom"
      ;;
    S5-*|S5)
      echo "bare 33 / solo_claude 98 with solo timeout in 20260513-s5-credit-headroom"
      ;;
    S6-*|S6)
      echo "bare 33 / solo_claude 98 with solo timeout in 20260514-s6-refund-headroom-v1"
      ;;
    *)
      return 1
      ;;
  esac
}
