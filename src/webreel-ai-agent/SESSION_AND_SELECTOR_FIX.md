# Fix Session Persistence va Selector Issues

## Van de 1: Browser-use luu session/token

### Van de
Browser-use mac dinh luu session vao user_data_dir, dan den:
- Lan chay thu 2: Da dang nhap san
- Webreel khong the record lai qua trinh dang nhap
- Video bi thieu cac buoc dang nhap

### Giai phap
Tat user_data_dir trong run_pipeline.py:

```python
# KHONG dung persistent profile de tranh luu session/token
# Moi lan chay la mot session moi, dam bao webreel co the record lai dang nhap
user_data_dir = None
```

### Ket qua
- Moi lan chay pipeline la mot browser session moi
- Webreel co the record day du qua trinh dang nhap
- Video hoan chinh tu dau den cuoi

## Van de 2: AI Reviewer tu y doi selector

### Van de
AI Reviewer dang duoc phep "sua loi selector" qua tu do:
- Doi selector tu browser-use log sang selector khac
- Tu y don gian hoa hoac "cai thien" selector
- Dan den selector khong tim thay element tren trang

Vi du:
- Browser-use: `input[name="email"]`
- AI Reviewer doi thanh: `input[type="email"]`
- Ket qua: Element khong tim thay vi trang dung name chu khong co type

### Giai phap
Cap nhat prompt trong ai_reviewer.py:

```
QUAN TRONG - SELECTOR RULES:
- GIU NGUYEN selector tu browser-use log neu co the
- CHI sua selector neu:
  * Co pseudo-selector khong hop le (:has-text, :contains)
  * Co loi cu phap ro rang
  * Selector qua phuc tap va co the don gian hoa
- UU TIEN: id > name attribute > type attribute > class > tag
- KHONG tu y doi selector neu no dang hoat dong
```

### Ket qua
- AI chi sua selector khi that su can thiet
- Giu nguyen selector tu browser-use log
- Giam thieu loi "Element not found"

## Test

Chay lai pipeline voi task phuc tap:

```bash
venv\Scripts\python.exe run_pipeline.py "Vao localhost3000 dang nhap voi email teacher@example.com va password la teacher@123 an vao quan ly sinh vien tren nav, tao 1 sinh vien moi ten la testtestvideo email la video@example.com va mat khau la 123456 ho ten la testess" --name test-fix
```

Kiem tra:
1. Browser-use khong luu session (phai dang nhap moi lan)
2. Webreel record duoc day du qua trinh dang nhap
3. Selector tu AI Reviewer khop voi browser-use log
4. Video render thanh cong
