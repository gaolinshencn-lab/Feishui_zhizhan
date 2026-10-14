// Places shown on the two sand tables.
// Coordinates are [lon, lat] (WGS84). Ancient sites follow 《水经注》, 胡三省《通鉴》注 and
// modern gazetteers; sites whose exact location is unknown are flagged with `approx`.
//
// kind: capital | city | fort | camp | pass | mountain | region | polity | ford | site
// rank: 1 = always shown, 2 = shown when zoomed in a little, 3 = only close up

export const TACTICAL_PLACES = [
  {
    id: 'shouyang', name: '寿阳', alt: '寿春', modern: '今安徽寿县', kind: 'city', rank: 1,
    at: [116.786, 32.578],
    note: '淮南郡治。东晋避讳称寿阳。城北临淝水，北望八公山。十月癸酉为苻融攻陷，决战后晋军收复。',
  },
  {
    id: 'bagong', name: '八公山', modern: '今淮南市八公山', kind: 'mountain', rank: 1,
    at: [116.800, 32.628],
    note: '胡三省注：“八公山在今寿春县北四里。”苻坚登城北望，见山上草木皆类人形，即“草木皆兵”所出。',
  },
  {
    id: 'xiashi', name: '硖石', modern: '今凤台县东南硖山口', kind: 'fort', rank: 1,
    at: [116.736, 32.697],
    note: '《水经注》：淮水过寿春北，“又北逕山峡中，谓之峡石，对岸山上结二城，以防津要”。胡彬退保于此。',
  },
  {
    id: 'feikou', name: '肥口', modern: '淝水入淮处', kind: 'site', rank: 2,
    at: [116.742, 32.626],
    note: '《水经注》：肥水“又西北注于淮，是曰肥口”。郦道元指此一带为“坚战败处”。',
  },
  {
    id: 'yingkou', name: '颍口', modern: '今寿县正阳关附近', kind: 'ford', rank: 1,
    at: [116.520, 32.505],
    note: '颍水入淮之口。九月，苻融等兵三十万先至颍口，由此渡淮南攻寿阳。',
  },
  {
    id: 'xiacai', name: '下蔡', modern: '今凤台县', kind: 'city', rank: 2,
    at: [116.706, 32.712],
    note: '淮北城邑，杜佑云“硖石，今汝阴郡下蔡县”。',
  },
  {
    id: 'luokou', name: '洛口', modern: '窑河入淮处', kind: 'site', rank: 2,
    at: [117.091, 32.772],
    note: '胡三省引《水经注》：“洛涧上承死马塘水，北历秦墟，下注淮，谓之洛口。”',
  },
  {
    id: 'luojian', name: '洛涧', modern: '今窑河—洛河', kind: 'ford', rank: 1,
    at: [117.140, 32.728],
    note: '秦卫将军梁成率众五万屯此，“栅淮以遏东兵”。十一月刘牢之以精兵五千夜袭破之。',
  },
  {
    id: 'jincamp', name: '晋军大营', modern: '去洛涧二十五里', kind: 'camp', rank: 1,
    at: [117.222, 32.702], approx: true,
    note: '谢石、谢玄等“去洛涧二十五里而军，惮成不敢进”。晋一里约合今435米，营址据此示意。',
  },
  {
    id: 'qinggang', name: '青冈', modern: '确址无考', kind: 'site', rank: 1,
    at: [116.640, 32.522], approx: true,
    note: '晋军乘胜追击“至于青冈”。胡三省注：“青冈去今寿春县三十里。”方位史无明文，图中按秦军西奔颍口方向示意。',
  },
  {
    id: 'huaibei', name: '淮北', modern: '', kind: 'region', rank: 2,
    at: [116.560, 32.700],
    note: '苻坚中流矢，单骑走至淮北。',
  },
  {
    id: 'huainan', name: '淮南', modern: '', kind: 'region', rank: 2,
    at: [116.990, 32.520],
    note: '',
  },
];

