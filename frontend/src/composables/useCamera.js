import { onBeforeUnmount, ref, shallowRef } from "vue";

/**
 * 摄像头调用逻辑：打开设备摄像头、预览、并拍照生成一个 File，
 * 生成的 File 可直接复用现有「拍照识景」的 vision 上传链路。
 */
export function useCamera() {
  const isSupported = ref(
    typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia,
  );
  const isActive = ref(false);
  const isStarting = ref(false);
  const error = ref("");
  const videoRef = ref(null);
  const streamRef = shallowRef(null);

  function bindVideo(element) {
    videoRef.value = element;
    if (element && streamRef.value && element.srcObject !== streamRef.value) {
      element.srcObject = streamRef.value;
      element.play?.().catch(() => {});
    }
  }

  async function start() {
    if (isActive.value) return true;
    error.value = "";
    if (!isSupported.value) {
      error.value = "当前浏览器不支持摄像头调用，请改用上传图片。";
      return false;
    }
    isStarting.value = true;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });
      streamRef.value = stream;
      isActive.value = true;
      if (videoRef.value) {
        videoRef.value.srcObject = stream;
        try {
          await videoRef.value.play();
        } catch {
          // 自动播放被拦截时交给用户手动点击
        }
      }
      return true;
    } catch (err) {
      error.value = cameraErrorMessage(err);
      stop();
      return false;
    } finally {
      isStarting.value = false;
    }
  }

  function stop() {
    const stream = streamRef.value;
    if (stream) {
      stream.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch {
          // ignore
        }
      });
    }
    streamRef.value = null;
    if (videoRef.value) {
      try {
        videoRef.value.srcObject = null;
      } catch {
        // ignore
      }
    }
    isActive.value = false;
  }

  /**
   * 从当前视频帧截取一张图片，返回 File 供 vision 上传复用。
   */
  async function capture({ type = "image/jpeg", quality = 0.92, filename } = {}) {
    const video = videoRef.value;
    if (!video || !isActive.value) {
      error.value = "摄像头尚未开启。";
      return null;
    }
    const width = video.videoWidth || 1280;
    const height = video.videoHeight || 720;
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    if (!context) {
      error.value = "当前浏览器无法截取摄像头画面。";
      return null;
    }
    context.drawImage(video, 0, 0, width, height);
    const blob = await new Promise((resolve) => {
      canvas.toBlob(resolve, type, quality);
    });
    if (!blob) {
      error.value = "拍照失败，请重试。";
      return null;
    }
    const suffix = type.includes("png") ? "png" : "jpg";
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    return new File([blob], filename || `camera-${stamp}.${suffix}`, { type });
  }

  onBeforeUnmount(stop);

  return { isSupported, isActive, isStarting, error, videoRef, bindVideo, start, stop, capture };
}

function cameraErrorMessage(err) {
  const name = err?.name || "";
  const messages = {
    NotAllowedError: "摄像头权限被拒绝，请在浏览器地址栏中允许摄像头后重试。",
    PermissionDeniedError: "摄像头权限被拒绝，请在浏览器地址栏中允许摄像头后重试。",
    NotFoundError: "没有检测到可用摄像头，请改用上传图片。",
    DevicesNotFoundError: "没有检测到可用摄像头，请改用上传图片。",
    NotReadableError: "摄像头被其他程序占用，请关闭后重试。",
    TrackStartError: "摄像头启动失败，请检查设备后重试。",
    SecurityError: "当前页面不是安全上下文（需要 HTTPS 或 localhost），无法调用摄像头。",
    OverconstrainedError: "当前设备不支持所需的摄像头参数，请改用上传图片。",
  };
  return messages[name] || "摄像头调用失败，请改用上传图片。";
}
