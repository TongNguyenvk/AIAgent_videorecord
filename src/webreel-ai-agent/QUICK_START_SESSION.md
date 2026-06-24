# Quick Start: Setup Google Session (Windows Local)

## Buoc 1: Cai dat dependencies

```bash
cd webreel-ai-agent
pip install -r requirements.txt
```

## Buoc 2: Setup session (dang nhap mot lan)

```bash
python setup_auth.py https://drive.google.com
```

Lam gi:
1. Chrome se mo ra (co giao dien)
2. Dang nhap Google binh thuong
3. Sau khi vao duoc Drive, DONG cua so Chrome
4. Profile se tu dong luu tai `output/browser_profile/`

## Buoc 3: Test session

Test nhanh (mo browser de tu kiem tra):

```bash
python quick_test_session.py
```

Test voi AI agent (tu dong kiem tra):

```bash
python test_google_session.py
```

## Buoc 4: Chay pipeline

Neu session hoat dong, chay pipeline:

```bash
python run_pipeline.py "Vao Google Drive va tao thu muc moi ten Test"
```

## Luu y

- Chi hoat dong tren Windows local
- Session co the het han sau vai ngay
- Neu bi yeu cau dang nhap lai, chay lai buoc 2
