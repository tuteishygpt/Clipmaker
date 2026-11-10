# Архітэктурны план: Разгортванне Clipmaker на Free Tier

Гэты дакумент апісвае архітэктуру і пакрокавую інструкцыю па разгортванні праекта **Clipmaker** у рэжыме гібрыднага безсервернага стэка (**GCP Always Free** + **Cloudflare** + **Supabase**) для працы на 100% Free Tier без падзенняў па памяці.

---

## 0. Асяроддзе распрацоўкі (Git & Workspace)
* **Актыўная галінка:** `feature/free-tier-cloud-run`
* **Ізаляваны воркспейс (Git Worktree):** `D:\googlePRJ\clipmaker-cloud-run`
* **Асноўны рэпазіторый:** `D:\googlePRJ\clipmaker\Clipmaker` (застаецца на `feature/subtitles`)
* **Перавага:** поўная ізаляцыя працы над воблачным воркерам і Docker без уплыву на лакальную версію.

---

## 1. Архітэктура сістэмы

Каб рэндэрынг відэа і аналіз аўдыё не выклікалі памылку `OOM (Out Of Memory)` на бясплатным сэрверы з 1 GB RAM, выкарыстоўваецца гібрыднае раздзяленне нагрузкі:

```mermaid
flowchart TD
    subgraph ClientLayer["1. Кліенцкі слой (Бясплатны глабальны CDN)"]
        User["Карыстальнік (Браўзер)"]
        CF_Pages["Cloudflare Pages<br/>(React SPA, 0$ трафік і хостынг)"]
        User -->|Загрузка інтэрфейсу| CF_Pages
    end

    subgraph APILayer["2. API & Аркестрацыя (GCP Always Free VM)"]
        VM["GCP e2-micro VM (2 vCPU burst, 1 GB RAM)<br/>• Рэгіён: us-central1 / us-east1 / us-west1<br/>• Дыск: 30 GB Standard Persistent Disk<br/>• Сетка: Dual-Stack з бясплатным вонкавым IPv6 (БЕЗ платнага IPv4!)<br/>• Cloudflare Tunnel (cloudflared) -> уваходны трафік 0$<br/>• Лёгкі FastAPI (кіраванне, аўтарызацыя)"]
        User -->|REST API запыты праз CF Tunnel| VM
    end

    subgraph ExternalServices["3. Сэрвісы захоўвання і AI (Free Tier)"]
        Supabase["Supabase Free Tier<br/>• PostgreSQL (метаданыя праектаў, сцэн і задач)<br/>• Auth & RLS"]
        Gemini["Google AI Studio (Gemini API)<br/>• Стварэнне прамптаў і выяваў сцэн"]
        R2["Cloudflare R2 (S3-сумяшчальнае)<br/>• 10 GB сховішча<br/>• 0$ за зыходны трафік кліентам"]
        
        VM -->|Захаванне праектаў і сцэн| Supabase
        VM -->|Прампты і генерацыя кадраў| Gemini
    end

    subgraph WorkerLayer["4. Безсерверны рэндэрынг (GCP Serverless)"]
        CR_Job["Cloud Run Job: clipmaker-render<br/>• Канфігурацыя: 8 vCPU / 16 GiB RAM<br/>• Вобраз: Public ghcr.io (0$ за сховішча кантэйнераў)<br/>• Спампоўвае матэрыялы ў /tmp, рэндэрыць і выгружае ў R2<br/>• Час працы: 35-50 секунд"]
        VM -->|Запуск задачы (Cloud Run API)| CR_Job
        CR_Job -->|Чытае метаданыя| Supabase
        CR_Job -->|Спампоўвае сырыя ассеты| R2
        CR_Job -->|Выгружае фінальны MP4| R2
        CR_Job -->|Абнаўляе статус: COMPLETED| Supabase
    end

    User -.->|Прамы стрымінг / спампоўка MP4| R2
```

---

## 2. Матэматыка Free Tier і ліміты

### 2.1. Віртуальная машына e2-micro і пастка IPv4
* **Умовы Always Free:** рэгіёны `us-central1`, `us-east1` альбо `us-west1`; тып дыска — толькі `pd-standard` да 30 GB.
* ⚠️ **Плата за знешні IPv4:** З 1 лютага 2024 года GCP спаганяе **$0.005/гадзіну (~$3.65–$3.72/мес)** за кожны вонкавы IPv4-адрас.
* ✅ **Рашэнне для 100% 0$:**
  * Ствараць VM **без вонкавага IPv4** (`--no-address`).
  * Уключыць у падсетцы **Dual-Stack з бясплатным вонкавым IPv6 ($0.00)**.
  * Падключыць **Cloudflare Tunnel (`cloudflared`)**, які працуе праз IPv6. Гэта адкрывае доступ да API па HTTPS без платных IP і без платнага Cloud NAT.

