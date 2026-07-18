"""
Script build ZFace Desktop menjadi portable folder.

Cara pakai:
  pip install pyinstaller
  python build.py

Output: dist/ZFace-Desktop/
  Zip folder itu → distribusikan ke tenant.
  Model buffalo_l (~280MB) auto-download ke models/ saat pertama kali jalan.
"""
import os
import shutil
import subprocess
import sys


def main():
    print("=== ZFace Desktop Builder ===\n")

    # Pastikan pyinstaller ada
    try:
        import PyInstaller
        print(f"PyInstaller {PyInstaller.__version__} ditemukan.")
    except ImportError:
        print("PyInstaller belum terinstall. Jalankan: pip install pyinstaller")
        sys.exit(1)

    # Bersihkan build lama
    for d in ['build', 'dist']:
        if os.path.exists(d):
            print(f"Membersihkan {d}/...")
            shutil.rmtree(d)

    # Build
    print("\nMemulai build...\n")
    result = subprocess.run(
        [sys.executable, '-m', 'PyInstaller', 'build.spec', '--clean', '--noconfirm'],
        check=False,
    )

    if result.returncode != 0:
        print("\nBuild gagal. Cek log di atas.")
        sys.exit(1)

    print("\n" + "="*40)
    print("Build BERHASIL!")
    print("="*40)
    print(f"\nOutput: dist/ZFace-Desktop/")
    print(f"Ukuran folder:")
    total = sum(
        os.path.getsize(os.path.join(dp, f))
        for dp, _, files in os.walk('dist/ZFace-Desktop')
        for f in files
    )
    print(f"  {total / 1024 / 1024:.1f} MB")
    print("\nCara distribusi:")
    print("  1. Zip seluruh folder dist/ZFace-Desktop/")
    print("  2. Kirim ke tenant")
    print("  3. Tenant extract → klik ZFace.exe → selesai")
    print("\nNote: Model buffalo_l (~280MB) akan di-download otomatis")
    print("      ke folder models/ saat pertama kali dijalankan.")


if __name__ == '__main__':
    main()
