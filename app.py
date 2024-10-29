import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from rutube import Rutube
import threading
import os
import random
import string
import webbrowser

# Класс для отображения подсказок
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # Без рамки окна
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

# Класс для отслеживания прогресса записи файла
class ProgressFile:
    def __init__(self, file, callback):
        self.file = file
        self.callback = callback

    def write(self, data):
        self.file.write(data)
        self.callback(len(data))

    def flush(self):
        self.file.flush()

    def close(self):
        self.file.close()

    def __getattr__(self, attr):
        return getattr(self.file, attr)

class RutubeDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Rutube Downloader")
        self.root.geometry("800x600")
        self.root.resizable(False, False)

        # Основной фрейм
        self.main_frame = tk.Frame(root, padx=10, pady=10)
        self.main_frame.pack(fill='both', expand=True)

        # URL Ввод и эмодзи
        self.url_frame = tk.Frame(self.main_frame)
        self.url_frame.pack(pady=5, fill='x')

        self.url_label = tk.Label(self.url_frame, text="URL видео:")
        self.url_label.pack(side='left')

        self.url_entry = tk.Entry(self.url_frame, width=50)
        self.url_entry.pack(side='left', padx=(5, 0))
        self.url_entry.bind("<FocusOut>", self.fetch_resolutions)
        self.url_entry.bind("<Return>", self.fetch_resolutions)  # Запуск при нажатии Enter

        # Кнопка для запуска обработки ссылки
        self.process_button = tk.Button(self.url_frame, text=" ▶", width=2, command=self.fetch_resolutions)
        self.process_button.pack(side='left', padx=(5, 0))

        # Эмодзи для индикации состояния
        self.status_emoji = tk.Label(self.url_frame, text="", font=("Arial", 14))
        self.status_emoji.pack(side='left', padx=(5, 0))

        # Кнопка "?" с подсказкой
        self.help_button = tk.Button(self.url_frame, text="?", width=2, command=self.show_help)
        self.help_button.pack(side='left', padx=(5, 0))
        # Генерация случайного ID для подсказки
        random_id = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        sample_links = [
            f"https://rutube.ru/video/{random_id}/",
            f"rutube.ru/video/{random_id}/",
            f"{random_id}"
        ]
        tooltip_text = (
            "Введите полный URL видео Rutube или только ID видео.\nПримеры:\n" +
            "\n".join(sample_links)
        )
        ToolTip(self.help_button, tooltip_text)

        # Кнопка выбора директории
        self.save_frame = tk.Frame(self.main_frame)
        self.save_frame.pack(pady=5, fill='x')

        self.save_button = tk.Button(self.save_frame, text="Выбрать папку сохранения", command=self.browse_directory)
        self.save_button.pack(side='left')

        self.save_path = tk.StringVar()
        self.save_path.set(os.getcwd())
        self.save_label = tk.Label(self.save_frame, textvariable=self.save_path, wraplength=650, anchor='w')
        self.save_label.pack(side='left', padx=(10, 0))

        # Режим скачивания
        self.mode_frame = tk.LabelFrame(self.main_frame, text="Режим скачивания")
        self.mode_frame.pack(pady=10, fill='x')

        self.mode = tk.StringVar()
        self.mode.set("best")

        self.best_radio = tk.Radiobutton(self.mode_frame, text="Лучшее качество", variable=self.mode, value="best", command=self.update_mode)
        self.best_radio.pack(anchor='w', padx=10, pady=2)

        self.worst_radio = tk.Radiobutton(self.mode_frame, text="Худшее качество", variable=self.mode, value="worst", command=self.update_mode)
        self.worst_radio.pack(anchor='w', padx=10, pady=2)

        self.custom_radio = tk.Radiobutton(self.mode_frame, text="Своё разрешение", variable=self.mode, value="custom", command=self.update_mode)
        self.custom_radio.pack(anchor='w', padx=10, pady=2)

        # Выпадающий список разрешений
        self.resolution_frame = tk.Frame(self.main_frame)
        self.resolution_frame.pack(pady=5, fill='x')

        self.resolution_label = tk.Label(self.resolution_frame, text="Выберите разрешение:")
        self.resolution_label.pack(side='left')

        self.resolution = tk.StringVar()
        self.resolution_dropdown = ttk.Combobox(self.resolution_frame, textvariable=self.resolution, state='disabled')
        self.resolution_dropdown.pack(side='left', padx=(5, 0))

        # Поле для названия файла
        self.filename_frame = tk.Frame(self.main_frame)
        self.filename_frame.pack(pady=5, fill='x')

        self.filename_label = tk.Label(self.filename_frame, text="Название файла:")
        self.filename_label.pack(side='left')

        self.filename_entry = tk.Entry(self.filename_frame, width=40)
        self.filename_entry.pack(side='left', padx=(5, 0))

        self.extension_label = tk.Label(self.filename_frame, text=".mp4")
        self.extension_label.pack(side='left', padx=(5, 0))

        # Кнопка скачивания
        self.download_button = tk.Button(self.main_frame, text="Начать скачивание", command=self.start_download, width=25)
        self.download_button.pack(pady=20)

        # Прогресс-бар
        self.progress_bar = ttk.Progressbar(self.main_frame, orient='horizontal', length=650, mode='determinate')
        self.progress_bar.pack(pady=10)

        # Лог-терминал
        self.log_label = tk.Label(self.main_frame, text="Лог:")
        self.log_label.pack(anchor='w')
        self.log_text = tk.Text(self.main_frame, height=10, state='disabled', wrap='word')
        self.log_text.pack(fill='both', padx=5, pady=(0, 10))

        # Инициализация переменных
        self.download_thread = None
        self.downloading = False
        self.output_path = ""
        self.total_bytes = 0
        self.downloaded_bytes = 0

    def show_help(self):
        # Дополнительная логика при нажатии на кнопку "?"
        pass  # Подсказка уже реализована через ToolTip

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.save_path.set(directory)

    def normalize_url(self, url):
        """
        Нормализует введенную пользователем ссылку.
        Добавляет 'https://' если отсутствует.
        """
        url = url.strip()
        if not url:
            return ""
        if not url.startswith("http"):
            if "rutube.ru/video/" in url:
                url = "https://" + url
            else:
                # Предполагаем, что это ID видео
                url = f"https://rutube.ru/video/{url}/"
        # Убедимся, что URL заканчивается '/'
        if not url.endswith("/"):
            url += "/"
        return url

    def fetch_resolutions(self, event=None):
        url = self.url_entry.get().strip()
        normalized_url = self.normalize_url(url)
        if not normalized_url:
            self.status_emoji.config(text="❌", fg="red")
            self.filename_entry.delete(0, tk.END)
            self.log("Некорректный URL.", error=True)
            return
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, normalized_url)
        self.status_emoji.config(text="⏳", fg="orange")
        self.log(f"Обрабатываем URL: {normalized_url}")
        # Запуск в отдельном потоке, чтобы не блокировать GUI
        threading.Thread(target=self.get_resolutions, args=(normalized_url,), daemon=True).start()

    def get_resolutions(self, url):
        try:
            rt = Rutube(url)
            video = rt.get_best()  # Получаем информацию о видео
            if not video:
                raise Exception("Видео не найдено.")
            resolutions = rt.available_resolutions
            if not resolutions:
                raise Exception("Нет доступных разрешений.")
            resolutions_sorted = sorted(resolutions)
            self.resolution_dropdown['values'] = resolutions_sorted
            # Установить значение по умолчанию
            self.resolution.set(resolutions_sorted[-1])
            # Если режим custom выбран, включить выпадающий список
            if self.mode.get() == "custom":
                self.resolution_dropdown.config(state='readonly')
            else:
                self.resolution_dropdown.config(state='disabled')
            # Установить название файла
            sanitized_title = self.sanitize_filename(video.title)
            self.filename_entry.delete(0, tk.END)
            self.filename_entry.insert(0, sanitized_title)
            # Успешно получили разрешения
            self.status_emoji.config(text="✅", fg="green")
            self.log(f"Доступные разрешения: {', '.join(map(str, resolutions_sorted))}")
        except Exception as e:
            self.resolution_dropdown['values'] = []
            self.resolution.set('')
            self.resolution_dropdown.config(state='disabled')
            self.filename_entry.delete(0, tk.END)
            self.status_emoji.config(text="❌", fg="red")
            self.log(f"Ошибка при получении разрешений: {e}", error=True)

    def sanitize_filename(self, name):
        """
        Удаляет недопустимые символы из имени файла.
        """
        return "".join(c for c in name if c.isalnum() or c in (' ', '.', '_', '-')).rstrip()

    def update_mode(self):
        mode = self.mode.get()
        if mode == "custom":
            self.resolution_dropdown.config(state='readonly')
        else:
            self.resolution_dropdown.config(state='disabled')

    def start_download(self):
        url = self.url_entry.get().strip()
        save_dir = self.save_path.get()
        mode = self.mode.get()
        resolution = self.resolution.get()
        filename = self.filename_entry.get().strip()

        if not url:
            messagebox.showwarning("Предупреждение", "Пожалуйста, введите URL видео.")
            self.log("Пользователь не ввёл URL видео.", error=True)
            return

        if mode == "custom" and not resolution:
            messagebox.showwarning("Предупреждение", "Пожалуйста, выберите разрешение.")
            self.log("Пользователь не выбрал разрешение в режиме 'Своё разрешение'.", error=True)
            return

        if not filename:
            messagebox.showwarning("Предупреждение", "Пожалуйста, укажите название файла.")
            self.log("Пользователь не указал название файла.", error=True)
            return

        # Проверка на наличие запрещенных символов в названии файла
        if any(c in filename for c in r'\/:*?"<>|'):
            messagebox.showwarning("Предупреждение", "Название файла содержит недопустимые символы (\\ / : * ? \" < > |).")
            self.log("Название файла содержит недопустимые символы.", error=True)
            return

        # Запуск скачивания в отдельном потоке
        self.download_thread = threading.Thread(target=self.download_video, args=(url, save_dir, mode, resolution, filename), daemon=True)
        self.download_thread.start()

    def download_video(self, url, save_dir, mode, resolution, filename):
        try:
            self.download_button.config(state='disabled')
            self.size_label.config(text="Размер файла: 0.00 MB")
            self.progress_bar['value'] = 0
            self.progress_bar.config(mode='indeterminate')
            self.progress_bar.start(10)
            self.downloading = True
            self.log("Начало скачивания...")

            rt = Rutube(url)

            if mode == "best":
                video = rt.get_best()
            elif mode == "worst":
                video = rt.get_worst()
            elif mode == "custom":
                video = rt.get_by_resolution(int(resolution))
                if not video:
                    raise Exception(f"Разрешение {resolution} недоступно.")
            else:
                raise Exception("Неизвестный режим скачивания.")

            if not video:
                raise Exception("Видео не найдено.")

            # Установить название файла с расширением
            output_filename = f"{filename}.mp4"
            desired_filepath = os.path.join(save_dir, output_filename)
            self.output_path = desired_filepath

            # Обёртка для отслеживания прогресса
            def progress_callback(bytes_written):
                self.downloaded_bytes += bytes_written
                size_mb = self.downloaded_bytes / (1024 * 1024)
                self.root.after(0, lambda: self.size_label.config(text=f"Размер файла: {size_mb:.2f} MB"))

            self.downloaded_bytes = 0
            with open(desired_filepath, 'wb') as f:
                progress_file = ProgressFile(f, progress_callback)
                video.download(stream=progress_file)

            # Завершение скачивания
            self.downloading = False
            self.progress_bar.stop()
            self.progress_bar.config(mode='determinate')
            self.progress_bar['value'] = 100
            size = os.path.getsize(self.output_path) / (1024 * 1024)  # В MB
            self.size_label.config(text=f"Размер файла: {size:.2f} MB")
            self.log(f"Видео успешно скачано: {self.output_path}")
            self.show_success_dialog()

        except Exception as e:
            self.size_label.config(text="Размер файла: 0.00 MB")
            self.progress_bar.stop()
            self.progress_bar.config(mode='determinate')
            self.progress_bar['value'] = 0
            self.downloading = False
            self.log(f"Ошибка при скачивании: {e}", error=True)
            messagebox.showerror("Ошибка", f"Не удалось скачать видео: {e}")
        finally:
            self.download_button.config(state='normal')

    def show_success_dialog(self):
        # Создание кастомного диалога с кнопкой "Открыть папку"
        success_dialog = tk.Toplevel(self.root)
        success_dialog.title("Успех")
        success_dialog.geometry("400x150")
        success_dialog.resizable(False, False)
        success_dialog.grab_set()  # Блокирует взаимодействие с другими окнами

        message = tk.Label(success_dialog, text="Видео успешно скачано!", font=("Arial", 12))
        message.pack(pady=20)

        open_button = tk.Button(success_dialog, text="Открыть папку", command=lambda: self.open_folder())
        open_button.pack(pady=10)

        close_button = tk.Button(success_dialog, text="Закрыть", command=success_dialog.destroy)
        close_button.pack(pady=5)

    def open_folder(self):
        # Открытие папки с сохранённым файлом
        folder_path = os.path.dirname(self.output_path)
        if os.path.exists(folder_path):
            webbrowser.open(folder_path)
            self.log(f"Открыта папка: {folder_path}")
        else:
            self.log(f"Папка не найдена: {folder_path}", error=True)
            messagebox.showerror("Ошибка", "Папка не найдена.")

    def log(self, message, error=False):
        self.log_text.config(state='normal')
        if error:
            self.log_text.insert(tk.END, f"❌ {message}\n")
        else:
            self.log_text.insert(tk.END, f"✅ {message}\n")
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END)

    def run(self):
        pass  # Нет необходимости в дополнительных методах

if __name__ == "__main__":
    root = tk.Tk()
    app = RutubeDownloaderGUI(root)
    root.mainloop()
