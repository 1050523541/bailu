<template>
  <main class="home">
    <header class="masthead">
      <div class="lantern-mark">福</div>
      <div class="masthead-copy">
        <p class="eyebrow">New Year Hypnosis Gift</p>
        <h1>新年催眠礼物</h1>
        <p class="subtitle">拜金女友 · 伪善伯母 · 腹黑小妹</p>
      </div>
    </header>

    <section v-if="!started" class="intro-layout">
      <div class="story-column">
        <div class="story-block">
          <span class="section-kicker">剧情序章</span>
          <h2>{{ preview_title }}</h2>
          <p>{{ preview_text }}</p>
          <p class="preview-note">
            {{ preview_note }}
          </p>
        </div>

        <div class="cast-row">
          <div v-for="cast in cast_list" :key="cast.key" class="cast-cell">
            <div class="cast-art" :style="{ '--accent': cast.accent }">
              <span>{{ cast.key.slice(0, 1) }}</span>
            </div>
            <div class="cast-copy">
              <h3>{{ cast.name }}</h3>
              <p>{{ cast.role }}</p>
            </div>
          </div>
        </div>
      </div>

      <form class="setup-panel" @submit.prevent="startGame">
        <div class="field">
          <span class="field-label">出身</span>
          <div class="segmented">
            <button
              v-for="option in origin_options"
              :key="option.value"
              type="button"
              class="segment"
              :class="{ selected: origin === option.value }"
              @click="origin = option.value"
            >
              {{ option.label }}
            </button>
          </div>
          <p class="field-hint">{{ origin_hint }}</p>
        </div>

        <div class="field">
          <span class="field-label">催眠风格</span>
          <div class="segmented">
            <button
              v-for="option in style_options"
              :key="option.value"
              type="button"
              class="segment"
              :class="{ selected: style === option.value }"
              @click="style = option.value"
            >
              {{ option.label }}
            </button>
          </div>
          <p class="field-hint">{{ style_hint }}</p>
        </div>

        <div class="field">
          <span class="field-label">开局模式</span>
          <div class="segmented opening-segments">
            <button
              v-for="option in opening_options"
              :key="option.value"
              type="button"
              class="segment opening-segment"
              :class="{ selected: opening === option.value }"
              @click="opening = option.value"
            >
              <span>{{ option.label }}</span>
              <small>{{ option.desc }}</small>
            </button>
          </div>
        </div>

        <button class="start-button" type="submit" :disabled="starting">
          <span>{{ starting ? '正在准备...' : '进入正篇' }}</span>
          <span class="start-arrow" aria-hidden="true">→</span>
        </button>
        <p v-if="error_message" class="error-message">{{ error_message }}</p>
      </form>
    </section>

    <section v-else class="game-screen">
      <div class="game-head">
        <span class="game-tag">正篇</span>
        <span>{{ game_meta }}</span>
      </div>
      <div class="maintext" v-html="rendered_maintext"></div>
      <div v-if="option_text" class="option-block">
        <span class="section-kicker">选择</span>
        <div class="option-text">{{ option_text }}</div>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import initvar from '../../世界书/变量/initvar.yaml';
import opening2_raw from '../../第一条消息/1.txt?raw';

type Origin = '普通男友' | '隐藏富二代';
type HypnoStyle = '渐进暗示' | '雷厉风行';
type OpeningMode = '第一章开头' | '第二章末尾快进';

const origin = ref<Origin>('普通男友');
const style = ref<HypnoStyle>('渐进暗示');
const opening = ref<OpeningMode>('第一章开头');
const starting = ref(false);
const started = ref(false);
const maintext = ref('');
const option_text = ref('');
const error_message = ref('');

const origin_options: { value: Origin; label: string }[] = [
  { value: '普通男友', label: '普通男友' },
  { value: '隐藏富二代', label: '隐藏富二代' },
];

const style_options: { value: HypnoStyle; label: string }[] = [
  { value: '渐进暗示', label: '渐进暗示' },
  { value: '雷厉风行', label: '雷厉风行' },
];

const opening_options: { value: OpeningMode; label: string; desc: string }[] = [
  { value: '第一章开头', label: '第一章开头', desc: '除夕登门 · 从零试探' },
  { value: '第二章末尾快进', label: '第二章末尾快进', desc: '年初一清晨 · 直入高潮' },
];

