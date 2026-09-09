from app.vision.verifier import iou


def test_iou_identical_boxes_is_one():
    assert iou((10, 20, 30, 40), (10, 20, 30, 40)) == 1.0


def test_iou_disjoint_boxes_is_zero():
    assert iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0


def test_iou_partially_overlapping_boxes():
    assert iou((0, 0, 10, 10), (5, 0, 15, 10)) == 1 / 3
