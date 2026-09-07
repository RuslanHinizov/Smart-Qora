"""Evaluation must not hide an over-count behind an under-count elsewhere."""
import importlib.util
import json
from pathlib import Path


def load_eval():
    path = Path(__file__).resolve().parents[2] / "training" / "counting_eval.py"
    spec = importlib.util.spec_from_file_location("counting_evaluation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_direction_and_clip_errors_do_not_cancel(monkeypatch, tmp_path):
    ev = load_eval()
    clips = []
    for clip in (1, 2):
        p = tmp_path / f"clip{clip}.json"
        p.write_text(json.dumps({"clip": clip, "line": [[0, 50], [100, 50]], "inside_direction": "DOWN"}))
        clips.append(p)
    monkeypatch.setattr(ev, "gt_events", lambda gt: None)
    monkeypatch.setattr(ev, "pred_events", lambda *args: (None, {}))
    def counts(ins, outs):
        return {"IN": ins, "OUT": outs, "crossing_ids": set(range(ins+outs)), "track_ids": set(range(ins+outs))}
    sequence = iter([counts(10, 0), counts(12, 0), counts(10, 0), counts(8, 0)])
    monkeypatch.setattr(ev, "tally_from_stream", lambda *args, **kwargs: next(sequence))
    result = ev.eval_weights("unused", {}, clips)
    assert result["overall"]["counting_error_pct"] == 20
    assert "id_switch_ratio" not in result["overall"]
    assert result["overall"]["track_count_ratio"] == 1


def test_dual_line_pending_crossing_matures():
    from app.vision.counter import LineCrossingCounter
    counter = LineCrossingCounter((0, 40), (100, 40), "DOWN", line2=((0, 80), (100, 80)), min_track_updates=4)
    assert counter.update(1, (50, 10), now=0) is None
    assert counter.update(1, (50, 60), now=1) is None
    assert counter.update(1, (50, 100), now=2) is None
    assert counter.update(1, (50, 105), now=3).direction == "IN"
    assert counter.update(1, (50, 110), now=4) is None
