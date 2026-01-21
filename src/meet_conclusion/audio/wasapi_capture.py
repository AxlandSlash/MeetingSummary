"""WASAPI Loopback 音频采集模块

使用 PyAudio 通过 WASAPI loopback 模式采集系统输出音频
"""

import threading
import time
from typing import Callable, Optional

import pyaudio

from meet_conclusion.config import get_config
from meet_conclusion.utils.logger import get_logger

logger = get_logger(__name__)


class WASAPICapture:
    """WASAPI Loopback 音频采集器"""

    def __init__(
        self,
        sample_rate: int = None,
        channels: int = None,
        chunk_size: int = None,
        on_data: Optional[Callable[[bytes], None]] = None,
    ):
        """初始化采集器

        Args:
            sample_rate: 采样率，默认从配置读取
            channels: 声道数，默认从配置读取
            chunk_size: 每次读取的帧数
            on_data: 数据回调函数
        """
        config = get_config()
        self.sample_rate = sample_rate or config.audio.sample_rate
        self.channels = channels or config.audio.channels
        self.chunk_size = chunk_size or config.audio.buffer_size

        self.on_data = on_data

        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._is_running = False
        self._capture_thread: Optional[threading.Thread] = None
        self._device_index: Optional[int] = None

    def _find_loopback_device(self) -> Optional[int]:
        """查找 WASAPI Loopback 设备

        Returns:
            设备索引，如果未找到返回 None
        """
        if self._pyaudio is None:
            self._pyaudio = pyaudio.PyAudio()

        # 获取主机 API 信息
        wasapi_index = None
        for i in range(self._pyaudio.get_host_api_count()):
            api_info = self._pyaudio.get_host_api_info_by_index(i)
            if "WASAPI" in api_info.get("name", ""):
                wasapi_index = i
                logger.info(f"找到 WASAPI Host API: index={i}, name={api_info['name']}")
                break

        if wasapi_index is None:
            logger.error("未找到 WASAPI Host API")
            return None

        # 查找默认输出设备的 loopback
        api_info = self._pyaudio.get_host_api_info_by_index(wasapi_index)

        # 尝试获取默认输出设备
        default_output = api_info.get("defaultOutputDevice", -1)
        if default_output >= 0:
            device_info = self._pyaudio.get_device_info_by_index(default_output)
            logger.info(f"默认输出设备: {device_info['name']}")

        # 遍历所有设备，查找 loopback 设备
        for i in range(self._pyaudio.get_device_count()):
            try:
                device_info = self._pyaudio.get_device_info_by_index(i)

                # 检查是否为 WASAPI 设备
                if device_info.get("hostApi") != wasapi_index:
                    continue

                # 检查是否支持输入（loopback 设备显示为输入设备）
                if device_info.get("maxInputChannels", 0) > 0:
                    name = device_info.get("name", "")
                    # WASAPI loopback 设备通常名称中包含 "Loopback" 或与输出设备同名
                    if "loopback" in name.lower() or "立体声混音" in name or "Stereo Mix" in name.lower():
                        logger.info(f"找到 Loopback 设备: index={i}, name={name}")
                        return i

            except Exception as e:
                logger.debug(f"获取设备 {i} 信息失败: {e}")

        # 如果没找到明确的 loopback，尝试使用默认输出设备（PyAudio WASAPI 可能支持）
        logger.warning("未找到明确的 Loopback 设备，尝试使用默认输出设备")
        return default_output if default_output >= 0 else None

    def list_devices(self) -> list[dict]:
        """列出所有音频设备

        Returns:
            设备信息列表
        """
        if self._pyaudio is None:
            self._pyaudio = pyaudio.PyAudio()

        devices = []
        for i in range(self._pyaudio.get_device_count()):
            try:
                info = self._pyaudio.get_device_info_by_index(i)
                devices.append({
                    "index": i,
                    "name": info.get("name", "Unknown"),
                    "maxInputChannels": info.get("maxInputChannels", 0),
                    "maxOutputChannels": info.get("maxOutputChannels", 0),
                    "defaultSampleRate": info.get("defaultSampleRate", 0),
                    "hostApi": info.get("hostApi", -1),
                })
            except Exception as e:
                logger.debug(f"获取设备 {i} 信息失败: {e}")

        return devices

    def start(self, device_index: Optional[int] = None) -> bool:
        """开始采集

        Args:
            device_index: 指定设备索引，None 则自动查找

        Returns:
            是否成功启动
        """
        if self._is_running:
            logger.warning("采集器已在运行中")
            return True

        if self._pyaudio is None:
            self._pyaudio = pyaudio.PyAudio()

        # 查找设备
        if device_index is None:
            device_index = self._find_loopback_device()

        if device_index is None:
            logger.error("无法找到可用的音频采集设备")
            return False

        self._device_index = device_index

        try:
            # 获取设备信息
            device_info = self._pyaudio.get_device_info_by_index(device_index)
            logger.info(f"使用设备: {device_info['name']}")

            # 确定实际的声道数和采样率
            max_channels = int(device_info.get("maxInputChannels", 2))
            actual_channels = min(self.channels, max_channels) if max_channels > 0 else self.channels

            default_rate = int(device_info.get("defaultSampleRate", self.sample_rate))

            # 打开流
            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=actual_channels,
                rate=default_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk_size,
                as_loopback=True,  # WASAPI loopback 模式
            )

            self._is_running = True

            # 启动采集线程
            self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._capture_thread.start()

            logger.info(f"音频采集已启动: rate={default_rate}, channels={actual_channels}")
            return True

        except Exception as e:
            logger.error(f"启动音频采集失败: {e}")
            self._cleanup()
            return False

    def _capture_loop(self):
        """采集循环"""
        while self._is_running and self._stream:
            try:
                # 读取音频数据
                data = self._stream.read(self.chunk_size, exception_on_overflow=False)

                # 调用回调
                if self.on_data and data:
                    self.on_data(data)

            except Exception as e:
                if self._is_running:
                    logger.error(f"采集数据时出错: {e}")
                    time.sleep(0.1)

    def stop(self):
        """停止采集"""
        self._is_running = False

        if self._capture_thread:
            self._capture_thread.join(timeout=2.0)
            self._capture_thread = None

        self._cleanup()
        logger.info("音频采集已停止")

    def _cleanup(self):
        """清理资源"""
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception as e:
                logger.debug(f"关闭流时出错: {e}")
            self._stream = None

        if self._pyaudio:
            try:
                self._pyaudio.terminate()
            except Exception as e:
                logger.debug(f"终止 PyAudio 时出错: {e}")
            self._pyaudio = None

    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._is_running

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def test_capture():
    """测试音频采集"""
    import wave

    config = get_config()
    output_file = config.audio_dir / "test_capture.wav"

    frames = []

    def on_data(data: bytes):
        frames.append(data)

    capture = WASAPICapture(on_data=on_data)

    # 列出设备
    print("可用设备:")
    for device in capture.list_devices():
        print(f"  [{device['index']}] {device['name']} "
              f"(in={device['maxInputChannels']}, out={device['maxOutputChannels']})")

    # 开始采集
    print("\n开始采集音频（5秒）...")
    if capture.start():
        time.sleep(5)
        capture.stop()

        # 保存为 WAV 文件
        if frames:
            with wave.open(str(output_file), "wb") as wf:
                wf.setnchannels(capture.channels)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(capture.sample_rate)
                wf.writeframes(b"".join(frames))

            print(f"音频已保存到: {output_file}")
        else:
            print("未采集到数据")
    else:
        print("启动采集失败")


if __name__ == "__main__":
    test_capture()
