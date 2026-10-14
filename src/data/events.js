import { T } from './episodes.js';

// Event markers pinned to the table. kind: battle | capture | death | speech | note |
// intercept | idiom (成语 seal) | go (谢安's game). `unit` pins the marker to a moving unit.

export const STRATEGIC_EVENTS = [
  { id: 'e_toubian', kind: 'idiom', at: 'changan', t0: T('prologue', 0.04), t1: T('prologue', 0.46), title: '投鞭断流', text: '苻坚：“以吾之众旅，投鞭于江，足断其流。”' },
  { id: 'e_xiangyang', kind: 'battle', at: 'xiangyang', t0: T('prologue', 0.46), t1: T('prologue', 0.8), title: '桓冲攻襄阳', text: '五月出师，七月退还上明' },
  { id: 'e_wuwu', kind: 'note', at: 'changan', t0: T('march', 0.0), t1: T('march', 0.34), title: '八月戊午', text: '苻融督张蚝、慕容垂等步骑二十五万为前锋' },
  { id: 'e_jiazi', kind: 'note', at: 'changan', t0: T('march', 0.32), t1: T('march', 0.7), title: '八月甲子', text: '苻坚发长安，戎卒六十余万，骑二十七万' },
  { id: 'e_xiang', kind: 'note', at: 'xiangcheng', t0: T('converge', 0.36), t1: T('converge', 0.8), title: '九月 坚至项城', text: '谚曰“坚不出项”，群臣劝坚停项，坚不从' },
  { id: 'e_xiean', kind: 'go', at: 'jiankang', t0: T('converge', 0.12), t1: T('converge', 0.5), title: '围棋赌墅', text: '谢安夷然答曰：“已别有旨。”遂命驾出游山墅，与谢玄围棋赌墅' },
  { id: 'e_huan3000', kind: 'intercept', at: [117.8, 31.1], t0: T('converge', 0.72), t1: T('converge', 0.95), title: '谢安却之', text: '“朝廷处分已定，兵甲无阙，西藩宜留以为防。”' },
  { id: 'e_news', kind: 'go', at: 'jiankang', t0: T('news', 0.24), t1: T('news', 0.78), title: '小儿辈遂已破贼', text: '谢安得驿书，围棋如故；既罢还内，过户限，不觉屐齿之折' },
  { id: 'e_murong', kind: 'note', at: 'yuncheng', t0: T('news', 0.18), t1: T('news', 0.55), title: '唯慕容垂一军独全', text: '诸军皆溃，惟慕容垂所将三万人独全，坚以千余骑赴之' },
  { id: 'e_changan', kind: 'note', at: 'changan', t0: T('news', 0.86), t1: T('epilogue', 0.2), title: '十二月 坚至长安', text: '哭阳平公融而后入，谥曰哀公' },
  { id: 'e_houyan', kind: 'note', at: 'ye', t0: T('epilogue', 0.45), t1: T('epilogue', 1.0), title: '后燕', text: '384年正月，慕容垂自称燕王，进围邺城' },
  { id: 'e_houqin', kind: 'note', at: [108.85, 34.75], t0: T('epilogue', 0.4), t1: T('epilogue', 1.0), title: '后秦', text: '384年，姚苌于渭北自称万年秦王' },
  { id: 'e_jin_north', kind: 'note', at: [115.6, 34.6], t0: T('epilogue', 0.55), t1: T('epilogue', 1.0), title: '东晋北伐', text: '谢玄收复兖、青、司、豫诸州，兵锋抵于黄河' },
  { id: 'e_xinping', kind: 'death', at: 'xinping', t0: T('epilogue', 0.74), t1: T('epilogue', 1.0), title: '385年八月', text: '苻坚为姚苌缢杀于新平佛寺' },
];

