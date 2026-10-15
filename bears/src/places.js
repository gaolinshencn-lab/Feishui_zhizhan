// Map layout of Bear Ridge (狗熊岭). World units ≈ metres on a 200 × 200 board; x east, z south.
// The layout is a fan interpretation: places and their relative positions are drawn for clarity,
// not traced from any official map.

export const BOARD = 200;
export const LAKE = { x: -55, z: 54, rx: 30, rz: 20, level: 2.3 };
// Dark cliff on the lake's north-west shore with a waterfall dropping straight into the lake.
export const CLIFF = { from: -2.75, to: -1.3, e: 1.12, fallAngle: -2.0, height: 14 };
export const lakePoint = (theta, e = 1) => [LAKE.x + Math.cos(theta) * LAKE.rx * e, LAKE.z + Math.sin(theta) * LAKE.rz * e];

// Creek: from the pool under the waterfall, down through the forest into the lake.
export const RIVER = [
  [12, -53], [9, -40], [1, -27], [-8, -12], [-12, 2], [-18, 16], [-30, 28], [-42, 40], [-50, 50],
];
// Outflow from the lake to the south-west edge of the board.
export const OUTFLOW = [
  [-77, 67], [-84, 74], [-92, 80], [-101, 86],
];
export const WATERFALL = { top: [15, -66], pool: [12, -53] };

// Dirt tracks (width in metres).
export const PATHS = [
  { w: 2.2, pts: [[30, -7], [20, -3], [8, 1], [-4, 2], [-12, 2], [-24, -5], [-40, -10], [-56, -10], [-70, -8]] },
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
  { x: -70, z: -8, r: 7 }, // Tiki and Babu's cave
  { x: -6, z: 24, r: 4.5 }, // Hoo Hoo's tree house
  { x: -25, z: -11, r: 4.5 }, // Warren's tree hollow
  { x: -50, z: 78, r: 6 }, // lake beach and dock
];

// Hills added to the base terrain: [x, z, height, radius]
export const HILLS = [
  [38, -15, 5, 10],
  [-86, -12, 9, 18],
  [-72, 22, 12, 13], // high ground behind the lake cliff
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
    brief: '森林东南边的伐木工小屋：暗红色木板墙、灰蓝色石板屋顶、绿色格子门窗，门边挂着红辣椒串，院里停着他的蓝色皮卡。',
    text: S(
      '光头强又接到李老板的电话，扛起电锯准备进山。',
      '小院里晒着衣服，蓝色皮卡的引擎盖晒得发烫。',
      '院里堆起南瓜和柴火，烟囱开始冒烟。',
      '屋檐挂满冰凌，炉火烧得正旺，皮卡埋在雪里。'
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
    brief: '横跨小溪的木桥，连接熊大熊二的树洞和西边吉吉的山洞。',
    text: S(
      '溪水涨了，桥下哗哗作响。',
      '常有人在桥上钓鱼，也有人被挤下河。',
      '落叶顺着溪水漂向湖里。',
      '小溪结冰，过桥不如直接从冰面上滑过去。'
    ),
  },
  {
    id: 'lake', name: '林中大湖', x: -55, z: 56, y: 2, kind: 'water',
    brief: '小溪汇入的大湖。南岸是一片橙黄色的沙滩，常有小螃蟹横着爬；北岸是黑色的石崖，一道瀑布从崖顶直落湖中。',
    text: S(
      '湖冰消融，湖边柳枝抽芽。',
      '湖上荡着一条小木船，荷叶铺满湖湾。',
      '湖水更清，倒映着金黄的林子。',
      '湖面冻成天然滑冰场。'
    ),
  },
  {
    id: 'cliff', name: '湖边瀑布', x: -66, z: 34, y: 14, kind: 'water',
    brief: '大湖北岸的黑色石崖，瀑布从崖顶落进湖里，崖下和湖边长着金黄的白桦。',
    text: S('雪水让瀑布变得又宽又急。', '瀑布下的水花最凉快。', '夕阳下石崖和金黄的白桦倒映在湖里。', '瀑布冻成一道冰柱。'),
  },
  {
    id: 'cabinin', name: '光头强家里', x: 55, z: 38, y: 0, kind: 'interior',
    brief: '掀开屋顶看看光头强的家：石板地面、蓝灰色木板墙，土炕上铺着竹席和蓝底白花的旧被子，墙角一台绿色冰箱，青绿色的灶台上放着炒锅，圆窗旁挂着辣椒串和玉米。',
    text: S('开春了，光头强把炕上的被子拿出去晒。', '天热，光头强穿着背心短裤在灶台前做饭。', '玉米和辣椒挂满房梁，冰箱里放着强妈腌的酸菜。', '炕烧得热乎乎的，光头强困了就上炕睡觉。'),
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
    id: 'cave', name: '吉吉和毛毛的山洞', x: -73, z: -8, y: 6, kind: 'home',
    brief: '西边山坡上的石洞，熊大熊二帮吉吉国王和毛毛建的家。洞口有吉吉的石头宝座和一堆果子。',
    text: S(
      '吉吉国王坐在洞口的石头上，指挥毛毛去摘新果子。',
      '洞里凉快，猴子们中午都躲在里面。',
      '果子堆得最高的季节，吉吉国王最得意。',
      '洞口积雪，吉吉和毛毛缩在洞里取暖。'
    ),
  },
  {
    id: 'owlhouse', name: '涂涂的树屋', x: -6, z: 24, y: 10, kind: 'home',
    brief: '小溪东岸一棵大树上的小木屋，猫头鹰涂涂住在这里。',
    text: S('涂涂从树屋里飞出来，在草甸上空打转。', '树冠浓密，树屋几乎看不见。', '黄叶落尽前，树屋重新露出来。', '树屋顶上积着雪，涂涂在里面打瞌睡。'),
  },
  {
    id: 'squirrel', name: '蹦蹦的树洞', x: -25, z: -11, y: 8, kind: 'home',
    brief: '木桥西边一棵大松树上的树洞，松鼠蹦蹦在里面囤满了松果。',
    text: S('蹦蹦清点过冬剩下的松果。', '蹦蹦在树下跑来跑去，打探消息。', '松果成熟，蹦蹦一趟趟往树洞里搬。', '树洞里塞满松果，蹦蹦很少出门。'),
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
    brief: '从木屋通往山外的土路，光头强开着蓝色皮卡从这里进出森林。',
    text: S('路边野花盛开。', '尘土飞扬，运木材的车来来往往。', '路面铺满落叶。', '积雪没过车轮，大雪封山。'),
  },
  {
    id: 'pines', name: '松林', x: -70, z: -50, y: 8, kind: 'forest',
    brief: '主峰脚下的一片常绿松林，四季都是绿色。',
    text: S('松针换上新绿。', '林下凉爽，松鼠很多。', '松果成熟落了一地。', '松枝上压着厚厚一层雪。'),
  },
];
