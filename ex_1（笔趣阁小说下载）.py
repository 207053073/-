import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog
import threading
import requests
import re
import webbrowser
from lxml import html
import time
import os
from urllib.parse import urlparse, urljoin

# 全局变量
stop_flag = False
crawl_delay = 0.5  # 默认0.5秒
current_url = None
last_title = None
chapter_content = ""
page_count = 0
crawl_state = "ready"  # "ready", "running", "paused"
preview_content = ""  # 新增：预览内容
save_path = os.getcwd()  # 默认保存路径为当前工作目录


def crawl(start_url, filename, log_widget, overwrite_mode):
    global stop_flag, crawl_delay, current_url, last_title, chapter_content, page_count, save_path
    parsed_url = urlparse(start_url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    if current_url is None:
        current_url = start_url
        last_title = None
        chapter_content = ""
        page_count = 0

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
    }

    full_path = os.path.join(save_path, filename)
    
    if overwrite_mode and os.path.exists(full_path):
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write('')
        log_widget.insert(tk.END, f"已清空文件: {full_path}\n")

    with requests.Session() as session:
        session.headers.update(headers)
        while current_url and not (stop_flag and page_count % 2 == 1):
            try:
                page_count += 1
                log_widget.insert(tk.END, f"爬取第 {page_count} 页: {current_url}\n")
                log_widget.see(tk.END)
                log_widget.update()
                time.sleep(crawl_delay)
                response = session.get(current_url)
                response.encoding = 'utf-8'
                tree = html.fromstring(response.text)

                title_elem = tree.xpath('//h1/text()')
                title = title_elem[0].strip() if title_elem else f"第{page_count}章"
                title = re.sub(r'（.*?）|\(.*?\)', '', title).strip()

                content_element = tree.xpath('//div[@id="content"]')
                if not content_element:
                    content_element = tree.xpath('//div[contains(@class, "content")]')

                cleaned_content = ""
                if content_element:
                    content_html = html.tostring(content_element[0], encoding='unicode')
                    content_html = content_html.replace('<p>', '\n').replace('</p>', '')
                    content_html = content_html.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
                    content_html = content_html.replace('\xa0', ' ').replace('&nbsp;', ' ')
                    cleaned_tree = html.fromstring(content_html)
                    content = cleaned_tree.xpath('string()')
                    cleaned_content = '\n'.join([line.strip() for line in content.splitlines() if line.strip()])
                else:
                    log_widget.insert(tk.END, "未找到文章内容，停止爬取。\n")
                    break

                if last_title is None:
                    last_title = title
                if title != last_title:
                    with open(full_path, 'a', encoding='utf-8') as f:
                        f.write(f"\n\n=== {last_title} ===\n")
                        f.write(indent_paragraphs(chapter_content))
                    log_widget.insert(tk.END, f"已保存: {last_title}\n")
                    chapter_content = ""
                    last_title = title
                chapter_content += cleaned_content + "\n"

                next_links = tree.xpath('//a[contains(text(), "下一页") or contains(text(), "下一章")]/@href')
                next_url = urljoin(base_url, next_links[0]) if next_links else None

                if next_url:
                    current_url = next_url
                else:
                    if chapter_content:
                        with open(full_path, 'a', encoding='utf-8') as f:
                            f.write(f"\n\n=== {last_title} ===\n")
                            f.write(indent_paragraphs(chapter_content))
                        log_widget.insert(tk.END, f"已保存: {last_title}\n")
                    log_widget.insert(tk.END, "已到达最后一章，爬取结束。\n")
                    break

            except Exception as e:
                log_widget.insert(tk.END, f"爬取失败: {e}\n")
                break

    if crawl_state == "paused":
        log_widget.insert(tk.END, "已暂停爬取...\n")
    log_widget.insert(tk.END, f"完成爬取，共获取 {page_count} 页\n")
    log_widget.see(tk.END)


