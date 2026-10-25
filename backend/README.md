# AgentGuard backend

Backend FastAPI untuk console Next.js di direktori induk. Implementasi mencakup P0 dan fitur P1 yang masuk Definition of Done MVP: redaksi, approval, replay, usage, metrics, dan trace. P2 belum diimplementasikan.

## Menjalankan dengan Docker

Dari root proyek:

```powershell
docker compose up --build -d
docker compose exec api python -m app.cli create-admin --email admin@example.com --tenant "My workspace"
```

Perintah kedua meminta password baru melalui terminal. Tidak ada akun, password, atau API key bawaan. Migrasi dijalankan oleh service `migrate` sebelum API dan worker mulai.

Isi `.env.local` di root frontend:

```dotenv
NEXT_PUBLIC_AGENTGUARD_API_URL=http://localhost:8000
```

Restart `npm run dev`, buka `http://localhost:3000/login`, lalu buat project. Untuk pengujian tanpa biaya, pilih provider `Mock` dan model `mock-model` pada form project.

- Swagger/OpenAPI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`
- Metrics: `http://localhost:8000/metrics`
- Prometheus: `http://localhost:9090`
- Jaeger: `http://localhost:16686`, service `agentguard`

Compose adalah konfigurasi lokal. PostgreSQL, API, dan UI telemetry hanya dipublikasikan ke loopback.

## Menjalankan tanpa Docker di Windows

Gunakan PostgreSQL dan database kosong milik proyek ini, lalu:

```powershell
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.lock
Copy-Item .env.example .env
# Sesuaikan AG_DATABASE_URL di .env.
.venv/Scripts/alembic upgrade head
.venv/Scripts/python -m app.cli create-admin --email admin@example.com --tenant "My workspace"
.venv/Scripts/uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Jalankan `.venv/Scripts/python -m app.worker` di terminal kedua dari `backend`. Pada Linux gunakan `.venv/bin/` sebagai pengganti `.venv/Scripts/`.

## Data contoh (seeder)

Setelah migrasi dan pembuatan admin, jalankan dari folder `backend`:

```powershell
.\.venv\Scripts\python -m app.cli seed-demo --email admin@example.com
```

Gunakan email admin yang sudah ada. Seeder memakai `AG_DATABASE_URL` dari `.env` dan membuat
project **Demo Seeder** di tenant admin tersebut tanpa mengubah project yang sudah ada.
Menjalankan ulang melewati project seed yang sudah dibuat, termasuk jika sudah dihapus melalui console.
Seluruh seed berada dalam satu transaksi; kegagalan membatalkan semua data seed.

Data sintetis mencakup 6 request Mock, 3 tool, 4 rule, 8 tool call, 3 approval
(pending, approved, rejected), temuan redaksi/instruksi mencurigakan, audit chain, dan 6 kasus replay.
Approval pending mengikuti masa berlaku backend (default 15 menit), bukan diperpanjang oleh seeder.
API key internal dibuat acak dan dicabut setelah seed; buat key sendiri di console untuk request baru.
Harga Mock nol ditambahkan hanya jika belum ada konfigurasi harga untuk model tersebut.
Tidak ada akun/password baru, panggilan AI cloud, atau transaksi refund sungguhan.

Refresh halaman Projects lalu buka **Demo Seeder**. Replay awal berstatus queued; jalankan worker
di terminal lain untuk memprosesnya:

```powershell
.\.venv\Scripts\python -m app.worker
```

## Alur penggunaan

1. Masuk ke console dan buat project. Sesi operator menggunakan cookie HttpOnly; API key agent tidak dapat mengakses route administrasi.
2. Buat API key melalui halaman API Keys. Salin sekali; database menyimpan SHA-256 dari secret acak 256-bit. Password operator menggunakan Argon2.
3. Daftarkan tool melalui `PUT /v1/console/projects/{projectId}/tools/{name}`. Endpoint ini memakai cookie console dan header `Origin` sesuai `AG_CONSOLE_ORIGINS`.
4. Publikasikan rule melalui editor Simple atau YAML. Setiap publikasi menghasilkan versi immutable baru. YAML mengganti dokumen aktif; editor Simple menambahkan rule ke versi sebelumnya.
5. Aplikasi agent mengirim `Authorization: Bearer <key>` ke `/v1/chat/completions`, `/v1/tools/authorize`, atau `/v1/tools/execute`.
6. Jika keputusan `REQUIRE_APPROVAL`, operator menyelesaikan approval di console. Agent memanggil `/v1/tools/execute` dengan `tool_call_id`, nama tool, dan argumen asli yang sama.

Contoh registrasi tool (body JSON):

```json
{
  "name": "payment.refund",
  "description": "Refund a payment",
  "risk_level": "HIGH",
  "executor_type": "mock",
  "input_schema": {
    "type": "object",
    "properties": { "amount": { "type": "number", "minimum": 0 } },
    "required": ["amount"],
    "additionalProperties": false
  }
}
```

Dokumen policy mendukung format RFC dan array rule dari editor frontend:

```json
{
  "projectId": "<project-id>",
  "document": {
    "version": 1,
    "defaults": { "tool_action": "deny" },
    "rules": [
      { "id": "refund-small", "match": { "tool": "payment.refund", "conditions": { "amount": { "lte": 500000 } } }, "effect": "allow" },
      { "id": "refund-large", "match": { "tool": "payment.refund", "conditions": { "amount": { "gt": 500000 } } }, "effect": "require_approval" }
    ]
  }
}
```

Operator kondisi: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`. Path tanpa prefix seperti `amount` mengacu ke arguments. Path terstruktur: `arguments.amount`, `actor.id`, `environment`, `security.suspicious_input`, `tenant`, `project`. Actor berasal dari identitas terautentikasi; environment dari project. `match.action: "llm"` menerapkan rule pada gateway LLM; defaultnya `tool`. `match.tool: "*"` cocok dengan semua tool. LLM default ALLOW; tool default DENY; prioritas DENY > REQUIRE_APPROVAL > ALLOW. Signal prompt injection tidak otomatis menolak request.

