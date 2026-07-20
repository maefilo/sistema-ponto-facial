class CameraManager {
    constructor(videoElement, canvasElement) {
        this.video = videoElement;
        this.canvas = canvasElement;
        this.ctx = this.canvas.getContext('2d');
        this.stream = null;
    }

    async start() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'user',
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                },
            });
            this.video.srcObject = this.stream;
            await this.video.play();
            return true;
        } catch (err) {
            console.error('Camera access error:', err);
            return false;
        }
    }

    stop() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        this.video.srcObject = null;
    }

    capture() {
        if (!this.video.srcObject) return null;

        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;
        this.ctx.drawImage(this.video, 0, 0);

        return new Promise(resolve => {
            this.canvas.toBlob(blob => {
                resolve(blob);
            }, 'image/jpeg', 0.85);
        });
    }

    captureDataUrl() {
        if (!this.video.srcObject) return null;
        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;
        this.ctx.drawImage(this.video, 0, 0);
        return this.canvas.toDataURL('image/jpeg', 0.85);
    }
}
