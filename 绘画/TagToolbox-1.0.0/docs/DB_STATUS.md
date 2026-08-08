# 数据库状态

更新：2026-08-02

## 现状

- 源库：`db/classification_editor_source.sqlite`
- 来源：`TagToolbox-v7-visual-r162-checkpoint-20260801.zip`
- revision：**162**（visual 质量提示词原子叶 / L2 首位）
- 运行库：`runtime/classification_editor.sqlite`（由 START 从源库复制）

## 丢失说明

封装前工作区中的 V8 暂时定版：

- 路径：`TagToolbox/v3/output/v8-accepted/classification_editor_v8_source.sqlite`
- revision：**181**
- SHA-256：`B8336DDB73F1A386072048B23CE91AC28D5BFCCB946660DFB49241E3D41D14AA`

在封装过程中发现 `TagToolbox/v3` 目录已空，上述文件与 `editor_server.py` 等均无法从该路径读取。  
目前以 r162 检查点恢复可运行包；若你本地 OneDrive/回收站仍有 r181，请放回 `db/classification_editor_source.sqlite` 后删除 `runtime/classification_editor.sqlite` 再启动。
