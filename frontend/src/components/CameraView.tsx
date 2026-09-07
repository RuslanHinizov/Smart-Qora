import { useEffect, useState } from "react";
import { useLanguage } from "../i18n/useLanguage";
import { Icon } from "./Icon";

/**
 * Annotated live feed from /api/stream/mjpeg. The browser sends the HttpOnly
 * session cookie automatically. onError shows an honest
 * "feed unavailable" card instead of a fake animation over a blank box.
 */
export function CameraView({ active }: { active: boolean }) {
  const { t } = useLanguage();
  const [failed, setFailed] = useState(false);
  const [nonce, setNonce] = useState(() => Date.now());

  useEffect(() => {
    setFailed(false);
    setNonce(Date.now());
  }, [active]);

  const src = `/api/stream/mjpeg?t=${nonce}`;
  const showImage = active && !failed;

  return (
    <div className="camera-view">
      {showImage && (
        <>
          <img src={src} alt={t.liveCamera} onError={() => setFailed(true)} />
          <span className="live-tag">
            <span className="dot" />
            {t.live}
          </span>
        </>
      )}
      {!showImage && (
        <div className="camera-fallback">
          <Icon name="camera" size={26} />
          <span>{t.cameraOffline}</span>
          <button className="btn sm ghost" onClick={() => setNonce(Date.now())}>
            <Icon name="refresh" size={14} />
            {t.retry}
          </button>
        </div>
      )}
    </div>
  );
}
