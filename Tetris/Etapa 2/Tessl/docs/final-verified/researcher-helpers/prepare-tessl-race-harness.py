"""Prepare researcher-owned external UI acceptance; never edit generated source."""
from pathlib import Path

root = Path(__file__).resolve().parent.parent / 'Tessl'
out = root / 'docs' / 'acceptance'
out.mkdir(exist_ok=True)
config = '''import {fileURLToPath} from 'node:url';
import { defineConfig } from '../../frontend/node_modules/vitest/config.js';
import react from '../../frontend/node_modules/@vitejs/plugin-react/dist/index.js';
export default defineConfig({root:fileURLToPath(new URL('.',import.meta.url)),resolve:{alias:[{find:/^react(?=\\/|$)/,replacement:fileURLToPath(new URL('../../frontend/node_modules/react',import.meta.url))},{find:/^react-dom(?=\\/|$)/,replacement:fileURLToPath(new URL('../../frontend/node_modules/react-dom',import.meta.url))}]},plugins:[react()],test:{environment:'jsdom',globals:true,include:['races.external.test.tsx'],coverage:{enabled:false}}});
'''
# Resolve the installed package's supported entrypoint through its package metadata.
import json
vp = json.loads((root/'frontend/node_modules/vitest/package.json').read_text())
entry = vp['exports']['./config']['default']
config = config.replace('../../frontend/node_modules/vitest/config.js', '../../frontend/node_modules/vitest/'+entry.removeprefix('./'))
(out/'vitest.external.config.mjs').write_text(config,encoding='utf-8')
test = r'''import React, { StrictMode } from 'react';
import { act, cleanup, fireEvent, render, screen } from '../../frontend/node_modules/@testing-library/react/dist/index.js';
import { afterEach, beforeEach, expect, test, vi } from '../../frontend/node_modules/vitest/dist/index.js';
import App from '../../frontend/src/App';

function deferred<T=any>() { let resolve!:(v:T)=>void; let reject!:(e:any)=>void; const promise=new Promise<T>((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject}; }
function state(id='old', extra:any={}) {return {id,board:Array.from({length:20},()=>Array(10).fill(null)),active_piece:{type:'O',origin:[0,3],cells:[[0,3],[0,4],[1,3],[1,4]]},status:'playing',score:0,total_lines:0,level:1,gravity_interval_ms:500,next_piece:'T',hold_piece:null,can_hold:true,...extra};}
const response=(s:any)=>({ok:true,json:()=>Promise.resolve(s)});
let calls:any[]=[];
let creates:any[]=[];
let mutations:any[]=[];
async function flush(){await act(async()=>{for(let n=0;n<12;n++)await Promise.resolve();});}
beforeEach(()=>{
 vi.useFakeTimers(); calls=[];creates=[];mutations=[];
 vi.stubGlobal('fetch',vi.fn((url:any,init:any)=>{
  calls.push({url:String(url),method:init?.method});
  const pending=deferred();
  if(String(url)==='/api/games')creates.push(pending);else mutations.push({url:String(url),...pending});
  return pending.promise;
 }));
 vi.spyOn(console,'error').mockImplementation(()=>{});
});
afterEach(()=>{cleanup();vi.useRealTimers();vi.unstubAllGlobals();vi.restoreAllMocks();});
async function start(){render(<App/>);await flush();creates[0].resolve(response(state()));await flush();}
async function restart(){fireEvent.click(screen.getByRole('button',{name:'Start New Game'}));await flush();creates.at(-1).resolve(response(state('new')));await flush();}
const hold=()=>fireEvent.click(screen.getByRole('button',{name:'Hold Piece'}));
const move=()=>fireEvent.keyDown(window,{key:'ArrowLeft'});
const tickCount=()=>calls.filter(x=>x.url.endsWith('/tick')).length;

test('S2-18 restart rejects old JSON and leaves new Hold usable',async()=>{
 await start();hold();await flush();const oldJson=deferred();mutations[0].resolve({ok:true,json:()=>oldJson.promise});await flush();
 await restart();hold();await flush();expect(mutations[1].url).toBe('/api/games/new/hold');
 oldJson.resolve(state('old',{score:999}));await flush();expect(screen.queryByText('999')).toBeNull();
 mutations[1].resolve(response(state('new',{hold_piece:'O',can_hold:false})));await flush();
 expect(screen.getByRole('button',{name:'Hold Piece'}).disabled).toBe(true);
});
test('S2-18 old rejection/finally cannot drain new queue or schedule a timer',async()=>{
 await start();hold();await flush();const old=mutations[0];await restart();hold();move();await flush();expect(mutations.length).toBe(2);
 old.reject(new Error('old lifecycle failure'));await flush();await act(async()=>{vi.advanceTimersByTime(1000)});await flush();expect(tickCount()).toBe(0);
 mutations[1].resolve(response(state('new',{can_hold:false})));await flush();expect(mutations[2].url).toBe('/api/games/new/move');
 mutations[2].resolve(response(state('new',{gravity_interval_ms:450,level:2})));await flush();
 await act(async()=>{vi.advanceTimersByTime(449)});await flush();expect(tickCount()).toBe(0);
 await act(async()=>{vi.advanceTimersByTime(1)});await flush();expect(tickCount()).toBe(1);
});
test('S2-18 two queued manual actions use 450ms after last completion',async()=>{
 await start();move();move();await flush();expect(mutations.length).toBe(1);
 mutations[0].resolve(response(state('old',{level:2,total_lines:10,gravity_interval_ms:450})));await flush();expect(mutations.length).toBe(2);
 await act(async()=>{vi.advanceTimersByTime(600)});await flush();expect(tickCount()).toBe(0);
 mutations[1].resolve(response(state('old',{level:2,total_lines:10,gravity_interval_ms:450})));await flush();
 await act(async()=>{vi.advanceTimersByTime(449)});await flush();expect(tickCount()).toBe(0);
 await act(async()=>{vi.advanceTimersByTime(1)});await flush();expect(tickCount()).toBe(1);
});
test('S2-18 queued game over leaves no gravity timeout',async()=>{
 await start();move();move();await flush();mutations[0].resolve(response(state()));await flush();
 mutations[1].resolve(response(state('old',{status:'game_over',can_hold:false})));await flush();
 expect(vi.getTimerCount()).toBe(0);await act(async()=>{vi.advanceTimersByTime(2000)});await flush();expect(tickCount()).toBe(0);
});
test('S2-17 StrictMode initial game accepts keyboard and Hold',async()=>{
 render(<StrictMode><App/></StrictMode>);await flush();expect(creates.length).toBe(2);
 creates[1].resolve(response(state('strict')));await flush();hold();await flush();expect(mutations.length).toBe(1);
 expect(mutations[0].url).toBe('/api/games/strict/hold');mutations[0].resolve(response(state('strict',{can_hold:false})));await flush();
 move();await flush();expect(mutations[1].url).toBe('/api/games/strict/move');
});
test('S2-18 late StrictMode first creation cannot overwrite a restarted game',async()=>{
 render(<StrictMode><App/></StrictMode>);await flush();creates[1].resolve(response(state('strict')));await flush();await restart();
 creates[0].resolve(response(state('obsolete',{score:999})));await flush();expect(screen.queryByText('obsolete')).toBeNull();expect(screen.queryByText('999')).toBeNull();
});
'''
(out/'races.external.test.tsx').write_text(test,encoding='utf-8')
print(json.dumps({'prepared':str(out),'tests':6,'source_edited':False}))