const cast_list = [
  { key: '芸曦', name: '芸曦', role: '20岁 · 拜金女友', accent: '#d33a44' },
  { key: '戚巧瑜', name: '戚巧瑜', role: '39岁 · 豪门主母', accent: '#d9a441' },
  { key: '璐瑶', name: '璐瑶', role: '18岁 · 腹黑小妹', accent: '#db6b97' },
];

const origin_hint = computed(() =>
  origin.value === '隐藏富二代'
    ? '车钥匙与钱包里的黑卡，会让伯母和芸曦的态度先软一半。'
    : '以穷小子的身份登门，更能看清她们拜金嘴脸下的破绽。',
);

const style_hint = computed(() =>
  style.value === '雷厉风行'
    ? '第一次对视就落下强暗示，直接用命令建立支配。'
    : '从言语与触碰开始，一层层改写她们的常识与欲望。',
);

const preview_title = computed(() => (opening.value === '第一章开头' ? '除夕，戚家门前' : '年初一，主卧晨光'));

const preview_text = computed(() =>
  opening.value === '第一章开头'
    ? '你提着年礼站在戚家别墅门前，身边是刻意冷着脸的芸曦。门内，戚巧瑜正用笑容丈量你的家底，璐瑶则从二楼探头，等着看姐姐的拜金戏码如何收场。'
    : '你还没完全醒来，就有一道温热晨光落在主卧里。璐瑶在被子下偷吃，戚巧瑜推门而入，母女俩为清晨的第一份“美容礼物”争了起来。',
);

const preview_note = computed(() =>
  opening.value === '第一章开头'
    ? '所有关系都从零开始，你的一言一行都会决定三位女性对你的看法。'
    : '三位女性已进入服从阶段，芸曦沉沦在即；你拥有更强的支配基础，可以从容改写今天的家宴。',
);

const game_meta = computed(() => `${opening.value} · ${origin.value} · ${style.value}`);

const rendered_maintext = computed(() => maintext.value.replace(/\n/g, '<br>'));

onMounted(() => {
  window.scrollTo(0, 0);
});

function parse_block(content: string, tag: string): string {
  const match = content.match(new RegExp(`<${tag}>([\\s\\S]*?)<\\/${tag}>`, 'i'));
  return match ? match[1].trim() : '';
}

function extract_initvar(raw: string): Record<string, any> {
  const match = raw.match(/<initvar>\s*```yaml\n([\s\S]*?)\n```\s*<\/initvar>/i);
  if (!match) {
    throw new Error('未能从快进开局中提取初始变量');
  }
  return YAML.parse(match[1]) as Record<string, any>;
}

function chapter_one_story(): string {
  const style_line =
    style.value === '雷厉风行'
      ? '门锁落下的瞬间，我的视线已经越过礼物，稳稳落在她的眼睛上。'
      : '门锁落下的瞬间，我把礼物递过去，指尖不着痕迹地在她手背上停了一秒。';

  const origin_line =
    origin.value === '隐藏富二代'
      ? '黑色轿车停在街角，司机没有跟过来，只留我一人在戚家门前演这场戏。'
      : '我提着两盒看起来不算名贵的年礼，站在戚家门前，准备看她们怎么表演。';

  return `<maintext>
除夕 09:50，戚家别墅。${origin_line}

芸曦站在我身边，米白色高领针织衫配黑色百褶短裙，肉色保暖丝袜裹着修长美腿，脚下是一双崭新的黑色高跟鞋。她低头刷着最新款手机，余光却一直往别墅大门瞟，嘴角带着冷笑：「有些话我可先说清楚，进去之后别乱说话，也别表现得像个第一次进豪宅的土包子。」

我还没接话，玄关门就从里面打开。戚巧瑜穿着淡红色金边牡丹长裙迎出来，波浪卷长发盘成优雅发髻，右手翠绿玉镯在日光里晃了一下。她笑得温柔又周到，眼尾却不动声色地把我的衣着、鞋子和手里礼物的牌子都扫了一遍：「哎呀，来就来，还带什么东西。芸曦，快让人家进来。」

二楼探出一颗蘑菇头。璐瑶咬着草莓牛奶的吸管，圆眼睛亮晶晶地看戏：「姐夫，你惨啦，姐姐昨晚就在家演练怎么嫌弃你了。」

芸曦瞪她一眼，璐瑶吐了吐舌头缩回门后。戚巧瑜侧身让路，声音又轻又软：「先进来喝杯茶吧，家里没有别的规矩，别拘束。」${style_line}

这个春节，将会从这里开始彻底改写。
</maintext>

<option>
A. 进门后先打量客厅布局，再不着痕迹地观察戚巧瑜对礼物的反应
B. 趁芸曦不注意，在她耳边落下第一句只有两人听得见的暗示
C. 主动和璐瑶搭话，用一盒草莓大福收买这个小内应
</option>

<StatusPlaceHolderImpl/>`;
}

