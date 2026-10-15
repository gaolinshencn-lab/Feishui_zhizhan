// Map layout of Bear Ridge (狗熊岭). World units ≈ metres on a 200 × 200 board; x east, z south.
// The layout is a fan interpretation: places and their relative positions are drawn for clarity,
// not traced from any official map.

export const BOARD = 200;
export const LAKE = { x: -52, z: 52, rx: 24, rz: 17, level: 2.3 };

// Creek: from the pool under the waterfall, down through the forest into the lake.
export const RIVER = [
  [12, -53], [9, -40], [1, -27], [-8, -12], [-12, 2], [-18, 16], [-30, 28], [-42, 40], [-50, 50],
];
// Outflow from the lake to the south-west edge of the board.
export const OUTFLOW = [
  [-64, 64], [-74, 72], [-86, 80], [-101, 86],
];
export const WATERFALL = { top: [15, -66], pool: [12, -53] };

// Dirt tracks (width in metres).
export const PATHS = [
  { w: 2.2, pts: [[30, -7], [20, -3], [8, 1], [-4, 2], [-12, 2], [-24, -5], [-40, -14], [-52, -20]] },
  { w: 2.0, pts: [[8, 1], [9, 14], [12, 28], [24, 38], [40, 42], [50, 42]] },
  { w: 3.4, pts: [[56, 46], [66, 52], [80, 58], [92, 64], [101, 68]] },
  { w: 1.6, pts: [[33, -10], [38, -18], [42, -24]] },
  { w: 1.6, pts: [[12, 28], [0, 38], [-14, 44], [-28, 46]] },
  { w: 1.4, pts: [[-4, 2], [2, -16], [8, -32], [11, -46]] },
  { w: 1.8, pts: [[50, 42], [62, 36], [70, 32]] },
];

// Flattened clearings with no trees.
export const CLEARINGS = [
  { x: 30, z: -6, r: 9 }, // bears' home
  { x: 43, z: -26, r: 6 }, // honey tree
  { x: 55, z: 42, r: 13 }, // Logger Vick's cabin
  { x: 70, z: 32, r: 9 }, // log yard
  { x: 12, z: 30, r: 15, meadow: true }, // flower meadow
  { x: -55, z: -21, r: 9 }, // monkey king's tree
  { x: -30, z: 47, r: 5 }, // lake shore landing
];

// Hills added to the base terrain: [x, z, height, radius]
export const HILLS = [
  [38, -15, 5, 10],
  [-86, -12, 9, 18],
  [80, -10, 7, 16],
  [-20, -82, 18, 22],
  [42, -84, 12, 18],
  [-70, -78, 10, 20],
];

const S = (spring, summer, autumn, winter) => ({ spring, summer, autumn, winter });

