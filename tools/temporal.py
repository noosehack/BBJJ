"""Sequence-aware temporal smoothing for radical match scores.

Groups FPTRecords by video sequence (image[:2]) and applies:
1. Score smoothing over a ±k frame window
2. Persistence filter requiring N consecutive frames before label switch
"""

from collections import defaultdict
from copy import copy
from tools.annotate import FPTRecord


def group_by_sequence(records: list[FPTRecord]) -> dict[str, list[FPTRecord]]:
    sequences: dict[str, list[FPTRecord]] = defaultdict(list)
    for r in records:
        vid = r.image[:2]
        sequences[vid].append(r)
    for vid in sequences:
        sequences[vid].sort(key=lambda r: r.frame)
    return dict(sequences)


def smooth_scores(records: list[FPTRecord], k: int = 3) -> list[FPTRecord]:
    """Average per-radical scores over a ±k frame window within each sequence.
    Frames without poses (no all_matches) pass through unchanged."""
    sequences = group_by_sequence(records)
    result = []

    for vid, seq in sequences.items():
        score_vectors: list[dict[str, float]] = []
        all_radicals: set[str] = set()
        for r in seq:
            sv = {m["radical"]: m["confidence"] for m in r.all_matches}
            score_vectors.append(sv)
            all_radicals.update(sv.keys())

        for i, r in enumerate(seq):
            if not r.all_matches:
                result.append(r)
                continue

            lo = max(0, i - k)
            hi = min(len(seq), i + k + 1)
            count = 0
            totals: dict[str, float] = defaultdict(float)
            for j in range(lo, hi):
                if not score_vectors[j]:
                    continue
                count += 1
                for rad in all_radicals:
                    totals[rad] += score_vectors[j].get(rad, 0.0)

            if count == 0:
                result.append(r)
                continue

            smoothed = {rad: totals[rad] / count for rad in all_radicals}
            best_rad = max(smoothed, key=smoothed.get)
            best_conf = smoothed[best_rad]

            new_r = copy(r)
            new_r.radical_match = best_rad if best_conf > 0 else None
            new_r.match_confidence = round(best_conf, 4)
            new_r.all_matches = [
                {"radical": rad, "confidence": round(conf, 4)}
                for rad, conf in sorted(smoothed.items(), key=lambda x: -x[1])[:5]
            ]
            result.append(new_r)

    return result


def apply_persistence(
    records: list[FPTRecord], min_frames: int = 3,
) -> list[FPTRecord]:
    """Require a label switch to persist for min_frames consecutive frames.
    Until then, emit the previous stable label.
    None labels are treated as no-observation: inherit stable label, don't
    reset pending counter."""
    sequences = group_by_sequence(records)
    result = []

    for vid, seq in sequences.items():
        stable_label = None
        pending_label = None
        pending_count = 0

        for r in seq:
            label = r.radical_match

            if label is None:
                if stable_label is not None:
                    new_r = copy(r)
                    new_r.radical_match = stable_label
                    result.append(new_r)
                else:
                    result.append(r)
                continue

            if label == stable_label:
                pending_label = None
                pending_count = 0
                result.append(r)
            elif label == pending_label:
                pending_count += 1
                if pending_count >= min_frames:
                    stable_label = label
                    pending_label = None
                    pending_count = 0
                    result.append(r)
                elif stable_label is not None:
                    new_r = copy(r)
                    new_r.radical_match = stable_label
                    result.append(new_r)
                else:
                    result.append(r)
            else:
                pending_label = label
                pending_count = 1
                if stable_label is not None:
                    new_r = copy(r)
                    new_r.radical_match = stable_label
                    result.append(new_r)
                else:
                    result.append(r)

    return result
