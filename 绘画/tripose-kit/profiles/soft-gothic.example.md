# TriPose Profile 示例：Soft Gothic Lolita（白发紫瞳）

把下列文本粘贴进模板对应 CLIP 节点。换角色时只改 Identity + Face Positive 的外观词，以及三个 Variant 的差分。

## Identity 共用角色

```text
masterpiece, best quality, absurdres, highly detailed, soft lighting, ethereal atmosphere,
1girl, solo, adult woman, standing full body portrait, character standing illustration,
white hair, long messy hair, bangs, lavender eyes, detailed eyes, beautiful face,
dark horns with black roses, large white angel wings,
black choker with blue gem,
blue butterfly motifs, floating glowing blue butterflies,
pink and black roses, decorative chains, petals in air, pastel color palette,
high-key dreamy lighting
```

## Variant1 正常服装

```text
gothic lolita dress, white frilled dress, black lace trim, elegant outfit,
white arm warmers, fluffy white fur stole, intricate lace details, clean composition, SFW
```

## Variant2 赤裸

```text
nsfw, explicit, uncensored, completely nude, naked, barefoot,
nude body, bare breasts, nipples, pussy, detailed anatomy,
only black choker accessory, no clothes, no bikini, no lingerie, no swimsuit,
elegant erotic composition
```

## Variant3 性爱事后（必须全裸，禁止内衣回退）

```text
nsfw, explicit, uncensored, completely nude, naked, barefoot,
nude body, bare breasts, nipples, pussy, detailed anatomy,
only black choker accessory, no clothes, no bikini, no lingerie, no swimsuit,
after sex, post-coital, afterglow,
flushed face, sweaty skin, messy hair, tired satisfied expression,
trembling legs, weak standing pose, holding own body for support,
cum on body, cum on breasts, cum on thighs, dripping, wet skin, disheveled,
elegant erotic composition
```

## Negative 共用

```text
lowres, blurry, worst quality, bad anatomy, bad hands, extra fingers, deformed, ugly,
watermark, text, logo, oily skin, harsh shadow, oversaturated, western cartoon, flat color,
simple background, child, loli, underage, toddler, baby, censored, mosaic censoring, bar censor,
multiple girls, couple, male
```

## Face Positive 面部专用

```text
masterpiece, best quality, absurdres, highly detailed face,
beautiful detailed face, detailed eyes, lavender eyes, long eyelashes,
soft skin, delicate nose, detailed lips, white hair, bangs,
looking at viewer, soft lighting, ethereal atmosphere
```

## 已验证实例

工作区根目录 `CF-OneObsession-v23-三图立绘.json` 使用上述文案 + One Obsession v23 底模，管线与模板相同。
