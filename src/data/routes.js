import { T } from './episodes.js';

// Route arrows. `unit` + `key` draws the arrow along that unit's movement (key = index of the
// destination key in its track); otherwise `path` is a list of waypoints.
// style: advance | retreat | rout | naval | envoy | courier | plan
// hide: timeline time after which the arrow fades (default: end of the episode it finishes in)

export const STRATEGIC_ROUTES = [
  // 一 投鞭断流
  { id: 'r_huanchong', unit: 's_huanchong', key: 2, side: 'jin', label: '桓冲率众十万攻襄阳', hide: T('prologue', 0.7) },
  { id: 'r_huanchong_back', unit: 's_huanchong', key: 4, side: 'jin', style: 'retreat', label: '七月退还上明', width: 0.75 },
  { id: 'r_qinrelief', unit: 's_qinrelief', key: 2, side: 'qin', label: '苻叡、慕容垂步骑五万救襄阳', width: 0.85 },
  { id: 'r_murong0', unit: 's_murong', key: 2, side: 'qin', width: 0.7 },
  // 二 大举南征
  { id: 'r_fujian', unit: 's_fujian', key: 2, side: 'qin', width: 1.25, lateral: 14, label: '甲子 苻坚发长安 · 前后千里', labelAt: 0.3, hide: T('converge', 1) },
  { id: 'r_furong', unit: 's_furong', key: 3, side: 'qin', width: 1.05, lateral: -14, label: '戊午 苻融前锋步骑二十五万', labelAt: 0.62, hide: T('converge', 1) },
  // 三 水陆齐进
  { id: 'r_furong2', unit: 's_furong', key: 4, side: 'qin', width: 1.05, label: '先至颍口', labelAt: 0.82, hide: T('converge', 1) },
  { id: 'r_liangzhou', unit: 's_liangzhou', key: 2, side: 'qin', width: 0.7, label: '凉州之兵始达咸阳', labelAt: 0.3 },
  { id: 'r_shuhan', unit: 's_shuhan', key: 2, side: 'qin', style: 'naval', width: 0.75, label: '蜀、汉之兵方顺流而下', labelAt: 0.5 },
  { id: 'r_youji', unit: 's_youji', key: 2, side: 'qin', width: 0.8, label: '幽、冀之兵至于彭城', labelAt: 0.45 },
  {
    id: 'r_grain', side: 'qin', style: 'naval', width: 0.7, t0: T('converge', 0.08), t1: T('converge', 0.6),
    path: [[110.55, 34.63], [111.4, 34.82], [112.3, 34.92], [113.0, 34.9], 'shimen', [113.75, 34.6], [114.2, 34.18], [114.6, 33.72]],
    label: '运漕万艘 自河入石门', labelAt: 0.45,
  },
  { id: 'r_murong1', unit: 's_murong', key: 5, side: 'qin', width: 0.8, label: '慕容垂攻郧城', labelAt: 0.7 },
  { id: 'r_xieshi', unit: 's_xieshi', key: 3, side: 'jin', width: 1.05, label: '谢石率众北上', labelAt: 0.4 },
  { id: 'r_xiexuan', unit: 's_xiexuan', key: 2, side: 'jin', width: 1.05, label: '谢玄自广陵西进', labelAt: 0.35 },
  { id: 'r_hubin', unit: 's_hubin', key: 2, side: 'jin', style: 'naval', width: 0.7, label: '胡彬水军五千援寿阳', labelAt: 0.55 },
  {
    id: 'r_huan3000', side: 'jin', style: 'plan', width: 0.7, t0: T('converge', 0.45), t1: T('converge', 0.75),
    path: ['shangming', [112.6, 30.4], [113.6, 30.15], [114.6, 30.45], [115.9, 29.95], [116.9, 30.45], [117.8, 31.1]],
    label: '桓冲遣三千入卫 谢安却之', labelAt: 0.5,
  },
  // 十二 小儿破贼
  {
    id: 'r_courier', side: 'jin', color: 'gold', style: 'courier', width: 0.8, t0: T('news', 0.02), t1: T('news', 0.28),
    path: ['shouyang', [117.3, 32.45], [117.9, 32.3], [118.4, 32.15], 'jiankang'], label: '驿书报捷', labelAt: 0.5,
  },
  { id: 'r_fujian_back', unit: 's_fujian', key: 5, side: 'qin', style: 'retreat', width: 1.0, label: '收集离散 至洛阳众十余万', labelAt: 0.5 },
  { id: 'r_fujian_back2', unit: 's_fujian', key: 6, side: 'qin', style: 'retreat', width: 1.0, label: '十二月 至长安', labelAt: 0.5, hide: T('epilogue', 0.4) },
  { id: 'r_xieshi_back', unit: 's_xieshi', key: 7, side: 'jin', style: 'retreat', width: 0.8, label: '谢石等班师建康', labelAt: 0.5 },
  { id: 'r_murong_back', unit: 's_murong', key: 7, side: 'qin', style: 'retreat', width: 0.8, label: '唯慕容垂三万人独全', labelAt: 0.5 },
  // 十三 南北再分
  { id: 'r_murong_yan', unit: 's_murong', key: 9, color: 'ink', side: 'qin', width: 0.95, label: '慕容垂复燕（后燕）', labelAt: 0.6 },
  { id: 'r_yaochang', unit: 's_yaochang', key: 3, color: 'ink', side: 'qin', width: 0.85, label: '姚苌自立（后秦）', labelAt: 0.5 },
  { id: 'r_xiexuan_north', unit: 's_xiexuan', key: 7, side: 'jin', width: 1.1, label: '谢玄北伐 收复兖、青、司、豫', labelAt: 0.55 },
  { id: 'r_fujian_end', unit: 's_fujian', key: 8, side: 'qin', style: 'retreat', width: 0.8, label: '385年 苻坚死于新平', labelAt: 0.5 },
];