def preview_content():
    global preview_content
    start_url = url_entry.get()
    if start_url == "请输入你要爬取小说的url":
        messagebox.showerror("错误", "请输入有效的起始URL")
        return

    if not start_url.startswith('http'):
        messagebox.showerror("错误", "请输入完整的起始URL")
        return

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(start_url, headers=headers)
        response.encoding = 'utf-8'
        tree = html.fromstring(response.text)

        title_elem = tree.xpath('//h1/text()')
        title = title_elem[0].strip() if title_elem else "未获取到标题"
        title = re.sub(r'（.*?）|\(.*?\)', '', title).strip()

        content_element = tree.xpath('//div[@id="content"]')
        if not content_element:
            content_element = tree.xpath('//div[contains(@class, "content")]')

        cleaned_content = ""
        if content_element:
            content_html = html.tostring(content_element[0], encoding='unicode')
            content_html = content_html.replace('<p>', '\n').replace('</p>', '')
            content_html = content_html.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
            content_html = content_html.replace('\xa0', ' ').replace('&nbsp;', ' ')
            cleaned_tree = html.fromstring(content_html)
            content = cleaned_tree.xpath('string()')
            cleaned_content = '\n'.join([line.strip() for line in content.splitlines() if line.strip()])
        else:
            cleaned_content = "未找到文章内容"

        preview_content = f"=== 预览: {title} ===\n\n{indent_paragraphs(cleaned_content)}"
        preview_text.delete(1.0, tk.END)
        preview_text.insert(tk.END, preview_content)
        notebook.select(1)  # 切换到预览标签页

    except Exception as e:
        messagebox.showerror("错误", f"预览失败: {e}")


def start_or_pause_crawl():
    global crawl_state, stop_flag
    if crawl_state == "ready":
        stop_flag = False
        started = start_crawl()
        if started:
            crawl_state = "running"
            crawl_btn.config(text="暂停爬取")
    elif crawl_state == "running":
        stop_flag = True
        crawl_state = "paused"
        crawl_btn.config(text="继续爬取")
        log_text.insert(tk.END, "已暂停爬取...\n")
        log_text.see(tk.END)
    elif crawl_state == "paused":
        stop_flag = False
        started = start_crawl()
        if started:
            crawl_state = "running"
            crawl_btn.config(text="暂停爬取")


def start_crawl():
    global stop_flag, current_url, last_title, chapter_content, page_count, save_path
    if current_url is None:
        start_url = url_entry.get()
        if start_url == "请输入你要爬取小说的url":
            messagebox.showerror("错误", "请输入有效的起始URL")
            return False
        last_title = None
        chapter_content = ""
        page_count = 0
    else:
        start_url = current_url

    filename = filename_entry.get()
    if filename == "请输入保存文件名(无需.txt后缀)":
        messagebox.showerror("错误", "请输入有效的文件名")
        return False

    overwrite_mode = overwrite_var.get()

    if not filename.lower().endswith('.txt'):
        filename += '.txt'
        filename_entry.delete(0, tk.END)
        filename_entry.insert(0, filename)

    if not start_url.startswith('http'):
        messagebox.showerror("错误", "请输入完整的起始URL")
        return False
    if not filename:
        messagebox.showerror("错误", "请输入文件名")
        return False

    full_path = os.path.join(save_path, filename)
    log_text.insert(tk.END, f"文件将保存到: {full_path}\n")
    
    threading.Thread(target=crawl, args=(start_url, filename, log_text, overwrite_mode), daemon=True).start()
    return True


def set_speed():
    global crawl_delay, stop_flag
    if crawl_state == "running":
        messagebox.showwarning("警告", "请先暂停爬取后再修改速度！")
        return
    try:
        val = float(speed_entry.get())
        if val < 0:
            raise ValueError
        crawl_delay = val
        log_text.insert(tk.END, f"已设置爬取速度为 {crawl_delay} 秒/页\n")
        log_text.see(tk.END)
    except Exception:
        messagebox.showerror("错误", "请输入有效的非负数字！")


def reset_crawl():
    global current_url, last_title, chapter_content, crawl_state, stop_flag, page_count
    current_url = None
    last_title = None
    chapter_content = ""
    crawl_state = "ready"
    stop_flag = False
    page_count = 0
    crawl_btn.config(text="开始爬取")
    log_text.delete(1.0, tk.END)
    log_text.insert(tk.END, "已重置爬取状态。\n")
    log_text.see(tk.END)


def open_biquge_home():
    webbrowser.open("http://www.bbbiquge.com/")


def indent_paragraphs(text):
    return '\n'.join(['　　' + line if line.strip() else '' for line in text.splitlines()])


def select_save_path():
    global save_path
    path = filedialog.askdirectory(title="选择保存路径")
    if path:
        save_path = path
        path_label.config(text=f"保存路径: {save_path}")
        log_text.insert(tk.END, f"已设置保存路径为: {save_path}\n")
        log_text.see(tk.END)


# 创建窗口
root = tk.Tk()
root.title("新笔趣阁内小说爬虫")
root.geometry("750x650")

# 顶部按钮栏
top_button_frame = tk.Frame(root)
top_button_frame.pack(pady=10)

home_btn = tk.Button(top_button_frame, text="笔趣阁首页", command=open_biquge_home, width=15)
home_btn.pack(side=tk.LEFT, padx=10)

