# Инструкция по созданию AppImage

Эта инструкция описывает процесс упаковки данного Streamlit-приложения в формат `.AppImage`, который позволит запускать его как обычное десктопное приложение в отдельном окне (без необходимости открывать браузер вручную).

Для реализации "десктопного" поведения мы будем использовать библиотеку `pywebview`, которая создаст окно и отобразит в нем интерфейс приложения.

## Шаг 1: Подготовка скрипта запуска

Создайте файл `run_desktop.py` в корне репозитория. Этот скрипт будет отвечать за копирование файлов приложения в рабочую директорию пользователя (для корректной работы сохранения истории и настроек), запуск Streamlit сервера и открытие окна.

**Содержимое `run_desktop.py`:**

```python
import os
import shutil
import sys
import threading
import time
import socket
import webview
from contextlib import closing

def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

def wait_for_server(port, timeout=10):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                return True
        except (OSError, ConnectionRefusedError):
            time.sleep(0.5)
    return False

def main():
    # 1. Определение рабочей директории
    # AppImage монтируется в режим только для чтения.
    # Чтобы приложение могло сохранять настройки и историю,
    # мы копируем его в ~/.local/share/gemini_tts_app
    app_name = "gemini_tts_app"
    work_dir = os.path.join(os.path.expanduser("~"), ".local", "share", app_name)

    if not os.path.exists(work_dir):
        os.makedirs(work_dir)

    # Директория, где находится сам скрипт (внутри AppImage)
    src_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. Копирование файлов приложения
    files_to_sync = [
        "app.py",
        "managers.py",
        "data_manager.py",
        "tts_engine.py",
        "requirements.txt",
        "settings.json" # Если есть дефолтный конфиг
    ]

    # Всегда обновляем код (.py), но настройки (.json) оставляем пользовательские, если они уже есть
    for filename in files_to_sync:
        src_path = os.path.join(src_dir, filename)
        dst_path = os.path.join(work_dir, filename)

        if os.path.exists(src_path):
            if filename.endswith(".py") or not os.path.exists(dst_path):
                shutil.copy2(src_path, dst_path)

    # Создаем папку для кеша аудио, если нет
    history_cache_dir = os.path.join(work_dir, "history_cache")
    if not os.path.exists(history_cache_dir):
        os.makedirs(history_cache_dir)

    # 3. Переход в рабочую директорию
    os.chdir(work_dir)

    # 4. Запуск Streamlit в отдельном потоке
    port = find_free_port()

    def run_streamlit():
        # Используем sys.executable для запуска streamlit через тот же интерпретатор python
        # --server.headless true отключает попытку открыть браузер самим streamlit
        cmd = f'"{sys.executable}" -m streamlit run app.py --server.port {port} --server.headless true'
        os.system(cmd)

    t = threading.Thread(target=run_streamlit)
    t.daemon = True
    t.start()

    # Ждем, пока сервер запустится
    if not wait_for_server(port):
        print("Не удалось запустить Streamlit сервер")
        sys.exit(1)

    # 5. Запуск окна с приложением
    window = webview.create_window(
        "Gemini TTS",
        f"http://localhost:{port}",
        width=1200,
        height=900
    )
    webview.start()

if __name__ == '__main__':
    main()
```

## Шаг 2: Установка зависимостей

Вам понадобится утилита `appimage-builder`. Установите её:

```bash
# Установка appimage-builder (требуется python3 и pip)
# Рекомендуется использовать виртуальное окружение, но для сборки можно поставить глобально или через pipx
pip install appimage-builder
```

Также убедитесь, что у вас установлен Docker (он часто используется `appimage-builder` для развертывания чистого окружения), или убедитесь, что ваша система соответствует требованиям (Ubuntu 20.04+ или аналоги).

## Шаг 3: Конфигурация сборки

Создайте файл `AppImageBuilder.yml` в корне репозитория. Этот файл описывает, как собирать приложение.

**Содержимое `AppImageBuilder.yml`:**

