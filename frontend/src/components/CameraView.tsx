import { useEffect, useState } from "react";
import { readToken } from "../api/client";
import { useLanguage } from "../i18n/useLanguage";
import { Icon } from "./Icon";

/**
 * Annotated live feed from /api/stream/mjpeg. An <img> cannot send an auth
 * header, so the JWT rides in the query string. onError shows an honest
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

  const token = readToken();
  const src = token ? `/api/stream/mjpeg?token=${encodeURIComponent(token)}&t=${nonce}` : "";
  const showImage = active && !failed && Boolean(src);

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
