import cv2

for i in range(5):
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
    if cap.isOpened():
        print(f"Cámara {i}: OK")
        ret, frame = cap.read()
        if ret:
            print(f"  Resolución: {frame.shape[1]}x{frame.shape[0]}")
        cap.release()
    else:
        print(f"Cámara {i}: NO disponible")