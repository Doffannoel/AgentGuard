# Analisis frontend dan pemetaan RFC backend

RFC yang digunakan: `RFC Backend — AgentGuard.md`, dibaca dari file yang diberikan pengguna. Bagian P0/P1 yang diperlukan Definition of Done menjadi lingkup MVP; daftar P2 adalah roadmap.

| Temuan frontend awal | Implementasi |
| --- | --- |
| Next.js, TanStack Query, semua akses data di `lib/api` | Backend mengikuti path dan DTO camelCase console yang sudah ada; gateway memakai snake_case RFC |
| Login hanya mengarahkan ke project demo | Login Argon2, cookie sesi HttpOnly, logout server dan pembersihan query cache |
| Client tidak mengirim kredensial | `credentials: include`, CORS origin spesifik, validasi Origin untuk mutation cookie |
| Simulasi policy tidak membawa project | `projectId` wajib dan diperiksa terhadap membership |
| YAML hanya divalidasi di browser | Publikasi dokumen ke server, validasi authoritative, immutable version |
| Approval mengubah state lokal | Database approval, expiry, versi policy, hash argumen dan registry, single execution |
| Replay menggunakan timer dan skor rekaan | Polling job PostgreSQL dan hasil kasus nyata saat backend aktif |
| Settings selalu mengaku tersimpan lokal | PATCH project, reload nilai server, error state |
| Audit selalu ditampilkan valid | Hanya menyatakan valid setelah verifikasi berhasil; hasil invalid terlihat |
| Jumlah finding statis | Jumlah dihitung dari finding server |
| Raw key tertinggal di cache mutation | Dihapus saat dialog ditutup, mutation cache `gcTime: 0` |
| Tipe chart tidak menerima UsageRow | Generic chart mengikat value ke keyof row, typecheck berhasil |

## Implementasi per area RFC

| Area | Lokasi |
| --- | --- |
| Tenant/project/user membership, API key, auth | `backend/app/auth.py`, `console.py`, `models.py` |
| Canonical model, adapter Mock/OpenAI-compatible/Ollama | `schemas.py`, `providers.py` |
| Gateway, streaming, interception tool calls | `gateway.py` |
| Policy, kondisi, prioritas, versioning | `policies.py`, migrasi trigger immutable |
| Registry, authorization, approval, execution | `tools.py` |
| Guard/redaksi | `guards.py` |
| Audit chain dan verifikasi | `audit.py` |
| Usage, harga, rate limit, budget reservation | `usage.py` |
| Replay queue dan worker | `replay.py`, `worker.py` |
| Trace, metric, log terstruktur | `observability.py`, `otel.yaml`, `prometheus.yaml` |
| HTTP routing dan kontrak error | `router.py`, `main.py` |
| Database dan migration | `db.py`, `models.py`, `migrations/` |
| Packaging/local/CI | `compose.yaml`, `Dockerfile`, `requirements.lock`, `.github/workflows/backend.yml` |

Business logic dipisahkan dari routing dalam service per domain. Model/schema/database repository query dikonsolidasikan agar tidak menggandakan file router/service/repository untuk setiap entity CRUD. Ini perbedaan struktur dari diagram folder RFC, bukan pemindahan enforcement ke frontend.

## Batas MVP yang perlu diketahui

- Executor optional hanya mock. Tool bisnis nyata perlu integrasi server yang targetnya tetap dan mempunyai idempotency.
- Replay adalah regresi deterministik tool boundary; belum menghasilkan serangan melalui provider LLM.
- Hourly/daily usage dihitung saat query, bukan tabel rollup materialized.
- Worker menggunakan PostgreSQL. Redis/Dramatiq dan seluruh P2 belum ditambahkan.
- Streaming memeriksa input sebelum token pertama; output yang sudah dikirim tidak bisa ditarik kembali.
- Pattern guard tidak menjamin bebas prompt injection/PII. Audit bukan bukti anti-DBA tanpa checkpoint eksternal.
- Provider live, Docker image, collector/Jaeger, dan k6 membutuhkan layanan/binary yang sesuai; hasil validasi aktual dicatat terpisah, tidak diasumsikan dari keberadaan konfigurasi.

Panduan setup dan contoh request ada di `backend/README.md` dan OpenAPI `/docs`.
