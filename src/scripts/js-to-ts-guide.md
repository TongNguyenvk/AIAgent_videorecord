# Hướng dẫn Dịch ngược JS → TS

## Tại sao nên làm?

✅ Giữ được custom code khi rebuild
✅ Type safety và IDE support
✅ Dễ maintain và collaborate
✅ Có thể publish lên npm chính thức

## Cách thực hiện

### Bước 1: Tìm file TS gốc tương ứng

Mỗi file `.js` trong `dist/` đều có file `.ts` gốc trong `src/`:

```
packages/webreel/dist/index.js       → packages/webreel/src/index.ts
packages/webreel/dist/config.js      → packages/webreel/src/config.ts
packages/@webreel/core/dist/recorder.js → packages/@webreel/core/src/recorder.ts
```

### Bước 2: So sánh changes

```bash
# Xem file JS đã sửa gì
cat packages/webreel/dist/index.js

# Mở file TS gốc
code packages/webreel/src/index.ts
```

### Bước 3: Port changes sang TS

**Ví dụ:**

Nếu trong JS bạn sửa:
```javascript
// dist/index.js
function processVideo(input) {
  // CUSTOM: Thêm validation
  if (!input || !input.url) {
    throw new Error('Invalid input');
  }
  
  // CUSTOM: Thêm logging
  console.log('Processing:', input.url);
  
  return originalProcess(input);
}
```

Port sang TS:
```typescript
// src/index.ts
interface VideoInput {
  url: string;
  options?: VideoOptions;
}

function processVideo(input: VideoInput): Promise<VideoResult> {
  // CUSTOM: Thêm validation
  if (!input || !input.url) {
    throw new Error('Invalid input');
  }
  
  // CUSTOM: Thêm logging
  console.log('Processing:', input.url);
  
  return originalProcess(input);
}
```

### Bước 4: Rebuild và test

```bash
# Build lại từ TS
pnpm build

# Kiểm tra output JS
cat packages/webreel/dist/index.js

# Test
pnpm test
pnpm type-check
```

## Tools hỗ trợ

### 1. Sử dụng .js.map files

File `.js.map` giúp map ngược JS → TS:

```bash
# Xem source map
cat packages/webreel/dist/index.js.map
```

### 2. Diff tool

```bash
# So sánh JS hiện tại vs JS mới build
git diff packages/webreel/dist/index.js
```

### 3. AI Assistant

Dùng AI để convert JS → TS nhanh hơn:

```
Prompt: "Convert this JavaScript code to TypeScript with proper types:
[paste JS code]
"
```

## Workflow khuyên dùng

### Step-by-step

1. **Backup code custom**
```bash
mkdir -p .backup-custom
cp packages/webreel/dist/index.js .backup-custom/
```

2. **Tìm file TS gốc**
```bash
# Dựa vào source map hoặc cấu trúc folder
ls packages/webreel/src/
```

3. **Mở cả 2 files song song**
```bash
# VS Code split view
code -d packages/webreel/dist/index.js packages/webreel/src/index.ts
```

4. **Copy logic custom sang TS**
- Giữ nguyên logic
- Thêm types
- Thêm comment `// CUSTOM:` để đánh dấu

5. **Rebuild**
```bash
cd packages/webreel
pnpm build
```

6. **Verify**
```bash
# So sánh JS mới vs JS cũ
diff .backup-custom/index.js dist/index.js
```

7. **Test**
```bash
pnpm test
pnpm type-check
```

## Xử lý các trường hợp đặc biệt

### Nếu JS có code không hợp lệ TS

```typescript
// Dùng type assertion
const data = JSON.parse(input) as VideoData;

// Hoặc any nếu cần
const legacy: any = oldFunction();
```

### Nếu thêm dependencies mới

```bash
# Cài type definitions
pnpm add -D @types/library-name
```

### Nếu sửa nhiều files

Tạo script tự động:

```bash
#!/bin/bash
# scripts/port-custom-changes.sh

FILES=(
  "packages/webreel/dist/index.js:packages/webreel/src/index.ts"
  "packages/@webreel/core/dist/recorder.js:packages/@webreel/core/src/recorder.ts"
)

for file_pair in "${FILES[@]}"; do
  IFS=':' read -r js_file ts_file <<< "$file_pair"
  echo "Port changes from $js_file to $ts_file"
  # Manual review needed
  code -d "$js_file" "$ts_file"
done
```

## Checklist

- [ ] Backup tất cả file JS đã custom
- [ ] Tìm được file TS gốc tương ứng
- [ ] Port logic sang TS với proper types
- [ ] Thêm comment đánh dấu custom code
- [ ] Rebuild thành công
- [ ] Type check pass
- [ ] Tests pass
- [ ] Verify output JS giống với JS custom cũ
- [ ] Commit changes vào git
- [ ] Update documentation

## Lợi ích sau khi hoàn thành

✅ Có thể chạy `pnpm build` bất cứ lúc nào
✅ Code được version control đúng cách
✅ Có type safety
✅ Dễ collaborate với team
✅ Có thể tạo changeset và publish npm
✅ CI/CD hoạt động bình thường

## Ví dụ thực tế

Giả sử bạn sửa `packages/webreel/dist/commands/record.js`:

**Before (JS custom):**
```javascript
// dist/commands/record.js
async function record(config) {
  // CUSTOM: Add retry logic
  let attempts = 0;
  while (attempts < 3) {
    try {
      return await originalRecord(config);
    } catch (err) {
      attempts++;
      if (attempts >= 3) throw err;
      await sleep(1000);
    }
  }
}
```

**After (Port to TS):**
```typescript
// src/commands/record.ts
import type { RecordConfig, RecordResult } from '../types';

async function record(config: RecordConfig): Promise<RecordResult> {
  // CUSTOM: Add retry logic
  let attempts = 0;
  const maxAttempts = 3;
  
  while (attempts < maxAttempts) {
    try {
      return await originalRecord(config);
    } catch (err) {
      attempts++;
      if (attempts >= maxAttempts) throw err;
      await sleep(1000);
    }
  }
  
  throw new Error('Unreachable');
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
```

Rebuild:
```bash
cd packages/webreel
pnpm build
# Output: dist/commands/record.js sẽ có logic mới
```

## Kết luận

Dịch ngược JS → TS là cách đúng đắn nhất để maintain custom code. Mất thời gian ban đầu nhưng đáng giá về lâu dài.
