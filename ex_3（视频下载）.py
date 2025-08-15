import os
import requests
import m3u8
from concurrent.futures import ThreadPoolExecutor
import subprocess
import warnings
from Crypto.Cipher import AES
import binascii
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import time
from urllib.parse import urlparse

# 禁用HTTPS证书警告
warnings.filterwarnings("ignore", category=requests.packages.urllib3.exceptions.InsecureRequestWarning)


class M3U8DownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("M3U8超速下载器 v2.0")
        self.root.geometry("700x550")

        # 样式配置
        self.style = ttk.Style()
        self.style.configure("TButton", padding=6)
        self.style.configure("TLabel", padding=5)

        # 主框架
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # URL输入
        ttk.Label(self.main_frame, text="M3U8 URL:").grid(row=0, column=0, sticky=tk.W)
        self.url_entry = ttk.Entry(self.main_frame, width=60)
        self.url_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)

        # 保存路径
        ttk.Label(self.main_frame, text="保存路径:").grid(row=1, column=0, sticky=tk.W)
        self.path_entry = ttk.Entry(self.main_frame, width=60)
        self.path_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        ttk.Button(self.main_frame, text="浏览", command=self.browse_path).grid(row=1, column=2, padx=5)

        # 下载选项
        options_frame = ttk.LabelFrame(self.main_frame, text="下载选项", padding=10)
        options_frame.grid(row=2, column=0, columnspan=3, sticky=tk.EW, pady=5)

        ttk.Label(options_frame, text="并发线程:").grid(row=0, column=0)
        self.threads_spin = ttk.Spinbox(options_frame, from_=1, to=20, width=5)
        self.threads_spin.grid(row=0, column=1, padx=5)
        self.threads_spin.set(5)

        ttk.Label(options_frame, text="重试次数:").grid(row=0, column=2)
        self.retry_spin = ttk.Spinbox(options_frame, from_=0, to=10, width=5)
        self.retry_spin.grid(row=0, column=3, padx=5)
        self.retry_spin.set(3)

        # 控制按钮
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=10)

        self.download_btn = ttk.Button(btn_frame, text="开始下载", command=self.toggle_download)
        self.download_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="清除日志", command=self.clear_log).pack(side=tk.LEFT, padx=5)

        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self.main_frame, variable=self.progress_var, maximum=100)
        self.progress.grid(row=4, column=0, columnspan=3, sticky=tk.EW, pady=5)

        # 状态信息
        self.status_var = tk.StringVar()
        self.status_var.set("准备就绪")
        ttk.Label(self.main_frame, textvariable=self.status_var).grid(row=5, column=0, columnspan=3)

        # 日志区域
        self.log_area = scrolledtext.ScrolledText(self.main_frame, height=12, state=tk.DISABLED)
        self.log_area.grid(row=6, column=0, columnspan=3, sticky=tk.NSEW)

        # 网格配置
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(6, weight=1)

        # 下载控制变量
        self.is_downloading = False
        self.stop_flag = False
        self.downloaded_count = 0
        self.total_segments = 0
        self.start_time = 0

    def browse_path(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4文件", "*.mp4"), ("所有文件", "*.*")],
            title="选择保存位置"
        )
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)

    def toggle_download(self):
        if self.is_downloading:
            self.stop_flag = True
            self.download_btn.config(text="开始下载")
            self.log("用户手动停止下载")
        else:
            self.start_download()

    def start_download(self):
        m3u8_url = self.url_entry.get().strip()
        output_path = self.path_entry.get().strip()

        if not m3u8_url:
            messagebox.showerror("错误", "请输入M3U8 URL地址")
            return
        if not output_path:
            messagebox.showerror("错误", "请选择视频保存路径")
            return

        self.is_downloading = True
        self.stop_flag = False
        self.downloaded_count = 0
        self.download_btn.config(text="停止下载")
        self.progress_var.set(0)
        self.clear_log()
        self.start_time = time.time()

        # 启动下载线程
        download_thread = threading.Thread(
            target=self.download_process,
            args=(m3u8_url, output_path),
            daemon=True
        )
        download_thread.start()

    def download_process(self, m3u8_url, output_path):
        try:
            self.log(f"开始解析M3U8文件: {m3u8_url}")

            # 1. 解析M3U8文件
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Referer": urlparse(m3u8_url).scheme + "://" + urlparse(m3u8_url).netloc + "/"
            }

            response = requests.get(m3u8_url, headers=headers, verify=False, timeout=10)
            response.raise_for_status()
            m3u8_content = response.text

            if not m3u8_content.strip():
                raise ValueError("M3U8文件内容为空")

            playlist = m3u8.loads(m3u8_content)
            if not playlist.segments:
                raise ValueError("M3U8中没有找到视频分片")

            # 2. 处理加密密钥
            key, iv = None, None
            if playlist.keys and playlist.keys[0]:
                key_uri = playlist.keys[0].uri
                if not key_uri.startswith(('http://', 'https://')):
                    base_url = m3u8_url.rsplit('/', 1)[0]
                    key_uri = f"{base_url}/{key_uri}"

                self.log(f"获取加密密钥: {key_uri}")
                key_response = requests.get(key_uri, headers=headers, verify=False)
                key = key_response.content

                if playlist.keys[0].iv:
                    iv_hex = playlist.keys[0].iv.replace('0x', '')
                    iv = binascii.unhexlify(iv_hex)
                else:
                    iv = playlist.media_sequence.to_bytes(16, byteorder='big')

                self.log(f"密钥长度: {len(key)}字节, IV长度: {len(iv)}字节")

            # 3. 准备分片URL列表
            base_url = m3u8_url.rsplit('/', 1)[0]
            ts_urls = []
            for segment in playlist.segments:
                if segment.uri.startswith(('http://', 'https://')):
                    ts_urls.append(segment.uri)
                else:
                    ts_urls.append(f"{base_url}/{segment.uri}")

            self.total_segments = len(ts_urls)
            self.log(f"共发现 {self.total_segments} 个视频分片")
            self.log(f"第一个分片URL: {ts_urls[0]}")

            # 4. 多线程下载
            max_workers = int(self.threads_spin.get())
            retry_count = int(self.retry_spin.get())

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                for i, ts_url in enumerate(ts_urls):
                    if self.stop_flag:
                        break

                    ts_file = f"temp_{i:04d}.ts"
                    futures.append(executor.submit(
                        self.download_ts_segment,
                        ts_url=ts_url,
                        output_path=ts_file,
                        headers=headers,
                        key=key,
                        iv=iv,
                        segment_num=i,
                        retry_count=retry_count
                    ))

                for future in futures:
                    future.result()

            # 5. 合并分片（如果未停止）
            if not self.stop_flag and self.downloaded_count > 0:
                self.merge_segments(output_path)

        except Exception as e:
            self.log(f"下载出错: {str(e)}", error=True)
        finally:
            self.cleanup_temp_files()
            self.is_downloading = False
            self.download_btn.config(text="开始下载")
            elapsed = time.time() - self.start_time
            self.log(f"任务完成，耗时: {elapsed:.2f}秒")
            self.status_var.set(f"完成: {self.downloaded_count}/{self.total_segments}")

    def download_ts_segment(self, ts_url, output_path, headers, key, iv, segment_num, retry_count=3):
        for attempt in range(retry_count + 1):
            if self.stop_flag:
                return False

            try:
                self.log(f"下载分片 {segment_num + 1}/{self.total_segments} (尝试 {attempt + 1}/{retry_count + 1})")

                response = requests.get(ts_url, headers=headers, stream=True, verify=False, timeout=30)
                response.raise_for_status()

                content = response.content

                # 解密处理
                if key:
                    cipher = AES.new(key, AES.MODE_CBC, iv=iv[:16] if iv else None)
                    content = cipher.decrypt(content)

                with open(output_path, "wb") as f:
                    f.write(content)

                self.downloaded_count += 1
                progress = (self.downloaded_count / self.total_segments) * 100
                self.progress_var.set(progress)
                self.status_var.set(f"下载中: {self.downloaded_count}/{self.total_segments}")
                self.root.update()

                return True

            except Exception as e:
                if attempt == retry_count:
                    self.log(f"分片 {segment_num + 1} 下载失败: {str(e)}", error=True)
                    return False
                time.sleep(1)

    def merge_segments(self, output_path):
        try:
            self.log("开始合并视频分片...")

            # 获取有效的分片文件列表
            ts_files = sorted(
                [f for f in os.listdir() if f.startswith("temp_") and f.endswith(".ts")],
                key=lambda x: int(x[5:-3])
            )

            if not ts_files:
                raise ValueError("没有找到有效的分片文件")

            self.log(f"找到 {len(ts_files)} 个有效分片，开始合并...")

            # 方法1：极速合并（不重新编码）
            with open("concat_list.txt", "w") as f:
                for ts_file in ts_files:
                    f.write(f"file '{os.path.abspath(ts_file)}'\n")

            subprocess.run([
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", "concat_list.txt",
                "-c", "copy",  # 直接拷贝流
                "-movflags", "faststart",
                "-y",
                output_path
            ], check=True, stderr=subprocess.PIPE)

            self.log(f"视频合并完成: {output_path}")
            self.log(f"文件大小: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")

        except subprocess.CalledProcessError as e:
            self.log(f"FFmpeg合并失败: {e.stderr.decode('utf-8')}", error=True)
        except Exception as e:
            self.log(f"合并过程中出错: {str(e)}", error=True)

    def cleanup_temp_files(self):
        self.log("清理临时文件...")
        for f in os.listdir():
            if f.startswith("temp_") and f.endswith(".ts"):
                os.remove(f)
        if os.path.exists("concat_list.txt"):
            os.remove("concat_list.txt")

    def log(self, message, error=False):
        tag = "ERROR" if error else "INFO"
        timestamp = time.strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] [{tag}] {message}\n"

        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, log_msg)
        if error:
            self.log_area.tag_add("error", "end-2l linestart", "end-2l lineend")
            self.log_area.tag_config("error", foreground="red")
        self.log_area.config(state=tk.DISABLED)
        self.log_area.see(tk.END)
        self.root.update()

    def clear_log(self):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state=tk.DISABLED)


if __name__ == "__main__":
    root = tk.Tk()
    app = M3U8DownloaderApp(root)
    root.mainloop()