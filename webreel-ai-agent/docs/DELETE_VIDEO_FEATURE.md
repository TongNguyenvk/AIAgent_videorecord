# Tính năng xóa video trong tab Lịch sử

## Tổng quan

Đã thêm nút xóa vào tab Lịch sử để người dùng có thể xóa video không cần thiết.

## Tính năng

### 1. Nút xóa trong history card

**Vị trí:** Tab "Lịch sử", mỗi video card

**Icon:** `DELETE_OUTLINE` (icon thùng rác)

**Màu:** Đỏ (RED_600)

**Tooltip:** "Xóa video"

### 2. Dialog xác nhận

Khi người dùng nhấn nút xóa, hiển thị dialog xác nhận với:

**Tiêu đề:**
- Icon cảnh báo (màu cam)
- Text: "Xác nhận xóa"

**Nội dung:**
- Câu hỏi xác nhận: "Bạn có chắc chắn muốn xóa video '[tên video]' không?"
- Thông tin thư mục:
  - Đường dẫn
  - Số file
  - Kích thước (MB)
- Cảnh báo: "Toàn bộ thư mục sẽ bị xóa vĩnh viễn!" (màu đỏ)

**Các nút:**
- "Hủy" (màu xám) - Đóng dialog, không làm gì
- "Xóa" (màu đỏ) - Xác nhận xóa

### 3. Xử lý xóa

**Khi người dùng xác nhận xóa:**

1. Xóa toàn bộ thư mục chứa video bằng `shutil.rmtree()`
2. Đóng dialog
3. Refresh tab lịch sử
4. Hiển thị thông báo thành công (snackbar màu xanh)

**Nếu có lỗi:**

1. Đóng dialog
2. Hiển thị thông báo lỗi (snackbar màu đỏ)
3. Log lỗi để debug

## Cấu trúc thư mục

### Web mode
```
desktop_app/output/
└── [video_name]/
    ├── [video_name]_final.mp4
    ├── [video_name]_raw.mp4
    ├── audio/
    │   ├── narration_000.mp3
    │   ├── narration_001.mp3
    │   └── ...
    ├── agent/
    │   └── plan.json
    └── .webreel/
        └── traces/
            └── [video_name].trace.json
```

### Desktop mode
```
os_recorder/workspace/output/
└── [video_name]/
    ├── [video_name]_final.mp4
    ├── [video_name]_raw.mp4
    ├── [video_name].docx
    ├── [video_name].pdf
    ├── audio/
    │   ├── narration_000.mp3
    │   └── ...
    ├── screenshots/
    │   ├── step_001.png
    │   └── ...
    └── agent/
        └── plan.json
```

**Khi xóa:** Toàn bộ thư mục `[video_name]/` bị xóa vĩnh viễn

## Code implementation

### Hàm `show_delete_confirmation_dialog()`

```python
def show_delete_confirmation_dialog(video_data):
    """Show confirmation dialog before deleting video folder."""
    video_name = video_data["name"]
    video_path = Path(video_data["path"])
    folder_path = video_path.parent
    
    # Calculate folder size
    total_size = 0
    file_count = 0
    for file in folder_path.rglob("*"):
        if file.is_file():
            total_size += file.stat().st_size
            file_count += 1
    
    size_mb = total_size / (1024 * 1024)
    
    def on_confirm_delete(e):
        try:
            # Delete entire folder
            shutil.rmtree(folder_path)
            logger.info(f"Deleted folder: {folder_path}")
            
            # Close dialog and refresh history
            page.dialog.open = False
            page.update()
            load_history_tab()
            
            # Show success message
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Đã xóa '{video_name}' thành công!"),
                bgcolor=ft.Colors.GREEN_600,
            )
            page.snack_bar.open = True
            page.update()
            
        except Exception as ex:
            logger.error(f"Failed to delete folder: {ex}")
            # Show error message
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Lỗi khi xóa: {str(ex)[:50]}"),
                bgcolor=ft.Colors.RED_600,
            )
            page.snack_bar.open = True
            page.update()
    
    # Build and show dialog...
```

