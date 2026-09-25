# SpravaHub Documents

FastAPI-сервіс для генерації трьох юридичних документів:

- `application_recalc` — заява про перерахунок;
- `claim_indexation` — позов про індексацію;
- `claim_recalc` — позов про перерахунок.

## Що важливо

- форма автоматично показує **тільки поля, які потрібні вибраному документу**;
- backend підтримує всі placeholders поточних master-шаблонів;
- перед видачею/відкриттям документа перевіряється, що **не залишилося жодного `{{...}}`**;
- червоне підсвічування змінних із master-шаблонів прибирається з готового документа;
- відмінювання ПІБ виконується локально з можливістю ручного override.

## Два результати генерації

### 1. Завантажити файл

Файл можна отримати у DOCX або PDF.

Для цього лишаються два двигуни:

- **Local** — персональні дані підставляються тільки на SpravaHub VPS;
- **Google export** — створюється тимчасова копія Google Doc, заповнюється, експортується в DOCX/PDF і видаляється.

Готовий документ у цьому сценарії постійно не зберігається.

### 2. Відкрити в Google Docs

При виборі `Відкрити в Google Docs`:

1. створюється **постійна** копія відповідного native Google Doc master;
2. у неї підставляються всі дані;
3. прибирається червоне authoring-підсвічування;
4. перевіряється відсутність `{{...}}`;
5. документ залишається у Google Drive;
6. браузер одразу відкриває його у Google Docs для редагування.

Назва формується приблизно так:

```text
Заява_перерахунок_Прокопов Олександр Ігорович_2026-09-14
```

За замовчуванням документи складаються у папку:

```text
SpravaHub Generated Documents
```

Якщо папки ще немає, backend створить її автоматично. Якщо потрібно використовувати вже існуючу конкретну папку, можна задати її ID у `.env`.

## Google folder settings

```env
GOOGLE_GENERATED_FOLDER_ID=
GOOGLE_GENERATED_FOLDER_NAME=SpravaHub Generated Documents
```

Логіка:

- якщо `GOOGLE_GENERATED_FOLDER_ID` заданий — використовується саме ця папка;
- якщо ID порожній — шукається папка з `GOOGLE_GENERATED_FOLDER_NAME`;
- якщо її немає — вона створюється автоматично.

## Авторизація

Один fixed user задається в `.env`:

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=strong-password
SESSION_SECRET=random-secret
SESSION_HTTPS_ONLY=true
```

## Google OAuth

OAuth client має бути типу **Desktop app**. Після одноразової авторизації:

```bash
python scripts/google_oauth_setup.py
```

створюється:

```text
secrets/google-token.json
```

Поточний scope `https://www.googleapis.com/auth/drive` достатній і для export, і для створення/збереження готових Google Docs.

## Синхронізація master DOCX

Після зміни Google master-шаблонів:

```bash
source .venv/bin/activate
python scripts/sync_local_templates.py
python scripts/validate_templates.py
deactivate
```

Очікується:

```text
OK application_recalc.docx: ... placeholders, all supported
OK claim_indexation.docx: ... placeholders, all supported
OK claim_recalc.docx: ... placeholders, all supported
```

## Поточний SpravaHub VPS

Сервіс слухає локально:

```text
127.0.0.1:8091
```

і підключений до external Docker network:

```text
superbot-edge
```

Traefik маршрутизує:

```text
https://docs.spravahub.com.ua -> spravahub-docgen:8000
```

## Оновлення на VPS

Архів оновлення навмисно **не містить `.env` і `secrets/*`**.

```bash
cd /opt/spravahub-docgen
unzip -o /root/spravahub-docgen-google-open.zip

source .venv/bin/activate
python scripts/sync_local_templates.py
python scripts/validate_templates.py
deactivate

docker compose build --no-cache
docker compose up -d

docker compose ps
curl http://127.0.0.1:8091/health
```

Після оновлення достатньо зробити `Ctrl+F5` на `https://docs.spravahub.com.ua`.

## Приватність

- немає БД справ/history;
- Local download не передає PII Google;
- Google export використовує лише тимчасовий Doc і видаляє його;
- `Відкрити в Google Docs` навмисно **залишає готовий документ у Google Drive**, бо інакше редагування через Google Docs неможливе;
- при помилці підстановки недозаповнена Google-копія автоматично видаляється.

## Google master IDs

- `application_recalc`: `13pl29xCjmo4fDtbHH8Cug5_ssGOqq_reyDW-k4dnjHg`
- `claim_indexation`: `157jeX1I3HERMeiFozpc-wtYOkExPdS4dXHfY2CKGQgY`
- `claim_recalc`: `1bu4hcNQnE9hWx4j6mmYSWTS0j3W4RkiUg2elqheO_OM`

## Довідник адміністративних судів

Для позовів поле суду у веб-формі є випадаючим списком. Дані судів зберігаються в `app/courts.py`; у списку відображається тільки назва суду. Після вибору бекенд автоматично підставляє у документ `{{court.name}}`, `{{court.address}}` та `{{court.phone_line}}`.
