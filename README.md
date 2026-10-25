# AgentGuard

AgentGuard adalah **AI security gateway** untuk membantu tim mengendalikan bagaimana aplikasi dan AI agent berinteraksi dengan model bahasa serta tools yang dapat menimbulkan dampak nyata. AgentGuard memeriksa request, menerapkan policy, dan mencatat keputusan agar aktivitas AI dapat ditinjau oleh operator.

## Gambaran umum

AgentGuard terdiri dari dua bagian yang bekerja bersama:

- **Backend** menangani gateway request, autentikasi, evaluasi policy, approval, audit, replay, usage, dan telemetry. Backend adalah sumber keputusan keamanan.
- **Frontend** menyediakan console untuk mengelola project, policy, API key, approval, aktivitas, replay, dan penggunaan. Frontend menampilkan keputusan backend; frontend tidak menegakkan kontrol keamanan sendiri.

Alur sederhananya:

```text
Aplikasi / AI agent
        |
        v
AgentGuard backend ──> Evaluasi guard dan policy
        |                         |
        |              ALLOW / DENY / APPROVAL
        |                         |
        v                         v
Model atau tool             Console operator
        |
        v
Audit dan telemetry
```

## Kapabilitas utama

- **Gateway model dan tools** untuk menerima request AI dan mengevaluasi tool call berdasarkan konteks serta policy project.
- **Policy yang dapat dikelola operator**, termasuk keputusan `ALLOW`, `DENY`, dan `REQUIRE_APPROVAL`, serta publikasi versi policy yang tidak dapat diubah.
- **Human approval** untuk tindakan berisiko, dengan keputusan yang terikat pada project, identitas pemanggil, argumen, dan versi policy.
- **Audit dan investigasi** melalui aktivitas, detail keputusan, redaksi payload, serta verifikasi rantai audit.
- **Replay skenario keamanan** untuk menguji hasil evaluasi terhadap kasus serangan atau regresi tanpa menjalankan tool eksternal.
- **Usage dan observability** untuk melihat penggunaan, estimasi biaya, latency, error, metrics, dan trace.
- **Penyedia model** Mock untuk pengujian lokal, serta integrasi OpenAI-compatible dan Ollama melalui konfigurasi backend.

## Struktur proyek

| Direktori | Tanggung jawab |
| --- | --- |
| [`backend/`](backend/) | API FastAPI, policy dan guard, autentikasi, database, worker replay, audit, serta observability. |
| [`frontend/`](frontend/) | Console Next.js untuk operator dan antarmuka pengelolaan AgentGuard. |

## Teknologi

- **Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL, Alembic, OpenTelemetry, dan Prometheus.
- **Frontend:** Next.js, React, TypeScript, Tailwind CSS, TanStack Query, Zod, dan Playwright.

## Batasan MVP

Backend saat ini hanya menyediakan executor `mock` bawaan; eksekusi tool nyata memerlukan executor yang ditambahkan secara eksplisit di sisi server. Replay menggunakan evaluator guard dan policy yang sama dengan runtime, tetapi tidak mengeksekusi tool eksternal atau menjalankan generasi LLM nondeterministik. Dukungan gateway juga terbatas pada subset OpenAI Chat Completions yang didokumentasikan backend.

## Dokumentasi

- [README backend](backend/README.md) — detail backend, konfigurasi, penggunaan, pengujian, dan batas implementasi.
- [README frontend](frontend/README.md) — detail console, alur UI, struktur frontend, dan panduan menjalankan frontend.
- [Kontrak API](frontend/API_CONTRACT.md) — kontrak komunikasi frontend dan backend.