export const PLACES = [
  {
    id: 'home', name: '熊大熊二的家', x: 29, z: -7, y: 8, kind: 'home',
    brief: '一棵巨大老树的树洞，熊大熊二住在里面。树根下开着拱形木门，门前小路通往木桥和蜂蜜树。',
    text: S(
      '冬眠结束，熊大推开木门伸个懒腰，门口的野花一夜之间全开了。',
      '天热，兄弟俩常在门前树荫下乘凉，熊二惦记着蜂蜜树。',
      '熊二把采来的松果、蘑菇和蜂蜜一筐筐囤进屋里，为过冬做准备。',
      '大雪封门，屋顶积着厚厚的雪；熊大熊二围着围巾出门堆雪人。'
    ),
  },
  {
    id: 'honey', name: '蜂蜜树', x: 43, z: -26, y: 9, kind: 'tree',
    brief: '熊窝后面的老树，树杈上挂着几个蜂巢，是熊二最爱去的地方。',
    text: S(
      '花开了，蜜蜂嗡嗡地忙起来，蜂巢一天比一天沉。',
      '一年里蜂蜜最多的时候，熊二常常被蜜蜂追着满山跑。',
      '树叶变黄，蜂巢里存满了过冬的蜜。',
      '蜜蜂躲进蜂巢过冬，树枝光秃秃地挂着雪。'
    ),
  },
  {
    id: 'cabin', name: '光头强的木屋', x: 55, z: 40, y: 5, kind: 'cabin',
    brief: '森林东南边的伐木工小屋，门口停着伐木车，屋后是木材堆。',
    text: S(
      '光头强又接到老板的电话，扛起油锯准备进山。',
      '小院里晒着衣服，伐木车的引擎盖晒得发烫。',
      '院里堆起南瓜和柴火，烟囱开始冒烟。',
      '屋檐挂满冰凌，炉火烧得正旺，伐木车埋在雪里。'
    ),
  },
  {
    id: 'logyard', name: '伐木场', x: 70, z: 32, y: 2, kind: 'yard',
    brief: '木屋东边的空地，一排排树桩和码放整齐的原木。',
    text: S(
      '新冒出的嫩芽从树桩边钻出来。',
      '原木堆在太阳下散发松脂香。',
      '落叶把树桩盖了一层。',
      '原木堆变成了一座座雪丘。'
    ),
  },
  {
    id: 'falls', name: '山间瀑布', x: 13, z: -60, y: 10, kind: 'water',
    brief: '主峰南坡的瀑布，跌入水潭后汇成穿过森林的小溪。',
    text: S(
      '雪水融化，瀑布水量大增，水声隆隆。',
      '水潭边最凉快，是森林里的避暑地。',
      '水边枫叶红透，倒映在潭里。',
      '整条瀑布冻成了冰帘。'
    ),
  },
  {
    id: 'bridge', name: '小溪木桥', x: -12, z: 2, y: 2, kind: 'bridge',
    brief: '横跨小溪的木桥，连接熊窝和西边的猴王树。',
    text: S(
      '溪水涨了，桥下哗哗作响。',
      '常有人在桥上钓鱼，也有人被挤下河。',
      '落叶顺着溪水漂向湖里。',
      '小溪结冰，过桥不如直接从冰面上滑过去。'
    ),
  },
  {
    id: 'lake', name: '林中大湖', x: -52, z: 52, y: 2, kind: 'water',
    brief: '小溪汇入的湖泊，湖边有一个小码头。',
    text: S(
      '湖冰消融，湖边柳枝抽芽。',
      '湖上荡着一条小木船，荷叶铺满湖湾。',
      '湖水更清，倒映着金黄的林子。',
      '湖面冻成天然滑冰场。'
    ),
  },
  {
    id: 'meadow', name: '花海草甸', x: 12, z: 30, y: 2, kind: 'meadow',
    brief: '森林中央的一片开阔草地，几条小路在这里交汇。',
    text: S(
      '漫山遍野的野花，蝴蝶成群。',
      '青草齐膝，夜里满是萤火虫。',
      '草甸变成金黄色，堆着草垛。',
      '一片平整的雪原，适合打雪仗。'
    ),
  },
  {
    id: 'monkey', name: '猴王树', x: -55, z: -21, y: 12, kind: 'tree',
    brief: '西边林子里最粗的一棵大树，树上搭着吉吉国王的宝座平台。',
    text: S(
      '吉吉国王在树上巡视他的“领地”。',
      '树冠最浓密的时候，树下一片阴凉。',
      '满树黄叶，平台上堆着收来的果子。',
      '平台积雪，猴子们挤在一起取暖。'
    ),
  },
  {
    id: 'burrow', name: '萝卜头的地洞', x: 26, z: 20, y: 3, kind: 'home',
    brief: '花海草甸东边的地洞，旁边是萝卜头种的萝卜地。',
    text: S('萝卜刚种下，冒出嫩叶。', '萝卜长得正好，萝卜头天天守着。', '收萝卜的季节，地洞里囤满了萝卜。', '萝卜地被雪盖住，萝卜头躲在洞里不出来。'),
  },
  {
    id: 'peak', name: '狗熊岭主峰', x: -20, z: -80, y: 30, kind: 'mountain',
    brief: '北边的山脊，是整片森林的水源。',
    text: S(
      '山顶积雪开始融化。',
      '山脊一片苍翠。',
      '山腰红黄相间。',
      '整座山一片雪白。'
    ),
  },
  {
    id: 'road', name: '出山公路', x: 92, z: 64, y: 2, kind: 'road',
    brief: '从木屋通往山外小镇的土路，木材从这里运出去。',
    text: S('路边野花盛开。', '尘土飞扬，运木材的车来来往往。', '路面铺满落叶。', '积雪没过车轮，大雪封山。'),
  },
  {
    id: 'pines', name: '松林', x: -70, z: -50, y: 8, kind: 'forest',
    brief: '主峰脚下的一片常绿松林，四季都是绿色。',
    text: S('松针换上新绿。', '林下凉爽，松鼠很多。', '松果成熟落了一地。', '松枝上压着厚厚一层雪。'),
  },
];