export const TACTICAL_ROUTES = [
  // 四 寿阳失守
  { id: 't_rong', unit: 'q_rong', key: 2, side: 'qin', width: 1.2, label: '苻融等渡淮 进攻寿阳', labelAt: 0.4, hide: T('blockade', 0.25) },
  { id: 't_hubin', unit: 'j_hubin', key: 1, side: 'jin', style: 'naval', width: 0.8, label: '胡彬水军援寿阳', labelAt: 0.4 },
  { id: 't_hubin_back', unit: 'j_hubin', key: 3, side: 'jin', style: 'retreat', width: 0.8, label: '闻寿阳陷 退保硖石', labelAt: 0.55, hide: T('envoy', 1) },
  { id: 't_xiashi', unit: 'q_xiashi', key: 2, side: 'qin', width: 0.8, label: '苻融进攻硖石', labelAt: 0.6, hide: T('envoy', 1) },
  // 五 栅淮遏东
  { id: 't_liang', unit: 'q_liang', key: 2, side: 'qin', width: 1.1, label: '梁成率众五万屯洛涧', labelAt: 0.5 },
  { id: 't_jin_arrive', unit: 'j_xieshi', key: 2, side: 'jin', width: 1.0, label: '晋军进至洛涧东二十五里', labelAt: 0.1, hide: T('envoy', 0.3) },
  { id: 't_navy_arrive', unit: 'j_navy', key: 2, side: 'jin', style: 'naval', width: 0.8, label: '舟师受阻于淮栅', labelAt: 0.2 },
  // 六 轻骑兼道
  {
    id: 't_hubin_msg', side: 'jin', color: 'gold', style: 'courier', width: 0.7, t0: T('envoy', 0.04), t1: T('envoy', 0.22),
    path: ['xiashi', [116.80, 32.715], [116.88, 32.69], [116.94, 32.668]], label: '胡彬潜遣使告急', labelAt: 0.35,
  },
  {
    id: 't_rong_msg', side: 'qin', color: 'gold', style: 'courier', width: 0.7, t0: T('envoy', 0.12), t1: T('envoy', 0.3),
    path: ['shouyang', [116.70, 32.556], [116.60, 32.53], [116.53, 32.52], [116.47, 32.58], [116.43, 32.62]], label: '苻融驰使：贼少易擒', labelAt: 0.55,
  },
  { id: 't_fujian', unit: 'q_fujian', key: 2, side: 'qin', width: 1.0, label: '苻坚轻骑八千兼道赴寿阳', labelAt: 0.3, hide: T('advance', 0.3) },
  { id: 't_zhuxu', unit: 'q_zhuxu', key: 2, side: 'qin', color: 'gold', style: 'envoy', width: 0.7, label: '朱序往说谢石', labelAt: 0.5 },
  // 七 洛涧夜袭
  { id: 't_liu', unit: 'j_liu', key: 4, side: 'jin', width: 1.05, label: '刘牢之精兵五千奔袭洛涧', labelAt: 0.35 },
  { id: 't_liu_cross', unit: 'j_liu', key: 5, side: 'jin', width: 1.1, label: '直前渡水', labelAt: 0.5 },
  { id: 't_liu_det', unit: 'j_liu_det', key: 2, side: 'jin', width: 0.75, label: '分兵断其归津', labelAt: 0.6 },
  { id: 't_liang_rout', unit: 'q_liang', key: 6, side: 'qin', style: 'rout', width: 1.0, label: '步骑崩溃 争赴淮水', labelAt: 0.75 },
  // 八 草木皆兵
  { id: 't_advance', unit: 'j_xieshi', key: 4, side: 'jin', width: 1.3, label: '谢石等诸军水陆继进', labelAt: 0.45 },
  { id: 't_navy', unit: 'j_navy', key: 4, side: 'jin', style: 'naval', width: 0.85, label: '舟师溯淮而上', labelAt: 0.35 },
  { id: 't_zhanghao', unit: 'q_zhanghao', key: 3, side: 'qin', width: 0.8, label: '张蚝败谢石于肥南', labelAt: 0.4 },
  { id: 't_lift_siege', unit: 'q_xiashi', key: 4, side: 'qin', style: 'retreat', width: 0.75, label: '秦军撤围 回守淝水', labelAt: 0.4 },
  // 九 临淝对峙
  {
    id: 't_xuan_envoy', side: 'jin', color: 'gold', style: 'envoy', width: 0.6, t0: T('standoff', 0.12), t1: T('standoff', 0.4),
    path: [[116.794, 32.6012], [116.789, 32.594], [116.781, 32.5855]], label: '谢玄遣使请移陈少却', labelAt: 0.6, hide: T('standoff', 0.8),
  },
  {
    id: 't_plan', side: 'qin', style: 'plan', width: 0.9, t0: T('standoff', 0.55), t1: T('standoff', 0.9),
    path: [[116.756, 32.583], [116.766, 32.588], [116.778, 32.591], [116.79, 32.5925]], label: '苻坚之计：半渡而击', labelAt: 0.5, hide: T('battle', 0.35),
  },
  // 十 淝水决战
  {
    id: 't_pullback_w', side: 'qin', style: 'retreat', width: 0.7, t0: T('battle', 0.04), t1: T('battle', 0.26),
    path: [[116.770, 32.5895], [116.768, 32.583], [116.766, 32.577]], label: '麾兵使却', labelAt: 0.5, hide: T('battle', 0.6),
  },
  {
    id: 't_pullback_e', side: 'qin', style: 'retreat', width: 0.7, t0: T('battle', 0.05), t1: T('battle', 0.27),
    path: [[116.796, 32.5878], [116.795, 32.581], [116.794, 32.575]], hide: T('battle', 0.6),
  },
  { id: 't_xuan_cross', unit: 'j_xiexuan', key: 6, side: 'jin', width: 1.2, label: '精锐八千涉渡淝水', labelAt: 0.75 },
  { id: 't_yan_cross', unit: 'j_xieyan', key: 6, side: 'jin', width: 1.0 },
  { id: 't_yi_cross', unit: 'j_huanyi', key: 6, side: 'jin', width: 1.0 },
  { id: 't_rong_rout', unit: 'q_rong', key: 10, side: 'qin', style: 'rout', width: 1.2, label: '秦兵遂退 不可复止', labelAt: 0.25, hide: T('rout', 1) },
  { id: 't_zhang_rout', unit: 'q_zhanghao', key: 8, side: 'qin', style: 'rout', width: 0.9, hide: T('rout', 1) },
  // 十一 风声鹤唳
  { id: 't_pursuit', unit: 'j_xiexuan', key: 8, side: 'jin', width: 1.2, label: '乘胜追击 至于青冈', labelAt: 0.7 },
  { id: 't_cav_rout', unit: 'q_cav', key: 6, side: 'qin', style: 'rout', width: 0.9, label: '溃兵北渡淮水', labelAt: 0.75 },
  { id: 't_fujian_flee', unit: 'q_fujian_alone', key: 2, side: 'qin', style: 'retreat', width: 0.75, label: '苻坚中流矢 单骑走淮北', labelAt: 0.55 },
  { id: 't_retake', unit: 'j_xieshi', key: 9, side: 'jin', width: 0.9, label: '复取寿阳 执郭褒', labelAt: 0.6 },
];
