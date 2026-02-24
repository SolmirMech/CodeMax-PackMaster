import os
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk


# noinspection PyTypeChecker,SpellCheckingInspection
class InstallerGUI:
    def __init__(self):
        self.copy_btn = None
        self.error_text = None
        self.error_frame = None
        self.progress = None
        self.status_label = None
        self.root = tk.Tk()
        self.root.title("Установщик CodeMax-PackMaster")
        self.root.geometry("600x300")

        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_path = r"M:\CodeMax-PackMaster"
        self.installer_dir = r"M:\Tests\PackMaster_Installer"

        # ⭐ПУТЬ К ANACONDA PYTHON⭐
        self.anaconda_python = r"C:\Users\User\anaconda3\python.exe"

        self.create_ui()
        self.center_window()

        # Запускаем сборку после создания UI
        self.root.after(100, self.start_build)

    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def create_ui(self):
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Статус
        self.status_label = ttk.Label(main_frame, text="", font=("Arial", 12))
        self.status_label.pack(pady=20)

        # Прогресс-бар
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=10)

        # Текст ошибки (изначально скрыт)
        self.error_frame = ttk.Frame(main_frame)
        self.error_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.error_frame.pack_forget()

        error_header = ttk.Label(self.error_frame, text="Ошибка сборки:", foreground="red", font=("Arial", 10, "bold"))
        error_header.pack(anchor="w")

        self.error_text = tk.Text(self.error_frame, height=8, wrap=tk.WORD, font=("Courier", 9))
        self.error_text.pack(fill=tk.BOTH, expand=True, pady=5)

        scrollbar = ttk.Scrollbar(self.error_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.error_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.error_text.yview)

        # Кнопка копирования ошибки
        self.copy_btn = ttk.Button(self.error_frame, text="Копировать ошибку", command=self.copy_error)
        self.copy_btn.pack(pady=5)

    def copy_error(self):
        """Копирует текст ошибки в буфер обмена"""
        error_text = self.error_text.get("1.0", tk.END).strip()
        if error_text:
            self.root.clipboard_clear()
            self.root.clipboard_append(error_text)
            self.copy_btn.config(text="Скопировано!")
            self.root.after(2000, lambda: self.copy_btn.config(text="Копировать ошибку"))

    def start_build(self):
        """Запускает сборку в отдельном потоке"""
        self.progress.start()
        self.status_label.config(text="🔄 Идёт сборка...")

        # Запускаем сборку в потоке, чтобы не блокировать UI
        thread = threading.Thread(target=self.build_exe)
        thread.daemon = True
        thread.start()

    def get_requirements(self):
        """Читает зависимости из requirements.txt"""
        requirements_path = os.path.join(self.project_path, "requirements.txt")
        dependencies = []

        if os.path.exists(requirements_path):
            try:
                with open(requirements_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and not line.startswith('--'):
                            package = line.split('==')[0].split('>')[0].split('<')[0].strip()
                            if package:
                                dependencies.append(package)
            except Exception as e:
                print(f"Ошибка чтения requirements.txt: {e}")

        return dependencies

    def build_exe(self):
        """Запускает сборку PyInstaller"""
        if not os.path.exists(self.project_path):
            self.show_error(f"Папка проекта не найдена:\n{self.project_path}")
            return

        os.makedirs(self.installer_dir, exist_ok=True)

        try:
            # Настройки зависимостей проекта
            dependencies = self.get_requirements()
            cmd = [
                self.anaconda_python, "-c",
                "import sys; sys.setrecursionlimit(5000); from PyInstaller.__main__ import run; run()",
                "--clean",
                "--distpath", self.installer_dir,
                "--workpath", os.path.join(self.installer_dir, "_temp_build"),
                "--specpath", self.installer_dir,
                "--name", "CodeMax-PackMaster",
                "--noconsole",
                "--exclude", "matplotlib",
                "--exclude", "pandas",
                "--exclude", "sphinx",
                "--exclude", "bokeh",
                "--exclude", "dask",
                "--exclude", "tensorflow",
                "--exclude", "torch",
                "--exclude", "sklearn",
                "--exclude", "keras",
                "--exclude", "jupyter",
                "--exclude", "IPython",
                "--exclude", "PyQt5",
                "--exclude", "PyQt6",
                "--exclude", "PySide2",
                "--exclude", "PySide6",
                "--exclude", "qtpy",
                "--add-data", f"{os.path.join(self.project_path, 'assets')};assets",
                os.path.join(self.project_path, "main.py")
            ]

            for dep in dependencies:
                cmd.extend(["--hidden-import", dep])

            # Добавляем иконку если она существует
            possible_paths = [
                os.path.join(self.project_path, "assets", "icon.ico"),
                os.path.join(self.project_path, "assets", "icons", "icon.ico"),
                os.path.join(self.project_path, "icon.ico"),
            ]

            for icon_test in possible_paths:
                if os.path.exists(icon_test):
                    cmd.extend(["--icon", icon_test])
                    break

            # Запускаем процесс
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                # Успешная сборка
                self.cleanup_after_build()
                self.root.after(0, self.on_build_success)
            else:
                # Ошибка сборки
                error_details = stderr if stderr else stdout
                self.root.after(0, lambda: self.show_error(f"Код ошибки: {process.returncode}\n\n{error_details}"))

        except Exception as e:
            self.root.after(0, lambda: self.show_error(str(e)))

    def on_build_success(self):
        """Действия при успешной сборке"""
        self.progress.stop()
        self.progress.pack_forget()
        self.status_label.config(text="✅ Сборка успешно завершена!")

        # Закрываем окно через 5 секунд
        self.root.after(3000, self.root.destroy)

    def show_error(self, error_text):
        """Показывает ошибку в интерфейсе"""
        self.progress.stop()
        self.progress.pack_forget()

        self.status_label.config(text="❌ Ошибка сборки", foreground="red")

        # Показываем фрейм с ошибкой
        self.error_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Вставляем текст ошибки
        self.error_text.config(state="normal")
        self.error_text.delete("1.0", tk.END)
        self.error_text.insert("1.0", error_text)
        self.error_text.config(state="disabled")

    def cleanup_after_build(self):
        """Удаляем временные файлы после сборки"""
        temp_build_dir = os.path.join(self.installer_dir, "_temp_build")
        spec_file = os.path.join(self.installer_dir, "CodeMax-PackMaster.spec")

        if os.path.exists(temp_build_dir):
            try:
                shutil.rmtree(temp_build_dir)
            except:
                pass

        if os.path.exists(spec_file):
            try:
                os.remove(spec_file)
            except:
                pass


if __name__ == "__main__":
    InstallerGUI().root.mainloop()