### Thêm nút xóa vào history card

```python
def make_delete_handler(video_data):
    def handler(e):
        show_delete_confirmation_dialog(video_data)
    return handler

# Add delete button
action_buttons.append(
    ft.IconButton(
        icon=ft.Icons.DELETE_OUTLINE,
        icon_size=28,
        icon_color=ft.Colors.RED_600,
        tooltip="Xóa video",
        on_click=make_delete_handler(video)
    )
)
```

## UI/UX Flow

```
User clicks "Xóa video" button
    |
    v
Show confirmation dialog
    |
    +-- User clicks "Hủy"
    |   |
    |   v
    |   Close dialog, do nothing
    |
    +-- User clicks "Xóa"
        |
        v
        Delete folder with shutil.rmtree()
        |
        +-- Success
        |   |
        |   v
        |   Close dialog
        |   Refresh history tab
        |   Show success snackbar
        |
        +-- Error
            |
            v
            Close dialog
            Show error snackbar
            Log error
```

## Safety features

### 1. Confirmation dialog
- Người dùng phải xác nhận trước khi xóa
- Hiển thị thông tin chi tiết (đường dẫn, số file, kích thước)
- Cảnh báo rõ ràng: "Toàn bộ thư mục sẽ bị xóa vĩnh viễn!"

### 2. Error handling
- Try-catch khi xóa folder
- Hiển thị thông báo lỗi nếu xóa thất bại
- Log lỗi để debug

### 3. Visual feedback
- Snackbar thành công (màu xanh)
- Snackbar lỗi (màu đỏ)
- Auto refresh history tab sau khi xóa

## Testing checklist

- [ ] Test xóa video Web mode
  - [ ] Kiểm tra dialog hiển thị đúng thông tin
  - [ ] Kiểm tra xóa thành công
  - [ ] Kiểm tra snackbar hiển thị
  - [ ] Kiểm tra history tab refresh
  
- [ ] Test xóa video Desktop mode
  - [ ] Kiểm tra xóa cả DOCX và PDF
  - [ ] Kiểm tra xóa cả screenshots
  - [ ] Kiểm tra snackbar hiển thị
  
- [ ] Test cancel delete
  - [ ] Nhấn "Hủy" không xóa gì
  - [ ] Dialog đóng đúng cách
  
- [ ] Test error handling
  - [ ] Xóa folder đang mở (permission denied)
  - [ ] Xóa folder không tồn tại
  - [ ] Kiểm tra error snackbar

## Known issues

### Permission denied khi folder đang mở

**Triệu chứng:** Lỗi khi xóa nếu video đang phát hoặc folder đang mở

**Giải pháp:** 
- Đóng video player trước khi xóa
- Đóng File Explorer nếu đang mở folder

### Không thể undo

**Triệu chứng:** Folder bị xóa vĩnh viễn, không thể khôi phục

**Giải pháp:** 
- Confirmation dialog để tránh xóa nhầm
- Có thể thêm tính năng "Move to Recycle Bin" thay vì xóa vĩnh viễn

## Future improvements

### Short-term
- [ ] Move to Recycle Bin thay vì xóa vĩnh viễn
- [ ] Thêm nút "Xóa tất cả" để xóa nhiều video cùng lúc
- [ ] Thêm filter để chọn video cần xóa

### Long-term
- [ ] Undo delete (restore from backup)
- [ ] Archive video thay vì xóa
- [ ] Cloud backup trước khi xóa

## Kết luận

Tính năng xóa video giúp người dùng:
- Quản lý dung lượng ổ đĩa
- Xóa video không cần thiết dễ dàng
- Tránh xóa nhầm với confirmation dialog
- Trải nghiệm mượt mà với visual feedback
