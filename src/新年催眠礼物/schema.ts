export const Schema = z.object({
  世界: z.object({
    当前时间: z.string().prefault('待初始化'),
    当前地点: z.string().prefault('待初始化'),
    近期事务: z.record(z.string().describe('事务名'), z.string().describe('事务描述')).prefault({}),
  }),

  主角: z.object({
    身份: z.string().prefault('玩家扮演的男主角'),
    出身: z.enum(['普通男友', '隐藏富二代']).prefault('普通男友'),
    催眠风格: z.enum(['渐进暗示', '雷厉风行']).prefault('渐进暗示'),
    开局模式: z.enum(['第一章开头', '第二章末尾快进']).prefault('第一章开头'),
    催眠能力: z.string().prefault('视线暗示与常识修改'),
    目标: z.string().prefault('让三个女人在春节期间彻底沉沦'),
  }),

  芸曦: z
    .object({
      催眠阶段: z.coerce.number().prefault(0).transform(value => _.clamp(Math.floor(value), 0, 4)),
      身体部位: z
        .record(z.enum(['脸', '胸', '下体', '腿', '全身']), z.string().prefault('待初始化'))
        .prefault({
          脸: '待初始化',
          胸: '待初始化',
          下体: '待初始化',
          腿: '待初始化',
          全身: '待初始化',
        }),
      服装: z.string().prefault('待初始化'),
      心里话: z.string().prefault('待初始化'),
    })
    .transform(data => ({
      ...data,
      $催眠阶段: ['抗拒', '迷惑', '服从', '沉沦', '信赖'][data.催眠阶段] ?? '抗拒',
    })),

  戚巧瑜: z
    .object({
      催眠阶段: z.coerce.number().prefault(0).transform(value => _.clamp(Math.floor(value), 0, 4)),
      身体部位: z
        .record(z.enum(['脸', '胸', '下体', '腿', '全身']), z.string().prefault('待初始化'))
        .prefault({
          脸: '待初始化',
          胸: '待初始化',
          下体: '待初始化',
          腿: '待初始化',
          全身: '待初始化',
        }),
      服装: z.string().prefault('待初始化'),
      心里话: z.string().prefault('待初始化'),
    })
    .transform(data => ({
      ...data,
      $催眠阶段: ['抗拒', '迷惑', '服从', '沉沦', '信赖'][data.催眠阶段] ?? '抗拒',
    })),

  璐瑶: z
    .object({
      催眠阶段: z.coerce.number().prefault(0).transform(value => _.clamp(Math.floor(value), 0, 4)),
      身体部位: z
        .record(z.enum(['脸', '胸', '下体', '腿', '全身']), z.string().prefault('待初始化'))
        .prefault({
          脸: '待初始化',
          胸: '待初始化',
          下体: '待初始化',
          腿: '待初始化',
          全身: '待初始化',
        }),
      服装: z.string().prefault('待初始化'),
      心里话: z.string().prefault('待初始化'),
    })
    .transform(data => ({
      ...data,
      $催眠阶段: ['抗拒', '迷惑', '服从', '沉沦', '信赖'][data.催眠阶段] ?? '抗拒',
    })),
});
export type Schema = z.output<typeof Schema>;
