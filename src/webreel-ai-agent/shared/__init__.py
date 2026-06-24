"""
Shared modules - ban chinh duy nhat cua cac module dung chung.

Sau khi chuyen doi import, tat ca pipeline (Web, Office, OS) deu import tu day.
Hien tai chi la ban copy, chua thay doi import (giu demo hoat dong).

Modules:
  - trace_composer.py: Ghep audio vao video theo trace timestamps
  - audio_injector.py: Inject TTS duration vao [NARRATION:idx] pause
  - tts.py: FPT.AI TTS engine
  - tts_edge.py: Edge TTS engine
  - bu_to_webreel.py: Parser browser-use history -> Webreel config
  - webreel_runner.py: Webreel CLI runner (recording)
"""