export const STRATEGIC_PLACES = [
  { id: 'changan', name: '长安', modern: '今陕西西安', kind: 'capital', rank: 1, at: [108.88, 34.30], side: 'qin', note: '前秦都城。八月甲子，苻坚自此发兵。' },
  { id: 'xianyang', name: '咸阳', modern: '今陕西咸阳', kind: 'city', rank: 3, at: [108.70, 34.38], note: '苻坚至项城时，“凉州之兵始达咸阳”。' },
  { id: 'xinping', name: '新平', modern: '今陕西彬州', kind: 'city', rank: 3, at: [108.08, 35.03], note: '太元十年（385年），姚苌缢杀苻坚于新平佛寺。' },
  { id: 'tongguan', name: '潼关', modern: '今陕西潼关', kind: 'pass', rank: 3, at: [110.28, 34.55], note: '' },
  { id: 'luoyang', name: '洛阳', modern: '今河南洛阳东', kind: 'city', rank: 1, at: [112.62, 34.72], note: '战后苻坚收集离散，比至洛阳，众十余万。' },
  { id: 'shimen', name: '石门', modern: '今河南荥阳北', kind: 'pass', rank: 3, at: [113.40, 34.93], note: '秦军“运漕万艘，自河入石门，达于汝、颍”。' },
  { id: 'ye', name: '邺', modern: '今河北临漳', kind: 'city', rank: 2, at: [114.38, 36.33], note: '太元九年，慕容垂起兵攻邺，复建燕国（后燕）。' },
  { id: 'xiangcheng', name: '项城', modern: '今河南沈丘', kind: 'city', rank: 1, at: [115.13, 33.43], note: '九月苻坚至项城。谚曰“坚不出项”，坚不从，留大军于项城，自引轻骑赴寿阳。' },
  { id: 'yingkou', name: '颍口', modern: '今安徽寿县正阳关附近', kind: 'ford', rank: 2, at: [116.52, 32.505], note: '苻融等兵三十万先至颍口。' },
  { id: 'shouyang', name: '寿阳', modern: '今安徽寿县', kind: 'city', rank: 1, at: [116.786, 32.578], note: '淝水之战发生地。' },
  { id: 'pengcheng', name: '彭城', modern: '今江苏徐州', kind: 'city', rank: 1, at: [117.19, 34.26], note: '“幽、冀之兵至于彭城”。' },
  { id: 'huaiyin', name: '淮阴', modern: '今江苏淮安', kind: 'city', rank: 2, at: [119.02, 33.545], note: '邗沟北口，晋军水道入淮之所。' },
  { id: 'guangling', name: '广陵', modern: '今江苏扬州', kind: 'city', rank: 1, at: [119.455, 32.395], side: 'jin', note: '谢玄以兖州刺史领广陵相，北府兵所在。' },
  { id: 'jingkou', name: '京口', modern: '今江苏镇江', kind: 'city', rank: 2, at: [119.45, 32.21], side: 'jin', note: '北府所在，北府兵由此得名。' },
  { id: 'jiankang', name: '建康', modern: '今江苏南京', kind: 'capital', rank: 1, at: [118.78, 32.05], side: 'jin', note: '东晋都城。谢安坐镇，“与玄围棋赌墅”。' },
  { id: 'hefei', name: '合肥', modern: '今安徽合肥', kind: 'city', rank: 2, at: [117.26, 31.86], note: '' },
  { id: 'xiangyang', name: '襄阳', modern: '今湖北襄阳', kind: 'city', rank: 1, at: [112.14, 32.02], side: 'qin', note: '太元四年为秦所取。八年五月桓冲率众十万攻之，不克而还。' },
  { id: 'jiangling', name: '江陵', modern: '今湖北荆州', kind: 'city', rank: 2, at: [112.19, 30.35], side: 'jin', note: '' },
  { id: 'shangming', name: '上明', modern: '今湖北松滋', kind: 'city', rank: 2, at: [111.78, 30.20], side: 'jin', approx: true, note: '荆州刺史桓冲驻地。冲遣精锐三千入卫京师，谢安却之。' },
  { id: 'yuncheng', name: '郧城', modern: '今湖北京山一带', kind: 'city', rank: 2, at: [113.30, 30.95], approx: true, note: '杜预曰“江夏云杜县东南有郧城”。十月，慕容垂拔郧城。' },
  { id: 'huaiyin_r', name: '中原', kind: 'region', rank: 2, at: [113.95, 34.30] },
  { id: 'guanzhong', name: '关中', kind: 'region', rank: 2, at: [108.95, 34.62] },
  { id: 'huaibei_r', name: '淮北', kind: 'region', rank: 2, at: [116.10, 33.45] },
  { id: 'huainan_r', name: '淮南', kind: 'region', rank: 2, at: [117.25, 32.30] },
  { id: 'jiangdong', name: '江东', kind: 'region', rank: 2, at: [119.85, 31.30] },
  { id: 'jingzhou', name: '荆州', kind: 'region', rank: 2, at: [112.90, 30.70] },
  { id: 'qin_polity', name: '前秦', kind: 'polity', rank: 1, at: [111.30, 35.55], side: 'qin' },
  { id: 'jin_polity', name: '东晋', kind: 'polity', rank: 1, at: [116.20, 30.75], side: 'jin' },
  // mountains
  { id: 'qinling', name: '秦岭', kind: 'mountain', rank: 1, at: [108.70, 33.86] },
  { id: 'huashan', name: '华山', kind: 'mountain', rank: 3, at: [110.08, 34.48] },
  { id: 'songshan', name: '嵩高', modern: '嵩山', kind: 'mountain', rank: 2, at: [113.03, 34.48] },
  { id: 'funiu', name: '伏牛山', kind: 'mountain', rank: 3, at: [111.95, 33.62] },
  { id: 'tongbai', name: '桐柏山', kind: 'mountain', rank: 3, at: [113.45, 32.42] },
  { id: 'dabie', name: '大别山', kind: 'mountain', rank: 2, at: [115.85, 31.20] },
  { id: 'taihang', name: '太行', kind: 'mountain', rank: 3, at: [113.55, 35.95] },
  { id: 'zhongshan', name: '钟山', kind: 'mountain', rank: 3, at: [118.85, 32.08], note: '会稽王道子以威仪鼓吹求助于钟山之神。' },
];