```yaml
version: 1

AppDir:
  path: ./AppDir
  app_info:
    id: org.gemini.tts
    name: GeminiTTS
    icon: utilities-terminal # Можно заменить на путь к иконке (например, icon.png)
    version: 1.0.0
    exec: usr/bin/python3
    exec_args: "$APPDIR/usr/src/app/run_desktop.py"

  apt:
    arch: amd64
    sources:
      - sourceline: 'deb [arch=amd64] http://archive.ubuntu.com/ubuntu/ jammy main restricted universe multiverse'
      - sourceline: 'deb [arch=amd64] http://archive.ubuntu.com/ubuntu/ jammy-updates main restricted universe multiverse'
    include:
      - python3
      - python3-pip
      - python3-venv
      - python3-dev
      - build-essential
      # Зависимости для pywebview (GTK/WebKit)
      - libgirepository1.0-dev
      - libcairo2-dev
      - libwebkit2gtk-4.0-dev
      - gir1.2-webkit2-4.0
    exclude: []

  files:
    include: []
    exclude:
      - usr/share/man
      - usr/share/doc
      - usr/share/info

  runtime:
    env:
      APPDIR_LIBRARY_PATH: "$APPDIR/usr/lib/x86_64-linux-gnu:$APPDIR/usr/lib"
      PYTHONHOME: "$APPDIR/usr"
      PYTHONPATH: "$APPDIR/usr/lib/python3.10/site-packages:$APPDIR/usr/src/app"

  test:
    fedora:
      image: appimagecrafters/tests-env:fedora-30
      command: ./AppRun --help
    debian:
      image: appimagecrafters/tests-env:debian-stable
      command: ./AppRun --help
    arch:
      image: appimagecrafters/tests-env:archlinux-latest
      command: ./AppRun --help

AppImage:
  arch: x86_64
  update-information: guess
```

> **Важно:** Приведенная выше конфигурация использует репозитории Ubuntu Jammy (22.04). В зависимости от версии `appimage-builder` и вашей системы, вам может потребоваться скрипт для установки pip-пакетов внутрь AppDir.

Однако, `appimage-builder` имеет удобный режим `bundle-python`, который часто проще в настройке. Но самый надежный способ для сложных зависимостей (как streamlit и webview) — это выполнить установку `pip` вручную перед упаковкой.

**Альтернативный (простой) способ сборки через скрипт:**

Вместо сложного yaml, можно подготовить `AppDir` вручную и упаковать его. Вот последовательность команд, которую нужно выполнить в терминале:

```bash
# 1. Создаем структуру AppDir
mkdir -p AppDir/usr/src/app

# 2. Копируем исходный код
cp *.py *.txt *.json AppDir/usr/src/app/
cp run_desktop.py AppDir/usr/src/app/

# 3. Устанавливаем зависимости в AppDir
# Важно: используем pip для установки прямо в директорию
python3 -m pip install --ignore-installed --prefix=$(pwd)/AppDir/usr -r requirements.txt
python3 -m pip install --ignore-installed --prefix=$(pwd)/AppDir/usr pywebview

# 4. Копируем сам python (если хотим полную автономность)
# Это сложный шаг, обычно appimage-builder делает это сам.
# Если вы используете appimage-builder, вернитесь к YAML файлу выше.
```

**Рекомендуемый процесс с `appimage-builder`:**

1.  Убедитесь, что `requirements.txt` содержит `pywebview`. Если нет, добавьте его временно или установите вручную в процессе.
2.  Обновите `AppImageBuilder.yml` добавив секцию `script` для установки зависимостей pip:

Вставьте это в `AppDir` секцию (после `apt`):

```yaml
  after_apt:
    - python3 -m pip install --upgrade pip
    - python3 -m pip install --ignore-installed --prefix=$APPDIR/usr -r requirements.txt
    - python3 -m pip install --ignore-installed --prefix=$APPDIR/usr pywebview
```

3.  Запустите сборку:

```bash
appimage-builder --recipe AppImageBuilder.yml
```

## Запуск

После успешной сборки в папке появится файл (например, `GeminiTTS-1.0.0-x86_64.AppImage`).
Сделайте его исполняемым и запустите:

```bash
chmod +x GeminiTTS-1.0.0-x86_64.AppImage
./GeminiTTS-1.0.0-x86_64.AppImage
```

При первом запуске приложение скопирует свои файлы в `~/.local/share/gemini_tts_app` и запустит окно интерфейса.
