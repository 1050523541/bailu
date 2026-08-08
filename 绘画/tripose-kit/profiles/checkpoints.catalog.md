# 推荐底模目录（全量 Checkpoint）

全部放入 `ComfyUI/models/checkpoints/`。  
本模板只接受 **全量 SDXL / Illustrious / NoobAI checkpoint**（约 6GB 级、含 CLIP+UNET+VAE）。  
下载页请确认文件是 Checkpoint，而不是 UNET / LoRA / VAE 单件。

## 已用本套件验证

| 名称 | 说明 | 链接 |
|------|------|------|
| One Obsession v23 | 软向 NSFW Illustrious 全量 ckpt，三图立绘已跑通 | https://civitai.com/models/1318945/one-obsession |

## 软画风备选（需自测采样参数）

| 名称 | 说明 | 链接 |
|------|------|------|
| Plant Milk（Model Suite） | 柔和高调 Illustrious/Noob 向，多 flavor | https://civitai.com/models/1162518/plant-milk-model-suite |
| CAT - Citron Anime Treasure | Illustrious & NoobAI 软二次元，选 **全量 IL/NAI ckpt** 版本 | https://civitai.com/models/131986/cat-citron-anime-treasure-illustrious-and-noobai |
| Smooth Mix (Illustrious2 + NoobAI) | 半写实/动漫光滑向全量 merge | https://civitai.com/models/1695253/smooth-mix-illustrious2-noobai |
| Obsession (Illustrious-XL) | 注意区分 **epsilon-pred 全量** 与 **v-pred**；v-pred 需对应采样设置 | https://civitai.com/models/820208/obsession-illustrious-xl |

选模时：

1. 下载 **fp16 / pruned SafeTensor checkpoint**（通常 ~6.46 GB）。  
2. 避免误下 UNET-only、ControlNet、Embedding。  
3. v-pred 底模不要与本模板默认 `dpmpp_2m + karras` 盲用，先看模型页推荐采样器。

## 明确不进本模板

| 名称 | 原因 | 链接 |
|------|------|------|
| One Obsession Anima | 多为 UNET-only，需 Qwen CLIP + 独立 VAE 管线 | 在 One Obsession 系列页内的 Anima 条目（如作者注明的 Anima 模型页） |

Anima 请使用工作区里的 Anima 专用工作流，不要塞进本 SDXL 三图模板。

## VAE

优先使用 checkpoint 内嵌 VAE（本模板默认）。  
若必须外置 SDXL VAE，放到 `models/vae/` 并自行改图；模板未接独立 VAELoader。
