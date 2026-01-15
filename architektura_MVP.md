# Архітэктура MVP (Python backend + JavaScript frontend) без DB і без Redis

## Прынцыпы
- **Няма базы дадзеных**: стан праекта і сцэн — у JSON-файлах
- **Няма Redis/чаргі**: пайплайн запускаецца як background job або асобны worker-працэс (subprocess)
- **Асэты** (аўдыё, выявы, відэа) — у файлах на дыску або ў object storage (GCS/S3) без DB

---

## Кампаненты

### Агульная схема (з Google GenAI)

```
Web/Mobile UI
   │
   ├─(Auth)──────────────────────────────┐
   │                                     │
API Gateway / Backend (Projects API)     │
   │                                     │
   ├─ Object Storage (Audio, Images, Video outputs)
   ├─ JSON (Projects, Segments, Prompts, Versions)
   ├─ Queue / Orchestrator (Jobs, retries, state machine)
   │
   ├─ Audio Analysis Service  ──► Gemini (audio→text+timestamps, summary, emotions)
   ├─ Storyboard Service      ──► Gemini (segments/scenes + structured JSON)
   ├─ Prompt Factory          ──► Gemini (final prompts per scene, negative prompts)
   ├─ Image Generation        ──► Gemini Image (e.g. Gemini Flash Image) / Imagen
   └─ Render Service          ──► ffmpeg (assemble scenes + subtitles + audio)
```

### Frontend (JavaScript)
- Экран Upload + налады (фармат, стыль, субцітры)
- Экран Scenes/Storyboard (спіс сцэн з мініяцюрамі, форма рэдагавання)
- Экран Render/Download
- Атрыманне статусу:
  - **Polling** (MVP-стандарт), або
  - SSE/WebSocket (калі трэба “live”)

### Backend (Python / FastAPI)
- REST API для праектаў/сцэн/рэндэру
- Запуск пайплайна (analysis → storyboard → prompts → images → render)
- Інтэграцыя з Google GenAI SDK (Gemini)
- ffmpeg для склейкі фінальнага MP4

### Storage (без DB)
- Лакальны дыск (`data/`) або бакет (GCS/S3)
- JSON-файлы для стану і прагрэс-інфармацыі

---

## Структура файлаў (рэкамендаваны layout)

```
data/projects/{project_id}/
  source/track.wav
  project.json
  analysis.json
  segments.json
  prompts.json
  images/
    seg_001_v1.png
    seg_001_v2.png
  renders/
    final_v1.mp4
    final_v2.mp4
  jobs/
    pipeline.json
    render.json
```

### Ролі файлаў
- `project.json` — агульныя налады і статус (state machine)
- `analysis.json` — транскрыпт/таймкоды/мood
- `segments.json` — сцэны: start/end + lyric line + intent
- `prompts.json` — прампты і версіі па сцэнах
- `jobs/*.json` — прагрэс, памылкі, лагічныя крокі

---

## Пайплайн MVP (адна кнопка Generate)

1) **Analyze Audio (Gemini)**
   - транскрыпцыя вакалу з timestamps
   - mood/energy (прыкладна)
   → `analysis.json`, update `jobs/pipeline.json`

2) **Build Segments/Storyboard (Gemini)**
   - сцэны з `start_ms/end_ms`, `lyric_text`, `visual_intent`, `mood`
   → `segments.json`, update jobs

3) **Create Prompts (Gemini)**
   - `image_prompt` + `negative_prompt` + `style_hints`
   → `prompts.json`, update jobs

4) **Generate Images (Gemini Image model)**
   - Fast: `gemini-2.5-flash-image`
   - Pro:  `gemini-3-pro-image-preview`
   - для кожнай сцэны генеруецца PNG, захоўваецца як `seg_XXX_vN.png`
   → update jobs

5) **Render Video (ffmpeg)**
   - простая анімацыя (zoom/pan) + пераходы + субцітры (опцыянальна)
   → `renders/final_vN.mp4`, `project.json.status = DONE`

---

## Паток даных end-to-end (варыянт з DB/queue, бліжэй да production)

