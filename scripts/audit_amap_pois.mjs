#!/usr/bin/env node
// Server-side audit only. Never expose the Web Service key to browser code.
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseEnv } from 'node:util';
import { scenicSpots } from '../frontend/src/constants/touristCatalog.js';

const root = fileURLToPath(new URL('../', import.meta.url));
const args = process.argv.slice(2);
if (args.includes('--help')) {
  console.log('Usage: node scripts/audit_amap_pois.mjs [--name 景点名] [--out 输出文件]\nKey: AMAP_WEB_SERVICE_KEY in process environment or backend/.env\nQueries Amap POI v3 in Binhu (320211); saves candidates, never edits live coordinates.');
  process.exit(0);
}
for (let i=0; i<args.length; i+=2) {
  if (!['--name','--out'].includes(args[i]) || !args[i+1]) {
    console.error('参数错误，请运行 --help。'); process.exit(2);
  }
}
const option = name => { const i=args.indexOf(name); return i<0 ? undefined : args[i+1]; };
let key = process.env.AMAP_WEB_SERVICE_KEY?.trim();
if (!key) {
  try { key = parseEnv(await fs.readFile(path.join(root,'backend/.env'),'utf8')).AMAP_WEB_SERVICE_KEY?.trim(); }
  catch (error) { if (error.code!=='ENOENT') { console.error('无法读取 backend/.env，请检查文件格式。'); process.exit(2); } }
}
if (!key) {
  console.error('缺少 AMAP_WEB_SERVICE_KEY（高德 Web 服务类型 Key）。未发送请求，也未修改坐标。');
  process.exit(2);
}
const names = option('--name') ? [option('--name')] : scenicSpots.map(spot=>spot.name);
const queries = [];
for (const name of names) {
  // Stay below the individual-account Web Service QPS limit (commonly 3 QPS).
  if (queries.length) await new Promise(resolve => setTimeout(resolve, 550));
  const url = new URL('https://restapi.amap.com/v3/place/text');
  url.search = new URLSearchParams({key,keywords:name,city:'320211',citylimit:'true',offset:'20',page:'1',extensions:'all'}).toString();
  try {
    const response = await fetch(url, {signal:AbortSignal.timeout(15000)});
    if (!response.ok) throw new Error('http');
    const data = await response.json();
    if (data.status !== '1') {
      // Do not print API response text or URL: either could contain credentials.
      console.error(`高德查询被拒绝，infocode=${String(data.infocode || '').replace(/[^0-9]/g,'')}。已停止，未修改坐标。`);
      process.exitCode = 1; break;
    }
    const pois = Array.isArray(data.pois) ? data.pois : [];
    queries.push({name,reviewStatus:'pending',totalCandidates:Number(data.count)||0,firstPageOnly:true,candidates:pois.map(poi=>({
      id:poi.id,name:poi.name,location:poi.location,coordinateSystem:'GCJ-02',
      address:poi.address,province:poi.pname,city:poi.cityname,district:poi.adname,
      adcode:poi.adcode,type:poi.type,typecode:poi.typecode,parent:poi.parent,
      sourceUrl:`https://ditu.amap.com/place/${encodeURIComponent(poi.id)}`,
    }))});
    console.log(`${name}：返回 ${pois.length} 个候选，待核对。`);
  } catch {
    console.error('高德查询失败或超时，已停止。不会打印含 Key 的请求地址。');
    process.exitCode = 1; break;
  }
}
if (queries.length) {
  const output = path.resolve(root,option('--out') || 'output/amap-poi-audit.json');
  await fs.mkdir(path.dirname(output),{recursive:true});
  await fs.writeFile(output,JSON.stringify({queriedAt:new Date().toISOString(),provider:'Amap POI v3',scope:'320211',complete:queries.length===names.length,queries},null,2));
  console.log('已保存候选清单。没有自动写入游客地图，也没有将首条结果视为核验通过。');
}
