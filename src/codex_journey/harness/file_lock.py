"""
FileLock — 文件锁

防止多个 Worker 同时修改同一个文件。
"""

import os
import time
from pathlib import Path


class FileLock:
    """
    简单的文件锁，防止多 Worker 同时修改同一文件

    使用方式：
        lock = FileLock()
        if lock.acquire("src/sort.py"):
            try:
                # 安全的文件操作
                write_file(...)
            finally:
                lock.release("src/sort.py")
        else:
            # 文件被锁定，等待或跳过
    """

    def __init__(self, lock_dir: str = ".locks"):
        """
        初始化文件锁

        Args:
            lock_dir: 锁文件存放目录
        """
        self.lock_dir = lock_dir
        # 确保锁目录存在
        os.makedirs(self.lock_dir, exist_ok=True)

    def _get_lock_path(self, file_path: str) -> str:
        """
        获取锁文件路径

        Args:
            file_path: 被锁定的文件路径

        Returns:
            锁文件的完整路径
        """
        # 把路径中的 / 替换为 _，避免目录创建问题
        safe_name = file_path.replace("/", "_").replace("\\", "_").replace(":", "_")
        return os.path.join(self.lock_dir, f"{safe_name}.lock")

    def acquire(self, file_path: str, timeout: int = 30, retry_interval: float = 0.5) -> bool:
        """
        尝试获取文件锁

        Args:
            file_path: 要锁定的文件路径
            timeout: 最大等待时间（秒）
            retry_interval: 重试间隔（秒）

        Returns:
            True 表示成功获取锁，False 表示超时未能获取
        """
        lock_path = self._get_lock_path(file_path)
        start_time = time.time()

        while True:
            # 尝试创建锁文件（原子操作）
            try:
                # O_EXCL 表示如果文件存在则失败
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                # 写入当前时间戳和进程ID
                os.write(fd, f"{time.time()}:{os.getpid()}".encode())
                os.close(fd)
                return True
            except FileExistsError:
                # 锁文件已存在，检查是否过期
                if self._is_lock_expired(lock_path):
                    # 锁过期，删除并重试
                    try:
                        os.remove(lock_path)
                    except FileNotFoundError:
                        pass
                    continue
                # 锁未过期，检查是否超时
                if time.time() - start_time > timeout:
                    return False
                # 等待后重试
                time.sleep(retry_interval)

    def release(self, file_path: str) -> bool:
        """
        释放文件锁

        Args:
            file_path: 要解锁的文件路径

        Returns:
            True 表示成功释放，False 表示锁不存在
        """
        lock_path = self._get_lock_path(file_path)
        try:
            os.remove(lock_path)
            return True
        except FileNotFoundError:
            return False

    def _is_lock_expired(self, lock_path: str, ttl: int = 300) -> bool:
        """
        检查锁是否过期

        Args:
            lock_path: 锁文件路径
            ttl: 锁的生存时间（秒），默认5分钟

        Returns:
            True 表示锁已过期，False 表示锁有效
        """
        try:
            with open(lock_path, "r") as f:
                timestamp_str = f.read().split(":")[0]
                timestamp = float(timestamp_str)
                return time.time() - timestamp > ttl
        except (ValueError, IndexError, FileNotFoundError):
            # 解析失败或文件不存在，视为过期
            return True

    def is_locked(self, file_path: str) -> bool:
        """
        检查文件是否被锁定

        Args:
            file_path: 要检查的文件路径

        Returns:
            True 表示文件被锁定，False 表示未锁定
        """
        lock_path = self._get_lock_path(file_path)
        if not os.path.exists(lock_path):
            return False
        if self._is_lock_expired(lock_path):
            return False
        return True

    def force_release(self, file_path: str) -> bool:
        """
        强制释放锁（不管是否过期）

        Args:
            file_path: 要解锁的文件路径

        Returns:
            True 表示成功释放
        """
        lock_path = self._get_lock_path(file_path)
        try:
            os.remove(lock_path)
            return True
        except FileNotFoundError:
            return False

    def release_all(self) -> int:
        """
        释放所有锁

        Returns:
            释放的锁数量
        """
        count = 0
        for filename in os.listdir(self.lock_dir):
            if filename.endswith(".lock"):
                try:
                    os.remove(os.path.join(self.lock_dir, filename))
                    count += 1
                except FileNotFoundError:
                    pass
        return count


class FileLockContext:
    """文件锁上下文管理器，更方便的使用方式"""

    def __init__(self, file_lock: FileLock, file_path: str, timeout: int = 30):
        self.file_lock = file_lock
        self.file_path = file_path
        self.timeout = timeout
        self._acquired = False

    def __enter__(self) -> bool:
        """获取锁"""
        self._acquired = self.file_lock.acquire(self.file_path, self.timeout)
        return self._acquired

    def __exit__(self, exc_type, exc_val, exc_tb):
        """释放锁"""
        if self._acquired:
            self.file_lock.release(self.file_path)
        return False  # 不吞掉异常