`/tools/execute` hanya memasang executor `mock` yang tidak mempunyai efek eksternal. Integrasi refund/customer nyata harus berupa executor yang didaftarkan di kode server, dengan target tetap dan idempotency di sistem tujuan. Tidak tersedia executor shell atau HTTP URL dari agent. Provider URL hanya bisa diatur oleh operator server melalui environment. Referensi eksternal JSON Schema ditolak.

Tool call yang dikembalikan model disimpan dan dievaluasi, termasuk tool call yang dirakit dari chunk streaming. Respons memuat `agentguard.tool_decisions`. Proposal model bukan izin mengeksekusi di luar gateway: aplikasi harus mengarahkan eksekusi melalui `/tools/execute` atau menegakkan hasil otorisasi pada executor miliknya.

## Provider, harga, dan limit

- `Mock`: lokal dan deterministik, tanpa network atau biaya.
- `OpenAI`: protokol OpenAI-compatible; `AG_OPENAI_BASE_URL` dan `AG_OPENAI_API_KEY` berasal dari konfigurasi server.
- `Ollama`: protokol `/v1/chat/completions`; `AG_OLLAMA_BASE_URL` default `http://localhost:11434/v1`.
- Model request harus sama dengan model project. Nama model tidak mengubah URL provider.
- Connect timeout 5 detik; deadline keseluruhan 60 detik, termasuk streaming. Upstream error tidak diteruskan mentah ke client.

Harga bersifat versioned dan dapat diperbarui tanpa mengubah controller:

```powershell
docker compose exec api python -m app.cli set-price --provider Mock --model mock-model --input 0 --output 0
```

`--input` dan `--output` adalah USD per juta token. Masukkan harga model sebenarnya saat memakai provider berbayar. Tanpa pricing, request ditandai unpriced; budget aktif menolak request unpriced. Usage aktual menggunakan token yang dilaporkan provider. Angka biaya adalah estimasi, bukan tagihan provider.

Limit per menit dihitung untuk project dan key. Reservasi token harian dan budget dibuat di dalam row lock PostgreSQL sebelum pemanggilan provider. Reservasi input memakai byte UTF-8 ditambah overhead dan batas output `max_tokens`; ini konservatif, sehingga request dapat ditolak lebih awal. Jika provider putus tanpa usage, reservasi dipertahankan hingga pergantian hari UTC. Panggilan yang ditinggalkan karena proses crash ditandai FAILED oleh worker setelah 10 menit.

`GET /v1/usage` menerima `project_id`, `provider`, `model`, `feature`, `environment`, `since`, `until`, dan `period=hourly|daily`. Saat ini rollup dihitung dari `llm_requests`, belum dimaterialisasi dalam tabel `usage_rollups`; tambahkan materialisasi jika volume historis memerlukan. Semua timestamp dan batas harian menggunakan UTC.

## Approval dan audit

Approval terikat ke project, API key pembuat call, hash argumen, konfigurasi registry, versi policy, dan expiry (default 15 menit). Hanya operator admin tenant yang dapat approve/reject. Perubahan policy mengharuskan otorisasi baru. Eksekusi yang sama hanya dapat diselesaikan sekali.

Capture OFF tidak menyimpan prompt; REDACTED menyimpan hasil guard; FULL menyimpan prompt mentah atas pilihan admin. Audit payload selalu melalui redaksi. Regex guard mendeteksi pola umum email, nomor telepon internasional, bearer token, API key, dan credential fields; ini tidak menjamin deteksi semua format PII/secret atau obfuscation.

