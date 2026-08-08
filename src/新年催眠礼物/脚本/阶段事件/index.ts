const stage_keys = [
  { key: '芸曦', keyword: '【阶段事件·芸曦】' },
  { key: '戚巧瑜', keyword: '【阶段事件·戚巧瑜】' },
  { key: '璐瑶', keyword: '【阶段事件·璐瑶】' },
] as const;

$(async () => {
  await waitGlobalInitialized('Mvu');

  eventOn(Mvu.events.VARIABLE_UPDATE_ENDED, (variables, variables_before_update) => {
    const before = _.get(variables_before_update, 'stat_data', {});
    const after = _.get(variables, 'stat_data', {});

    for (const { key, keyword } of stage_keys) {
      const old_stage = _.get(before, `${key}.催眠阶段`, 0);
      const new_stage = _.get(after, `${key}.催眠阶段`, 0);
      if (Number(new_stage) > Number(old_stage)) {
        console.info(`[新年催眠礼物] ${key} 催眠阶段推进 ${old_stage} -> ${new_stage}`);
        injectPrompts(
          [
            {
              id: `新年催眠礼物:${key}:阶段事件`,
              position: 'none',
              depth: 0,
              role: 'system',
              content: keyword,
              should_scan: true,
            },
          ],
          { once: true },
        );
      }
    }
  });
});
