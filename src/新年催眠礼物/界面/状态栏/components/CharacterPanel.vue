<template>
  <article class="char-panel" :style="{ '--accent': props.accent }">
    <div class="portrait-zone">
      <img
        v-if="!portrait_error"
        :src="portrait_src"
        :alt="`${props.label} 立绘`"
        class="portrait-img"
        @error="portrait_error = true"
      />
      <div v-else class="portrait-fallback" aria-hidden="true">
        <span class="fallback-mark">{{ props.label.slice(0, 1) }}</span>
        <span class="fallback-line"></span>
      </div>
      <div class="stage-ribbon">{{ stage_label }}</div>
    </div>

    <div class="char-head">
      <div>
        <h3 class="char-name">{{ props.label }}</h3>
        <p class="char-subtitle">{{ props.subtitle }}</p>
      </div>
      <div class="stage-dots" :title="`催眠阶段 ${stage}`">
        <span v-for="dot in 5" :key="dot" class="stage-dot" :class="{ active: dot <= stage }"></span>
      </div>
    </div>

    <div class="body-grid">
      <div v-for="(description, part) in char_data.身体部位" :key="part" class="body-cell">
        <span class="body-part">{{ part }}</span>
        <span class="body-desc">{{ description }}</span>
      </div>
    </div>

    <div class="outfit-block">
      <span class="block-label">服装</span>
      <p class="outfit-text">{{ char_data.服装 }}</p>
    </div>

    <div class="inner-block">
      <span class="block-label">心里话</span>
      <p class="inner-text">{{ char_data.心里话 }}</p>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useDataStore } from '../store';

const props = defineProps<{
  characterKey: '芸曦' | '戚巧瑜' | '璐瑶';
  label: string;
  subtitle: string;
  accent: string;
}>();

const store = useDataStore();
const portrait_error = ref(false);

const char_data = computed(() => (store.data as any)[props.characterKey]);
const stage = computed(() => Number(char_data.value.催眠阶段) || 0);
const stage_label = computed(() => char_data.value.$催眠阶段 || '抗拒');
const portrait_src = computed(() => `./portraits/${props.characterKey}/阶段${stage.value}.png`);

watch(stage, () => {
  portrait_error.value = false;
});
</script>

<style lang="scss" scoped>
.char-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #fffaf2;
  border: 1.5px solid var(--ink);
  box-shadow: 3px 3px 0 rgba(27, 22, 18, 0.14);
}

.portrait-zone {
  position: relative;
  height: 170px;
  background:
    repeating-linear-gradient(135deg, rgba(27, 22, 18, 0.05) 0 1px, transparent 1px 8px),
    var(--paper-deep);
  border-bottom: 2px solid var(--accent);
  overflow: hidden;
}

.portrait-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: top center;
  display: block;
}

.portrait-fallback {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  position: relative;
  color: var(--accent);
}

.fallback-mark {
  width: 92px;
  height: 92px;
  display: grid;
  place-items: center;
  border: 2px solid currentColor;
  background: rgba(255, 250, 242, 0.7);
  font-size: 40px;
  font-weight: 700;
  border-radius: 8px;
  transform: rotate(-3deg);
}

.fallback-line {
  position: absolute;
  left: 12%;
  right: 12%;
  bottom: 22px;
  height: 2px;
  background: currentColor;
  opacity: 0.45;
}

.stage-ribbon {
  position: absolute;
  right: 8px;
  top: 8px;
  padding: 4px 9px;
  background: var(--crimson-deep);
  color: #ffeac2;
  font-size: 11px;
  font-weight: 700;
  border: 1px solid var(--gold-soft);
  box-shadow: 2px 2px 0 rgba(27, 22, 18, 0.3);
}

.char-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 9px 10px 7px;
  border-bottom: 1px dashed var(--line);
}

.char-name {
  font-size: 17px;
  color: var(--crimson-deep);
  line-height: 1.2;
}

.char-subtitle {
  margin-top: 2px;
  color: var(--muted);
  font-size: 10px;
}

.stage-dots {
  display: flex;
  gap: 3px;
  padding-top: 3px;
}

.stage-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #d8c9b2;
  border: 1px solid rgba(27, 22, 18, 0.35);
}

.stage-dot.active {
  background: var(--accent);
  border-color: var(--ink);
}

.body-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
  padding: 9px 10px;
}

.body-cell {
  min-width: 0;
  padding: 5px 6px;
  background: #fff3df;
  border: 1px solid var(--line);
}

.body-part {
  display: inline-block;
  margin-bottom: 2px;
  padding: 1px 5px;
  background: var(--ink);
  color: var(--gold-soft);
  font-size: 9px;
  font-weight: 700;
}

.body-desc {
  display: block;
  font-size: 11px;
  color: #4d4036;
}

.outfit-block,
.inner-block {
  margin: 0 10px 9px;
  padding: 7px 8px;
  border-left: 4px solid var(--accent);
  background: #fff6e6;
}

.block-label {
  display: block;
  margin-bottom: 2px;
  font-size: 10px;
  font-weight: 700;
  color: var(--crimson-deep);
}

.outfit-text,
.inner-text {
  font-size: 11px;
  color: #4d4036;
}

.inner-text {
  font-style: italic;
}

@media (max-width: 480px) {
  .portrait-zone {
    height: 220px;
  }
}
</style>
