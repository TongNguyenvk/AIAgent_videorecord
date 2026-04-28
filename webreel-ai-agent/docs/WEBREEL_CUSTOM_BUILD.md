# Webreel Custom Build Guide

## Tổng quan

Đây là bản Webreel đã được custom lại cho dự án AI Agent Video Tutor. Khác với workflow TypeScript chuẩn, chúng ta sửa trực tiếp file `.js` compiled và build lại.

## Workflow Custom

### 1. Cấu trúc file trong packages/@webreel/core/src/

```
packages/@webreel/core/src/
├── actions.ts          # TypeScript source gốc (từ upstream)
├── actions.js          # JavaScript compiled (ĐÃ CUSTOM - file này được sửa)
├── actions.d.ts        # Type definitions (auto-generated)
├── actions.js.map      # Source map (auto-generated)
└── ...
```

### 2. Quy trình sửa code

**Bước 1: Sửa file .js trực tiếp**
```bash
# Mở và sửa file JavaScript compiled
code packages/@webreel/core/src/actions.js
```

**Bước 2: Build lại bằng tsc**
```bash
# Chạy TypeScript compiler để generate lại .d.ts và .js.map
cd packages/@webreel/core
tsc
```

**Bước 3: Test thay đổi**
```bash
# Test với webreel runner
node packages/webreel/dist/index.js record test.config.json
```

### 3. Tại sao sửa .js thay vì .ts?

**Lý do:**
- Đây là bản fork/custom của Webreel gốc
- Sửa `.js` nhanh hơn, không cần hiểu hết TypeScript types
- File `.ts` giữ nguyên để tham khảo logic gốc
- Khi build bằng `tsc`, nó sẽ generate lại `.d.ts` và `.js.map` từ `.js`

**Ưu điểm:**
- Nhanh chóng thử nghiệm và debug
- Không bị ràng buộc bởi type system
- Dễ dàng revert về version gốc nếu cần

**Nhược điểm:**
- Mất type safety của TypeScript
- Khó maintain nếu cần merge với upstream
- File `.ts` và `.js` không sync

### 4. Các file cần commit

**Nên commit:**
- `packages/@webreel/core/src/*.js` - File JavaScript đã custom
- `packages/@webreel/core/src/*.d.ts` - Type definitions (nếu có thay đổi)
- `packages/@webreel/core/dist/*.js` - Compiled output trong dist/

**Không cần commit:**
- `packages/@webreel/core/src/*.js.map` - Source maps (có thể ignore)
- `node_modules/` - Dependencies

### 5. Build commands

```bash
# Build toàn bộ monorepo
pnpm build

# Build chỉ @webreel/core
cd packages/@webreel/core
pnpm build

# Build với tsc trực tiếp
cd packages/@webreel/core
tsc

# Build và copy sang dist
pnpm build && cp src/*.js dist/
```

### 6. Các thay đổi custom chính

**File: packages/@webreel/core/src/actions.js**
- Thêm support cho các action mới (scroll, extract, etc.)
- Tùy chỉnh timing và animation
- Fix bugs liên quan đến selector

**File: packages/@webreel/core/src/chrome.js**
- Custom CDP integration
- Thêm debug logging
- Fix session management

**File: packages/@webreel/core/src/download.js**
- Custom download handling
- Thêm retry logic

### 7. Sync với upstream (nếu cần)

Nếu cần update từ Webreel gốc:

```bash
# 1. Backup các thay đổi custom
cp -r packages/@webreel/core/src packages/@webreel/core/src.backup

# 2. Pull upstream changes
git fetch upstream
git merge upstream/main

# 3. So sánh và merge thủ công
diff -r packages/@webreel/core/src.backup packages/@webreel/core/src

# 4. Test lại toàn bộ
pnpm test
```

### 8. Troubleshooting

**Lỗi: "Cannot find module"**
```bash
# Rebuild lại dependencies
pnpm install
pnpm build
```

**Lỗi: Type errors khi build**
```bash
# Bỏ qua type check, chỉ generate .d.ts
tsc --noEmit false
```

**Lỗi: Changes không apply**
```bash
# Clear cache và rebuild
rm -rf node_modules/.cache
pnpm build
```

## Kết luận

Workflow này phù hợp cho rapid prototyping và custom nhanh. Khi project ổn định, nên cân nhắc:
1. Sync lại `.ts` với `.js` để có type safety
2. Tạo fork riêng của Webreel
3. Document tất cả custom changes

## Tham khảo

- Webreel gốc: https://github.com/oslabs-beta/webreel
- TypeScript Compiler: https://www.typescriptlang.org/docs/handbook/compiler-options.html
- Monorepo với pnpm: https://pnpm.io/workspaces
