# Hướng dẫn Quản lý Custom Build

## Tình trạng hiện tại

Bạn đã custom trực tiếp file `.js` trong folder `dist` thay vì sửa file `.ts` gốc.

**Vị trí custom:**
- `packages/webreel/dist/**/*.js`
- `packages/@webreel/core/dist/**/*.js`
- `webreel-ai-agent/desktop_app/webreel/packages/webreel/dist/**/*.js`

## Vấn đề

1. Nếu chạy `pnpm build` hoặc `tsc`, code custom sẽ bị ghi đè
2. Không có source control cho phần custom
3. Khó maintain và debug

## Giải pháp

### Option 1: Lock dist folder (Nhanh nhất)

Ngăn không cho rebuild ghi đè:

```bash
# Tạo file .gitkeep để track custom changes
cd packages/webreel/dist
echo "# Custom build - DO NOT run pnpm build" > .CUSTOM_BUILD

cd packages/@webreel/core/dist
echo "# Custom build - DO NOT run pnpm build" > .CUSTOM_BUILD
```

Thêm vào `package.json`:

```json
{
  "scripts": {
    "build": "echo 'Build disabled - using custom JS' && exit 1",
    "build:original": "rm -rf dist && tsc"
  }
}
```

### Option 2: Patch system (Khuyên dùng)

Dùng `patch-package` để track changes:

```bash
# Cài patch-package
pnpm add -D patch-package

# Tạo patch từ changes hiện tại
npx patch-package webreel
npx patch-package @webreel/core

# Thêm vào package.json
{
  "scripts": {
    "postinstall": "patch-package"
  }
}
```

Patch files sẽ được lưu trong `patches/` và tự động apply sau mỗi `pnpm install`.

### Option 3: Fork và maintain riêng

Tạo custom packages:

```bash
# Rename packages
mv packages/@webreel/core packages/@webreel/core-custom
mv packages/webreel packages/webreel-custom

# Update package.json
{
  "name": "@yourname/webreel-core",
  "version": "0.1.4-custom.1"
}
```

### Option 4: Build script wrapper (Tốt nhất)

Tạo custom build script giữ lại modifications:

```bash
# Tạo file scripts/custom-build.sh
```

```bash
#!/bin/bash

echo "Building with custom modifications..."

# Backup custom files
mkdir -p .custom-backup
cp packages/webreel/dist/index.js .custom-backup/webreel-index.js
cp packages/@webreel/core/dist/recorder.js .custom-backup/core-recorder.js
# ... backup các file đã custom

# Build từ TypeScript
pnpm build

# Restore custom modifications
cp .custom-backup/webreel-index.js packages/webreel/dist/index.js
cp .custom-backup/core-recorder.js packages/@webreel/core/dist/recorder.js
# ... restore các file

echo "Custom build completed!"
```

Thêm vào `package.json`:

```json
{
  "scripts": {
    "build": "bash scripts/custom-build.sh",
    "build:clean": "rm -rf dist && tsc"
  }
}
```

## Với Docker (Hiện tại)

Docker đang copy toàn bộ `dist` folder đã custom, nên:

✅ **Không cần làm gì thêm** nếu chỉ deploy qua Docker

Dockerfile đã đúng:
```dockerfile
COPY --from=webreel-builder /build/packages/webreel/dist ./packages/webreel/dist
COPY --from=webreel-builder /build/packages/@webreel/core/dist ./packages/@webreel/core/dist
```

## Checklist bảo vệ custom code

- [ ] Thêm comment `// CUSTOM:` ở đầu mỗi file đã sửa
- [ ] Document những gì đã thay đổi
- [ ] Backup dist folder trước khi ai đó chạy build
- [ ] Thêm warning trong README
- [ ] Disable build script hoặc dùng patch-package

## Khuyến nghị

**Nếu chỉ deploy Docker:**
→ Không cần làm gì, Docker image đã chứa code custom

**Nếu có người khác contribute:**
→ Dùng patch-package hoặc build script wrapper

**Nếu muốn publish npm:**
→ Fork thành package riêng với tên khác

## Kiểm tra custom changes

```bash
# So sánh với bản gốc
git diff packages/webreel/dist/
git diff packages/@webreel/core/dist/

# List files đã modified
git status packages/webreel/dist/
```

## Sync giữa root và desktop_app

Nếu cần sync:

```bash
# Copy từ root sang desktop_app
cp -r packages/webreel/dist/* webreel-ai-agent/desktop_app/webreel/packages/webreel/dist/
cp -r packages/@webreel/core/dist/* webreel-ai-agent/desktop_app/webreel/packages/@webreel/core/dist/

# Hoặc tạo symlink (Windows cần admin)
# mklink /D webreel-ai-agent\desktop_app\webreel\packages packages
```

## Kết luận

Với setup Docker hiện tại, bạn **không cần làm gì thêm**. Code custom đã được đóng gói vào image.

Chỉ cần lưu ý:
- Không chạy `pnpm build` hoặc `tsc` nếu không muốn mất custom code
- Document những gì đã custom để người khác biết
- Nếu cần maintain lâu dài, nên chuyển sang patch-package
