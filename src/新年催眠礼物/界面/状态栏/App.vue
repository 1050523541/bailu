<template>
  <section class="status-shell">
    <div class="status-head">
      <div class="brand-mark">新</div>
      <div class="head-meta">
        <span class="meta-time">{{ store.data.世界.当前时间 }}</span>
        <span class="meta-place">{{ store.data.世界.当前地点 }}</span>
      </div>
      <div class="head-title">新年催眠礼物</div>
    </div>

    <div class="affairs-row">
      <div v-for="(description, name) in store.data.世界.近期事务" :key="name" class="affair-chip">
        <span class="affair-name">{{ name }}</span>
        <span class="affair-desc">{{ description }}</span>
      </div>
      <div v-if="_.isEmpty(store.data.世界.近期事务)" class="affair-chip">
        <span class="affair-name">暂无事务</span>
        <span class="affair-desc">当前没有需要记录的事务</span>
      </div>
    </div>

    <div class="char-grid">
      <CharacterPanel
        v-for="character in characters"
        :key="character.key"
        :character-key="character.key"
        :label="character.label"
        :subtitle="character.subtitle"
        :accent="character.accent"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import _ from 'lodash';
import CharacterPanel from './components/CharacterPanel.vue';
import { useDataStore } from './store';

const store = useDataStore();

const characters = [
  { key: '芸曦', label: '芸曦', subtitle: '20岁 · 大三 · 拜金女友', accent: '#c9303c' },
  { key: '戚巧瑜', label: '戚巧瑜', subtitle: '39岁 · 豪门主母 · 伪善伯母', accent: '#b8863b' },
  { key: '璐瑶', label: '璐瑶', subtitle: '18岁 · 大一新生 · 腹黑小妹', accent: '#d05a8a' },
];
</script>

<style lang="scss" scoped>
.status-shell {
  width: 100%;
  background: var(--paper);
  border: 2px solid var(--ink);
  box-shadow: 4px 4px 0 rgba(27, 22, 18, 0.18);
  overflow: hidden;
  color: var(--ink);
  font-size: 13px;
}

.status-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: var(--ink);
  color: var(--paper);
  border-bottom: 3px solid var(--gold);
}

.brand-mark {
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  display: grid;
  place-items: center;
  background: var(--crimson);
  border: 1px solid var(--gold-soft);
  color: #fff6e6;
  font-size: 18px;
  font-weight: 700;
}

.head-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
  font-size: 12px;
  color: var(--gold-soft);
}

.meta-time,
.meta-place {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.head-title {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: #fff;
  white-space: nowrap;
}

.affairs-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px;
  padding: 10px 12px;
  background: var(--paper-deep);
  border-bottom: 2px solid var(--line);
}

.affair-chip {
  min-width: 0;
  padding: 6px 8px;
  background: #fffaf0;
  border-left: 4px solid var(--gold);
  box-shadow: 0 1px 0 rgba(27, 22, 18, 0.08);
}

.affair-name {
  display: block;
  font-weight: 700;
  color: var(--crimson-deep);
  font-size: 12px;
}

.affair-desc {
  display: block;
  color: var(--muted);
  font-size: 11px;
}

.char-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  padding: 12px;
}

@media (max-width: 760px) {
  .char-grid {
    grid-template-columns: 1fr;
  }

  .head-title {
    display: none;
  }
}
</style>
