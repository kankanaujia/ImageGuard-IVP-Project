from pathlib import Path
import cv2
import numpy as np
from backend.processing.video.frame_hashing import hash_frames
from backend.processing.video.ssim_analysis import analyze_ssim
from backend.processing.video.scene_detection import detect_scenes
from PIL import Image

def test_hash_ssim_and_scene_no_change(tmp_path: Path):
    frames=[]
    for index in range(3):
        path=tmp_path/f"{index}.jpg"
        Image.fromarray(np.full((32,32,3),128,dtype=np.uint8)).save(path)
        frames.append({"file":path.name,"timestamp":float(index)})
    hashed=hash_frames(frames,tmp_path)
    assert len(hashed["pairs"]) == 2
    ssim=analyze_ssim(frames,tmp_path,tmp_path/"ssim.png")
    assert all(score > .99 for score in ssim["scores"])
    assert (tmp_path/"ssim.png").exists()
    assert detect_scenes(frames,tmp_path)["candidates"] == []

def test_frame_extraction(tmp_path: Path):
    from backend.processing.video.frame_extraction import extract_frames
    path=tmp_path/"synthetic.avi"
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*"MJPG"),5,(32,32))
    for i in range(10): writer.write(np.full((32,32,3),i*20,dtype=np.uint8))
    writer.release()
    result=extract_frames(path,tmp_path/"frames",interval_seconds=.5)
    assert result["fps"] > 0
    assert result["frames"]