function chapter_two_story(): string {
  const option_marker = opening2_raw.indexOf('<option>');
  const story = option_marker >= 0 ? opening2_raw.slice(0, option_marker).trim() : opening2_raw.trim();
  const option = parse_block(opening2_raw, 'option');
  return `<maintext>
${story}
</maintext>

<option>
${option}
</option>

<StatusPlaceHolderImpl/>`;
}

function build_story(): string {
  return opening.value === '第二章末尾快进' ? chapter_two_story() : chapter_one_story();
}

function build_stat_data(): Record<string, any> {
  const data = JSON.parse(JSON.stringify(initvar)) as Record<string, any>;
  data['主角']['出身'] = origin.value;
  data['主角']['催眠风格'] = style.value;
  data['主角']['开局模式'] = opening.value;

  if (opening.value === '第二章末尾快进') {
    const fast_forward = extract_initvar(opening2_raw);
    data['世界'] = fast_forward['世界'];
    data['芸曦'] = fast_forward['芸曦'];
    data['戚巧瑜'] = fast_forward['戚巧瑜'];
    data['璐瑶'] = fast_forward['璐瑶'];
  }

  return data;
}

async function startGame() {
  if (starting.value) {
    return;
  }
  starting.value = true;
  error_message.value = '';

  try {
    await waitGlobalInitialized('Mvu');
    const story = build_story();
    const stat_data = build_stat_data();

    await createChatMessages([{ role: 'assistant', message: story }], { refresh: 'none' });

    const message_id = getLastMessageId();
    const mvu_data = Mvu.getMvuData({ type: 'message', message_id });
    _.set(mvu_data, 'stat_data', stat_data);
    await Mvu.replaceMvuData(mvu_data, { type: 'message', message_id });

    maintext.value = parse_block(story, 'maintext');
    option_text.value = parse_block(story, 'option');
    started.value = true;
    window.scrollTo(0, 0);
  } catch (error) {
    console.error('[新年催眠礼物] 开局创建失败', error);
    error_message.value = '开局创建失败，请检查酒馆助手与 MVU 框架是否已启用。';
  } finally {
    starting.value = false;
  }
}
</script>

<style lang="scss" scoped>
.home {
  width: 100%;
  min-height: 100%;
  padding: 22px 18px 30px;
  background:
    linear-gradient(rgba(200, 155, 74, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(200, 155, 74, 0.05) 1px, transparent 1px),
    var(--night);
  background-size: 26px 26px;
}

.masthead {
  max-width: 980px;
  margin: 0 auto 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 18px;
  background: var(--night-soft);
  border: 1px solid var(--gold);
  box-shadow: 4px 4px 0 rgba(200, 155, 74, 0.14);
}

.lantern-mark {
  width: 52px;
  height: 52px;
  flex: 0 0 52px;
  display: grid;
  place-items: center;
  background: var(--crimson);
  border: 1px solid var(--gold-soft);
  color: #fff2d9;
  font-size: 24px;
  font-weight: 700;
  border-radius: 8px;
  box-shadow: inset 0 0 0 3px rgba(255, 242, 217, 0.18);
}

.masthead-copy {
  min-width: 0;
}

.eyebrow {
  font-size: 11px;
  letter-spacing: 0.22em;
  color: var(--gold-soft);
  text-transform: uppercase;
}

h1 {
  font-size: 30px;
  line-height: 1.15;
  color: #fff4df;
  letter-spacing: 0.08em;
}

.subtitle {
  margin-top: 3px;
  color: var(--muted);
  font-size: 13px;
}

.intro-layout {
  max-width: 980px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(300px, 0.8fr);
  gap: 18px;
  align-items: start;
}

.story-column {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.story-block {
  padding: 18px;
  background: rgba(246, 236, 219, 0.96);
  color: var(--ink);
  border: 1px solid var(--gold);
  box-shadow: 4px 4px 0 rgba(200, 155, 74, 0.14);
}

.section-kicker {
  display: inline-block;
  margin-bottom: 8px;
  padding: 2px 8px;
  background: var(--crimson-deep);
  color: #ffe9bf;
  font-size: 11px;
  font-weight: 700;
}

.story-block h2 {
  font-size: 22px;
  color: var(--crimson-deep);
  margin-bottom: 8px;
}

.story-block p {
  font-size: 14px;
}

.story-block .preview-note {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed rgba(126, 30, 37, 0.35);
  color: #6d5745;
  font-size: 12px;
}

.cast-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.cast-cell {
  min-width: 0;
  background: var(--night-soft);
  border: 1px solid var(--line);
  overflow: hidden;
}

.cast-art {
  height: 150px;
  display: grid;
  place-items: center;
  position: relative;
  background:
    repeating-linear-gradient(135deg, rgba(246, 236, 219, 0.06) 0 1px, transparent 1px 9px),
    rgba(246, 236, 219, 0.06);
  color: var(--accent);
}

.cast-art::before {
  content: '';
  position: absolute;
  inset: 14px;
  border: 1px solid currentColor;
  opacity: 0.55;
  transform: rotate(2deg);
}

.cast-art span {
  position: relative;
  z-index: 1;
  font-size: 46px;
  font-weight: 700;
}

.cast-copy {
  padding: 9px 10px;
  border-top: 2px solid var(--accent);
}

.cast-copy h3 {
  color: #fff0d5;
  font-size: 16px;
}

.cast-copy p {
  color: var(--muted);
  font-size: 11px;
}

.setup-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
  background: var(--paper);
  color: var(--ink);
  border: 1px solid var(--gold);
  box-shadow: 4px 4px 0 rgba(200, 155, 74, 0.14);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.field-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--crimson-deep);
}

