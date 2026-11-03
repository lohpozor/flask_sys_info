import platform
import socket
import time

import psutil

try:
    import pynvml
except ImportError:
    pynvml = None

BYTES_IN_GB = 1024 ** 3

# Первый вызов cpu_percent без интервала всегда возвращает 0.0, поэтому "заводим" счётчик заранее.
# Дальше каждый вызов мгновенно отдаёт загрузку с момента предыдущего вызова.
psutil.cpu_percent(interval=None)

# Счётчики сети с прошлого вызова: (время, отправлено байт, получено байт). Нужны, чтобы посчитать скорость.
_last_net = None


def _init_gpu():
    if pynvml is None:
        return None
    try:
        pynvml.nvmlInit()
        return pynvml.nvmlDeviceGetHandleByIndex(0)
    except pynvml.NVMLError:
        return None


_gpu_handle = _init_gpu()


def _os_name():
    system = platform.system()
    if system == "Windows":
        # Python < 3.12 называет Windows 11 "10", но у Windows 11 номер сборки начинается с 22000
        build = int(platform.version().split(".")[-1])
        return "Windows 11" if build >= 22000 else f"Windows {platform.release()}"
    return f"{system} {platform.release()}"


def _cpu_temperature():
    # psutil умеет читать температуры только на Linux; на Windows датчики CPU доступны лишь драйверу с правами администратора
    if not hasattr(psutil, "sensors_temperatures"):
        return None
    sensors = psutil.sensors_temperatures()
    for name in ("coretemp", "k10temp", "cpu_thermal"):
        if sensors.get(name):
            return round(sensors[name][0].current)
    return None


def _gpu():
    if _gpu_handle is None:
        return {"percent": None, "temperature": None}
    try:
        return {
            "percent": pynvml.nvmlDeviceGetUtilizationRates(_gpu_handle).gpu,
            "temperature": pynvml.nvmlDeviceGetTemperature(_gpu_handle, pynvml.NVML_TEMPERATURE_GPU),
        }
    except pynvml.NVMLError:
        return {"percent": None, "temperature": None}


def _usage(used, total, percent):
    return {
        "used_gb": round(used / BYTES_IN_GB, 1),
        "total_gb": round(total / BYTES_IN_GB, 1),
        "percent": percent,
    }


def _interfaces():
    stats = psutil.net_if_stats()
    result = []
    for name, addresses in psutil.net_if_addrs().items():
        ipv4 = next((a.address for a in addresses if a.family == socket.AF_INET), None)
        if ipv4 is None or ipv4.startswith("127."):
            continue
        result.append({"name": name, "ip": ipv4, "up": name in stats and stats[name].isup})
    return result


def _network():
    global _last_net
    counters = psutil.net_io_counters()
    now = time.monotonic()

    download = upload = 0
    if _last_net is not None:
        elapsed = now - _last_net[0]
        if elapsed > 0:
            upload = (counters.bytes_sent - _last_net[1]) / elapsed
            download = (counters.bytes_recv - _last_net[2]) / elapsed
    _last_net = (now, counters.bytes_sent, counters.bytes_recv)

    return {
        "download_bps": round(download),
        "upload_bps": round(upload),
        "received_gb": round(counters.bytes_recv / BYTES_IN_GB, 2),
        "sent_gb": round(counters.bytes_sent / BYTES_IN_GB, 2),
        "interfaces": _interfaces(),
    }


def get_info():
    return {
        "hostname": socket.gethostname(),
        "os": _os_name(),
    }


def get_metrics():
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return {
        "cpu": {
            "percent": psutil.cpu_percent(interval=0.5),
            "temperature": _cpu_temperature(),
        },
        "gpu": _gpu(),
        "memory": _usage(mem.used, mem.total, mem.percent),
        "disk": _usage(disk.used, disk.total, disk.percent),
        "uptime_seconds": int(time.time() - psutil.boot_time()),
        "processes": len(psutil.pids()),
        "network": _network(),
    }