### Крок A — Upload + ініцыялізацыя праекта
Карыстальнік загружае аўдыя.

Backend:
- кладзе файл у Object Storage;
- стварае запіс `Project` у DB;
- ставіць задачу `ANALYZE_AUDIO` у чаргу.

### Крок B — Аналіз аўдыя (Gemini)
Audio Analysis Service робіць запыт у Gemini з аўдыя-файлам і просіць структураваны адказ (JSON):
- транскрыпцыя вакалу (speech-to-text) з timestamps;
- (опцыйна) speaker diarization (калі ёсць некалькі галасоў);
- выяўленне настрою/эмоцый і “energy curve” па часе;
- кароткі сэнсавы канспект (пра што песня, ключавыя вобразы).

Вынік запісваецца ў DB як `AudioAnalysis`.

**Заўвага:** Gemini добра закрывае “вакал/тэкст/змест”. Для дакладнага біт-трэкінгу часта разумна дадаць DSP-экстракцыю (librosa і пад.), але гэта можна трымаць як дадатковы модуль, а Gemini выкарыстоўваць як галоўны “разумны” інтэрпрэтатар.

### Крок C — Разбіўка на сцэны + сцэнар (Gemini)
Storyboard Service атрымлівае:
- транскрыпт з таймкодамі,
- эмоцыі/энергію,
- (опцыйна) біт-маркеры,
і просіць Gemini сфармаваць спіс сцэн.

Для кожнай сцэны:
- `start_ms`, `end_ms`
- `lyric_line` (радок/фраза або пусто для інструментала)
- `visual_intent` (што паказаць)
- `shot_type` (wide/close-up/abstract)
- `mood` (халодны/цёплы, напружаны/спакойны)
- `style_id` (прэсет стылю праекта)

Вынік: `Segments[]` у DB.

### Крок D — Фабрыка прамптаў (Gemini)
Prompt Factory бярэ кожны `Segment` + “Style Bible” (кароткія правілы стылю праекта) і генеруе:
- `image_prompt`
- `negative_prompt`
- `consistency_hints` (апісанне героя/сімвалаў, каб кадры былі падобныя)

### Крок E — Генерацыя малюнкаў (Gemini)
На гэтым кроку ёсць 2 асноўныя варыянты:

**Варыянт 1: Imagen праз Gemini API**  
Imagen — мадэль генерацыі малюнкаў; у дакументацыі адзначаецца, што яна высокай якасці і мае SynthID watermark.

**Варыянт 2: Gemini image-мадэль (напрыклад, Gemini 2.5 Flash Image)**  
Гэты кірунак карысны, калі вам важныя рэдагаванне, character consistency і “multi-image fusion” для аднолькавых персанажаў у розных сцэнах.

Image Generation Service:
- стварае задачы `GENERATE_IMAGE(segment_id)` у чарзе;
- захоўвае вынікі (PNG/JPEG) у Object Storage;
- фіксуе `seed/model/version/prompt_hash` у DB (для паўтору і кэшу).

### Крок F — Склейка відэа (Render Service)
Render Service збірае:
- аўдыя як асноўную дарожку,
- малюнкі па сцэнах,
- лёгкую анімацыю (Ken Burns/zoom/pan), пераходы,
- субцітры (з транскрыпта) як ASS/SRT,
і рэндэрыць праз ffmpeg у MP4.

Вынік: `final.mp4` у Object Storage + спасылка ў праекце.

---

## Як арганізаваць рэдагаванне “па кавалках”
Ключавая ідэя: праект — гэта набор незалежных сегментаў.

У DB кожны `Segment` мае:
- `analysis` (тэкст, эмоцыя, таймкоды),
- `prompt` (версія N),
- `assets[]` (спіс “take”-аў: `image_v1`, `image_v2`…).

Калі карыстальнік адрэдагаваў адзін сегмент:
1) абнаўляем `Segment.prompt` (новая версія),
2) запускаем `GENERATE_IMAGE` толькі для гэтага сегмента,
3) запускаем `RENDER_FINAL` (склейка хуткая, бо ўсе астатнія ассеты ўжо гатовыя).

