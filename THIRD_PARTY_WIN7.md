# Runtime của ứng viên Win7

CPython 3.8.10 x64 chính thức (Python Software Foundation License), OpenSSL 1.1.1k và SQLite từ bản phân phối embeddable của PSF. Python DLL/EXE có chữ ký PSF được kiểm tra trước build. PyInstaller 5.13.2 (GPL với bootloader exception cho phép phân phối sản phẩm), hooks-contrib 2023.8; danh sách build ghim trong requirements-build.txt. Ứng dụng chỉ dùng thư viện chuẩn Python và Windows DPAPI, không Google SDK hay requests bổ sung.

Python 3.8 đã hết vòng hỗ trợ; bộ này là toolchain cũ để nhắm Win7, không phải runtime được hỗ trợ bảo mật hiện hành. OpenSSL 1.1.1k cũng là phiên bản cũ. Không thay DLL ngẫu nhiên, không chép DLL hệ thống Windows 11 sang máy Win7, không tắt kiểm tra chứng chỉ. Tệp LICENSE-python.txt kèm theo là giấy phép từ bản phân phối PSF. Build dependencies không được cài trên máy đích.

Nguồn chính thức: https://www.python.org/downloads/release/python-3810/ ; https://docs.python.org/3.10/using/windows.html ; https://pyinstaller.org/en/v5.13.2/usage.html ; https://pyinstaller.org/en/v5.13.2/license.html .