### 2.2. Cloud Run Jobs (8 vCPU / 16 GiB RAM)
* **Агульны месячны пул Always Free (Tier 1):**
  * **240 000 vCPU-секунд**.
  * **450 000 GiB-секунд**.
* ⚠️ **Правіла 60 секунд (Minimum Billing):** Кожны запуск Cloud Run Job тарыфікуецца мінімум за 60 секунд.
* **Выдаткі за 1 запуск (пры рэндэры да 60 секунд):**
  * Па CPU: $8\text{ vCPU} \times 60\text{ с} = 480\text{ vCPU-с}$.
  * Па RAM: $16\text{ GiB} \times 60\text{ с} = 960\text{ GiB-с}$.
* **Рэальная ёмістасць Free Tier:**
  $$\text{Па памяці: } \frac{450\,000\text{ GiB}\cdot\text{s}}{960\text{ GiB}\cdot\text{s}} = \mathbf{468\text{ кліпаў у месяц}}$$
  $$\text{Па CPU: } \frac{240\,000\text{ vCPU}\cdot\text{s}}{480\text{ vCPU}\cdot\text{s}} = \mathbf{500\text{ кліпаў у месяц}}$$
  *Вузкім месцам з'яўляецца RAM — ліміт складае **да 468 кліпаў у месяц**.*

### 2.3. Сеткавы трафік (Egress) — выгрузка ў R2
* Спампоўка гатовага відэа карыстальнікам з Cloudflare R2 каштуе **0.00 $**.
* Уваходны трафік у GCP (Ingress) — **0.00 $**.
* ⚠️ **Выхадны трафік з GCP (Egress):** Калі Cloud Run Job адрэндэрыў ролік і адпраўляе яго ў Cloudflare R2, гэты трафік лічыцца **Internet Egress з GCP**. У Always Free уключаны толькі **1 GiB у месяц**.
* **Разлік:**
  * Пры памеры роліка ~40–50 МБ: першыя **20–25 кліпаў у месяц** будуць на **100% 0.00 $**.
  * Пры аптымізацыі (раздзяленне 720×1280, бітрэйт 2.5 Mbps, CRF 24) памер роліка складзе 15–20 МБ — гэта дазваляе рэндэрыць **да 50–60 кліпаў цалкам бясплатна**.
  * Калі рэндэрыць усе 400+ кліпаў, за лішні трафік налічыцца сімвалічная сума **~$1.50 – $2.50 у месяц** ($0.12 за кожны дадатковы GB).

### 2.4. Рэестр кантэйнераў
* Google Artifact Registry дае толькі 0.5 GB (вобраз воркера зойме 1.0–1.3 GB).
* ✅ Выкарыстоўваем **GitHub Container Registry (`ghcr.io`)** або Docker Hub.
* ⚠️ **Умова:** Пакет на GitHub павінен мець статус **Public**, каб Cloud Run мог пуліць вобраз наўпрост без платнага Artifact Registry.

---

## 3. Дакладны пафайлавы спіс змен і прынцып лакальнага Fallback

Усе змены распрацоўваюцца па прынцыпе **зваротнай сумяшчальнасці (Backward Compatibility)**: калі зменныя воблака не зададзеныя, праект працуе **на 100% як раней на лакальным ПК або звычайнай VM**.

### 3.1. Канфігурацыя: `Clipmaker/app/core/config.py`
* Дадаюцца перамыкачы рэжымаў (з дэфолтнымі значэннямі для лакальнага запуску):
  * `RENDER_BACKEND: str = "local"` (варыянты: `"local"` | `"cloud_run"`).
  * `STORAGE_BACKEND: str = "local"` (варыянты: `"local"` | `"s3"`).
  * Параметры падключэння да Cloud Run (`GCP_PROJECT_ID`, `GCP_REGION`, `CLOUD_RUN_JOB_NAME`).
  * Параметры падключэння да Cloudflare R2 / S3 (`S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME`).

### 3.2. Эндпоінты API: `Clipmaker/app/api/projects.py`
* У функцыі запуску рэндэру `render_project` (і `render_standalone`) дадаецца праверка рэжыму:
  * **Калі `RENDER_BACKEND == "local"`:** запускаецца лакальны фанавы паток `background.add_task(pipeline_service.render_only, project_id)` (як і зараз).
  * **Калі `RENDER_BACKEND == "cloud_run"`:** праз кліент `google.cloud.run_v2.JobsClient` адпраўляецца лёгкі HTTP-запыт у GCP для старту кантэйнера воркера з перадачай `--project_id`.

### 3.3. Залежнасці: `Clipmaker/requirements.txt`
* Дадаюцца дзве лёгкія бібліятэкі:
  * `boto3>=1.34.0` — для працы з S3/R2 сховішчам.
  * `google-cloud-run>=0.10.0` — для запуску Cloud Run Jobs з FastAPI.

