import urllib.request
from you_get import common as you_get
from you_get.extractors import bilibili
import os
import sys
import json
import time
import logging
import requests
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bilibili_downloader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 设置请求头（模拟浏览器）
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}

# 设置全局 opener
opener = urllib.request.build_opener()
opener.addheaders = [(k, v) for k, v in headers.items()]
urllib.request.install_opener(opener)

def validate_bilibili_url(url):
    """验证是否为有效的B站视频URL"""
    parsed = urlparse(url)
    if not parsed.netloc.endswith('bilibili.com'):
        return False
    if '/video/' not in url and not url.startswith('BV'):
        return False
    return True

def get_video_info(url, cookies=None):
    """获取视频详细信息"""
    try:
        site = bilibili.Bilibili()
        info = site.prepare(url=url, cookies=cookies)
        if not info:
            logger.error("无法获取视频信息")
            return None
        
        logger.debug("视频信息: %s", json.dumps(info, indent=2, ensure_ascii=False))
        return info
    except Exception as e:
        logger.error("获取视频信息失败: %s", str(e))
        return None

def download_with_youget(info, output_dir, quality=None, cookies=None):
    """使用you-get下载视频"""
    try:
        you_get.download_media(
            info,
            output_dir=output_dir,
            merge=True,
            format=quality,
            cookies=cookies,
            extractor_proxy=None,
            debug=False,
            **{'ignore_ssl_errors': True}
        )
        return True
    except Exception as e:
        logger.error("you-get下载失败: %s", str(e))
        return False

def download_bilibili_video(url, output_dir="./downloads", quality=None, cookies=None, max_retries=3):
    """
    下载Bilibili视频
    :param url: 视频URL (BV号或完整URL)
    :param output_dir: 输出目录
    :param quality: 视频质量 (如 'flv480', 'flv720'等)
    :param cookies: cookies文件路径
    :param max_retries: 最大重试次数
    :return: 是否下载成功
    """
    # 自动补全URL
    if url.startswith('BV'):
        url = f'https://www.bilibili.com/video/{url}'
    
    # 验证URL
    if not validate_bilibili_url(url):
        logger.error("无效的B站视频URL: %s", url)
        return False
    
    # 验证cookies文件
    cookie_dict = None
    if cookies:
        if not os.path.exists(cookies):
            logger.warning("cookies文件不存在: %s", cookies)
        else:
            try:
                with open(cookies, 'r') as f:
                    cookie_dict = json.load(f)
                logger.info("已加载cookies文件")
            except Exception as e:
                logger.warning("解析cookies文件失败: %s", str(e))
    
    retry_count = 0
    while retry_count < max_retries:
        try:
            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)
            
            logger.info("开始处理视频: %s", url)
            logger.info("输出目录: %s", os.path.abspath(output_dir))
            if quality:
                logger.info("视频质量: %s", quality)
            
            # 获取视频信息
            video_info = get_video_info(url, cookie_dict)
            if not video_info:
                raise Exception("无法获取视频信息")
            
            # 打印可用格式
            if 'streams' in video_info:
                logger.info("可用格式:")
                for stream_id, stream in video_info['streams'].items():
                    logger.info(" - %s: %s", stream_id, stream.get('quality', '未知'))
            
            # 下载视频
            if not download_with_youget(video_info, output_dir, quality, cookie_dict):
                raise Exception("you-get下载失败")
            
            logger.info("视频下载成功!")
            return True
            
        except Exception as e:
            retry_count += 1
            logger.error("下载失败 (第%d次重试): %s", retry_count, str(e))
            
            if retry_count < max_retries:
                wait_time = min(2 ** retry_count, 60)  # 指数退避，最多等待60秒
                logger.info("等待%d秒后重试...", wait_time)
                time.sleep(wait_time)
            else:
                logger.error("达到最大重试次数，下载终止")
                return False

def main():
    print("""
    Bilibili视频下载工具
    ==================
    功能说明:
    1. 支持BV号或完整URL输入
    2. 支持选择视频质量
    3. 支持使用cookies下载会员视频
    4. 自动重试机制
    """)
    
    # 获取用户输入
    url = input("请输入Bilibili视频BV号或URL (例如 BV1xx411c7mu 或 https://www.bilibili.com/video/BV1xx411c7mu): ").strip()
    if not url:
        print("错误: URL不能为空")
        sys.exit(1)
    
    output_dir = input("请输入输出目录 (默认: ./downloads): ").strip()
    if not output_dir:
        output_dir = "./downloads"
    
    quality = input("请输入视频质量 (可选，如 flv480, flv720, flv1080 等，不输入则自动选择最高质量): ").strip()
    if not quality:
        quality = None
    
    cookies = input("请输入cookies文件路径 (JSON格式，可选，用于下载会员视频): ").strip()
    if not cookies:
        cookies = None
    
    # 执行下载
    print("\n开始下载...")
    success = download_bilibili_video(
        url=url,
        output_dir=output_dir,
        quality=quality,
        cookies=cookies,
        max_retries=3
    )
    
    if success:
        print("\n下载完成! 视频已保存到:", os.path.abspath(output_dir))
    else:
        print("\n下载失败，请查看日志文件 bilibili_downloader.log 获取详细信息")

if __name__ == "__main__":
    main()