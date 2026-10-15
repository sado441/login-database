"""Download the official release, verify SHA-256, prepare files; never install."""
import hashlib
import io
from pathlib import Path
import tempfile
import urllib.request
import zipfile
import argparse

URL = "https://github.com/oblitum/Interception/releases/download/v1.0.1/Interception.zip"
# Recorded from the official GitHub release over verified HTTPS.
ARCHIVE_SHA256 = "ad038963d6413055765128b0b931f6e765147c9916dba79e65d872b261f9af10"
INSTALLER_SHA256 = "e137863a79da797f08e7a137280ff2a123809044a888fd75ce9c973198915abe"
DLL_HASHES = {
    "x64": "ab88164c11b1b48488772d4c3bfaa4509d5b0ae9dbc5a691dc4f96f0260443c8",
    "x86": "9e1def27b804df9ba97fd07f9de835c70660ae568c00950102f70034e293a684",
}
FILES = {
    "x64/interception.dll": "Interception/library/x64/interception.dll",
    "x86/interception.dll": "Interception/library/x86/interception.dll",
    "install-interception.exe": "Interception/command line installer/install-interception.exe",
    "LGPL-3.0.txt": "Interception/licenses/non-commercial-usage/LGPL 3.0.txt",
}


def prepare(data, destination):
    if hashlib.sha256(data).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("Resmi Interception arşivinin SHA-256 doğrulaması başarısız. Hiçbir dosya hazırlanmadı.")
    destination = Path(destination)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        contents = {name: archive.read(source) for name, source in FILES.items()}
    # Preserve files that weren't produced from this exact upstream release.
    for name, content in contents.items():
        target = destination / name
        if target.exists() and target.read_bytes() != content:
            raise ValueError(f"Mevcut dosya farklı; üzerine yazılmadı: {target}")
    for name, content in contents.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temporary:
                temporary.write(content)
                name_on_disk = Path(temporary.name)
            name_on_disk.replace(target)


def main():
    print("Resmi Interception 1.0.1 arşivi indiriliyor (HTTPS + SHA-256 doğrulaması)...")
    with urllib.request.urlopen(URL, timeout=60) as response:
        data = response.read(10_000_001)
    if len(data) > 10_000_000:
        raise ValueError("Beklenmeyen arşiv boyutu.")
    destination = Path(__file__).resolve().parent / "drivers" / "Interception-1.0.1"
    prepare(data, destination)
    print("Dosyalar doğrulandı ve hazırlandı. Bu işlem sürücü KURMADI.")
    print("Sürücü kurulu değilse INTERCEPTION_SURUCU_KUR.bat aç; ardından Windows'u yeniden başlat.")
    print("Kaynak ve lisans: https://github.com/oblitum/Interception")


def verify_installer():
    path = Path(__file__).resolve().parent / "drivers" / "Interception-1.0.1" / "install-interception.exe"
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != INSTALLER_SHA256:
        raise RuntimeError("Kurulum dosyası doğrulanamadı. INTERCEPTION_HAZIRLA.bat ile resmi dosyaları hazırla.")
    print("Resmi Interception kurulum dosyası SHA-256 ile doğrulandı.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-installer", action="store_true")
    args = parser.parse_args()
    if args.verify_installer:
        verify_installer()
    else:
        main()