---

## Аркестрацыя і стан (каб было надзейна)
Рэкамендуем state machine з ідэмпатэнтнымі крокамі і паўторамі:

```
UPLOADED
ANALYZING → ANALYZED
STORYBOARDING → STORYBOARDED
PROMPTING → PROMPTED
GENERATING_ASSETS → ASSETS_READY
RENDERING → DONE / FAILED
```

Queue патрэбна для:
- паралельнай генерацыі малюнкаў па сегментах,
- retry/backoff,
- абмежавання concurrency (ліміты API).

---

## Размяшчэнне (практычны варыянт на Google Cloud)
Каб мінімізаваць інтэграцыйныя рызыкі з Gemini:
- **Frontend:** Firebase Hosting / Cloud Run static
- **Auth:** Firebase Auth
- **API:** Cloud Run (Projects API)
- **Queue/Events:** Pub/Sub + Cloud Tasks або Workflows
- **Storage:** Cloud Storage
- **DB:** Firestore (хутка) або Cloud SQL (строга)
- **AI:** Gemini/Imagen праз Gemini API або Vertex AI (калі патрэбны enterprise-контроль і палітыкі)

Vertex AI таксама мае “audio understanding (speech only)” і прыклады транскрыпцыі з GCS.

---

## Што важна закласці адразу
- **Structured outputs (JSON)** ад Gemini для ўсіх прамежкавых вынікаў (analysis, storyboard, prompts), каб UI мог стабільна рэндэрыць сцэны.
- **Versioning:** кожны сегмент і яго генерацыі — з версіямі.
- **Prompt hash cache:** калі прампт і налады не змяніліся — не генерыць паўторна.
- **Policy/rights:** песні могуць быць абаронены аўтарскім правам; варта мець “user-owns-rights” флажок і базавыя абмежаванні па распаўсюджванні.

---

## Рэдагаванне па сцэнах (без DB)

### Як захоўваць версіі
- Для кожнай сцэны падтрымліваем `version` у `prompts.json`
- Кожны regenerate дадае новую версію і новы файл `seg_XXX_v{N}.png`

### Regenerate сцэны
1) Frontend робіць PATCH сцэны (intent/prompt)
2) Backend павялічвае версію, генеруе толькі адзін кадр
3) Абнаўляе `jobs/pipeline.json` (кароткая задача)

### Render final
- Склейка выкарыстоўвае “апошнюю версію” для кожнай сцэны

---

## Запуск доўгіх задач без Redis (2 варыянты)

### Варыянт A: Background task у FastAPI (самы просты)
- API запускае `asyncio.create_task(run_pipeline(project_id))`
- Статус пішацца ў `jobs/pipeline.json`

### Варыянт B: Subprocess worker (больш надзейна для MVP)
- API запускае `python worker.py --project_id ...`
- worker робіць аналіз/генерацыю/рэндэр і піша прагрэс у JSON
- API толькі аддае статус і файлы

---

## Мінімальныя API-эндпойнты (FastAPI)

- `POST /projects` — стварыць праект
- `POST /projects/{id}/upload` — загрузіць аўдыё (multipart)
- `POST /projects/{id}/run` — запусціць Generate пайплайн
- `GET  /projects/{id}` — праект + статус
- `GET  /projects/{id}/segments` — сцэны + актуальныя мініяцюры
- `PATCH /projects/{id}/segments/{seg_id}` — абнаўленне intent/prompt
- `POST /projects/{id}/segments/{seg_id}/regenerate` — regenerate аднаго кадра
- `POST /projects/{id}/render` — перарэндэр фінальнага MP4
- `GET  /projects/{id}/jobs` — прагрэс/памылкі

---

## Важныя абмежаванні MVP
- 1 інстанс (без кластару)
- магчымыя канфлікты пры паралельных запусках — патрэбен просты lock на `{project_id}`
- пры падзенні працэсу пайплайн спыняецца; можна зрабіць resume па `project.json`/`jobs/*.json`
