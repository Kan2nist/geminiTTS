# Gemini TTS Studio

Gemini TTS Studio is a Streamlit-based web application designed for batch generation of character voiceovers using Google's Gemini 2.5 Pro TTS models. It provides a user-friendly interface for managing characters, configuring rate limits, and processing script files with persistent history and audio caching.

## Features

- **Model Management**: Support for multiple Gemini models (defaulting to `gemini-2.5-pro-preview-tts`) with fallback mechanisms.
- **Rate Limiting**: User-configurable rate limits (requests per minute/day) with visual gauges using Plotly.
- **Character Management**: Create and persist character profiles with specific voice assignments and style instructions.
- **Batch Generation**: Process multi-line scripts with format validation (`Character | Text | Filename`).
- **Version Control**: Generate multiple versions of audio lines and select specific versions for the final export.
- **History & Persistence**: Local caching of generated audio and request history. Settings and usage logs are persisted via JSON.
- **Export**: Download selected audio versions as a ZIP archive.

## Installation

Prerequisites: Python 3.8+

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Run the application:**
   ```bash
   streamlit run app.py
   ```

2. **Configuration:**
   - Enter your Google Gemini API Key in the sidebar.
   - Adjust model selection and rate limits if necessary.

3. **Workflow:**
   - **Add Characters**: Define characters in the "Character Manager" with specific voices and style prompts.
   - **Input Script**: Enter your script in the "Batch Audio Generation" section using the format: `Character Name | Text to speak | Filename`.
   - **Generate**: Click "Generate Audio" to process the queue.
   - **Review & Export**: Listen to generated files, regenerate if needed, and download the final package as a ZIP file.

---

# Gemini TTS Studio (RU)

Gemini TTS Studio — это веб-приложение на базе Streamlit, предназначенное для пакетной генерации озвучки персонажей с использованием моделей Google Gemini 2.5 Pro TTS. Приложение предоставляет интерфейс для управления персонажами, настройки лимитов запросов и обработки скриптов с сохранением истории и кэшированием аудио.

## Функциональные возможности

- **Управление моделями**: Поддержка нескольких моделей Gemini (по умолчанию `gemini-2.5-pro-preview-tts`) с механизмами отката.
- **Ограничение скорости (Rate Limiting)**: Настраиваемые пользователем лимиты (запросов в минуту/день) с визуализацией через Plotly.
- **Управление персонажами**: Создание и сохранение профилей персонажей с назначением голоса и инструкций по стилю.
- **Пакетная генерация**: Обработка многострочных скриптов с валидацией формата (`Имя Персонажа | Текст | Имя файла`).
- **Версионность**: Генерация нескольких вариантов аудио для одной реплики и выбор конкретной версии для финального экспорта.
- **История и сохранение данных**: Локальное кэширование сгенерированных аудиофайлов и истории запросов. Настройки и логи использования сохраняются в JSON.
- **Экспорт**: Скачивание выбранных версий аудио в виде ZIP-архива.

## Установка

Требования: Python 3.8+

1. **Клонируйте репозиторий:**
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Создайте и активируйте виртуальное окружение:**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```

3. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

## Использование

1. **Запуск приложения:**
   ```bash
   streamlit run app.py
   ```

2. **Настройка:**
   - Введите ваш API Key для Google Gemini на боковой панели.
   - При необходимости измените модель и лимиты запросов.

3. **Рабочий процесс:**
   - **Добавление персонажей**: Определите персонажей в "Character Manager", указав голос и стиль речи.
   - **Ввод скрипта**: Введите текст скрипта в разделе "Batch Audio Generation", используя формат: `Имя Персонажа | Текст для озвучки | Имя файла`.
   - **Генерация**: Нажмите "Generate Audio" для обработки очереди.
   - **Обзор и экспорт**: Прослушайте сгенерированные файлы, перегенерируйте при необходимости и скачайте итоговый пакет в виде ZIP-файла.
