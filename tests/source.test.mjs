import test from 'node:test';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';
test('web demo uses the exact desktop policy and runtime',async()=>{for(const name of ['policy.mjs','runtime.mjs'])assert.equal(await readFile('core/'+name,'utf8'),await readFile('dist/lib/'+name,'utf8'))});
