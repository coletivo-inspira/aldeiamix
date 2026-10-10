import test from 'node:test';
import assert from 'node:assert/strict';
import {pastEditions,todaySP} from '../assets/editions.js';
test('latest completed event ignores future dates and preserves source',()=>{
 const input=[{id:'old',date:'2026-01-01'},{id:'future',date:'2027-01-01'},{id:'latest',date:'2026-10-10'}];
 assert.deepEqual(pastEditions(input,'2026-10-10').map(e=>e.id),['latest','old']);assert.equal(input[0].id,'old');
});
test('empty library remains empty and São Paulo date is ISO',()=>{assert.deepEqual(pastEditions([]),[]);assert.match(todaySP(),/^\d{4}-\d{2}-\d{2}$/);});