### 3.4. Воркер рэндэрынгу: `Clipmaker/app/worker.py`
* Выпраўленне бітага імпарту (`from .pipeline import run_pipeline` -> імпарт `PipelineService`).
* Адаптацыя пад асінхронны запуск праз `asyncio.run()`.
* Падтрымка рэжымаў запуску:
  * Калі `STORAGE_BACKEND == "s3"`: спампоўка ассетаў праекта з R2 у часовы каталог кантэйнера `/tmp/{project_id}`, рэндэрынг і загрузка фінальнага MP4 назад у бакет R2.
  * Калі `STORAGE_BACKEND == "local"`: праца наўпрост з лакальнай тэчкай `data/` без звароту ў воблака.

### 3.5. Сховішча файлаў: `Clipmaker/app/repositories/file_storage.py`
* Даданне ўніверсальнага адаптара для S3/R2:
  * Метады атрымання і захавання файлаў падтрымліваюць як лакальны шлях `Path`, так і спампоўку/выгрузку ў S3-сумяшчальнае сховішча.
  * Генерацыя Presigned URLs для прамой аддачы відэа і выяваў кліенту (эканомія трафіку сервера).

### 3.6. Метаданыя праекта: `Clipmaker/app/repositories/project_repo.py`
* Захаванне маніфеста праекта:
  * Перад запускам рэндэру ў воблаку актуальныя `segments.json` і `prompts.json` сінхранізуюцца ў бакет R2 (альбо чытаюцца з Supabase PostgreSQL). Гэта дазваляе ізаляванаму кантэйнеру воркера Cloud Run атрымаць усе патрэбныя таймкоды і налады без наяўнасці агульнага жорсткага дыска з серверам.

### 3.7. Кантэйнерызацыя: новы файл `Dockerfile.worker`
* Кантэйнер на базе `python:3.11-slim`:
  * Устаноўка `ffmpeg`, `libsndfile1`, а таксама сістэмных шрыфтоў (`fonts-dejavu-core`, `fonts-liberation`).
  * Капіяванне лакальных шрыфтоў з `app/static/fonts`.
  * Устаноўка `requirements.txt`.
  * Кропка ўваходу: `ENTRYPOINT ["python", "-m", "app.worker"]`.

### 3.8. Фронтэнд: `Clipmaker/frontend-react`
* У самім кодзе React змены не патрэбныя.
* У файле `.env.production` адрас `VITE_API_BASE_URL` указваецца на дамен Cloudflare Tunnel (напрыклад, `https://api.yourdomain.com`).
* Білд (`npm run build`) дэплоіцца ў Cloudflare Pages (бясплатны глабальны хостынг).

### 3.9. Сетка на e2-micro: Cloudflare Tunnel (`cloudflared`)
* Налады службы `cloudflared` для праксіравання знешніх HTTPS-запытаў на лакальны порт `8000` FastAPI. Гэта цалкам пазбаўляе ад неабходнасці купляць знешні IPv4 і адкрываць парты ў фаерволе.

---

## 4. Падагульняючы бюджэт

| Сцэнар выкарыстання | Штомесячны кошт |
| :--- | :--- |
| **Да 25 кліпаў у месяц (базавы памер 40 МБ)** | **0.00 $ (100% Free)** |
| **Да 50 кліпаў у месяц (аптымізаваны бітрэйт 20 МБ)** | **0.00 $ (100% Free)** |
| **100 кліпаў у месяц** | **~$0.40 – $0.60** (толькі за лішні Egress) |
| **Максімум квоты (468 кліпаў у месяц)** | **~$2.20 – $2.70** (толькі за лішні Egress) |

---

## 5. Актуальныя налады і прадакшн-рэквізіты (Разгорнута 11.11.2026)

### 5.1. Google Cloud Platform (GCP)
* **Актыўны акаўнт:** `user69@belarusbeehive.eu`
* **Праект GCP:** `clipmaker-prod-2026`
* **Плацежны акаўнт (Billing Account):** `014B92-595C6D-A468F6`
* **Асноўны рэгіён:** `us-central1` (Зона VM: `us-central1-a`)
* **Уключаныя API:**
  * `run.googleapis.com` (Cloud Run Admin API)
  * `compute.googleapis.com` (Compute Engine API)
  * `artifactregistry.googleapis.com` (Artifact Registry API)
  * `storage-component.googleapis.com` (Cloud Storage API)

