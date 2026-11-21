"""The metrics report parses every recorded evaluation in backend/eval/."""
from nextrun_cv import model_metrics as mm


def test_f1_and_change():
    assert mm.f1(0.5, 0.5) == 0.5
    assert mm.f1(None, 0.5) is None
    assert mm.change(100, 58) == -0.42
    assert mm.change(0, 5) is None


def test_report_covers_every_model():
    r = mm.report()
    keys = [m["key"] for m in r["models"]]
    assert keys == ["players", "ball_hoop", "court", "events"]
    for m in r["models"]:
        h = m["headline"]
        assert 0 < h["precision"] <= 1 and 0 < h["recall"] <= 1 and 0 < h["f1"] <= 1
        assert m["iou_rule"] and m["improvements"]
    ball = r["models"][1]
    assert 0 < ball["headline"]["map50_95"] < ball["headline"]["map50"] <= 1
    assert {c["name"] for c in ball["classes"]} == {"ball", "rim"}
    players = r["models"][0]
    assert players["tracking"]["id_switches"] == 591 and players["tracking"]["track_ids"] == 434


def test_parse_yolo_val_reads_all_rows():
    text = (
        "                   all         27         41          1      0.943       0.96      0.568\n"
        "Speed: 0.5ms preprocess, 9.1ms inference, 0.0ms loss, 0.5ms postprocess per image\n"
        "set_a            {'images': 27, 'ball': {'P': 1.0, 'R': 0.9, 'mAP50': 0.92}}\n"
    )
    out = mm.parse_yolo_val(text)
    assert out["sets"][0]["mAP50_95"] == 0.568 and out["sets"][0]["classes"]["ball"]["R"] == 0.9
    assert out["speeds"][0]["inference"] == 9.1
