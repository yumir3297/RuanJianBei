import { test } from 'node:test';
import assert from 'node:assert/strict';
import { groupMapPoints } from '../src/utils/mapMarkers.js';

const points = [
  {name:'甲',x:0,y:0,heat:1,lat:31,lng:120},
  {name:'乙',x:20,y:10,heat:2,lat:32,lng:121},
  {name:'丙',x:200,y:0,heat:3,lat:33,lng:122},
];
test('nearby markers cluster without losing or mutating their geographic data', () => {
  const before = structuredClone(points);
  const groups = groupMapPoints(points);
  assert.deepEqual(groups.map(g=>g.length).sort(),[1,2]);
  assert.deepEqual(groups.flat().map(p=>p.name).sort(),points.map(p=>p.name).sort());
  assert.deepEqual(points,before);
  assert.deepEqual(groups.find(g=>g.length===2)[0],points[1]);
});
test('the selected place remains the representative of its nearby group', () => {
  const selected = groupMapPoints(points,44,'甲').find(g=>g.some(p=>p.name==='甲'));
  assert.equal(selected[0].name,'甲');
  assert.equal(selected[0].lat,31);
});
test('zoomed-apart places and empty input need no clusters', () => {
  assert.equal(groupMapPoints(points.map(p=>({...p,x:p.x*10,y:p.y*10}))).length,3);
  assert.deepEqual(groupMapPoints([]),[]);
});
