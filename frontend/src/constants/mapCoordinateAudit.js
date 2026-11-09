import { SPOT_COORDS } from './mapSpots.js';
import { wgs84ToGcj02 } from './narration.js';

// These are map reference positions, not surveyed entrances or navigable stops.
// WGS84 records must be converted exactly once for the existing GCJ-02 tiles.
const mapReferences = {
  灵山大佛: { lat:31.430194, lng:120.096477, crs:'GCJ-02', source:'高德 POI B01FE00DQ6', url:'https://ditu.amap.com/place/B01FE00DQ6', meaning:'景点 POI 参考点；非入口' },
  九龙灌浴: { lat:31.424601, lng:120.099984, crs:'GCJ-02', source:'高德 POI B01FE199JX', url:'https://ditu.amap.com/place/B01FE199JX', meaning:'景区内景点 POI 参考点；非入口' },
  降魔浮雕: { lat:31.425559, lng:120.099569, crs:'GCJ-02', source:'高德 POI B01FE199CS', url:'https://ditu.amap.com/place/B01FE199CS', meaning:'景区内景点 POI 参考点；非入口' },
  阿育王柱: { lat:31.426188, lng:120.099261, crs:'GCJ-02', source:'高德 POI B01FE1997R', url:'https://ditu.amap.com/place/B01FE1997R', meaning:'景区内景点 POI 参考点；非入口' },
  百子戏弥勒: { lat:31.427190, lng:120.098844, crs:'GCJ-02', source:'高德 POI B01FE199JN', url:'https://ditu.amap.com/place/B01FE199JN', meaning:'景区内景点 POI 参考点；非入口' },
  灵山梵宫: { lat:31.428218, lng:120.102420, crs:'GCJ-02', source:'高德 POI B01FE176MH', url:'https://ditu.amap.com/place/B01FE176MH', meaning:'景区内建筑 POI 参考点；非入口' },
  五印坛城: { lat:31.424676, lng:120.103054, crs:'GCJ-02', source:'高德 POI B01FE197GZ', url:'https://ditu.amap.com/place/B01FE197GZ', meaning:'景区内景点 POI 参考点；非入口' },
  曼飞龙塔: { lat:31.426070, lng:120.104609, crs:'GCJ-02', source:'高德 POI B01FE199KC', url:'https://ditu.amap.com/place/B01FE199KC', meaning:'景区内景点 POI 参考点；非入口' },
  无尽意斋: { lat:31.428729, lng:120.096710, crs:'GCJ-02', source:'高德 POI B01FE199EK', url:'https://ditu.amap.com/place/B01FE199EK', meaning:'景区内景点 POI 参考点；非入口' },
  菩提大道: { lat:31.423182, lng:120.101143, crs:'GCJ-02', source:'高德 POI B01FE199LG', url:'https://ditu.amap.com/place/B01FE199LG', meaning:'景区内步道 POI 参考点；非入口' },
  灵山大照壁: { lat:31.421388, lng:120.102499, crs:'GCJ-02', source:'高德 POI B0FFF75IDE', url:'https://ditu.amap.com/place/B0FFF75IDE', meaning:'景区内景点 POI 参考点；非入口' },
  佛足坛: { lat:31.422725, lng:120.101497, crs:'GCJ-02', source:'高德 POI B01FE199E0', url:'https://ditu.amap.com/place/B01FE199E0', meaning:'景区内景点 POI 参考点；非入口' },
  五智门: { lat:31.423055, lng:120.101292, crs:'GCJ-02', source:'高德 POI B01FE197RG', url:'https://ditu.amap.com/place/B01FE197RG', meaning:'景区内景点 POI 参考点；非入口' },
  五明桥: { lat:31.421749, lng:120.102248, crs:'GCJ-02', source:'高德 POI B01FE197VB', url:'https://ditu.amap.com/place/B01FE197VB', meaning:'景区内景点 POI 参考点；非入口' },
  祥符禅寺: { lat:31.427949, lng:120.098012, crs:'GCJ-02', source:'高德 POI B0FFF0EWZU', url:'https://ditu.amap.com/place/B0FFF0EWZU', meaning:'景区内寺庙 POI 参考点；非入口' },
};
const otherScenicSources = {
  五灯湖:'https://en.wuxi.gov.cn/2018-02/09/c_664207.htm',
  拈花广场:'https://wxsfj.wuxi.gov.cn/wxpf/doc/2025/11/03/4675488.shtml',
  香月花街:'https://www.chinalingshan.com/member/scenic/2',
  梵天花海:'https://www.wuxi.gov.cn/doc/2024/06/08/4326534.shtml',
  鹿鸣谷:'https://www.chinalingshan.com/member/scenic/2',
  拈花堂:'https://wuxi.marathon.org.cn/post-94.html',
};
export const MAP_COORDINATE_AUDIT = Object.fromEntries(Object.keys(SPOT_COORDS).map(name => {
  const reference = mapReferences[name];
  if (reference) {
    const converted = reference.crs === 'WGS84' ? wgs84ToGcj02(reference.lat,reference.lng) : reference;
    return [name, { coordinateStatus:'reference', lat:converted.lat, lng:converted.lng, source:reference.source, sourcePoiId:reference.source.match(/[A-Z0-9]{10}/)?.[0], sourceUrl:reference.url, sourceCoordinate:{lat:reference.lat,lng:reference.lng,crs:reference.crs}, coordinateNote:reference.meaning, checkedAt:'2026-11-09' }];
  }
  if (otherScenicSources[name]) return [name, {coordinateStatus:'other-scenic', coordinateNote:'拈花湾项目；不放置在灵山胜境内部', sourceUrl:otherScenicSources[name], checkedAt:'2026-11-09'}];
  return [name, {coordinateStatus:'pending', coordinateNote:'缺少可核对的同名坐标；暂不落点', checkedAt:'2026-11-09'}];
}));