reset_btn = tk.Button(top_button_frame, text="重置", command=reset_crawl, width=15)
reset_btn.pack(side=tk.LEFT, padx=10)

# 保存路径选择
path_frame = tk.Frame(root)
path_frame.pack(pady=5, fill='x')
tk.Button(path_frame, text="选择保存路径", command=select_save_path).pack(side=tk.LEFT, padx=5)
path_label = tk.Label(path_frame, text=f"保存路径: {save_path}", anchor='w')
path_label.pack(side=tk.LEFT, fill='x', expand=True)

# 创建Notebook作为多标签页容器
notebook = ttk.Notebook(root)
notebook.pack(fill='both', expand=True, padx=10, pady=5)

# 第一页：控制面板
control_frame = ttk.Frame(notebook)
notebook.add(control_frame, text="控制面板")

# URL输入框
url_frame = tk.Frame(control_frame)
url_frame.pack(pady=5, fill='x')
tk.Label(url_frame, text="起始URL:").pack(side=tk.LEFT)
url_entry = tk.Entry(url_frame, width=60)
url_entry.pack(side=tk.LEFT, expand=True, fill='x')


def on_entry_click(event):
    if url_entry.get() == "请输入你要爬取小说的url":
        url_entry.delete(0, tk.END)
        url_entry.config(fg='black')


def on_focusout(event):
    if url_entry.get() == "":
        url_entry.insert(0, "请输入你要爬取小说的url")
        url_entry.config(fg='grey')


url_entry.insert(0, "请输入你要爬取小说的url")
url_entry.config(fg='grey')
url_entry.bind('<FocusIn>', on_entry_click)
url_entry.bind('<FocusOut>', on_focusout)

# 文件名输入框
file_frame = tk.Frame(control_frame)
file_frame.pack(pady=5, fill='x')
tk.Label(file_frame, text="保存文件名:").pack(side=tk.LEFT)
filename_entry = tk.Entry(file_frame, width=60)
filename_entry.pack(side=tk.LEFT, expand=True, fill='x')


def on_filename_click(event):
    if filename_entry.get() == "请输入保存文件名(无需.txt后缀)":
        filename_entry.delete(0, tk.END)
        filename_entry.config(fg='black')


def on_filename_focusout(event):
    if filename_entry.get() == "":
        filename_entry.insert(0, "请输入保存文件名(无需.txt后缀)")
        filename_entry.config(fg='grey')


filename_entry.insert(0, "请输入保存文件名(无需.txt后缀)")
filename_entry.config(fg='grey')
filename_entry.bind('<FocusIn>', on_filename_click)
filename_entry.bind('<FocusOut>', on_filename_focusout)

# 覆盖模式选择
overwrite_var = tk.BooleanVar()
overwrite_check = tk.Checkbutton(control_frame, text="覆盖模式（重复内容时覆盖而不是跳过）", variable=overwrite_var)
overwrite_check.pack(pady=5)

# 速度设置
speed_frame = tk.Frame(control_frame)
speed_frame.pack(pady=5, fill='x')
tk.Label(speed_frame, text="爬取速度(秒):").pack(side=tk.LEFT)
speed_entry = tk.Entry(speed_frame, width=5)
speed_entry.pack(side=tk.LEFT)
speed_entry.insert(0, str(crawl_delay))
tk.Button(speed_frame, text="设置速度", command=set_speed).pack(side=tk.LEFT, padx=5)

# 操作按钮
btn_frame = tk.Frame(control_frame)
btn_frame.pack(pady=10, fill='x')
preview_btn = tk.Button(btn_frame, text="预览内容", width=15, command=preview_content)
preview_btn.pack(side=tk.LEFT, padx=10)
crawl_btn = tk.Button(btn_frame, text="开始爬取", width=15, command=start_or_pause_crawl)
crawl_btn.pack(side=tk.LEFT, padx=10)

# 第二页：预览面板
preview_frame = ttk.Frame(notebook)
notebook.add(preview_frame, text="内容预览")
preview_text = scrolledtext.ScrolledText(preview_frame, width=85, height=25, wrap=tk.WORD, font=('Microsoft YaHei', 10))
preview_text.pack(fill='both', expand=True, padx=10, pady=10)

# 第三页：运行日志
log_frame = ttk.Frame(notebook)
notebook.add(log_frame, text="运行日志")
log_text = scrolledtext.ScrolledText(log_frame, width=85, height=25, wrap=tk.WORD)
log_text.pack(fill='both', expand=True, padx=10, pady=10)

root.mainloop()