### 5.2. Cloud Run Job (Рэндэрынг)
* **Назва Job:** `clipmaker-render`
* **Канфігурацыя рэсурсаў:** `8 vCPU` / `16 GiB RAM`
* **Таймаўт задачы:** `1800s` (30 хвілін)
* **Docker вобраз:** `ghcr.io/tuteishygpt/clipmaker-worker:latest` (і тэгі `sha-*`)
* **Канфігураваныя зменныя асяроддзя (унутры Job):**
  * `STORAGE_BACKEND=s3`
  * `RENDER_BACKEND=cloud_run`
  * `S3_ENDPOINT_URL=https://e36d7f81ca0e27cb2100b35d5c812b3d.r2.cloudflarestorage.com`
  * `S3_BUCKET_NAME=clipmaker-assets`
  * `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY`
  * `SUPABASE_URL` / `SUPABASE_KEY`
  * `GOOGLE_CLOUD_PROJECT=tuteishygpt-site` (або `clipmaker-prod-2026`)
  * `GOOGLE_CLOUD_LOCATION=global` (для Vertex AI / Gemini мадэляў)
  * `GCP_REGION=us-central1` (для Cloud Run Jobs)
* **Каманда ручнога запуску / тэсту:**
  ```powershell
  gcloud run jobs execute clipmaker-render --args="--project_id=PROJECT_ID,--mode=render" --region=us-central1 --project=tuteishygpt-site --account=svsvec@gmail.com
  ```
* **Прагляд логаў рэндэру:**
  ```powershell
  gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=clipmaker-render" --limit=30 --project=tuteishygpt-site --account=svsvec@gmail.com --format="value(textPayload)"
  ```

### 5.3. Cloudflare R2 (Сховішча ассетаў і MP4)
* **Акаўнт Cloudflare:** `User69@belarusbeehive.eu` (`e36d7f81ca0e27cb2100b35d5c812b3d`)
* **Назва бакета:** `clipmaker-assets`
* **S3 Endpoint:** `https://e36d7f81ca0e27cb2100b35d5c812b3d.r2.cloudflarestorage.com`
* **CORS палітыка:** Наладжана праз `wrangler r2 bucket cors set` для прамой загрузкі (`PUT`) і прайгравання (`GET`/`HEAD`) з `https://clipmaker-frontend.pages.dev` (абыходзіць ліміт 32 MB Cloud Run).
* **Ключы доступу:** наладжаныя ў лакальным `.env` і ў Cloud Run Service / Job.
* **Тэставанне сувязі з R2:**
  ```powershell
  & "D:\googlePRJ\clipmaker\.venv\Scripts\python.exe" scripts/test_s3_connection.py
  ```

### 5.4. Cloudflare Pages + Edge Proxy (`_worker.js`)
* **Назва праекта:** `clipmaker-frontend`
* **Публічны URL:** [https://clipmaker-frontend.pages.dev](https://clipmaker-frontend.pages.dev)
* **API Proxy (`public/_worker.js`):** Перанакіроўвае ўсе запыты `/api/*` на публічны сервер Cloud Run API, захоўваючы паводзіны `307 Redirect` для прамога стрымінгу з R2.
* **Каманда зборкі:** `npm run build` у каталогу `frontend-react`
* **Каманда разгортвання (у production branch `main`):**
  ```powershell
  npx wrangler pages deploy "D:\googlePRJ\clipmaker-cloud-run\frontend-react\dist" --project-name="clipmaker-frontend" --branch=main
  ```

### 5.5. Cloud Run API (`clipmaker-api` на праекце `tuteishygpt-site`)
* **Чаму `tuteishygpt-site`:** У праекце `clipmaker-prod-2026` арганізацыйная палітыка `belarusbeehive.eu` (`iam.allowedPolicyMemberDomains`) блакуе публічны доступ `allUsers` да Cloud Run Service. На акаўнце `svsvec@gmail.com` (`tuteishygpt-site`, Billing `01EB6D-CE8B58-4764AF`) публічны доступ працуе наўпрост.
* **Публічны Endpoint:** `https://clipmaker-api-536283296767.us-central1.run.app`
* **Сінхранізацыя стану:** Праектныя метаданыя, маніфесты, субцітры і статусы заданняў сінхранізуюцца з Cloudflare R2 для поўнай stateless-працы пры маштабаванні або рэстартах.

### 5.6. Рэзервовая VM (`clipmaker-api` на `clipmaker-prod-2026`)
* **Назва VM:** `clipmaker-api` (`e2-micro`, `us-central1-a`, 30 GB pd-standard, VPC `clipmaker-vpc`, без вонкавага IPv4).
* **Падключэнне праз IAP SSH:**
  ```powershell
  gcloud compute ssh clipmaker-api --zone=us-central1-a --project=clipmaker-prod-2026 --tunnel-through-iap
  ```

### 5.7. База дадзеных і Auth (Supabase)
* **URL праекта:** `https://aqcdxlnzrfxqmftsemek.supabase.co`
* **Схема дадзеных:** метаданыя праектаў, сцэн і карыстальнікаў (`supabase_schema.sql`)