// Exact route landmarks returned by Amap but not part of the original scenic catalog.
// Kept separate so coordinate-audit counts still describe the 22 catalog entries.
export const MAP_ROUTE_STOPS = [
  { name:'佛手广场', lat:31.427066, lng:120.098781, poiId:'B0FFG6ROHI', zone:'qianshan', type:'foxiang', desc:'灵山胜境内的佛手广场', sourceUrl:'https://ditu.amap.com/place/B0FFG6ROHI' },
  { name:'杏坛广场', lat:31.428946, lng:120.097377, poiId:'B01FE1997N', zone:'qianshan', type:'wenhua', desc:'灵山胜境西北侧杏坛广场', sourceUrl:'https://ditu.amap.com/place/B01FE1997N' },
  { name:'三圣殿', lat:31.424395, lng:120.096300, poiId:'B0FFHX4MOR', zone:'qianshan', type:'simiao', desc:'灵山胜境内三圣殿', sourceUrl:'https://ditu.amap.com/place/B0FFHX4MOR' },
  { name:'梵宫广场', lat:31.427205, lng:120.102651, poiId:'B01FE19VVI', zone:'houshan', type:'wenhua', desc:'灵山梵宫前广场', sourceUrl:'https://ditu.amap.com/place/B01FE19VVI' },
  { name:'天下第一掌', lat:31.426957, lng:120.098366, poiId:'B01FE197GT', zone:'qianshan', type:'foxiang', desc:'灵山胜境内天下第一掌', sourceUrl:'https://ditu.amap.com/place/B01FE197GT' },
].map(stop => ({ ...stop, emoji:'', heat:0, coordinateStatus:'reference', source:`高德 POI ${stop.poiId}`, sourcePoiId:stop.poiId, sourceCoordinate:{lat:stop.lat,lng:stop.lng,crs:'GCJ-02'}, coordinateNote:'路线站点 POI 参考点；不代表入口', checkedAt:'2026-11-09' }));
