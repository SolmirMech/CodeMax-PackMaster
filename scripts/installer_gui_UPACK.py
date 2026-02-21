import os
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class InstallerGUI:
    def __init__(self):
        self.clean_build = None
        self.root = tk.Tk()
        self.root.title("Установщик CodeMax-PackMaster")
        self.root.geometry("500x300")
        
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_path = tk.StringVar(value=r"M:\CodeMax-PackMaster")
        
        # ⭐ПУТЬ К ANACONDA PYTHON⭐
        self.anaconda_python = r"C:\Users\User\anaconda3\python.exe"
        
        self.create_ui()    
        self.center_window()
        
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
        
        # Выбор папки проекта
        ttk.Label(main_frame, text="Путь к папке проекта:").pack(anchor="w", pady=(0, 5))
        
        path_frame = ttk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Entry(path_frame, textvariable=self.project_path, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="Обзор", command=self.browse_folder).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Опция очистки предыдущей сборки
        self.clean_build = tk.BooleanVar(value=True)
        ttk.Checkbutton(main_frame, text="Очистить предыдущую сборку", variable=self.clean_build).pack(anchor="w", pady=(20, 10))
        
        # Кнопки
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(btn_frame, text="Собрать EXE", command=self.build_exe).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Отмена", command=self.root.quit).pack(side=tk.RIGHT)
        
    def browse_folder(self):
        folder = filedialog.askdirectory(
            title="Выберите папку с проектом",
            initialdir=self.script_dir
        )
        if folder:
            self.project_path.set(folder)
    
    @staticmethod
    def get_requirements(project_path):
        """Читает зависимости из requirements.txt"""
        requirements_path = os.path.join(project_path, "requirements.txt")
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
        project_path = self.project_path.get()
        if not project_path or not os.path.exists(project_path):
            messagebox.showerror("Ошибка", "Укажите корректный путь к проекту")
            return

        # Фиксированный путь для сборки
        installer_dir = r"M:\Tests\PackMaster_Installer"
        os.makedirs(installer_dir, exist_ok=True)

        try:
            # Настройки зависимостей проекта
            dependencies = self.get_requirements(project_path)
            cmd = [
                self.anaconda_python, "-c",
                "import sys; sys.setrecursionlimit(5000); from PyInstaller.__main__ import run; run()",
                "--clean",
                "--distpath", installer_dir,
                "--workpath", os.path.join(installer_dir, "_temp_build"),
                "--specpath", installer_dir,
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
                "--add-data", f"{os.path.join(project_path, 'assets')};assets",
                os.path.join(project_path, "main.py")
            ]

            for dep in dependencies:
                cmd.extend(["--hidden-import", dep])

            # Добавляем иконку если она существует
            possible_paths = [
                os.path.join(project_path, "assets", "icon.ico"),
                os.path.join(project_path, "assets", "icons", "icon.ico"),
                os.path.join(project_path, "icon.ico"),
            ]

            for icon_test in possible_paths:
                if os.path.exists(icon_test):
                    cmd.extend(["--icon", icon_test])
                    break

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            process.communicate()  # Переменные не нужны, так как не используются

            if process.returncode == 0:
                self.cleanup_after_build(installer_dir)
                messagebox.showinfo("Успех",
                                    f"EXE успешно собран!\n"
                                    f"Папка: {installer_dir}\n"
                                    f"Запускаемый файл: CodeMax-PackMaster.exe")

                try:
                    os.startfile(installer_dir)
                except:
                    pass
            else:
                error_msg = f"Ошибка сборки (код: {process.returncode})"
                messagebox.showerror("Ошибка", error_msg)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить PyInstaller: {str(e)}")
            
    @staticmethod
    def cleanup_after_build(installer_dir):
        """Удаляем временные файлы после сборки
        :param installer_dir:
        """
        temp_build_dir = os.path.join(installer_dir, "_temp_build")
        spec_file = os.path.join(installer_dir, "CodeMax-PackMaster.spec")
        
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