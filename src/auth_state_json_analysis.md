# Auth State JSON cho LMS (Microsoft SSO) trong Docker: Phan tich kha thi

## 1. Boi Canh: Da That Bai Voi Google

File [google_docker_auth_issue.md](file:///f:/==HK1-2526==/ThucTap/webreel/google_docker_auth_issue.md) ghi nhan **4 lan that bai** khi ap dung cac chien thuat tuong tu cho **Google SSO**:

| Cach | Ky thuat | Ket qua |
|------|----------|---------|
| 1 | `storage_state.json` (Cookie thuan) | **That bai** - Google phat hien fingerprint Linux Headless khac Windows |
| 2 | [user_data_dir](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/browser-use/browser_use/browser/profile.py#512-519) (Copy ca Profile) | **That bai** - Cookie SQLite ma hoa DPAPI, Linux khong giai ma duoc |
| 3 | [storage_state](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/browser-use/browser_use/browser/session.py#1326-1370) + Stealth Flags + UA | **That bai** - Google phat hien WebGL/hardware khong nhat quan |
| 4 | `playwright-stealth` monkeypatch | **That bai** - Google qua quen voi cac thu vien stealth |

## 2. Microsoft SSO (LMS TVU) co Khac Google Khong?

> [!IMPORTANT]
> **Cau tra loi ngan: CO, nhung chi khac mot phan.** Microsoft Entra ID (Azure AD) co he thong chong bot tuong tu Google nhung **khong khac nghiet bang** trong mot so truong hop.

### 2.1. Diem khac biet co loi

- **Session lifetime:** Microsoft SSO token (Refresh Token) co the song **90 ngay**, dai hon Google (thong thuong 7 ngay)
- **Fingerprint checking:** Microsoft lam **khong nghiem ngat bang Google** o muc browser fingerprint. Google co riskAnalysis sieu viet, Microsoft chu yeu dua vao IP range, device compliance (Intune), va Conditional Access policies
- **LMS TVU la ung dung Enterprise:** Truong hoc thuong cau hinh Conditional Access "loi" hon (khong bat MFA moi lan, khong bat device compliance nghiem ngat), nen co hoi thanh cong cao hon Google Drive

### 2.2. Diem rui ro van con

- **IP Mismatch:** Neu Docker chay tren server co IP khac may login, Microsoft **co the** bat re-auth
- **Platform shift:** Cookie tu Windows Chrome inject vao Linux Headless Chrome **van co the** bi phat hien qua `Sec-CH-UA-Platform` header va JavaScript `navigator.platform`
- **Token Revocation:** Refresh token co the bi revoke bat cu luc nao boi admin truong

## 3. Danh Gia Giai Phap "Auth State JSON" Cho Webreel Docker

### 3.1. Kien truc hien tai cua pipeline

```
run_pipeline.py (Phase 1: The Scout)
    |
    +-- Browser(cdp_url=CDP_URL)  <-- Ket noi Chrome qua CDP, KHONG co storage_state
    |
    +-- Agent chay browser-use, navigate trang web
```

Pipeline hien tai dung [cdp_url](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/browser-use/browser_use/browser/session.py#442-446) de ket noi toi Chrome debug instance. **Khong co injection [storage_state](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/browser-use/browser_use/browser/session.py#1326-1370)** o bat ky dau.

### 3.2. Kha nang tich hop: RAT DE

> [!TIP]
> `browser-use` da co san toan bo ha tang `StorageStateWatchdog` va `BrowserProfile.storage_state`. Ban chi can truyen them 1 tham so khi tao [Browser()](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/browser-use/browser_use/browser/profile.py#278-288).

Code hien tai trong [run_pipeline.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/run_pipeline.py#L162-L166):
```python
browser = Browser(
    cdp_url=cdp_url,
    keep_alive=True,
)
```

Chi can them [storage_state](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/browser-use/browser_use/browser/session.py#1326-1370):
```python
browser = Browser(
    cdp_url=cdp_url,
    keep_alive=True,
    storage_state='lms_auth.json',  # Tiem cookie vao day
)
```

### 3.3. Van de cot loi: CDP Mode vs Playwright Mode

> [!CAUTION]
> **Day la "noi dau" chinh.** Khi ban dung [cdp_url](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/browser-use/browser_use/browser/session.py#442-446) de ket noi, browser-use ket noi truc tiep qua Chrome DevTools Protocol. `StorageStateWatchdog` se dung CDP commands (`Network.setCookies`) de inject cookie, **KHONG** dung Playwright `newContext(storageState)`.

**Dieu nay co nghia la:**

1. **Cookie injection van hoat dong** - CDP `Network.setCookies` co the set cookie cho bat ky domain nao
2. **LocalStorage injection khong tu dong** - CDP khong co lenh tuong duong `setLocalStorage`. `StorageStateWatchdog` chi save/load cookie qua CDP, **KHONG** inject localStorage/sessionStorage (xem [storage_state_watchdog.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/browser-use/browser_use/browser/watchdogs/storage_state_watchdog.py))
3. **Microsoft SSO co the can localStorage** - Azure AD MSAL luu `id_token`, `access_token` trong localStorage

## 4. Ket Luan va De Xuat

### 4.1. Giai phap "Auth State JSON" co kha thi khong?

**Co dieu kien.** No se hoat dong neu:

| Dieu kien | Kha thi? |
|-----------|----------|
| Docker va may login **cung IP range** (cung mang LAN/VPN) | Can kiem tra |
| LMS TVU **khong bat** Conditional Access nghiem ngat | Rat co the (truong hoc thuong loi) |
| Session **chi can Cookie** (khong can localStorage) | Can thu nghiem |
| Khong bi fingerprint check qua platform | Co the bypass bang User-Agent |

### 4.2. De xuat 3 phuong an (sap xep theo do uu tien)

#### Phuong an A: Auth State JSON + CDP Cookie Injection (Nhanh nhat)
- **Cach lam:** Dung script Python tao `lms_auth.json` tren may that, truyen [storage_state](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/browser-use/browser_use/browser/session.py#1326-1370) vao Browser()
- **Uu diem:** De lam, co san ha tang trong browser-use
- **Rui ro:** Neu Microsoft kiem tra fingerprint/platform, se that bai nhu Google
- **Nen thu truoc**

#### Phuong an B: Xvfb + Headed Chrome trong Docker (Chac chan nhat)
- **Cach lam:** Cai `Xvfb` vao Dockerfile, chay Chrome headed mode, login **trong Docker 1 lan**
- **Uu diem:** Cookie sinh ra **trong chinh moi truong Docker**, fingerprint nhat quan 100%
- **Nhuoc diem:** Docker tang ~1-2GB, can VNC hoac noVNC de login lan dau
- **Day la giai phap "chot ha" neu Phuong an A that bai**

#### Phuong an C: Tiep tuc chay tren Windows truc tiep (Khong can Docker)
- **Dung cho truong hop** ban chi can 1 may chay pipeline, khong can scale
- **Da duoc de xuat** trong [google_docker_auth_issue.md](file:///f:/==HK1-2526==/ThucTap/webreel/google_docker_auth_issue.md) Phuong an A

### 4.3. Buoc hanh dong tiep theo

1. **Thu nghiem nhanh Phuong an A** (30 phut):
   - Chay script thu hoach `lms_auth.json` tren may Windows
   - Mount file vao Docker, truyen [storage_state](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/browser-use/browser_use/browser/session.py#1326-1370) vao [Browser()](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/browser-use/browser_use/browser/profile.py#278-288)
   - Xem LMS TVU co chap nhan session khong

2. **Neu that bai, chuyen sang Phuong an B**:
   - Them `Xvfb` + `x11vnc` vao Dockerfile
   - Login bang tay qua VNC 1 lan
   - Cookie tu sinh trong Docker, dam bao fingerprint nhat quan