export const TACTICAL_EVENTS = [
  // 四
  { id: 'e_siege', kind: 'battle', at: 'shouyang', t0: T('shouyang', 0.5), t1: T('shouyang', 0.73), title: '攻寿阳', text: '苻融等兵临城下' },
  { id: 'e_fall', kind: 'capture', side: 'qin', at: 'shouyang', t0: T('shouyang', 0.72), t1: T('blockade', 0.15), title: '十月癸酉 寿阳陷落', text: '执平虏将军徐元喜、安丰太守王先' },
  { id: 'e_hubin', kind: 'note', at: 'xiashi', t0: T('shouyang', 0.82), t1: T('blockade', 0.2), title: '退保硖石', text: '胡彬闻寿阳陷，退保硖石，融进攻之' },
  // 五
  { id: 'e_palisade', kind: 'note', at: [117.088, 32.783], t0: T('blockade', 0.56), t1: T('envoy', 0.1), title: '栅淮以遏东兵', text: '梁成沿淮立栅，截断东来水道' },
  { id: 'e_afraid', kind: 'note', at: 'jincamp', t0: T('blockade', 0.66), t1: T('blockade', 1.0), title: '惮成不敢进', text: '晋军营于洛涧东二十五里' },
  // 六
  { id: 'e_sand', kind: 'note', at: 'xiashi', t0: T('envoy', 0.0), t1: T('envoy', 0.3), title: '粮尽 · 扬沙示敌', text: '胡彬“诈扬沙以示融军”' },
  { id: 'e_caught', kind: 'intercept', at: [116.94, 32.668], t0: T('envoy', 0.2), t1: T('envoy', 0.46), title: '使者为秦军所获', text: '“今贼盛，粮尽，恐不复见大军！”' },
  { id: 'e_tongue', kind: 'speech', unit: 'q_fujian', side: 'qin', t0: T('envoy', 0.42), t1: T('envoy', 0.7), title: '苻坚', text: '敢言吾至寿春者拔舌！' },
  { id: 'e_zhuxu', kind: 'speech', at: 'jincamp', side: 'qin', t0: T('envoy', 0.8), t1: T('envoy', 1.0), title: '朱序私谓谢石', text: '今乘诸军未集，宜速击之；若败其前锋，则彼已夺气，可遂破也。' },
  // 七
  { id: 'e_luojian', kind: 'battle', at: [117.128, 32.727], t0: T('raid', 0.38), t1: T('raid', 0.75), title: '洛涧之战', text: '刘牢之夜袭梁成垒' },
  { id: 'e_liang_dead', kind: 'death', at: [117.112, 32.736], t0: T('raid', 0.5), t1: T('raid', 0.95), title: '斩梁成、王咏', text: '晋书谢玄传：并斩成弟梁云' },
  { id: 'e_drown', kind: 'note', at: [117.083, 32.762], t0: T('raid', 0.7), t1: T('advance', 0.1), title: '争赴淮水', text: '士卒死者万五千人，执扬州刺史王显' },
  // 八
  { id: 'e_feinan', kind: 'battle', at: [116.838, 32.586], t0: T('advance', 0.5), t1: T('advance', 0.74), title: '张蚝败谢石于肥南', text: '谢玄、谢琰勒卒数万列阵以待，蚝乃退' },
  { id: 'e_caomu', kind: 'idiom', at: [116.808, 32.632], t0: T('advance', 0.62), t1: T('standoff', 0.06), title: '草木皆兵', text: '坚与融登城北望，见八公山上草木皆类人形' },
  { id: 'e_qingdi', kind: 'speech', at: [116.786, 32.586], side: 'qin', t0: T('advance', 0.74), t1: T('standoff', 0.04), title: '苻坚顾谓苻融', text: '此亦勍敌，何谓弱也！' },
  // 九
  { id: 'e_generals', kind: 'speech', at: [116.765, 32.582], side: 'qin', t0: T('standoff', 0.4), t1: T('standoff', 0.62), title: '秦诸将', text: '我众彼寡，不如遏之，使不得上，可以万全。' },
  { id: 'e_halfcross', kind: 'speech', unit: 'q_fujian', side: 'qin', t0: T('standoff', 0.6), t1: T('standoff', 0.98), title: '苻坚', text: '但引兵少却，使之半渡，我以铁骑蹙而杀之，蔑不胜矣！' },
  // 十
  { id: 'e_baile', kind: 'speech', unit: 'q_zhuxu', side: 'jin', t0: T('battle', 0.28), t1: T('battle', 0.58), title: '朱序在陈后大呼', text: '秦兵败矣！' },
  { id: 'e_battle', kind: 'battle', at: [116.786, 32.585], t0: T('battle', 0.36), t1: T('battle', 0.72), title: '决战淝水南', text: '谢石军拒张蚝，小退；谢玄、谢琰仍进' },
  { id: 'e_rong_dead', kind: 'death', at: [116.774, 32.584], t0: T('battle', 0.46), t1: T('rout', 0.3), title: '苻融战死', text: '驰骑略陈，欲以帅退者，马倒，为晋兵所杀' },
  { id: 'e_buliu', kind: 'note', at: [116.776, 32.5932], t0: T('battle', 0.62), t1: T('rout', 0.2), title: '肥水为之不流', text: '自相蹈藉投水死者不可胜计' },
  { id: 'e_arrow', kind: 'note', unit: 'q_fujian', side: 'qin', t0: T('battle', 0.62), t1: T('battle', 0.95), title: '苻坚中流矢', text: '' },
  // 十一
  { id: 'e_fengsheng', kind: 'idiom', at: [116.69, 32.585], t0: T('rout', 0.14), t1: T('rout', 0.8), title: '风声鹤唳', text: '其走者闻风声鹤唳，皆以为晋兵且至' },
  { id: 'e_defect', kind: 'note', at: [116.79, 32.6], t0: T('rout', 0.22), t1: T('rout', 0.5), title: '朱序等来奔', text: '朱序与张天锡、徐元喜皆归晋' },
  { id: 'e_yunmu', kind: 'capture', side: 'jin', at: [116.766, 32.574], t0: T('rout', 0.3), t1: T('rout', 0.72), title: '获云母车', text: '及仪服器械、军资珍宝畜产不可胜计' },
  { id: 'e_retake', kind: 'capture', side: 'jin', at: 'shouyang', t0: T('rout', 0.55), t1: T('rout', 1.0), title: '复取寿阳', text: '执淮南太守郭褒' },
  { id: 'e_qinggang', kind: 'note', at: 'qinggang', t0: T('rout', 0.6), t1: T('rout', 1.0), title: '追至青冈', text: '秦兵自相蹈藉而死者，蔽野塞川' },
];

/** Who holds 寿阳 at a given time (for the city banner). */
export function shouyangHolder(t) {
  if (t < T('shouyang', 0.72)) return 'jin';
  if (t < T('rout', 0.55)) return 'qin';
  return 'jin';
}
