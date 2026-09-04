import logging

from app.vision.classes import canonical

logger = logging.getLogger(__name__)


class LivestockDetector:
    def __init__(self, model_path: str, device: str, confidence: float, iou: float, image_size: int,
                 tracker: str, allowed_classes: list[str], require_cuda: bool = False,
                 half_precision: bool = True):
        from ultralytics import YOLO
        import torch
        self.model = YOLO(model_path)
        requested_cuda = device.lower() != "cpu"
        if requested_cuda and require_cuda and not torch.cuda.is_available():
            raise RuntimeError("CUDA is required but the installed PyTorch build cannot access it")
        self.device = device if not requested_cuda or torch.cuda.is_available() else "cpu"
        if self.device == "cpu" and requested_cuda:
            logger.warning("cuda_unavailable_falling_back_to_cpu")
        self.half_precision = half_precision and self.device != "cpu"
        self.confidence, self.iou, self.image_size, self.tracker = confidence, iou, image_size, tracker
        self.names = self.model.names
        wanted = {canonical(name) for name in allowed_classes} - {None}
        self.allowed_ids = None if not wanted else [i for i, name in self.names.items() if canonical(name) in wanted]
        if wanted and not self.allowed_ids:
            logger.warning("no_model_class_matches_allowed_classes allowed=%s model_names=%s", sorted(wanted), list(self.names.values()))

    def track(self, frame):
        return self.model.track(frame, persist=True, verbose=False, conf=self.confidence, iou=self.iou,
                                imgsz=self.image_size, tracker=self.tracker, device=self.device,
                                classes=self.allowed_ids, half=self.half_precision)[0]

    def reset_tracker(self) -> None:
        """Clear persistent track state so IDs restart from 1 (used when a video file loops)."""
        predictor = getattr(self.model, "predictor", None)
        trackers = getattr(predictor, "trackers", None)
        if trackers:
            for tracker in trackers:
                if hasattr(tracker, "reset"):
                    tracker.reset()
        elif predictor is not None:
            self.model.predictor = None
