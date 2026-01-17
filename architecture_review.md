# Аналіз архітэктуры праекта і Прапанова (Correct Architecture)

## 1. Аналіз бягучага стану (Current State Analysis)

Праект уяўляе сабой MVP (Minimum Viable Product) на базе **FastAPI**, які выкарыстоўвае файлавую сістэму (JSON) замест базы дадзеных.

### Моцныя бакі:
*   **Прастата**: Лёгкі старт, не патрабуе ўсталёўкі PostgreSQL/Redis.
*   **Google GenAI Integration**: Добрая модульнасць у `genai_client.py`.
*   **Гнуткасць**: JSON-файлы лёгка чытаць і дэбажыць.

### Праблемы і Рызыкі (Issues):
1.  **Праблема канкурэнтнасці (Race Conditions)**:
    *   У `storage.py` адбываюцца запісы ў JSON (`write_json`). Калі REST API і Background Task паспрабуюць запісаць у адзін файл адначасова, дадзеныя будуць страчаны або файл сапсуецца.
    *   *Рашэнне*: Патрэбны **file locks** або пераход на SQLite/DB.

2.  **Маналітнасць логікі ў `pipeline.py`**:
    *   Файл `pipeline.py` змяшчае ў сабе і бізнес-логіку, і працу з файламі, і аркестрацыю. Гэта ўскладняе тэставанне і падтрымку.

3.  **Адсутнасць Structured Outputs**:
    *   У `genai_client.py` выкарыстоўваюцца Regex (`re.search`) для "вылоўлівання" JSON з адказаў LLM. Гэта ненадзейна.
    *   *Рашэнне*: Выкарыстоўваць **Pydantic schemas** у запытах да Gemini (feature: Structured Output).

4.  **Блакаванне сэрвера рэндэрынгам (Blocking I/O)**:
    *   Рэндэрынг відэа (`RenderService`) — цяжкая аперацыя. Запуск яе ў `BackgroundTasks` FastAPI можа запаволіць або заблакаваць асноўны працэс API, асабліва калі `moviepy` выкарыстоўвае шмат CPU.
    *   *Рашэнне*: Вынас цяжкіх задач у асобны працэс (Worker).

---

## 2. Правільная Архітэктура (Proposed Architecture)

Каб зрабіць праект маштабаваным і надзейным, прапануецца **Слаістая Архітэктура (Layered Architecture)**.

### Асноўныя прынцыпы:
1.  **Separation of Concerns (Раздзяленне адказнасці)**: UI асобна, Бізнес-логіка асобна, Захоўванне дадзеных асобна.
2.  **Repository Pattern**: Код, які працуе з дыскам (JSON), павінен быць ізаляваны.
3.  **Worker Pattern**: Генерацыя відэа павінна адбывацца па-за вэб-сэрверам.

### Структура папак (Рэкамендаваная):

```text
Clipmaker/
├── app/
│   ├── api/                 # API Endpoints (routes)
│   │   ├── __init__.py
│   │   ├── projects.py      # /projects/...
│   │   └── web.py           # Статыка і HTML
│   │
│   ├── core/                # Канфігурацыя і налады
│   │   ├── config.py        # Env vars (GENAI_API_KEY і інш.)
│   │   └── logging.py
│   │
│   ├── services/            # Бізнес-логіка (Use Cases)
│   │   ├── audio_service.py # Аналіз аўдыя (Librosa + GenAI)
│   │   ├── story_service.py # Генерацыя сцэнара
│   │   ├── image_service.py # Генерацыя карцінак
│   │   └── render_service.py# Зборка відэа (ffmpeg/moviepy)
│   │
│   ├── repositories/        # Праца з дадзенымі (Data Layer)
│   │   ├── json_repo.py     # Чытанне/Запіс JSON з блакіроўкамі (Locks)
│   │   └── file_storage.py  # Захаванне малюнкаў/аўдыя
│   │
│   ├── clients/             # Знешнія інтэграцыі
│   │   └── genai.py         # Google Gemini Client
│   │
│   ├── schemas/             # Pydantic мадэлі (Common data structures)
│   │   ├── project.py
│   │   ├── segment.py
│   │   └── analysis.py
│   │
│   ├── worker.py            # Асобны скрыпт для апрацоўкі чаргі задач
│   └── main.py              # Кропка ўваходу FastAPI
│
├── data/                    # Дадзеныя карыстальнікаў (па-за кодам)
└── frontend/                # JS/HTML
```

### Дэталёвае апісанне зменаў:

#### 1. Repository Layer (`repositories/`)
Замест прамых выклікаў `load_json`/`write_json` у `storage.py`, ствараем клас `ProjectRepository`.
*   Ён адказвае за захаванне стану праекта.
*   **ВАЖНА**: Дадаем `FileLock` (бібліятэка `filelock`), каб пазбегнуць адначацовага запісу.

#### 2. Service Layer (`services/`)
Раздзяляем `pipeline.py` на некалькі сэрвісаў.
*   `AnalysisService`: Прымае `project_id`, вяртае структуру аналізу. Не ведае пра HTTP.
*   `RenderingService`: Атрымлівае спіс файлаў і налад, вяртае шлях да MP4.

#### 3. Structured Outputs (GenAI)
Перапісваем `genai.py` каб выкарыстоўваць `Pydantic` схемы для `response_schema` ў Gemini 1.5/2.0. Гэта прыбярэ патрэбу ў Regex і гарантуе, што мы заўсёды атрымаем валідны JSON.

#### 4. Background Worker (Чаргу задач)
Для пачатку ("MVP+") можна пакінуць `BackgroundTasks`, але лепш зрабіць найпрасцейшую чаргу на файлавай сістэме:
*   API стварае файл `data/queue/task_123.json`.
*   Асобны працэс `python worker.py` сочыць за папкай, бярэ задачы і выконвае іх.
*   Гэта не заблакуе API, калі ідзе цяжкі рэндэрынг.

## План пераходу (Refactoring Plan)

1.  **Move & Split**: Раскласці існуючы код `pipeline.py` і `storage.py` па папках `services/` і `repositories/`.
2.  **Schema Enforcement**: Укараніць Pydantic мадэлі для ўсіх JSON-структур (Segments, Project).
3.  **Locking**: Дадаць файлавыя блакіроўкі.
4.  **Worker**: Вылучыць `render_project` у асобны працэс.
