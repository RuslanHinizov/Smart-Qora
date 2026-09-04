import asyncio

from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user_header_or_query
from app.services.frame_bus import frame_bus

router = APIRouter(prefix="/stream", tags=["stream"], dependencies=[Depends(get_current_user_header_or_query)])

_BOUNDARY = "frame"
_OFFLINE_JPEG = bytes.fromhex(  # 1x1 black JPEG placeholder when no frame is available
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c19"
    "1213130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffc00011"
    "08000100010301220002110103110111ffc4001f0000010501010101010100000000000000000102030405060708090a"
    "0bffc400b5100002010303020403050504040000017d01020300041105122131410613516107227114328191a1082342"
    "b1c11552d1f02433627282090a161718191a25262728292a3435363738393a434445464748494a535455565758595a63"
    "6465666768696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8"
    "b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffda000c03010002"
    "11031100003f00f7fa28a2803fffd9"
)


async def _mjpeg():
    queue = frame_bus.subscribe()
    try:
        while True:
            try:
                jpeg = await asyncio.wait_for(queue.get(), timeout=2.0)
            except asyncio.TimeoutError:
                jpeg = frame_bus.latest_jpeg if frame_bus.is_fresh() else _OFFLINE_JPEG
            yield (b"--" + _BOUNDARY.encode() + b"\r\nContent-Type: image/jpeg\r\n"
                   b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n")
    finally:
        frame_bus.unsubscribe(queue)


@router.get("/mjpeg")
async def mjpeg_stream():
    return StreamingResponse(_mjpeg(), media_type=f"multipart/x-mixed-replace; boundary={_BOUNDARY}")


@router.get("/snapshot")
async def snapshot():
    jpeg = frame_bus.latest_jpeg if frame_bus.is_fresh(max_age=30.0) else _OFFLINE_JPEG
    return Response(content=jpeg, media_type="image/jpeg", headers={"Cache-Control": "no-store"})