Audit menggunakan SHA-256 atas representasi JSON kanonik termasuk previous hash, sequence, waktu, project, jenis event, dan payload. Project menyimpan head dan count sehingga perubahan payload, penghapusan di tengah, dan pemotongan ekor dapat ditemukan. Row lock mencegah cabang chain dari penulis bersamaan. Verifikasi tersedia di console dan `POST /v1/audit/verify?project_id=...`.

Chain bukan tanda tangan eksternal: administrator database yang dapat menulis ulang seluruh chain beserta head masih bisa memalsukannya. Arsipkan checkpoint head ke penyimpanan independen bila threat model mencakup DBA. Migrasi memasang trigger yang menolak UPDATE/DELETE policy_versions.

## Replay dan observability

`POST /v1/attack-cases` menerima structured `input` berisi `tool`, `arguments`, dan `context`, beserta `expected_tool` dan `expected_decision`. `POST /v1/replay-runs` mengambil snapshot kasus dan versi policy aktif, lalu mengantrekan pekerjaan PostgreSQL. Worker memilih job dengan `FOR UPDATE SKIP LOCKED` dan menggunakan evaluator guard/policy/registry yang sama dengan otorisasi runtime. Replay tidak mengeksekusi tool eksternal dan belum menjalankan generasi LLM nondeterministik.

Satu suite diproses dalam satu transaksi; rollback/crash mengembalikan job ke antrean. UI polling dapat melihat queued lalu completed tanpa status running per-kasus yang sudah committed. Redis/Dramatiq belum diperlukan untuk jalur ini.

OpenTelemetry membuat span request, guard, policy, provider, tool, dan execution. Ekspor OTLP aktif bila `AG_OTLP_ENDPOINT` diisi; Compose mengarahkannya ke collector dan Jaeger. Prometheus mengambil metric API port 8000 serta metric worker port 8002, termasuk counter replay. Hasil replay persisten juga tersedia dari endpoint run.

## Pengujian

```powershell
cd backend
.venv/Scripts/ruff check app tests migrations
.venv/Scripts/ruff format --check app tests migrations
.venv/Scripts/pyright
.venv/Scripts/python -m pytest -q
```

Tanpa `AG_TEST_DATABASE_URL`, pytest memakai SQLite sementara dan melewati test row-lock. Untuk PostgreSQL gunakan database disposable khusus pengujian:

```powershell
$env:AG_TEST_DATABASE_URL="postgresql+psycopg://agentguard:password@localhost:5432/agentguard_test"
$env:AG_DATABASE_URL=$env:AG_TEST_DATABASE_URL
.venv/Scripts/alembic upgrade head
.venv/Scripts/alembic check
.venv/Scripts/python -m pytest -q
cd ..
npx playwright install chromium
npm run test:e2e:backend
```

Browser test memakai API port 8001 dan frontend port 3010, membuat akun acak dan project pengujian. Data uji tidak dipakai sebagai akun aplikasi. Test frontend demo tetap tersedia lewat `npm run test:e2e`.

`tests/load.js` adalah k6 untuk 1.000 gateway calls dan 1.000 authorization calls dengan 50 VU masing-masing. Gunakan project benchmark terpisah dengan provider Mock, tool `benchmark.lookup`, rule allow, limit RPM >= 10000, dan token harian cukup. Jalankan `k6 run -e AG_API_KEY=<key> tests/load.js`. Target RFC p95 bukan hasil benchmark yang diklaim oleh implementasi ini.

Workflow GitHub Actions mencakup Ruff, Pyright, pytest PostgreSQL, migrasi, build frontend, browser integration, Gitleaks, Docker build, dan container health. Belum ada deployment otomatis atau kredensial cloud.

## Batas deployment

Aktifkan `AG_SECURE_COOKIES=true`, gunakan HTTPS dan daftar origin spesifik. Cookie SameSite=Lax membutuhkan frontend/API pada site yang sama; gunakan subdomain dalam domain yang sama atau reverse proxy jika frontend di Vercel. Jangan mengandalkan cookie lintas site berbeda. Batasi `/metrics` dan UI telemetry pada jaringan operator. Ubah password PostgreSQL lokal sebelum deployment dan gunakan role runtime dengan hak minimum.

Kontrak gateway mengikuti subset OpenAI chat text/function tools. Endpoint `/v1/responses`, multimodal, OPA, MCP, webhook, Slack, Anthropic/Gemini, routing model, dan rekomendasi FinOps merupakan pekerjaan lanjutan RFC.

Referensi implementasi: [FastAPI security](https://fastapi.tiangolo.com/tutorial/security/), [SQLAlchemy 2 ORM](https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html), [HTTPX async](https://www.python-httpx.org/async/).