.segmented {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}

.segment {
  min-height: 42px;
  padding: 7px 8px;
  border: 1.5px solid rgba(36, 26, 20, 0.35);
  background: #fff8ea;
  color: var(--ink);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.16s ease, color 0.16s ease, transform 0.16s ease;
}

.segment:hover {
  border-color: var(--crimson);
}

.segment.selected {
  background: var(--crimson);
  border-color: var(--crimson-deep);
  color: #fff4df;
}

.segment:active {
  transform: translateY(1px);
}

.opening-segments {
  grid-template-columns: 1fr;
}

.opening-segment {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  min-height: 56px;
}

.opening-segment small {
  font-size: 11px;
  font-weight: 400;
  opacity: 0.85;
}

.field-hint {
  font-size: 11px;
  color: #6d5745;
  min-height: 15px;
}

.start-button {
  width: 100%;
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border: 1px solid var(--gold-soft);
  background: var(--crimson-deep);
  color: #fff3d8;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 3px 3px 0 rgba(126, 30, 37, 0.35);
}

.start-button:hover:not(:disabled) {
  background: #8f222b;
}

.start-button:disabled {
  opacity: 0.6;
  cursor: wait;
}

.start-arrow {
  font-size: 19px;
}

.error-message {
  color: #a32b2b;
  font-size: 12px;
}

.game-screen {
  max-width: 860px;
  margin: 0 auto;
  padding: 16px;
  background: var(--paper);
  color: var(--ink);
  border: 1px solid var(--gold);
  box-shadow: 4px 4px 0 rgba(200, 155, 74, 0.14);
}

.game-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  padding-bottom: 9px;
  border-bottom: 2px solid var(--crimson-deep);
  color: #6d5745;
  font-size: 12px;
}

.game-tag {
  padding: 2px 8px;
  background: var(--crimson);
  color: #fff4df;
  font-weight: 700;
}

.maintext {
  font-size: 14px;
  line-height: 1.8;
  white-space: normal;
}

.option-block {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed rgba(36, 26, 20, 0.3);
}

.option-text {
  white-space: pre-wrap;
  font-size: 13px;
  color: #4d3b2d;
}

@media (max-width: 820px) {
  .intro-layout {
    grid-template-columns: 1fr;
  }

  .cast-art {
    height: 120px;
  }
}

@media (max-width: 560px) {
  .home {
    padding: 14px 10px 20px;
  }

  h1 {
    font-size: 24px;
  }

  .lantern-mark {
    width: 44px;
    height: 44px;
    flex-basis: 44px;
    font-size: 20px;
  }

  .cast-row {
    grid-template-columns: 1fr;
  }

  .cast-art {
    height: 170px;
  }
}
</style>
