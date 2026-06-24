"""
UI Inspector - Lay element tree (OS DOM) cua cua so desktop.
Su dung pywinauto UIA backend de duyet toan bo control tree,
tuong tu nhu DOM trong trinh duyet.
"""

import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class UIElement:
    """Mot element trong UI tree (tuong tu DOM node)."""
    control_type: str          # "Button", "Edit", "Text", "ListItem", ...
    name: str                  # Ten hien thi (nhu innerText)
    automation_id: str         # ID duy nhat (nhu CSS #id)
    class_name: str            # Lop cua so (nhu tag name)
    rect: tuple[int, int, int, int]  # (left, top, right, bottom)
    is_enabled: bool
    is_visible: bool
    value: str = ""            # Gia tri (cho Edit, Checkbox, ...)
    children: list["UIElement"] = field(default_factory=list)

    @property
    def center(self) -> tuple[int, int]:
        """Toa do trung tam cua element (de click)."""
        left, top, right, bottom = self.rect
        return ((left + right) // 2, (top + bottom) // 2)

    @property
    def width(self) -> int:
        return self.rect[2] - self.rect[0]

    @property
    def height(self) -> int:
        return self.rect[3] - self.rect[1]

    def to_dict(self) -> dict:
        """Chuyen sang dict (khong bao gom children de tranh qua sau)."""
        return {
            "control_type": self.control_type,
            "name": self.name,
            "automation_id": self.automation_id,
            "class_name": self.class_name,
            "rect": self.rect,
            "center": self.center,
            "is_enabled": self.is_enabled,
            "value": self.value,
        }


def _wrap_element(wrapper, max_depth: int = 5, current_depth: int = 0) -> UIElement:
    """Chuyen pywinauto wrapper thanh UIElement (de qui)."""
    try:
        element_info = wrapper.element_info
        rect_obj = element_info.rectangle
        rect = (rect_obj.left, rect_obj.top, rect_obj.right, rect_obj.bottom)
    except Exception:
        rect = (0, 0, 0, 0)

    try:
        name = element_info.name or ""
    except Exception:
        name = ""

    try:
        control_type = element_info.control_type or ""
    except Exception:
        control_type = ""

    try:
        automation_id = element_info.automation_id or ""
    except Exception:
        automation_id = ""

    try:
        class_name = element_info.class_name or ""
    except Exception:
        class_name = ""

    try:
        is_enabled = wrapper.is_enabled()
    except Exception:
        is_enabled = True

    try:
        is_visible = wrapper.is_visible()
    except Exception:
        is_visible = True

    # Lay value cho cac control co the chinh sua
    value = ""
    try:
        if control_type in ("Edit", "Document"):
            value = wrapper.get_value() or ""
        elif control_type == "CheckBox":
            toggle = wrapper.get_toggle_state()
            value = "checked" if toggle == 1 else "unchecked"
        elif control_type == "ComboBox":
            value = wrapper.selected_text() or ""
    except Exception:
        pass

    # De qui lay children
    children = []
    if current_depth < max_depth:
        try:
            for child in wrapper.children():
                try:
                    child_elem = _wrap_element(child, max_depth, current_depth + 1)
                    # Chi lay element co kich thuoc > 0
                    if child_elem.width > 0 and child_elem.height > 0:
                        children.append(child_elem)
                except Exception:
                    continue
        except Exception:
            pass

    return UIElement(
        control_type=control_type,
        name=name,
        automation_id=automation_id,
        class_name=class_name,
        rect=rect,
        is_enabled=is_enabled,
        is_visible=is_visible,
        value=value,
        children=children,
    )


def get_element_tree(pid: int, max_depth: int = 5) -> UIElement:
    """
    Lay toan bo element tree cua cua so theo PID.

    Args:
        pid: Process ID cua ung dung.
        max_depth: Do sau toi da de duyet (tranh qua cham).

    Returns:
        UIElement root chua toan bo cay con.
    """
    from pywinauto import Application

    app = Application(backend="uia").connect(process=pid)

    # Lay toan bo cac cua so cua process, chon cua so lon nhat
    all_windows = app.windows()
    if not all_windows:
        raise ValueError(f"No windows found for PID {pid}")

    # Sap xep theo dien tich, lay cua so lon nhat (thuong la cua so chinh)
    def _window_area(w):
        try:
            r = w.rectangle()
            return (r.right - r.left) * (r.bottom - r.top)
        except Exception:
            return 0

    all_windows.sort(key=_window_area, reverse=True)
    main_window = all_windows[0]

    logger.info(f"Inspecting PID={pid}: {main_window.window_text()} ({len(all_windows)} windows)")
    # windows() tra ve wrappers truc tiep, khong can goi wrapper_object()
    root = _wrap_element(main_window, max_depth=max_depth)
    logger.info(f"Element tree: {_count_elements(root)} element(s), depth={max_depth}")

    return root


def _count_elements(element: UIElement) -> int:
    """Dem tong so element trong cay."""
    count = 1
    for child in element.children:
        count += _count_elements(child)
    return count


def find_elements(
    root: UIElement,
    name: Optional[str] = None,
    control_type: Optional[str] = None,
    automation_id: Optional[str] = None,
) -> list[UIElement]:
    """
    Tim tat ca element khop voi dieu kien (de qui).

    Args:
        root: Goc cua cay element.
        name: Tim theo name (chua chuoi, khong phan biet hoa thuong).
        control_type: Tim theo control_type chinh xac (VD: "Button", "Edit").
        automation_id: Tim theo automation_id chinh xac.

    Returns:
        Danh sach cac element khop.
    """
    results = []

    def _match(elem: UIElement) -> bool:
        if name and name.lower() not in elem.name.lower():
            return False
        if control_type and elem.control_type != control_type:
            return False
        if automation_id and elem.automation_id != automation_id:
            return False
        return True

    def _search(elem: UIElement):
        if _match(elem):
            results.append(elem)
        for child in elem.children:
            _search(child)

    _search(root)
    return results


def find_element(
    root: UIElement,
    name: Optional[str] = None,
    control_type: Optional[str] = None,
    automation_id: Optional[str] = None,
) -> Optional[UIElement]:
    """Tim element dau tien khop. Tra ve None neu khong tim thay."""
    matches = find_elements(root, name, control_type, automation_id)
    return matches[0] if matches else None


def print_element_tree(
    element: UIElement,
    max_depth: int = 3,
    indent: int = 0,
    current_depth: int = 0,
):
    """In element tree ra console de debug (nhu Chrome DevTools)."""
    if current_depth > max_depth:
        return

    prefix = "  " * indent
    ctrl = element.control_type or "?"
    name_str = f' "{element.name}"' if element.name else ""
    aid_str = f" #{element.automation_id}" if element.automation_id else ""
    val_str = f" ={element.value}" if element.value else ""
    cx, cy = element.center
    size_str = f" [{element.width}x{element.height} @({cx},{cy})]"

    enabled_str = "" if element.is_enabled else " [DISABLED]"

    print(f"{prefix}{ctrl}{name_str}{aid_str}{val_str}{size_str}{enabled_str}")

    for child in element.children:
        print_element_tree(child, max_depth, indent + 1, current_depth + 1)





def get_clickable_elements(root: UIElement) -> list[UIElement]:
    """Lay danh sach tat ca element co the click."""
    clickable_types = {
        "Button", "MenuItem", "MenuBar", "Menu",
        "Hyperlink", "Link", "ListItem", "TreeItem",
        "TabItem", "CheckBox", "RadioButton", "ComboBox",
        "SplitButton", "ToggleButton",
    }
    results = []

    def _search(elem: UIElement):
        if elem.control_type in clickable_types and elem.is_enabled:
            results.append(elem)
        for child in elem.children:
            _search(child)

    _search(root)
    return results
