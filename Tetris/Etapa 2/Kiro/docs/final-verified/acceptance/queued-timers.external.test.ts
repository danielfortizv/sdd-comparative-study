// Researcher acceptance: real hook/API, two already-queued manual operations.
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { act, cleanup, renderHook } from '@testing-library/react';
import { useGame } from '../../frontend/src/useGame';
import fixtures from './queue-timer-fixtures.json';

function deferred<T>() { let resolve!: (value:T)=>void; const promise=new Promise<T>(r=>{resolve=r;}); return {promise,resolve}; }
let requests:any[]=[];
async function flush() {await act(async()=>{for(let n=0;n<16;n++) await Promise.resolve();});}
async function complete(request:any,value:any) {
  request.done.resolve({ok:true,status:200,json:async()=>value}); await flush();
}
async function advance(ms:number) {await act(async()=>{vi.advanceTimersByTime(ms);});await flush();}
beforeEach(()=>{requests=[];vi.useFakeTimers();vi.stubGlobal('fetch',vi.fn((url:any)=>{
  const item={path:new URL(String(url),'http://localhost').pathname,done:deferred<Response>()};requests.push(item);return item.done.promise;
}));});
afterEach(()=>{cleanup();vi.clearAllTimers();vi.useRealTimers();vi.unstubAllGlobals();});

async function queued(caseName:'level_up'|'game_over') {
  const values=fixtures.cases[caseName];
  const hook=renderHook(()=>useGame());await flush();
  await complete(requests[0],values.initial);
  act(()=>{void hook.result.current.move('left');void hook.result.current.move('down');});await flush();
  expect(requests).toHaveLength(2); // second mutation really waits for first
  await complete(requests[1],values.first);
  expect(requests).toHaveLength(3);
  await advance(100);
  await complete(requests[2],values.second);
  return hook;
}

it('R4 queued completion replaces the timer created by its predecessor with fresh450ms',async()=>{
  const hook=await queued('level_up');
  expect(hook.result.current.state?.gravity_interval_ms).toBe(450);
  await advance(449);
  expect(requests.filter(r=>r.path.endsWith('/tick'))).toHaveLength(0);
  await advance(1);
  expect(requests.filter(r=>r.path.endsWith('/tick'))).toHaveLength(1);
});

it('R5 queued game-over completion cancels the timer created by its predecessor',async()=>{
  const hook=await queued('game_over');
  expect(hook.result.current.state?.status).toBe('game_over');
  await advance(1000);
  expect(requests.filter(r=>r.path.endsWith('/tick'))).toHaveLength(0);
});
