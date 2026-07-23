# Instruksi Rebuild ZFace Desktop (.exe)

> Ditujukan untuk **Claude di komputer lain** yang punya environment build ZFace.
> Ditulis 2026-07-23. Tugas: **build ulang .exe** setelah perbaikan performa kamera.

## Konteks — kenapa perlu rebuild

Ada perbaikan **performa kamera** (bukan fitur baru, **tidak ada dependency baru**):

- `app/camera.py` (BARU): `open_capture()` memaksa backend **DirectShow (`cv2.CAP_DSHOW`)** di
  Windows karena backend default **MSMF lambat buka kamera (2-5 detik)**. + fallback default.
- `ui/tab_identify.py` & `ui/tab_register.py`: buka kamera lewat helper itu + `CAP_PROP_BUFFERSIZE=1`.
- `ui/tab_register.py`: kamera kini dibuka **di `CameraThread` (QThread)**, bukan di UI thread —
  supaya UI **tidak freeze** saat start. + `stop_camera()` dipanggil saat logout/close.
- `build.spec`: perbaikan agar path data insightface diambil dari **modul yang ter-import**
  (robust untuk venv/user-site), bukan scan `site.getsitepackages()` yang rapuh.

Commit terkait sudah ada di branch `main` (repo `djvpri/zface-desktop`). Semua perubahan
**pure Python** → rebuild hanya mem-package ulang, tidak perlu install apa pun yang baru
selama environment lama sudah lengkap.

## Prasyarat WAJIB

Build **HARUS** dijalankan dengan **Python yang SAMA** tempat ZFace biasa dijalankan/di-build
sebelumnya (yang punya insightface, PyQt6, onnxruntime, dll terpasang).

- **Jangan pakai Python 3.13/3.14** kalau harus install ulang deps — `insightface`/`onnx`
  sering belum punya wheel untuk versi itu → pip akan compile dari source (butuh MSVC) & gagal.
  Versi aman: **3.10 / 3.11 / 3.12**.
- Kalau ada beberapa Python / venv, panggil interpreter yang benar secara eksplisit, mis.
  `C:\path\ke\venv\Scripts\python.exe build.py` (bukan sekadar `python`).

## Langkah

```powershell
# 1. Masuk ke repo & ambil kode terbaru (berisi fix kamera + build.spec)
cd <path>\zface-desktop
git pull origin main

# 2. Pastikan dependency ada di env yang aktif (harus SUKSES tanpa error)
python -c "import insightface, cv2, PyQt6, onnxruntime, numpy; print('deps OK')"
#   -> kalau ModuleNotFoundError: aktifkan venv yang benar, atau:
#      pip install -r requirements.txt   (di env versi 3.10-3.12)

# 3. Pastikan PyInstaller ada
python -c "import PyInstaller; print(PyInstaller.__version__)"
#   -> kalau tidak ada: pip install pyinstaller

# 4. TUTUP ZFace.exe kalau sedang berjalan (kalau tidak, folder dist/ terkunci saat dihapus)
Get-Process ZFace -ErrorAction SilentlyContinue | Stop-Process

# 5. Build
python build.py
```

## Hasil & verifikasi

- Output: **`dist/ZFace-Desktop/ZFace.exe`** (script cetak ukuran folder di akhir).
- Jalankan `ZFace.exe`, lalu uji:
  - Tab **Identifikasi** → Mulai Kamera → harus terbuka **cepat (<1 detik)**, tidak lagi
    lama seperti sebelumnya.
  - Tab **Daftarkan** → Aktifkan Kamera → **UI tidak freeze** saat start.
- Model `buffalo_l` (~280MB) auto-download ke `models/` saat pertama run (normal, bukan bagian build).

## Kalau ada masalah

- **`StopIteration` / `ModuleNotFoundError: insightface` saat baca build.spec** → insightface
  tidak terpasang di Python yang dipakai. Betulkan env (lihat Prasyarat), jangan lanjut build.
- **Index kamera bergeser** setelah pakai DirectShow (DSHOW kadang mengurutkan device beda
  dari MSMF) → pilih ulang di tab **Setting → Indeks Kamera** (0-3).
- **`dist/` gagal dihapus / file terkunci** → masih ada `ZFace.exe` berjalan; tutup dulu (langkah 4).

## Distribusi (opsional, seperti biasa)

1. Zip seluruh folder `dist/ZFace-Desktop/`.
2. Kirim ke tenant → extract → klik `ZFace.exe`.
